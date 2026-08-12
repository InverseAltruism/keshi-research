#!/usr/bin/env python3
"""Stratified match rates and boundary analyses over a weight-scan dataset.

Emits the OBS-005 headline tables that ds002-aggregate.py does not cover:

  - the three-stratum table (m = 32,768 constant / m = 8,192 constant /
    varying m) over SCANNED candidates, with matched counts and rates;
  - the within-stratum decline across the boundary for fixed m = 8,192,
    with a two-sided Fisher exact P (pure integer arithmetic, no scipy);
  - last scanned candidate height per stratum (population disappearance);
  - scanned candidates and matches above the boundary, and inside the
    clean pre-fork window (boundary, earliest fork) for the
    protocol-change check;
  - the peak bin rate at two bin widths (the peak is bin-width dependent
    and must never be quoted without one);
  - the negative-control height window.

Scanned candidate = a non-control record whose candidate list is
non-empty and whose height appears in the results (i.e. it was actually
hashed); with a complete run this equals every record with candidates.
Unhashed candidates are excluded from strata, matching the coverage
accounting in summary.json.

Env / args mirror the other ds002 scripts:
  KESHI_DS002_DIR   dataset dir (default: the committed DS-002 copy)
Usage: ds002-strata.py [--boundary 54972] [--fork 71935]
"""

import argparse
import gzip
import json
import math
import os
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DS = HERE.parent / "docs" / "research" / "datasets" / "DS-002-weight-scan-v1"


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact for [[a, b], [c, d]] by point-probability rule."""
    n = a + b + c + d
    row1, col1 = a + b, a + c
    denom = math.comb(n, col1)

    def pmf(x: int) -> float:
        return math.comb(row1, x) * math.comb(n - row1, col1 - x) / denom

    p_obs = pmf(a)
    lo = max(0, col1 - (n - row1))
    hi = min(row1, col1)
    return min(1.0, sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs * (1 + 1e-9)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--boundary", type=int, default=54972,
                    help="last pre-gap match height (default: DS-002's 54,972)")
    ap.add_argument("--fork", type=int, default=71935,
                    help="earliest consensus fork height (PCCR-0002)")
    ap.add_argument("--combine", action="append", default=[],
                    help="additional dataset dir(s) recording the same frozen "
                    "population (e.g. the DS-002b coverage runs); emits a "
                    "combined per-bin table whose numerator is the union of "
                    "matches and whose denominator is all recorded candidate "
                    "blocks, so no known match ever sits in a zero row")
    args = ap.parse_args()

    ds = Path(os.environ.get("KESHI_DS002_DIR", str(DEFAULT_DS)))
    matched: set[int] = set()
    for part in (ds / "results").glob("*.jsonl.gz"):
        for line in gzip.open(part, "rt"):
            r = json.loads(line)
            if r["match"]:
                matched.add(r["height"])

    strata: dict[str, list[tuple[int, int]]] = defaultdict(list)  # name -> [(height, m)]
    controls: list[int] = []
    unhashed = 0
    for line in gzip.open(ds / "extract.jsonl.gz", "rt"):
        rec = json.loads(line)
        if rec.get("control"):
            controls.append(rec["height"])
            continue
        if not rec.get("candidates"):
            continue
        # Exclude candidates that were never hashed (coverage gap), so the
        # strata denominators describe the scanned set only.
        if rec.get("unhashed"):
            unhashed += 1
            continue
        m = rec["m"]
        name = "m=32768" if m == 32768 else ("m=8192" if m == 8192 else "varying m")
        strata[name].append((rec["height"], m))

    # DS-002 has no per-record unhashed flag; reconstruct from summary.json's
    # unhashed candidate families when present.
    summary = json.loads((ds / "summary.json").read_text())
    unhashed_by_cand = summary.get("unhashedByCandidate") or {}

    print(f"dataset: {ds}")
    print(f"matched heights: {len(matched)}")
    if unhashed_by_cand:
        print(f"unhashed candidate families in summary: {len(unhashed_by_cand)}")

    print("\n=== Stratified match rates (scanned candidates) ===")
    total_c = total_m = 0
    for name in ("varying m", "m=8192", "m=32768"):
        rows = strata[name]
        n_m = sum(1 for h, _ in rows if h in matched)
        total_c += len(rows)
        total_m += n_m
        rate = 100 * n_m / len(rows) if rows else 0.0
        print(f"  {name:10s}  matched {n_m:5d} / {len(rows):6d}  ({rate:.2f}%)")
    print(f"  {'TOTAL':10s}  matched {total_m:5d} / {total_c:6d}")

    print(f"\n=== Within-stratum decline, fixed m=8192, boundary h{args.boundary} ===")
    below = [(h, h in matched) for h, _ in strata["m=8192"] if h <= args.boundary]
    above = [(h, h in matched) for h, _ in strata["m=8192"] if h > args.boundary]
    mb, ma = sum(1 for _, x in below if x), sum(1 for _, x in above if x)
    print(f"  below: {mb} / {len(below)}  ({100 * mb / len(below):.2f}%)")
    print(f"  above: {ma} / {len(above)}  ({100 * ma / len(above):.2f}%)")
    p = fisher_two_sided(mb, len(below) - mb, ma, len(above) - ma)
    print(f"  Fisher exact (two-sided): P = {p:.2e}")

    print("\n=== Population disappearance (last scanned candidate per stratum) ===")
    for name in ("varying m", "m=8192", "m=32768"):
        rows = strata[name]
        if rows:
            print(f"  {name:10s}  last candidate h{max(h for h, _ in rows)}")

    print(f"\n=== Above boundary h{args.boundary} and the protocol-change check ===")
    ab_c = [h for rows in strata.values() for h, _ in rows if h > args.boundary]
    ab_m = [h for h in ab_c if h in matched]
    print(f"  scanned candidates above boundary: {len(ab_c)}, matched: {len(ab_m)} "
          f"{sorted(ab_m)}")
    cw = [h for h in ab_c if h < args.fork]
    cwm = [h for h in cw if h in matched]
    print(f"  clean pre-fork window h{args.boundary + 1}-{args.fork - 1}: "
          f"{len(cw)} candidates, {len(cwm)} matched")
    print(f"  boundary sits {args.fork - args.boundary} blocks below the earliest fork")

    print("\n=== Peak bin rate is bin-width dependent ===")
    for width in (5000, 1000):
        best = (0.0, 0, 0, 0)
        bins: dict[int, list[int]] = defaultdict(list)
        for rows in strata.values():
            for h, _ in rows:
                bins[h // width].append(h)
        for b, hs in bins.items():
            n_m = sum(1 for h in hs if h in matched)
            if len(hs) >= 50 and n_m / len(hs) > best[0]:
                best = (n_m / len(hs), b * width, n_m, len(hs))
        print(f"  width {width:5d}: peak {100 * best[0]:.2f}% at h{best[1]}+ "
              f"({best[2]}/{best[3]})")

    print("\n=== Negative-control window ===")
    print(f"  {len(controls)} control blocks, heights h{min(controls)}-h{max(controls)}")

    if args.combine:
        all_matched = set(matched)
        all_cands: set[int] = {h for rows in strata.values() for h, _ in rows}
        extra_cands = 0
        for other in args.combine:
            op = Path(other)
            for part in (op / "results").glob("*.jsonl.gz"):
                for line in gzip.open(part, "rt"):
                    r = json.loads(line)
                    if r["match"]:
                        all_matched.add(r["height"])
            for line in gzip.open(op / "extract.jsonl.gz", "rt"):
                rec = json.loads(line)
                if not rec.get("control") and rec.get("candidates") \
                        and rec["height"] not in all_cands:
                    all_cands.add(rec["height"])
                    extra_cands += 1
        print(f"\n=== Combined per-bin table ({1 + len(args.combine)} datasets) ===")
        print(f"  union: {len(all_matched)} matched / {len(all_cands)} recorded "
              f"candidate blocks ({extra_cands} beyond the primary dataset's "
              "strata; a recorded candidate the primary run never hashed is "
              "counted here once its coverage run hashed it)")
        bins: dict[int, int] = defaultdict(int)
        mbins: dict[int, int] = defaultdict(int)
        for h in all_cands:
            bins[h // 5000] += 1
        for h in all_matched:
            mbins[h // 5000] += 1
        for b in sorted(bins):
            n, m_n = bins[b], mbins.get(b, 0)
            print(f"  {b * 5000:6d}+  matched {m_n:4d} / {n:5d}  ({100 * m_n / n:5.1f}%)")
        cab = [h for h in all_cands if h > args.boundary]
        cmb = sorted(h for h in all_matched if h > args.boundary)
        cw = [h for h in cab if h < args.fork]
        cwm = sorted(h for h in cw if h in all_matched)
        print(f"  combined above boundary h{args.boundary}: {len(cab)} recorded "
              f"candidates, {len(cmb)} matched {cmb}")
        print(f"  combined clean pre-fork window h{args.boundary + 1}-{args.fork - 1}: "
              f"{len(cw)} candidates, {len(cwm)} matched {cwm}")
        print(f"  last combined match h{max(all_matched)} sits "
              f"{args.fork - max(all_matched)} blocks below the earliest fork")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
