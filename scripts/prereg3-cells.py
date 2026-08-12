#!/usr/bin/env python3
"""PREREG-003 R1 cell enumeration: emit DS-006 cells.json before hashing.

Enumerates the (model, family, tp, shard-shape) cells that PREREG-002 §3
declares mineable and the frozen classifier omits, with dims read from
the pinned checkpoints' safetensors headers (never config defaults), plus
the clearly-labeled exploratory column-parallel o cells. Counts DS-001
blocks per cell and writes the committed cell list PREREG-003 §2 requires
before any R1 hashing and before the R5 draw.

Usage (research venv):
  prereg3-cells.py --snapshot <model>=<snapshot-dir> [...] \
      --ds001 docs/research/datasets/DS-001-classification-v1/blocks.jsonl.gz \
      --out cells.json
"""

import argparse
import glob
import gzip
import json
import os
import struct
import sys

MIN_K = 1024
MIN_N = 256
TPS = (1, 2, 4, 8)


def read_headers(snapshot: str) -> dict:
    """Tensor name -> shape, from every safetensors file's own header."""
    shapes = {}
    for path in sorted(glob.glob(os.path.join(snapshot, "*.safetensors"))):
        with open(path, "rb") as f:
            hlen = struct.unpack("<Q", f.read(8))[0]
            header = json.loads(f.read(hlen))
        for name, meta in header.items():
            if name == "__metadata__":
                continue
            shapes[name] = (meta.get("dtype"), meta.get("shape"))
    return shapes


def model_cells(shapes: dict, num_kv_heads) -> list:
    """Cells for one checkpoint: o (row-parallel standard plus exploratory
    column-parallel) for every model, and fused qkv where the projections
    are I8. All dims from headers; the kv-head replication boundary comes
    from the config (a sharding-rule parameter, not a dim)."""
    cells = []
    qkv_dims = set()
    o_dims = set()
    for name, (dtype, shape) in shapes.items():
        if name.endswith("self_attn.o_proj.weight") and dtype == "I8":
            o_dims.add(tuple(shape))
        if name.endswith("self_attn.q_proj.weight") and dtype == "I8":
            base = name[: -len("q_proj.weight")]
            k = shapes.get(base + "k_proj.weight")
            v = shapes.get(base + "v_proj.weight")
            if k and v and k[0] == "I8" and v[0] == "I8":
                qkv_dims.add((shape[0], k[1][0], shape[1]))
    for qn_full, kvn_full, kdim in sorted(qkv_dims):
        if num_kv_heads is None:
            continue
        for tp in TPS:
            if qn_full % tp:
                continue
            kv_shard = kvn_full // tp if tp <= num_kv_heads else kvn_full
            shard_n = qn_full // tp + 2 * kv_shard
            if shard_n < MIN_N or kdim < MIN_K:
                continue
            cells.append({"family": "qkv_fused", "tp": tp, "n": shard_n,
                          "k": kdim, "exploratory": False})
    for n, kdim in sorted(o_dims):
        for tp in TPS:
            kshard = kdim // tp
            if kdim % tp or kshard < MIN_K or kshard % 64:
                continue
            cells.append({"family": "o", "tp": tp, "n": n, "k": kshard,
                          "exploratory": False})
        for tp in TPS:
            if tp == 1 or n % tp:
                continue
            nshard = n // tp
            if nshard < MIN_N or kdim < MIN_K or kdim % 64:
                continue
            cells.append({"family": "o_colparallel", "tp": tp, "n": nshard,
                          "k": kdim, "exploratory": True})
    return cells


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", action="append", required=True,
                    help="<model-label>=<snapshot dir>; repeatable")
    ap.add_argument("--ds001", required=True)
    ap.add_argument("--already-searched", required=True,
                    help="JSON list of [n, k] cells covered by executed scans (mandatory)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cells = []
    for spec in args.snapshot:
        label, path = spec.split("=", 1)
        shapes = read_headers(path)
        nkv = None
        cfg_path = os.path.join(path, "config.json")
        if os.path.exists(cfg_path):
            nkv = json.load(open(cfg_path)).get("num_key_value_heads")
        got = model_cells(shapes, nkv)
        for c in got:
            c["model"] = label
        cells.extend(got)

    searched = {tuple(x) for x in json.load(open(args.already_searched))}
    seen_cells = set()
    final = []
    for c in cells:
        cell_key = (c["model"], c["family"], c["tp"], c["n"], c["k"])
        if cell_key in seen_cells or (c["n"], c["k"]) in searched:
            continue
        seen_cells.add(cell_key)
        final.append(c)

    counts = {(c["n"], c["k"]): [] for c in final}
    with gzip.open(args.ds001, "rt") as f:
        for line in f:
            r = json.loads(line)
            key = (r["n"], r["k"])
            if key in counts:
                counts[key].append(r["height"])
    for c in final:
        hs = counts[(c["n"], c["k"])]
        c["blocks"] = len(hs)
        if len(hs) <= 64:
            c["heights"] = hs
        else:
            c["heightsSample"] = hs[:64]

    out = {"tool": "prereg3-cells.py", "cells": final,
           "ds001": os.path.abspath(args.ds001)}
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    nz = [c for c in final if c["blocks"]]
    print(f"{len(final)} cells, {len(nz)} nonzero:")
    for c in nz:
        print(f"  {c['model']} {c['family']} tp{c['tp']} (n={c['n']},k={c['k']}): {c['blocks']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
