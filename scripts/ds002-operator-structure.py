#!/usr/bin/env python3
"""Who actually produced the matched blocks? Address-level structure of the
matched population vs the m=32,768 and m=8,192 strata. Tests pseudo-replication:
are 1,066 matches 1,066 independent observations, or one operator?

Answer as of 2026-08-09: 46 distinct addresses, effective ~4.3 operators
(1/HHI), top address 432 matches, 62% of all matches on 2026-04-29. Zero
address overlap with the m=32,768 stratum. Feeds ROADMAP 8.4 note item 0d.

Caveat this script cannot resolve: addresses are not entities. Use
multi-input co-spend clustering to test whether the diffuse unattributed
stratum is many miners or one operator rotating addresses.

Modes:
  live (default)          fetch miner addresses from the Keshi API
  --emit PATH             live fetch, then write the fetched address/time
                          data as a JSON artifact (public chain data), so
                          the analysis is reproducible off this host
  --from-artifact PATH    no network: read the artifact instead

Env: KESHI_DS002_DIR (dataset dir), KESHI_API (default loopback).
Sampling is seeded, so live and artifact runs select identical heights.
"""
import argparse, gzip, json, os, random, sys, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

OUT = os.environ.get("KESHI_DS002_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs/research/datasets/DS-002-weight-scan-v1")
API = os.environ.get("KESHI_API", "http://127.0.0.1:8081/v1")
random.seed(7)

ap = argparse.ArgumentParser()
ap.add_argument("--emit", metavar="PATH", help="write fetched data as a JSON artifact")
ap.add_argument("--from-artifact", metavar="PATH", help="read a previously emitted artifact instead of the API")
args = ap.parse_args()
ARTIFACT = None
if args.from_artifact:
    ARTIFACT = json.load(open(args.from_artifact))

meta, controls = {}, set()
with gzip.open(os.path.join(OUT, "extract.jsonl.gz"), "rt") as f:
    for line in f:
        r = json.loads(line)
        meta[r["height"]] = r
        if r.get("control"):
            controls.add(r["height"])

matched = {}
for fn in sorted(os.listdir(os.path.join(OUT, "results"))):
    with gzip.open(os.path.join(OUT, "results", fn), "rt") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("Match") or rec.get("match"):
                matched[rec.get("Height", rec.get("height"))] = rec.get(
                    "Candidate", rec.get("candidate"))

scanned = {h: r for h, r in meta.items() if not r.get("control") and r.get("candidates")}

def fetch(h):
    try:
        with urllib.request.urlopen(f"{API}/blocks/{h}", timeout=20) as r:
            b = json.load(r)["block"]
        return h, b.get("minerAddress"), b.get("time"), (b.get("pool") or {}).get("name")
    except Exception as e:
        return h, None, None, f"ERR {e}"

emitted = {}

def fetch_many(section, hs):
    if ARTIFACT is not None:
        rows = ARTIFACT.get(section, {})
        out = {}
        for h in hs:
            v = rows.get(str(h))
            out[h] = tuple(v) if v else (None, None, "MISSING")
        return out
    out = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for h, a, t, p in ex.map(fetch, hs):
            out[h] = (a, t, p)
    emitted[section] = {str(h): list(v) for h, v in out.items()}
    return out

# --- 1. every matched block ---
mh = sorted(matched)
info = fetch_many("matched", mh)
addrs = Counter(info[h][0] for h in mh if info[h][0])
print(f"MATCHED BLOCKS: {len(mh)}, resolved {sum(1 for h in mh if info[h][0])}")
print(f"  distinct miner addresses: {len(addrs)}")
for a, c in addrs.most_common(12):
    hs = sorted(h for h in mh if info[h][0] == a)
    print(f"   {a[:26]}… {c:5d} blocks  h{hs[0]}–{hs[-1]}")

# effective sample size
tot = sum(addrs.values())
hhi = sum((c / tot) ** 2 for c in addrs.values())
print(f"  effective distinct operators (1/HHI): {1/hhi:.2f}")

# --- 2. m=32,768 stratum (the 0/50,049 population) ---
m32 = [h for h, r in scanned.items() if r["m"] == 32768]
s32 = random.sample(m32, 600)
i32 = fetch_many("m32Sample", s32)
a32 = Counter(i32[h][0] for h in s32 if i32[h][0])
print(f"\nm=32,768 STRATUM (sample {len(s32)} of {len(m32)}):")
print(f"  distinct addresses: {len(a32)}")
for a, c in a32.most_common(8):
    print(f"   {a[:26]}… {c:4d}")

# --- 3. overlap: do matched addresses also produce m=32768 blocks? ---
overlap = set(addrs) & set(a32)
print(f"\nADDRESS OVERLAP matched ∩ m=32768-sample: {len(overlap)}")
for a in list(overlap)[:8]:
    print(f"   {a[:26]}…  matched {addrs[a]}  m32k-sample {a32[a]}")

# --- 4. m=8,192 stratum both sides of the boundary ---
m8 = [h for h, r in scanned.items() if r["m"] == 8192]
lo = [h for h in m8 if h <= 54972]; hi = [h for h in m8 if h > 54972]
slo = random.sample(lo, min(300, len(lo))); shi = random.sample(hi, min(300, len(hi)))
ilo, ihi = fetch_many("m8Below", slo), fetch_many("m8Above", shi)
alo = Counter(ilo[h][0] for h in slo if ilo[h][0])
ahi = Counter(ihi[h][0] for h in shi if ihi[h][0])
print(f"\nm=8,192 STRATUM  below boundary: {len(alo)} distinct addrs (sample {len(slo)})")
print(f"                 above boundary: {len(ahi)} distinct addrs (sample {len(shi)})")
print(f"  addr overlap across the boundary: {len(set(alo)&set(ahi))}")
print(f"  below-top: {[ (a[:14], c) for a,c in alo.most_common(5) ]}")
print(f"  above-top: {[ (a[:14], c) for a,c in ahi.most_common(5) ]}")
matched_addr_in_lo = set(addrs) & set(alo)
matched_addr_in_hi = set(addrs) & set(ahi)
print(f"  matched-addrs present below: {len(matched_addr_in_lo)}, above: {len(matched_addr_in_hi)}")

# --- 5. temporal structure of matched blocks ---
times = [datetime.fromisoformat(info[h][1]) for h in mh if info[h][1]]
times.sort()
days = Counter(t.date().isoformat() for t in times)
print(f"\nMATCHED BLOCKS BY DAY ({len(days)} distinct days):")
for d, c in sorted(days.items()):
    print(f"   {d}  {c:4d}  {'#' * min(60, c//4)}")

if args.emit:
    if ARTIFACT is not None:
        sys.exit("refusing --emit in --from-artifact mode")
    payload = {"note": "miner address, block time, pool label per height; "
                       "public chain data fetched from the Keshi API",
               "seed": 7, **emitted}
    with open(args.emit, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"\nartifact written: {args.emit}")
