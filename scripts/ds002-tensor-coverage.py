#!/usr/bin/env python3
"""PREREG-002 analysis 4: tensor coverage and tile reuse over matched blocks.

Counts distinct (model, family, tp, shard, transformer layer index) tensors
that matched, the distribution of matches per tensor, and per-family layer
coverage. This is the direct test of the "a miner can reuse one tile
indefinitely" caveat: broad layer coverage is inconsistent with a single
reused tile. Reads only the frozen dataset; no API, no database.

Env: KESHI_DS002_DIR (default: the committed copy relative to this script).
"""
import gzip, json, os, statistics
from collections import Counter, defaultdict

OUT = os.environ.get("KESHI_DS002_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs/research/datasets/DS-002-weight-scan-v1")

# tensor key -> match count; family -> set of layer indices covered
per_tensor = Counter()
family_layers = defaultdict(set)
family_shards = defaultdict(set)
for fn in sorted(os.listdir(os.path.join(OUT, "results"))):
    with gzip.open(os.path.join(OUT, "results", fn), "rt") as f:
        for line in f:
            rec = json.loads(line)
            if not (rec.get("Match") or rec.get("match")):
                continue
            cid = rec.get("Candidate", rec.get("candidate"))
            li = rec.get("LayerIndex", rec.get("layerIndex"))
            sh = rec.get("Shard", rec.get("shard"))
            key = f"{cid}|L{li}|s{sh}"
            per_tensor[key] += 1
            family_layers[cid].add(li)
            family_shards[cid].add(sh)

counts = list(per_tensor.values())
total_matches = sum(counts)
print(f"distinct tensors matched: {len(per_tensor)}")
print(f"total matches: {total_matches}")
print(f"matches per tensor: median {statistics.median(counts):.0f}"
      f"  mean {statistics.mean(counts):.2f}  max {max(counts)}")
print(f"tensors matched exactly once: {sum(1 for c in counts if c == 1)}")

hist = Counter(counts)
print("\nmatches-per-tensor histogram (matches: #tensors):")
for c in sorted(hist):
    print(f"  {c:3d}: {hist[c]}")

print("\nper-family layer coverage:")
for cid in sorted(family_layers, key=lambda k: -len(family_layers[k])):
    print(f"  {cid:34} {len(family_layers[cid]):3d} distinct layers, "
          f"shards {sorted(family_shards[cid])}")
