#!/usr/bin/env python3
"""Deeper DS-002 interrogation: m-distributions, classifier disagreements,
straggler, calendar mapping, both extinction denominators."""
import gzip, json, os, urllib.request
from collections import Counter, defaultdict

# Dataset dir via KESHI_DS002_DIR (default: the committed copy relative to
# this script); API via KESHI_API. The API is only used for the calendar
# section, which degrades gracefully offline.
OUT = os.environ.get("KESHI_DS002_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs/research/datasets/DS-002-weight-scan-v1")
API = os.environ.get("KESHI_API", "http://127.0.0.1:8081/v1")

def get(path):
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.load(r)

SUMMARY = json.load(open(os.path.join(OUT, "summary.json")))
# DS-002 predates the coverage fields; its frozen tip is 96,774 (OBS-005 errata).
TIP = SUMMARY.get("toHeight") or SUMMARY.get("snapshotTip") or 96774

meta = {}
controls = set()
with gzip.open(os.path.join(OUT, "extract.jsonl.gz"), "rt") as f:
    for line in f:
        r = json.loads(line)
        meta[r["height"]] = r
        if r.get("control"):
            controls.add(r["height"])

matched = {}  # height -> (cid, layer, shard)
for fn in sorted(os.listdir(os.path.join(OUT, "results"))):
    with gzip.open(os.path.join(OUT, "results", fn), "rt") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("Match") or rec.get("match"):
                h = rec.get("Height", rec.get("height"))
                matched[h] = (rec.get("Candidate", rec.get("candidate")),
                              rec.get("LayerIndex", rec.get("layerIndex")),
                              rec.get("Shard", rec.get("shard")))

# ---- 1. m distribution of matched vs unmatched candidates ----
m_matched = Counter(meta[h]["m"] for h in matched)
big_m = sum(c for m, c in m_matched.items() if m > 16384)
print(f"matched blocks with m > 16384: {big_m} / {len(matched)}")
print("matched m top10:", m_matched.most_common(10))

# ---- 2. the CUSTOM-classified matches ----
custom = [h for h in matched if meta[h]["class"] == "MODEL_SHAPED_CUSTOM"]
print(f"\nMODEL_SHAPED_CUSTOM matches: {len(custom)}")
for h in sorted(custom):
    r = meta[h]
    print(f"  h{h}: m={r['m']} n={r['n']} k={r['k']} -> {matched[h][0]} L{matched[h][1]}")

# ---- 3. straggler + calendar mapping of key heights ----
print("\ncalendar mapping:")
for h in [21068, 25000, 40000, 54685, 60881]:
    try:
        b = get(f"/blocks/{h}")["block"]
        note = ""
        if h in matched:
            note = f"  MATCHED {matched[h][0]} L{matched[h][1]}"
        print(f"  h{h}: {b['time'][:16]}  pool={(b.get('pool') or {}).get('name')}{note}")
    except Exception as e:
        print(f"  h{h}: fetch err {e}")

s = meta[60881]
print(f"straggler h60881: m={s['m']} n={s['n']} k={s['k']} class={s['class']} pool={s['pool']}")

# ---- 4. extinction with BOTH denominators ----
print("\nheight-bin | matched | candidates | all-blocks | m/cand | m/all")
cand_bins = Counter((h // 5000) * 5000 for h in meta if h not in controls)
match_bins = Counter((h // 5000) * 5000 for h in matched)
for b in range(0, TIP + 1, 5000):
    allb = min(TIP + 1, b + 5000) - b
    n, c = match_bins.get(b, 0), cand_bins.get(b, 0)
    print(f"  {b:6d}+ {n:5d} {c:7d} {allb:6d}  {n/c if c else 0:7.1%} {n/allb:7.1%}")

# ---- 5. 8B vs 70B in time ----
h8 = sorted(h for h in matched if matched[h][0].startswith("Llama-3.1-8B"))
h70 = sorted(h for h in matched if matched[h][0].startswith("Llama-3.3-70B"))
print(f"\n8B: n={len(h8)} range {h8[0]}..{h8[-1]} | 70B: n={len(h70)} range {h70[0]}..{h70[-1]}")

# ---- 6. duplicate-buffer sanity (could a block have matched 2 identical buffers?) ----
sums = SUMMARY["bufferSha256"]
rev = defaultdict(list)
for k, v in sums.items():
    rev[v].append(k)
dups = {v: ks for v, ks in rev.items() if len(ks) > 1}
print(f"\nbyte-identical buffer groups: {len(dups)}")
for v, ks in list(dups.items())[:5]:
    print("  dup:", ks)
