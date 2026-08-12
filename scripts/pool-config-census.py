#!/usr/bin/env python3
"""Per-block configuration census: legal-boundary hugging and tile-software signatures.

Roadmap Phase 14.3 (configuration at the legal boundary) and Phase 14.4
(mining-software census by tile-pattern fingerprint), internal research
build, read-only over frozen datasets plus a clearly labeled live section.

Framing, binding for every number below: everything measured here is legal
on-chain behavior. Sitting at a constraint boundary (minimum rank, minimum
or maximum k) is an operator configuration choice and is reported as
stated, never as a violation. Tile patterns identify mining SOFTWARE, not
honesty: DS-002's MODEL_SHAPED_CUSTOM matches committed genuine published
weights from non-official software, so a non-official signature never
implies synthetic work. Conversely MINER_* environment overrides let custom
software emit the official pattern, so the official-signature share is an
upper bound on unmodified-stack share.

Definitions:
  - Boundary (14.3): the v1.3.0 rank-penalty softfork (activation height
    96,251) made rank 128 the legal minimum and k >= 16*rank; at rank 128
    the minimum k is 2,048 and the maximum is 4*rank^2 = 65,536 (OBS-001).
    "Boundary-hugging" = blocks at exactly (rank 128, k 2,048), the
    cheapest legal configuration. Before 96,251 that pair is just one
    configuration among many; the per-bin series is reported over the whole
    span for context, the "legal minimum" reading applies post-fork only.
  - Signature (14.4): (tileH, tileW, rank, byteExact) where byteExact means
    the certificate's rows/cols patterns equal the official sm90 wgmma
    fragment bytes (certclass.OfficialRowsPattern/OfficialColsPattern).
    tileH/tileW are products of pattern lengths, so distinct byte patterns
    can share a geometry; the byteExact split separates them where DS-001
    records it. The official signature is tile (2,64), byte-exact, rank in
    {64, 128} (the only ranks compiled in the published kernels).

Unit of analysis throughout: blocks (one certificate per block). The
genesis EMPTY certificate is excluded from every denominator.

Sections 1-4 read only frozen committed datasets and are byte-reproducible.
Section 5 (optional) reads the live keshi API and is NON-FROZEN: it moves
with the chain tip and is labeled as such in the output.

Env:
  KESHI_DS001_DIR   DS-001 dataset dir (default: the committed copy)
  KESHI_DS003_DIR   DS-003 dataset dir (default: the committed copy)
  KESHI_API         API base (default http://127.0.0.1:8081/v1)
  Scan dataset dirs for the matched-block cross-reference are passed
  positionally (default: the three committed weight-scan dirs).

Usage: pool-config-census.py [--bin 1000] [--skip-live] [--live-from H]
                             [--tail 1000] [--json PATH] [scan dirs...]
"""

import argparse
import gzip
import json
import os
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASETS = HERE.parent / "docs" / "research" / "datasets"
DS001 = Path(os.environ.get("KESHI_DS001_DIR", str(DATASETS / "DS-001-classification-v1")))
DS003 = Path(os.environ.get("KESHI_DS003_DIR", str(DATASETS / "DS-003-network-state-v1")))
API = os.environ.get("KESHI_API", "http://127.0.0.1:8081/v1")
DEFAULT_SCAN_DIRS = [
    str(DATASETS / "DS-002-weight-scan-v1"),
    str(DATASETS / "DS-002b-gemma-v1"),
    str(DATASETS / "DS-002b-o-tp48-v1"),
]

RANK_PENALTY_FORK = 96_251
BOUNDARY_RANK, BOUNDARY_K = 128, 2_048   # legal minimum post-fork: k >= 16*rank
MAX_K_AT_128 = 65_536                    # legal maximum at rank 128: k <= 4*rank^2 (OBS-001)
OFFICIAL_TILE = (2, 64)
OFFICIAL_RANKS = (64, 128)
OFFICIAL_ROWS_HEX = "070100000000"       # certclass.OfficialRowsPattern
OFFICIAL_COLS_HEX = "0001031f0000"       # certclass.OfficialColsPattern
# h68,332 matched Gemma o_proj L053 byte-exactly but is recorded only as a
# dated DS-002b erratum in the roadmap (datasets are append-only); it is in
# no committed results file, so it is counted on its own line, never in the
# dataset-derived totals.
ERRATUM_MATCH_HEIGHTS = {68_332}

ERAS = [
    ("pre-moe", 1, 71_934),
    ("moe-window", 71_935, 91_629),
    ("dense-only", 91_630, 96_250),
    ("rank-penalty", 96_251, None),
]

REPORT = {}  # filled as sections run; dumped by --json


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def share(num: int, den: int) -> str:
    return f"{num}/{den} ({num / den:.1%})" if den else f"{num}/0 (n/a)"


def is_official_sig(sig) -> bool:
    tile_h, tile_w, rank, exact = sig
    return (tile_h, tile_w) == OFFICIAL_TILE and exact and rank in OFFICIAL_RANKS


def sig_name(sig) -> str:
    tile_h, tile_w, rank, exact = sig
    pat = "exact" if exact else "other-bytes"
    return f"({tile_h:>2},{tile_w:>3}) r{rank:<4} {pat}"


# ---------------------------------------------------------------- DS-001 ----

def load_ds001():
    path = DS001 / "blocks.jsonl.gz"
    if not path.exists():
        fail(f"DS-001 not found at {path} (set KESHI_DS001_DIR)")
    rows, empty = [], 0
    heights = set()
    with gzip.open(path, "rt") as f:
        for line in f:
            r = json.loads(line)
            heights.add(r["height"])
            if r["class"] == "EMPTY":
                empty += 1
                continue
            t1 = r["t1"]
            rows.append({
                "height": r["height"],
                "pool": r["pool"],
                "class": r["class"],
                "rank": r["rank"],
                "k": r["k"],
                "tileH": r["tileH"],
                "tileW": r["tileW"],
                "exact": t1["rowsExact"] and t1["colsExact"],
            })
    lo, hi = min(heights), max(heights)
    if len(heights) != hi - lo + 1:
        fail(f"DS-001 height span {lo}..{hi} is not contiguous ({len(heights)} rows)")
    print(f"[frozen DS-001] {len(heights)} blocks, heights {lo}..{hi}, "
          f"{empty} EMPTY excluded, {len(rows)} in denominators")
    REPORT["ds001"] = {"blocks": len(heights), "minHeight": lo, "maxHeight": hi,
                       "emptyExcluded": empty, "denominator": len(rows)}
    return rows, hi


def per_bin_table(rows, bin_width):
    print(f"\n== 14.3 + 14.4 per-{bin_width}-block bin series [frozen DS-001] ==")
    print("share definitions: at-boundary = rank 128 and k 2,048 exactly; "
          "official-sig = tile (2,64) byte-exact, rank 64 or 128.")
    print("denominator per row: non-EMPTY blocks in the bin.")
    bins = {}
    for r in rows:
        bins.setdefault(r["height"] // bin_width, []).append(r)
    out = []
    print(f"{'bin':>13} {'blocks':>6} {'at(128,2048)':>12} {'share':>6} "
          f"{'official-sig':>12} {'share':>6}")
    for b in sorted(bins):
        rs = bins[b]
        n = len(rs)
        bd = sum(1 for r in rs if r["rank"] == BOUNDARY_RANK and r["k"] == BOUNDARY_K)
        off = sum(1 for r in rs
                  if is_official_sig((r["tileH"], r["tileW"], r["rank"], r["exact"])))
        lo, hi = b * bin_width, min((b + 1) * bin_width - 1, rows[-1]["height"])
        print(f"{lo:>6}-{hi:>6} {n:>6} {bd:>12} {bd / n:>6.1%} {off:>12} {off / n:>6.1%}")
        out.append({"from": lo, "to": hi, "blocks": n,
                    "atBoundary": bd, "officialSig": off})
    REPORT["ds001PerBin"] = {"binWidth": bin_width, "bins": out}


def pool_boundary_table(rows, label, frozen):
    tag = "frozen DS-001" if frozen else "NON-FROZEN live API"
    print(f"\n== 14.3 boundary-hugging per pool, {label} [{tag}] ==")
    print("denominator per row: the pool's blocks in the window (coinbase-tag "
          "attribution; unattributed is its own row, never redistributed).")
    print(f"{'pool':<14} {'n':>5} {'at min (128,2048)':>18} {'at max (128,65536)':>19} "
          f"  rank-128 k values (count)")
    pools = sorted({r["pool"] for r in rows},
                   key=lambda p: (-sum(1 for r in rows if r["pool"] == p), p))
    out = []
    for pool in ["ALL"] + pools:
        rs = rows if pool == "ALL" else [r for r in rows if r["pool"] == pool]
        n = len(rs)
        at_min = sum(1 for r in rs if r["rank"] == BOUNDARY_RANK and r["k"] == BOUNDARY_K)
        at_max = sum(1 for r in rs if r["rank"] == BOUNDARY_RANK and r["k"] == MAX_K_AT_128)
        k128 = Counter(r["k"] for r in rs if r["rank"] == BOUNDARY_RANK)
        kdist = "  ".join(f"{k}:{c}" for k, c in
                          sorted(k128.items(), key=lambda kv: (-kv[1], kv[0]))[:4])
        print(f"{pool:<14} {n:>5} {share(at_min, n):>18} {share(at_max, n):>19} "
              f"  {kdist}")
        out.append({"pool": pool, "blocks": n, "atMin": at_min, "atMax": at_max,
                    "rank128K": {str(k): c for k, c in sorted(k128.items())}})
    over_max = sum(1 for r in rows
                   if r["rank"] == BOUNDARY_RANK and r["k"] > MAX_K_AT_128)
    under_min = sum(1 for r in rows if r["rank"] < BOUNDARY_RANK)
    print(f"legality guard: rank-128 blocks with k > {MAX_K_AT_128}: {over_max}; "
          f"blocks with rank < 128: {under_min} "
          f"(both must be 0 in a post-fork window)")
    # This table only runs on post-fork windows (main clamps the live window
    # to the fork), so a nonzero guard is a data regression, not legal
    # pre-fork behaviour: fail loudly rather than ship it.
    if over_max or under_min:
        fail(f"legality guard violated in {label}: over_max={over_max} "
             f"under_min={under_min}")
    return out


def signature_census(rows, label, frozen, max_tip):
    tag = "frozen DS-001" if frozen else "NON-FROZEN live API"
    print(f"\n== 14.4 tile-signature census, {label} [{tag}] ==")
    print("signature = (tileH, tileW, rank, rows/cols bytes exact-official or not); "
          "denominator: non-EMPTY blocks in the window.")
    sigs = {}
    for r in rows:
        s = (r["tileH"], r["tileW"], r["rank"], r["exact"])
        e = sigs.setdefault(s, {"count": 0, "first": r["height"], "last": r["height"]})
        e["count"] += 1
        e["first"] = min(e["first"], r["height"])
        e["last"] = max(e["last"], r["height"])
    n = len(rows)
    official = sum(e["count"] for s, e in sigs.items() if is_official_sig(s))
    print(f"{len(sigs)} distinct signatures over {n} blocks; "
          f"official-signature blocks {share(official, n)}")
    print(f"{'signature':<26} {'blocks':>7} {'share':>7} {'first':>7} {'last':>7}")
    out = []
    for s, e in sorted(sigs.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
        mark = "  <- official" if is_official_sig(s) else ""
        print(f"{sig_name(s):<26} {e['count']:>7} {e['count'] / n:>7.2%} "
              f"{e['first']:>7} {e['last']:>7}{mark}")
        out.append({"tileH": s[0], "tileW": s[1], "rank": s[2], "byteExact": s[3],
                    "official": is_official_sig(s), **e})
    last_official = max((e["last"] for s, e in sigs.items() if is_official_sig(s)),
                        default=None)
    first_nonoff = min((e["first"] for s, e in sigs.items() if not is_official_sig(s)),
                       default=None)
    print(f"first non-official-signature block: h{first_nonoff}; "
          f"last official-signature block in window: h{last_official} "
          f"(window ends h{max_tip})")
    return {"signatures": out, "blocks": n, "officialBlocks": official,
            "firstNonOfficial": first_nonoff, "lastOfficial": last_official}


def era_table(rows):
    print("\n== 14.4 official-signature share per consensus era [frozen DS-001] ==")
    print("denominator per row: non-EMPTY blocks in the era within DS-001's span.")
    print(f"{'era':<13} {'span':>15} {'blocks':>7} {'official-sig':>14} "
          f"{'distinct sigs':>13}")
    out = []
    top = rows[-1]["height"]
    for era, lo, hi in ERAS:
        hi_eff = top if hi is None else min(hi, top)
        rs = [r for r in rows if lo <= r["height"] <= hi_eff]
        if not rs:
            continue
        off = sum(1 for r in rs
                  if is_official_sig((r["tileH"], r["tileW"], r["rank"], r["exact"])))
        nsig = len({(r["tileH"], r["tileW"], r["rank"], r["exact"]) for r in rs})
        print(f"{era:<13} {f'{lo}-{hi_eff}':>15} {len(rs):>7} "
              f"{share(off, len(rs)):>14} {nsig:>13}")
        out.append({"era": era, "from": lo, "to": hi_eff, "blocks": len(rs),
                    "officialSig": off, "distinctSigs": nsig})
    REPORT["ds001Eras"] = out


# ------------------------------------------------- matched cross-reference --

def matched_heights(scan_dirs):
    out = set()
    for d in scan_dirs:
        results = Path(d) / "results"
        if not results.is_dir():
            print(f"  scan dir missing, skipped: {d}")
            continue
        for part in sorted(results.glob("*.jsonl.gz")):
            with gzip.open(part, "rt") as f:
                for line in f:
                    if '"match":true' not in line:
                        continue
                    r = json.loads(line)
                    if r.get("match"):
                        out.add(r["height"])
    return out


def matched_crossref(rows, scan_dirs):
    print("\n== 14.4 cross-reference: weight-matched blocks by signature "
          "[frozen DS-001 + committed scan datasets] ==")
    print("a match = keyed-BLAKE3 hash_b equal to a published-checkpoint tensor "
          "(DS-002/DS-002b); it proves the software committed genuine weights.")
    have_results = any((Path(d) / "results").is_dir() for d in scan_dirs)
    heights = matched_heights(scan_dirs)
    if not heights:
        if have_results:
            fail("scan result dirs are present but zero matches parsed; "
                 "the match:true prefilter or the dataset format changed")
        print("  no scan datasets found; section skipped")
        return
    by_h = {r["height"]: r for r in rows}
    joined = [by_h[h] for h in sorted(heights) if h in by_h]
    n = len(joined)
    print(f"matched blocks joined to DS-001: {n} of {len(heights)} dataset matches "
          f"(misses are outside DS-001's span)")
    cls = Counter(r["class"] for r in joined)
    print(f"by frozen class: {dict(sorted(cls.items()))}")
    sigs = Counter((r["tileH"], r["tileW"], r["rank"], r["exact"]) for r in joined)
    off = sum(c for s, c in sigs.items() if is_official_sig(s))
    print(f"official signature among matched: {share(off, n)}; "
          f"non-official yet weight-matched: {share(n - off, n)}")
    for s, c in sorted(sigs.items(), key=lambda kv: (-kv[1], kv[0])):
        mark = "  <- official" if is_official_sig(s) else ""
        print(f"  {sig_name(s):<26} {c:>5}{mark}")
    msc = [r for r in joined if r["class"] == "MODEL_SHAPED_CUSTOM"]
    msc_off = sum(1 for r in msc
                  if is_official_sig((r["tileH"], r["tileW"], r["rank"], r["exact"])))
    print(f"MODEL_SHAPED_CUSTOM matched blocks: {len(msc)}, of which official "
          f"signature: {msc_off} (these committed real weights from non-official "
          f"software; the fingerprint identifies software, not honesty)")
    for h in sorted(ERRATUM_MATCH_HEIGHTS):
        r = by_h.get(h)
        if r:
            s = (r["tileH"], r["tileW"], r["rank"], r["exact"])
            print(f"roadmap-erratum match (not in any committed results file): "
                  f"h{h} {sig_name(s)} class {r['class']}")
    REPORT["matchedCrossref"] = {
        "joined": n, "datasetMatches": len(heights),
        "byClass": dict(sorted(cls.items())),
        "officialSig": off,
        "signatures": [{"tileH": s[0], "tileW": s[1], "rank": s[2],
                        "byteExact": s[3], "count": c} for s, c in sorted(
                            sigs.items(), key=lambda kv: (-kv[1], kv[0]))],
    }


# ---------------------------------------------------------------- DS-003 ----

def ds003_section(rows, ds001_tip):
    print("\n== 14.3 frozen extension + identity check against DS-003 ==")
    path = DS003 / "bins.json"
    if not path.exists():
        print(f"  DS-003 not found at {path}; section skipped")
        return
    bins = json.loads(path.read_text())
    counts = Counter()
    for r in rows:
        if r["rank"] == BOUNDARY_RANK and r["k"] == BOUNDARY_K:
            counts[r["height"] // 500] += 1
    mismatches = 0
    checked = 0
    for b in bins:
        if b["to"] > ds001_tip:
            continue
        checked += 1
        if counts.get(b["from"] // 500, 0) != b["rank128k2048"]:
            mismatches += 1
            print(f"  MISMATCH bin {b['from']}-{b['to']}: DS-001 "
                  f"{counts.get(b['from'] // 500, 0)} vs DS-003 {b['rank128k2048']}")
    print(f"identity check: DS-001 per-500-bin (128,2048) counts vs DS-003 "
          f"rank128k2048 over {checked} full bins inside DS-001's span: "
          f"{'PASS' if mismatches == 0 else f'{mismatches} MISMATCHES'}")
    if mismatches:
        fail(f"DS-001/DS-003 identity check failed: {mismatches} mismatched bins")
    print("DS-003 bins beyond DS-001's tip (frozen at DS-003's own tip; the bin "
          "straddling the fork and DS-001's tip is flagged):")
    print(f"{'bin':>13} {'blocks':>6} {'at(128,2048)':>12} {'share':>6}")
    out = []
    for b in bins:
        if b["to"] <= ds001_tip:
            continue
        note = ""
        if b["from"] < RANK_PENALTY_FORK:
            note = "  <- straddles fork + DS-001 tip, mixed denominator"
        if b.get("partial"):
            note += "  (partial bin)"
        print(f"{b['from']:>6}-{b['to']:>6} {b['blocks']:>6} "
              f"{b['rank128k2048']:>12} {b['rank128k2048'] / b['blocks']:>6.1%}{note}")
        out.append({"from": b["from"], "to": b["to"], "blocks": b["blocks"],
                    "atBoundary": b["rank128k2048"]})
    print("note the DS-003 gap: bins carry rankHistogram/kHistogram/poolShares/"
          "poolClassCounts but no per-pool-per-rank crosstab and no tile "
          "histogram, so the per-pool and signature series cannot be rebuilt "
          "from DS-003 alone (candidate DS-003-v2 fields).")
    REPORT["ds003"] = {"identityBinsChecked": checked, "identityMismatches": mismatches,
                       "postDs001Bins": out}


# ------------------------------------------------------------- live API -----

def fetch_json(path):
    req = urllib.request.Request(API + path,
                                 headers={"User-Agent": "pool-config-census"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_block(height):
    last = None
    for attempt in range(3):
        try:
            b = fetch_json(f"/blocks/{height}")["block"]
            p = (b.get("pool") or {}).get("name") or "unattributed"
            cp = (b.get("certificate") or {}).get("params") or {}
            return {
                "height": height,
                "pool": p,
                "class": (b.get("certificate") or {}).get("class"),
                "rank": cp.get("rank"),
                "k": cp.get("k"),
                "tileH": cp.get("tileH"),
                "tileW": cp.get("tileW"),
                "rowsHex": cp.get("rowsPatternHex"),
                "colsHex": cp.get("colsPatternHex"),
                "exact": (cp.get("rowsPatternHex") == OFFICIAL_ROWS_HEX
                          and cp.get("colsPatternHex") == OFFICIAL_COLS_HEX),
            }
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"block {height}: {last}")


def live_section(live_from, tail):
    print("\n================ NON-FROZEN SECTION: live keshi API ================")
    print(f"source {API}; this window moves with the chain tip and is NOT "
          f"reproducible byte-for-byte; frozen sections above are.")
    try:
        status = fetch_json("/status")
    except Exception as e:  # noqa: BLE001
        print(f"  live API unreachable ({e}); section skipped")
        return
    tip = status["index"]["tipHeight"]
    heights = list(range(live_from, tip + 1))
    print(f"window h{live_from}..h{tip} ({len(heights)} blocks, "
          f"post-fork window; fork at h{RANK_PENALTY_FORK}), fetched "
          f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = sorted(ex.map(fetch_block, heights), key=lambda r: r["height"])
    label = f"h{live_from}..h{tip}"
    REPORT["live"] = {"api": API, "tip": tip, "from": live_from,
                      "blocks": len(rows), "nonFrozen": True}
    REPORT["live"]["poolBoundary"] = pool_boundary_table(rows, label, frozen=False)
    REPORT["live"]["signatures"] = signature_census(rows, label, frozen=False,
                                                    max_tip=tip)
    # DS-001 stores tile geometry plus exact-vs-official flags only; the API
    # exposes the raw pattern bytes, so the live window can count byte
    # patterns directly. The geometry census is a lower bound on these.
    byte_sigs = Counter((r["rowsHex"], r["colsHex"], r["rank"]) for r in rows)
    geoms = {}
    for r in rows:
        geoms.setdefault((r["tileH"], r["tileW"], r["rank"], r["exact"]),
                         set()).add((r["rowsHex"], r["colsHex"]))
    split = sum(1 for pats in geoms.values() if len(pats) > 1)
    print(f"byte-pattern census [NON-FROZEN live API]: "
          f"{len(byte_sigs)} distinct (rowsPattern, colsPattern, rank) tuples "
          f"over {len(rows)} blocks; {split} of {len(geoms)} geometry "
          f"signatures above aggregate more than one byte pattern")
    REPORT["live"]["bytePatterns"] = {
        "distinct": len(byte_sigs),
        "geometrySignatures": len(geoms),
        "geometriesWithMultiplePatterns": split,
    }
    tail_rows = rows[-tail:]
    off = [r for r in tail_rows
           if is_official_sig((r["tileH"], r["tileW"], r["rank"], r["exact"]))]
    geom = sum(1 for r in tail_rows if (r["tileH"], r["tileW"]) == OFFICIAL_TILE)
    print(f"\n== 14.4 official stack at the tip [NON-FROZEN live API] ==")
    print(f"last {len(tail_rows)} blocks (h{tail_rows[0]['height']}.."
          f"h{tail_rows[-1]['height']}): official signature "
          f"{share(len(off), len(tail_rows))}; (2,64) geometry any-rank/any-bytes "
          f"{share(geom, len(tail_rows))}")
    if off:
        pools = Counter(r["pool"] for r in off)
        print(f"official-signature blocks in the tail by pool: "
              f"{dict(sorted(pools.items(), key=lambda kv: -kv[1]))}")
        print(f"latest official-signature block: h{off[-1]['height']}")
    REPORT["live"]["tail"] = {"blocks": len(tail_rows),
                              "officialSig": len(off), "officialGeometry": geom}


# ------------------------------------------------------------------ main ----

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scan_dirs", nargs="*", default=None,
                    help="weight-scan dataset dirs for the matched cross-reference")
    ap.add_argument("--bin", type=int, default=1000, help="DS-001 bin width")
    ap.add_argument("--skip-live", action="store_true",
                    help="skip the non-frozen live API section")
    ap.add_argument("--live-from", type=int, default=RANK_PENALTY_FORK,
                    help="first height of the live window")
    ap.add_argument("--tail", type=int, default=1000,
                    help="tip-window size for the official-stack-at-tip check")
    ap.add_argument("--json", metavar="PATH",
                    help="also write the machine-readable report to PATH")
    args = ap.parse_args()

    framing = next(p for p in __doc__.split("\n\n") if p.startswith("Framing"))
    print(framing)
    REPORT["framing"] = framing.replace("\n", " ")

    # The boundary-hugging tables read "legal minimum" as a post-fork fact,
    # so the live window must not dip below the fork (a below-fork start would
    # mislabel the window and trip the now-fatal legality guard on legal
    # pre-fork ranks).
    if args.live_from < RANK_PENALTY_FORK:
        print(f"note: --live-from {args.live_from} is below the rank-penalty "
              f"fork; clamping to h{RANK_PENALTY_FORK}")
        args.live_from = RANK_PENALTY_FORK

    rows, ds001_tip = load_ds001()
    per_bin_table(rows, args.bin)

    post = [r for r in rows if r["height"] >= RANK_PENALTY_FORK]
    print(f"\npost-fork blocks inside DS-001 (h{RANK_PENALTY_FORK}..h{ds001_tip}): "
          f"{len(post)}; small window, the live section widens it.")
    REPORT["ds001PostFork"] = {"blocks": len(post)}
    REPORT["ds001PostFork"]["poolBoundary"] = pool_boundary_table(
        post, f"post-fork h{RANK_PENALTY_FORK}..h{ds001_tip}", frozen=True)

    REPORT["ds001Signatures"] = signature_census(
        rows, f"whole span h1..h{ds001_tip}", frozen=True, max_tip=ds001_tip)
    era_table(rows)
    matched_crossref(rows, args.scan_dirs or DEFAULT_SCAN_DIRS)
    ds003_section(rows, ds001_tip)

    if args.skip_live:
        print("\nlive section skipped (--skip-live)")
    else:
        live_section(args.live_from, args.tail)

    if args.json:
        Path(args.json).write_text(json.dumps(REPORT, indent=1) + "\n")
        print(f"\nmachine-readable report written to {args.json}")


if __name__ == "__main__":
    main()
