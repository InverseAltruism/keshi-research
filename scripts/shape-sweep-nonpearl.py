#!/usr/bin/env python3
"""Non-pearl-ai shape sweep over the DS-001 corpus (ended vs moved).

Question (roadmap C4): when attested model-weight mining went extinct
(~h54,972, DS-002/OBS-005), did useful-work mining END, or MOVE to model
weights the scan could not verify? This sweep bounds one branch of "moved":
declared certificate (n, k) dims that match the linear-layer geometry of
popular open checkpoints OUTSIDE the four pearl-ai reference models T2
knows. A shape match is necessary but not sufficient for real mining (only
a hash_b weight match proves it); a non-match does not prove synthetic
work (private or custom weights would also not match). So the sweep bounds
the "moved to a KNOWN PUBLIC checkpoint" hypothesis only.

Inputs (both frozen and committed):
  - the shape dictionary emitted by shape-dictionary.py (config-only,
    pinned revisions);
  - DS-001 blocks.jsonl.gz (declared height/class/rank/m/n/k per block).

Matching mirrors T2 semantics: exact ordered (n, k) equality against the
dictionary grid; dense rows require an empty MoE trailer, expert rows
require the exact (experts, topK) trailer (trailer-inconsistent shape hits
are reported separately, never counted as matches). Any (n, k) that a
pearl-ai reference checkpoint can produce is EXCLUDED from the non-pearl
increment, whichever model it also belongs to; per-model shadowing is
reported so fully-shadowed targets (dimension twins of the pearl set) are
visible rather than silently absent.

Era split: the attested-mining extinction boundary h54,972 plus the three
fork heights 71,935 / 91,630 / 96,251.

Env / args mirror the other ds00x scripts:
  KESHI_DS001_DIR   DS-001 dataset dir (default: the committed copy)
  KESHI_SHAPE_DICT  dictionary path    (default: docs/research/shape-dictionary-v1.json)
  KESHI_API         API base for the optional live census cross-check
                    (default: http://127.0.0.1:8081)
Usage: shape-sweep-nonpearl.py [--census WINDOW] [--json OUT.json]
"""

import argparse
import gzip
import json
import os
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DS001 = HERE.parent / "docs" / "research" / "datasets" / "DS-001-classification-v1"
DEFAULT_DICT = HERE.parent / "docs" / "research" / "shape-dictionary-v1.json"

BOUNDARY = 54_972          # last attested block before the gap (OBS-005)
FORKS = (71_935, 91_630, 96_251)

SEGMENTS = [
    ("S1 attested era        h1-54,972", 1, BOUNDARY),
    ("S2 post-extinction     h54,973-71,934", BOUNDARY + 1, FORKS[0] - 1),
    ("S3 moe-window          h71,935-91,629", FORKS[0], FORKS[1] - 1),
    ("S4 dense-only          h91,630-96,250", FORKS[1], FORKS[2] - 1),
    ("S5 rank-penalty        h96,251-", FORKS[2], 1 << 62),
]


def segment(height: int) -> int:
    for i, (_, lo, hi) in enumerate(SEGMENTS):
        if lo <= height <= hi:
            return i
    return -1


def pow2(x: int) -> bool:
    return x > 0 and (x & (x - 1)) == 0


def load_dictionary(path: Path):
    d = json.loads(path.read_text())
    pearl_pairs: set[tuple[int, int]] = set()
    for t in d["targets"]:
        if t["role"] == "pearl-reference":
            for e in t.get("entries", []):
                pearl_pairs.add((e["n"], e["k"]))
    nonpearl: dict[tuple[int, int], list[dict]] = defaultdict(list)
    shadow: dict[str, Counter] = defaultdict(Counter)
    unresolved = []
    for t in d["targets"]:
        if t["role"] != "target":
            continue
        if t.get("status") != "ok":
            unresolved.append((t["label"], t.get("error", "no layers derived")))
            continue
        moe = (t.get("fields") or {}).get("moe")
        for e in t.get("entries", []):
            pair = (e["n"], e["k"])
            shadow[t["label"]]["total"] += 1
            if pair in pearl_pairs:
                shadow[t["label"]]["shadowed"] += 1
                continue
            nonpearl[pair].append({"model": t["label"], "layer": e["layer"],
                                   "tp": e["tp"], "moe": e.get("moe", False),
                                   "trailer": ((moe or {}).get("experts", 0),
                                               (moe or {}).get("topK", 0))})
    return d, pearl_pairs, nonpearl, shadow, unresolved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ds001", default=os.environ.get("KESHI_DS001_DIR", str(DEFAULT_DS001)))
    ap.add_argument("--dict", default=os.environ.get("KESHI_SHAPE_DICT", str(DEFAULT_DICT)))
    ap.add_argument("--census", metavar="WINDOW",
                    help="also cross-check live census topShapes (e.g. 7d); "
                         "LIVE data, not frozen, labeled as such")
    ap.add_argument("--json", help="write the structured result here")
    args = ap.parse_args()

    d, pearl_pairs, nonpearl, shadow, unresolved = load_dictionary(Path(args.dict))
    print(f"dictionary: {args.dict} (generated {d.get('generatedAt')}, "
          f"{sum(1 for t in d['targets'] if t.get('status') == 'ok')} resolved targets)")
    print(f"pearl-reference exclusion pairs: {len(pearl_pairs)}; "
          f"non-pearl dictionary pairs: {len(nonpearl)}")
    if unresolved:
        print("UNRESOLVED targets (absent from the dictionary, sweep says "
              "nothing about them):")
        for label, err in unresolved:
            print(f"  {label}: {err}")
    fully_shadowed = [m for m, c in shadow.items()
                      if c["total"] and c["shadowed"] == c["total"]]
    if fully_shadowed:
        print("fully shadowed targets (every grid cell collides with a "
              "pearl-reference shape; indistinguishable from the pearl set "
              "by geometry alone): " + ", ".join(sorted(fully_shadowed)))
    partial = {m: c for m, c in shadow.items()
               if 0 < c["shadowed"] < c["total"]}
    if partial:
        print("partially shadowed targets (shadowed cells excluded): "
              + ", ".join(f"{m} {c['shadowed']}/{c['total']}"
                          for m, c in sorted(partial.items())))

    n_seg = len(SEGMENTS)
    tot = [0] * n_seg
    pearl_ct = [0] * n_seg
    matched_ct = [0] * n_seg
    trailer_only_ct = [0] * n_seg
    pow2n_ct = [0] * n_seg            # over non-pearl-shaped blocks
    pow2both_ct = [0] * n_seg
    nothing_ct = [0] * n_seg
    per_model = [Counter() for _ in range(n_seg)]
    per_cell = [Counter() for _ in range(n_seg)]      # (model, layer, tp)
    per_shape = [Counter() for _ in range(n_seg)]     # (n, k)
    shape_meta: dict[tuple[int, int], dict] = {}
    model_layers = [defaultdict(set) for _ in range(n_seg)]
    # For the specificity bar: per era, per model, the DISTINCT (n, k) pairs
    # matched (two layer readings of one pair count once), and the set of m
    # values seen on those matches (a constant m == n is the synthetic
    # dims-grinding signature, not batched inference).
    model_pairs = [defaultdict(set) for _ in range(n_seg)]   # model -> {(n,k)}
    model_pair_m = [defaultdict(lambda: defaultdict(set)) for _ in range(n_seg)]  # model -> (n,k) -> {m}
    xcheck_ds1_not_pearl = 0
    xcheck_pearl_not_ds1 = 0
    tip = 0

    blocks_path = Path(args.ds001) / "blocks.jsonl.gz"
    with gzip.open(blocks_path, "rt") as f:
        for line in f:
            r = json.loads(line)
            h = r["height"]
            if h == 0 or r.get("class") == "EMPTY":
                continue
            tip = max(tip, h)
            s = segment(h)
            n, k = r["n"], r["k"]
            moe_e, moe_topk = r.get("moeE", 0), r.get("moeTopK", 0)
            ds1_matched = bool(r.get("matches"))
            tot[s] += 1
            if (n, k) in pearl_pairs:
                pearl_ct[s] += 1
                if not ds1_matched:
                    xcheck_pearl_not_ds1 += 1
                continue
            if ds1_matched:
                xcheck_ds1_not_pearl += 1
            if pow2(n):
                pow2n_ct[s] += 1
                if pow2(k):
                    pow2both_ct[s] += 1
            hits = nonpearl.get((n, k))
            gated, shape_only = [], []
            for hit in hits or []:
                if hit["moe"]:
                    (gated if (moe_e, moe_topk) == hit["trailer"]
                     else shape_only).append(hit)
                else:
                    (gated if moe_e == 0 else shape_only).append(hit)
            if gated:
                matched_ct[s] += 1
                per_shape[s][(n, k)] += 1
                meta = shape_meta.setdefault((n, k), {
                    "models": set(), "cells": set(), "m": Counter(),
                    "hmin": h, "hmax": h})
                meta["hmin"] = min(meta["hmin"], h)
                meta["hmax"] = max(meta["hmax"], h)
                meta["m"][r["m"]] += 1
                for hit in gated:
                    meta["models"].add(hit["model"])
                    meta["cells"].add((hit["model"], hit["layer"], hit["tp"]))
                    per_model[s][hit["model"]] += 1
                    per_cell[s][(hit["model"], hit["layer"], hit["tp"])] += 1
                    model_layers[s][hit["model"]].add(hit["layer"])
                    model_pairs[s][hit["model"]].add((n, k))
                    model_pair_m[s][hit["model"]][(n, k)].add(r["m"])
            elif shape_only:
                trailer_only_ct[s] += 1
            else:
                nothing_ct[s] += 1

    print(f"\ncorpus: {blocks_path} (non-empty blocks h1-{tip}, "
          f"n={sum(tot)})")
    print(f"DS-001 cross-check: blocks DS-001 T2-matched but outside the "
          f"pearl exclusion set: {xcheck_ds1_not_pearl} (want 0); "
          f"pearl-shaped here but not DS-001-matched: {xcheck_pearl_not_ds1} "
          f"(expected nonzero: down rows, config-derived non-frozen rows, "
          f"trailer-gated cells)")

    hdr = (f"{'segment':<40}{'blocks':>8}{'pearl':>8}{'p%':>7}"
           f"{'match':>7}{'m%':>7}{'m%np':>7}{'trlr':>6}{'pow2n':>8}"
           f"{'p2%np':>7}{'none':>8}")
    print("\nPer-era table. Denominators: blocks = all non-empty DS-001 "
          "blocks in the segment; p% over blocks; m%np and p2%np over "
          "NON-pearl-shaped blocks in the segment; pow2n counts non-pearl "
          "blocks whose declared n is a power of two; none = matches no "
          "dictionary shape at all.")
    print(hdr)
    print("-" * len(hdr))
    for i, (name, _, _) in enumerate(SEGMENTS):
        np_blocks = tot[i] - pearl_ct[i]
        def pct(x, d):
            return f"{100 * x / d:.2f}" if d else "-"
        print(f"{name:<40}{tot[i]:>8}{pearl_ct[i]:>8}"
              f"{pct(pearl_ct[i], tot[i]):>7}"
              f"{matched_ct[i]:>7}{pct(matched_ct[i], tot[i]):>7}"
              f"{pct(matched_ct[i], np_blocks):>7}"
              f"{trailer_only_ct[i]:>6}{pow2n_ct[i]:>8}"
              f"{pct(pow2n_ct[i], np_blocks):>7}{nothing_ct[i]:>8}")

    print("\nNon-pearl model hits per era (blocks; a block with an ambiguous "
          "shape counts under every model sharing it):")
    for i, (name, _, _) in enumerate(SEGMENTS):
        if not per_model[i]:
            print(f"  {name}: none")
            continue
        print(f"  {name}:")
        for model, c in per_model[i].most_common():
            layers = ", ".join(sorted(model_layers[i][model]))
            print(f"    {model:<28}{c:>7} blocks  layers hit: {layers}")

    # Specificity bar, computed (not eyeballed). A (model, era) is a real
    # "moved" candidate only if EITHER it matched >= 2 distinct (n, k) pairs
    # from that model's grid, OR it matched exactly one pair that is
    # dictionary-unique (no other target shares it), has neither dim a power
    # of two, and shows a varying-m signature (more than one m, and not the
    # constant m == n of a dims-grinder). Everything else is coincidence.
    print("\nSpecificity bar (computed per model per era; a PASS is a real "
          "non-pearl 'moved' candidate, FAIL is coincidence):")
    total_pass = 0
    for i, (name, _, _) in enumerate(SEGMENTS):
        verdicts = []
        for model, pairs in sorted(model_pairs[i].items()):
            distinct = sorted(pairs)
            if len(distinct) >= 2:
                verdicts.append((model, "PASS", f"{len(distinct)} distinct pairs {distinct}"))
                total_pass += 1
                continue
            (n, k) = distinct[0]
            unique = shape_meta[(n, k)]["models"] == {model}
            ms = model_pair_m[i][model][(n, k)]
            varying = len(ms) > 1 or any(m != n for m in ms)
            reason = (f"1 pair ({n},{k}); unique={unique}; "
                      f"pow2 n={pow2(n)} k={pow2(k)}; "
                      f"m={'varying' if varying else f'constant=={n}'}")
            if unique and not pow2(n) and not pow2(k) and varying:
                verdicts.append((model, "PASS", reason))
                total_pass += 1
            else:
                verdicts.append((model, "FAIL", reason))
        if not verdicts:
            print(f"  {name}: no non-pearl matches")
            continue
        print(f"  {name}:")
        for model, v, reason in sorted(verdicts, key=lambda x: (x[1] != "PASS", x[0])):
            print(f"    [{v}] {model:<28} {reason}")
    print(f"\nBar summary: {total_pass} (model, era) pairs PASS the "
          f"specificity bar across all eras. A zero here is the "
          f"'ENDED (no move to a known public checkpoint)' verdict.")

    print("\nMatched (n, k) shapes (all eras; ambiguity and specificity "
          "flags inline):")
    all_shapes = Counter()
    for i in range(n_seg):
        all_shapes.update(per_shape[i])
    for (n, k), c in all_shapes.most_common():
        meta = shape_meta[(n, k)]
        seg_counts = "/".join(str(per_shape[i].get((n, k), 0)) for i in range(n_seg))
        cells = "; ".join(f"{m}/{l}@tp{tp}" for m, l, tp in sorted(meta["cells"]))
        flags = []
        if pow2(n) and pow2(k):
            flags.append("n,k both pow2 (weak)")
        elif pow2(n) or pow2(k):
            flags.append("one dim pow2")
        if len(meta["models"]) > 1:
            flags.append(f"shared by {len(meta['models'])} models (ambiguous)")
        top_m = ", ".join(f"m={m}x{cnt}" for m, cnt in meta["m"].most_common(3))
        print(f"  ({n}, {k}) blocks={c} by-era {seg_counts} "
              f"h{meta['hmin']}-{meta['hmax']}\n"
              f"      {cells}\n"
              f"      m: {len(meta['m'])} distinct ({top_m})"
              + (f"  [{'; '.join(flags)}]" if flags else ""))

    if args.census:
        base = os.environ.get("KESHI_API", "http://127.0.0.1:8081")
        url = f"{base}/v1/certs/census?window={args.census}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            census = json.load(resp)
        print(f"\nLIVE census cross-check ({url}; NOT frozen, computed at "
              f"{census.get('meta', {}).get('computedAt')}, window blocks="
              f"{census.get('blocks')}); topShapes classified with the same "
              f"dictionary:")
        for row in census.get("topShapes", []):
            pair = (row["n"], row["k"])
            if pair in pearl_pairs:
                cls = "pearl-reference shape"
            elif pair in nonpearl:
                cls = "NON-PEARL DICT HIT: " + "; ".join(
                    f"{h['model']}/{h['layer']}@tp{h['tp']}" for h in nonpearl[pair])
            elif pow2(row["n"]):
                cls = "no dict match, n pow2 (synthetic-looking)"
            else:
                cls = "no dict match"
            print(f"  m={row['m']} n={row['n']} k={row['k']} rank={row['rank']}"
                  f" blocks={row['blocks']}: {cls}")

    if args.json:
        result = {
            "dictionary": str(args.dict),
            "ds001": str(blocks_path),
            "tip": tip,
            "boundary": BOUNDARY, "forks": list(FORKS),
            "unresolvedTargets": [u[0] for u in unresolved],
            "fullyShadowedTargets": sorted(fully_shadowed),
            "segments": [
                {"name": SEGMENTS[i][0].strip(), "lo": SEGMENTS[i][1],
                 "hi": min(SEGMENTS[i][2], tip),
                 "blocks": tot[i], "pearlShaped": pearl_ct[i],
                 "nonPearlMatched": matched_ct[i],
                 "trailerInconsistentShapeHits": trailer_only_ct[i],
                 "pow2NonPearl": pow2n_ct[i],
                 "pow2BothNonPearl": pow2both_ct[i],
                 "matchesNothing": nothing_ct[i],
                 "perModel": {m: c for m, c in per_model[i].items()},
                 "perCell": {f"{m}/{l}@tp{tp}": c
                             for (m, l, tp), c in per_cell[i].items()}}
                for i in range(n_seg)],
            "matchedShapes": [
                {"n": n, "k": k, "blocks": c,
                 "models": sorted(shape_meta[(n, k)]["models"]),
                 "cells": [f"{m}/{l}@tp{tp}"
                           for m, l, tp in sorted(shape_meta[(n, k)]["cells"])],
                 "distinctM": len(shape_meta[(n, k)]["m"]),
                 "heights": [shape_meta[(n, k)]["hmin"], shape_meta[(n, k)]["hmax"]]}
                for (n, k), c in all_shapes.most_common()],
        }
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
