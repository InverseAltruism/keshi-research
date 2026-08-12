#!/usr/bin/env python3
"""Materialize candidate weight buffers for `keshictl scan-weights`.

RESEARCH TOOLING: runs in /opt/pearl_keshi/.venv-research (huggingface_hub +
safetensors + numpy). Downloads a published pearl-ai checkpoint at a pinned
revision, extracts the INT7 (int8-stored) layers the miner can actually mine,
fuses and tensor-parallel-shards them exactly as vLLM does, and writes
contiguous row-major .bin buffers plus the manifest.json the Go engine
validates against the frozen certclass tables.

Layer selection is NOT guesswork: it is read from the checkpoint's own
`quantization_config` (num_bits 7, type int → mineable; num_bits 8, type
float → FP8, not mineable) and cross-checked against each tensor's stored
safetensors dtype (I8 vs F8_E4M3). See PREREG-002 §3: for the Llama models
`down_proj` is FP8 and only the upper half of the `qkv` layers are INT7.

Conventions frozen by PREREG-002 §5:
  - buffer bytes = row-major contiguous int8 of the (n, k) tensor
  - fused layers concatenate along dim 0 in vLLM order: q|k|v, gate|up
  - column-parallel layers (qkv, gate_up) shard n; row-parallel (o) shard k
  - one buffer per (layer name, tp, shard, transformer layer index)

Usage:
  extract-weights.py --probe --model Llama-3.3-70B-Instruct-pearl
  extract-weights.py --model Llama-3.3-70B-Instruct-pearl \\
      --out /opt/pearl_keshi/weights --tp 1,2 [--layers gate_up_fused,o]
      [--max-layer-index N]

--probe fetches one small file and exits 0/1: HuggingFace LFS reachability
is not assumed on this host (cdn-lfs.huggingface.co does not resolve here;
the resolve/ redirect chain is what matters). Probe before any large pull.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# Model short name (must match internal/certclass Models()) → HF repo.
MODELS = {
    "Llama-3.1-8B": "pearl-ai/Llama-3.1-8B-Instruct-pearl",
    "Llama-3.3-70B": "pearl-ai/Llama-3.3-70B-Instruct-pearl",
    "Qwen3-30B-A3B": "pearl-ai/Qwen3-30B-A3B-Instruct-2507-pearl",
    "Gemma-4-31B": "pearl-ai/Gemma-4-31B-it-pearl",
}
REPO_TO_MODEL = {v.split("/")[-1]: k for k, v in MODELS.items()}

# Fused layer definitions: certclass layer name → source projections, in the
# vLLM concatenation order, and the parallelism axis. Dense layers only.
#
# `expert_gate_up_fused` (Qwen3) is deliberately absent: vLLM stacks ALL
# experts into one w1 of shape [E*N, K] and the per-expert order is part of
# the commitment, so it is a different extraction problem: emitting a
# per-expert buffer here would produce something that cannot match. Add it
# with its own layout code and a PREREG amendment when MoE is in scope.
FUSED = {
    "gate_up_fused": (["gate_proj", "up_proj"], "col"),
    "qkv_fused": (["q_proj", "k_proj", "v_proj"], "col"),
    "o": (["o_proj"], "row"),
}


def die(msg: str, code: int = 1) -> None:
    print(f"extract-weights: {msg}", file=sys.stderr)
    sys.exit(code)


def compile_target(t: str) -> re.Pattern:
    return re.compile(t[3:] if t.startswith("re:") else re.escape(t))


def int7_targets(config: dict) -> tuple[list[re.Pattern], bool, list[re.Pattern]]:
    """Selectors for the INT7 (mineable) group.

    Returns (name_patterns, linear_class_target, exclude_patterns). Two target
    conventions exist in the published checkpoints:
      - the Llamas name tensor paths (optionally `re:`-prefixed regexes);
      - Gemma-4-31B targets the literal module class `Linear` as the default
        group, carved down by the top-level `ignore` list AND by any other
        group's explicit targets (its q/k/v and down sit in the FP8 group but
        are Linear modules too, so explicit targets must take precedence over
        the class fallback).
    """
    q = config.get("quantization_config", {})
    if q.get("quant_method") != "pearl":
        die(f"unexpected quant_method {q.get('quant_method')!r}")
    pats: list[re.Pattern] = []
    exclude: list[re.Pattern] = [compile_target(t) for t in q.get("ignore", [])]
    linear_class = False
    for name, group in q.get("config_groups", {}).items():
        w = group.get("weights", {})
        targets = group.get("targets", [])
        if w.get("num_bits") == 7 and w.get("type") == "int":
            for t in targets:
                if t == "Linear":
                    linear_class = True
                else:
                    pats.append(compile_target(t))
            print(f"  INT7 group {name}: {len(targets)} target patterns"
                  f"{' (module class Linear)' if linear_class else ''}")
        else:
            exclude.extend(compile_target(t) for t in targets if t != "Linear")
    if linear_class:
        print(f"  class-fallback exclusions (ignore + other groups): {len(exclude)}")
    if not pats and not linear_class:
        die("no INT7 group found in quantization_config")
    return pats, linear_class, exclude


def is_int7(tensor_name: str,
            pats: list[re.Pattern], linear_class: bool, exclude: list[re.Pattern]) -> bool:
    base = tensor_name.removesuffix(".weight")
    if any(p.search(base) or p.fullmatch(base) for p in pats):
        return True
    if linear_class:
        # Every projection weight this script considers lives on a Linear
        # module, so the class target admits it unless the ignore list or an
        # explicit other-group target claims it first.
        return not any(p.search(base) or p.fullmatch(base) for p in exclude)
    return False


def probe(repo: str) -> int:
    from huggingface_hub import hf_hub_download

    try:
        p = hf_hub_download(repo_id=repo, filename="config.json")
    except Exception as e:  # noqa: BLE001 (the point is to report any failure)
        print(f"PROBE FAILED for {repo}: {e}", file=sys.stderr)
        return 1
    print(f"PROBE OK: fetched {p} ({Path(p).stat().st_size} bytes)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True, help="short name or HF repo suffix")
    ap.add_argument("--out", help="weights root (a per-model subdir is created)")
    ap.add_argument("--tp", default="1,2", help="comma-separated tensor-parallel degrees")
    ap.add_argument("--layers", help="comma-separated certclass layer names (default: all INT7)")
    ap.add_argument("--max-layer-index", type=int, default=-1,
                    help="stop after this transformer layer index (default: all)")
    ap.add_argument("--revision", help="pin the checkpoint revision sha "
                    "(default: resolve the repo head; a coverage run must pass "
                    "the revision its parent dataset pinned)")
    ap.add_argument("--expect", action="append", default=[],
                    help="layer=NxK full fused dims filter, repeatable "
                    "(e.g. o=5376x8192): emit only layers matching the frozen "
                    "certclass tables; Gemma's 10 attention-variant layers "
                    "carry o at k=16384, which the tables exclude")
    ap.add_argument("--probe", action="store_true", help="check LFS reachability and exit")
    args = ap.parse_args()

    model = args.model if args.model in MODELS else REPO_TO_MODEL.get(args.model, args.model)
    if model not in MODELS:
        die(f"unknown model {args.model!r}; known: {', '.join(sorted(MODELS))}")
    repo = MODELS[model]

    if args.probe:
        return probe(repo)
    if not args.out:
        die("--out is required unless --probe")

    import numpy as np
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import EntryNotFoundError
    from safetensors import safe_open

    tps = [int(x) for x in args.tp.split(",") if x.strip()]
    want_layers = set(args.layers.split(",")) if args.layers else None
    expect: dict[str, tuple[int, int]] = {}
    for spec in args.expect:
        name, _, dims = spec.partition("=")
        en, _, ek = dims.partition("x")
        if not (name and en.isdigit() and ek.isdigit()):
            die(f"bad --expect {spec!r}; want layer=NxK")
        expect[name] = (int(en), int(ek))

    revision = args.revision
    if not revision:
        try:
            from huggingface_hub import HfApi

            revision = HfApi().model_info(repo).sha
        except Exception:  # noqa: BLE001
            pass
    if not revision:
        die("could not resolve the repository revision sha: refusing an unpinned extract")
    print(f"{model} @ {repo} revision {revision}")

    cfg_path = hf_hub_download(repo_id=repo, filename="config.json", revision=revision)
    config = json.loads(Path(cfg_path).read_text())

    pats, linear_class, exclude = int7_targets(config)
    try:
        idx = json.loads(Path(hf_hub_download(repo_id=repo,
                                              filename="model.safetensors.index.json",
                                              revision=revision)).read_text())
        weight_map = idx["weight_map"]
    except EntryNotFoundError:
        # Single-file checkpoint (Gemma-4-31B ships one model.safetensors and
        # no index): enumerate tensor names from the file itself.
        print("  no safetensors index: single-file checkpoint, downloading it")
        single = hf_hub_download(repo_id=repo, filename="model.safetensors",
                                 revision=revision)
        with safe_open(single, framework="numpy") as f:
            weight_map = {name: "model.safetensors" for name in f.keys()}

    # Group tensor names by (transformer layer index, projection). Gemma's
    # multimodal checkpoint nests the text stack under `language_model`.
    by_layer: dict[int, dict[str, str]] = {}
    name_re = re.compile(
        r"model\.(?:language_model\.)?layers\.(\d+)\.(?:mlp|self_attn)\.(\w+)\.weight$")
    for name in weight_map:
        m = name_re.match(name)
        if not m:
            continue
        li, proj = int(m.group(1)), m.group(2)
        if not is_int7(name, pats, linear_class, exclude):
            continue
        by_layer.setdefault(li, {})[proj] = name

    out_dir = Path(args.out) / model
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict] = []
    skipped_expect = 0
    shard_cache: dict[str, object] = {}

    def load(name: str):
        shard = weight_map[name]
        if shard not in shard_cache:
            path = hf_hub_download(repo_id=repo, filename=shard, revision=revision)
            shard_cache[shard] = path
        with safe_open(shard_cache[shard], framework="numpy") as f:
            return f.get_tensor(name)

    for li in sorted(by_layer):
        if args.max_layer_index >= 0 and li > args.max_layer_index:
            break
        have = by_layer[li]
        for layer_name, (projs, axis) in FUSED.items():
            if want_layers and layer_name not in want_layers:
                continue
            if not all(p in have for p in projs):
                continue  # this layer index does not carry these INT7 projections
            parts = []
            for p in projs:
                t = load(have[p])
                if t.dtype != np.int8:
                    die(f"{have[p]} has dtype {t.dtype}, expected int8; "
                        "the INT7 group and the stored dtype disagree")
                parts.append(t)
            n = int(sum(t.shape[0] for t in parts))
            k = int(parts[0].shape[1])
            if layer_name in expect and expect[layer_name] != (n, k):
                skipped_expect += 1
                continue
            for tp in tps:
                dim = n if axis == "col" else k
                if dim % tp:
                    continue
                # Column-parallel MERGED layers shard each sub-projection and
                # concatenate per rank: vLLM's MergedColumnParallelLinear /
                # QKVParallelLinear split q|k|v and gate|up individually, so
                # rank r holds gate[r-th slice] ‖ up[r-th slice]. Slicing the
                # already-fused tensor instead yields the raw single
                # projections, which no tp>1 miner ever commits.
                if axis == "col" and any(t.shape[0] % tp for t in parts):
                    continue
                for shard in range(tp):
                    if axis == "col":
                        piece = np.concatenate(
                            [t[t.shape[0] // tp * shard : t.shape[0] // tp * (shard + 1), :]
                             for t in parts],
                            axis=0,
                        ) if len(parts) > 1 or tp > 1 else parts[0]
                    else:
                        fused = parts[0] if len(parts) == 1 else np.concatenate(parts, axis=0)
                        lo, hi = shard * (k // tp), (shard + 1) * (k // tp)
                        piece = fused[:, lo:hi]
                    buf = np.ascontiguousarray(piece).tobytes()
                    fname = f"{layer_name}.tp{tp}.s{shard}.L{li:03d}.bin"
                    (out_dir / fname).write_bytes(buf)
                    files.append({
                        "file": fname, "layer": layer_name, "tp": tp, "shard": shard,
                        "layer_index": li,
                        "n": int(piece.shape[0]), "k": int(piece.shape[1]),
                        "bytes": len(buf),
                        "sha256": hashlib.sha256(buf).hexdigest(),
                    })
        print(f"  layer {li}: {len(files)} buffers so far", end="\r", flush=True)

    if not files:
        die("no buffers produced: check --layers/--tp against the INT7 groups")
    manifest = {"model": model, "hf_repo": repo, "revision": revision, "files": files}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    total = sum(f["bytes"] for f in files)
    print(f"\nwrote {len(files)} buffers ({total / 1e9:.1f} GB) + manifest to {out_dir}")
    if skipped_expect:
        print(f"--expect skipped {skipped_expect} layer/projection groups "
              "whose full dims did not match; this is a deliberate, "
              "declared exclusion, record it in the run notes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
