#!/usr/bin/env python3
"""PREREG-002 analysis 2: corrected layer mixture on matched blocks.

Compares observed layer-family frequencies among matched blocks against the
per-token INT7-mineable MAC shares over the layers the published checkpoints
can actually mine (PREREG-002 §3: gate_up and o over all 80/32 layers, qkv
only over the upper-half layers, down excluded as FP8). Statistic and
thresholds are PREREG-001 §6's total variation distance, TV <= 0.10 =>
MIXTURE_CONSISTENT, and N < 200 => INSUFFICIENT_SAMPLE.

The expected vector is the layer-count-weighted one PREREG-002 §6.2 mandates;
the arithmetic is printed so the value is auditable, not asserted. Reads only
the frozen dataset; no API, no database.

Env: KESHI_DS002_DIR (default: the committed copy relative to this script).
"""
import gzip, json, os
from collections import Counter

OUT = os.environ.get("KESHI_DS002_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs/research/datasets/DS-002-weight-scan-v1")

# Family -> (n, k, mineable layer count) per model, from PREREG-002 §3.
#   70B: hidden 8192, fused gate/up n=57344, o n=8192, fused qkv n=10240
#        (q 8192 + k/v 1024 each), qkv mineable only on layers 40-79 (40).
#   8B:  hidden 4096, fused gate/up n=14336, o n=4096, fused qkv n=6144,
#        qkv mineable only on layers 16-31 (16).
MODELS = {
    "Llama-3.3-70B": {
        "gate_up_fused": (57344, 8192, 80),
        "o":             (8192,  8192, 80),
        "qkv_fused":     (10240, 8192, 40),
    },
    "Llama-3.1-8B": {
        "gate_up_fused": (14336, 4096, 32),
        "o":             (4096,  4096, 32),
        "qkv_fused":     (6144,  4096, 16),
    },
}

def expected(model):
    fam = MODELS[model]
    mac = {f: n * k * layers for f, (n, k, layers) in fam.items()}
    tot = sum(mac.values())
    return {f: v / tot for f, v in mac.items()}, mac

def tv(obs, exp):
    fams = set(obs) | set(exp)
    return 0.5 * sum(abs(obs.get(f, 0.0) - exp.get(f, 0.0)) for f in fams)

# matched height -> family (from the candidate id "model/family/tp")
matched = {}
for fn in sorted(os.listdir(os.path.join(OUT, "results"))):
    with gzip.open(os.path.join(OUT, "results", fn), "rt") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("Match") or rec.get("match"):
                cid = rec.get("Candidate", rec.get("candidate"))
                matched[rec.get("Height", rec.get("height"))] = cid

for model in ("Llama-3.3-70B", "Llama-3.1-8B"):
    fams = [matched[h].split("/")[1] for h in matched if matched[h].startswith(model + "/")]
    n = len(fams)
    obs_c = Counter(fams)
    obs = {f: c / n for f, c in obs_c.items()} if n else {}
    exp, mac = expected(model)
    print(f"\n=== {model} : N = {n} matched blocks ===")
    print("  family        observed        expected (MAC share)")
    for f in ("gate_up_fused", "o", "qkv_fused"):
        print(f"    {f:14} {obs.get(f,0):7.4f} ({obs_c.get(f,0):4d})   {exp[f]:7.4f}"
              f"  [n={MODELS[model][f][0]} k={MODELS[model][f][1]} x {MODELS[model][f][2]} layers]")
    if n < 200:
        print(f"  N < 200 -> INSUFFICIENT_SAMPLE (PREREG-001 §6); TV not graded")
        continue
    d = tv(obs, exp)
    verdict = "MIXTURE_CONSISTENT" if d <= 0.10 else "MIXTURE_INCONSISTENT"
    print(f"  TV = {d:.4f}  (threshold 0.10)  -> {verdict}")
