#!/usr/bin/env python3
"""DS-002 final results: full aggregation over all 840 result parts."""
import gzip, json, os
from collections import Counter, defaultdict

# Dataset dir: KESHI_DS002_DIR, else the committed copy relative to this script
# (keshi/scripts -> keshi/docs/research/datasets/...), so a third party runs it
# from a clone with no edits.
OUT = os.environ.get("KESHI_DS002_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs/research/datasets/DS-002-weight-scan-v1")

controls = set()
meta = {}  # height -> (pool, cls, era, m)
with gzip.open(os.path.join(OUT, "extract.jsonl.gz"), "rt") as f:
    for line in f:
        rec = json.loads(line)
        if rec.get("control"):
            controls.add(rec["height"])
        meta[rec["height"]] = (rec.get("pool"), rec.get("class"),
                               rec.get("era"), rec.get("m"))

matches_by_height = defaultdict(list)
control_hits = 0
for fn in sorted(os.listdir(os.path.join(OUT, "results"))):
    with gzip.open(os.path.join(OUT, "results", fn), "rt") as f:
        for line in f:
            rec = json.loads(line)
            if not (rec.get("Match") or rec.get("match")):
                continue
            h = rec.get("Height", rec.get("height"))
            cid = rec.get("Candidate", rec.get("candidate"))
            li = rec.get("LayerIndex", rec.get("layerIndex"))
            sh = rec.get("Shard", rec.get("shard"))
            if h in controls:
                control_hits += 1
            matches_by_height[h].append((cid, li, sh))

total = sum(len(v) for v in matches_by_height.values())
multi = {h: v for h, v in matches_by_height.items() if len(v) > 1}
print(f"match records: {total} | distinct heights: {len(matches_by_height)}")
print(f"CONTROL HITS (must be 0): {control_hits}")
print(f"heights matching >1 buffer: {len(multi)}")
for h, v in list(multi.items())[:6]:
    print("  multi:", h, v)

fam = Counter(v[0][0] for v in matches_by_height.values())
print("\nmatched blocks by family:")
for f_, c in fam.most_common():
    print(f"  {f_:45s} {c:5d}")

hs = sorted(matches_by_height)
print(f"\nheight range: {hs[0]}..{hs[-1]}")
tensors = len({(c, l, s) for v in matches_by_height.values() for c, l, s in v})
print(f"distinct tensors hit: {tensors}")

print("\nmatched-block pool/class/era:")
pools = Counter(meta[h][0] for h in hs)
cls = Counter(meta[h][1] for h in hs)
era = Counter(meta[h][2] for h in hs)
print("  pools:", pools.most_common(6))
print("  class:", cls.most_common(6))
print("  era:  ", era.most_common(4))

print("\nextinction curve (matched blocks per 5k-height bin, vs candidates):")
cand_bins = Counter()
for h, (_p, _c, _e, _m) in meta.items():
    if h not in controls:
        cand_bins[h // 5000 * 5000] += 1
m_bins = Counter(h // 5000 * 5000 for h in hs)
for b in sorted(cand_bins):
    n = m_bins.get(b, 0)
    print(f"  {b:6d}+  matched {n:4d} / {cand_bins[b]:5d} candidates "
          f"({(n/cand_bins[b] if cand_bins[b] else 0):6.1%})")
