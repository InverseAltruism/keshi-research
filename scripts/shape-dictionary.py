#!/usr/bin/env python3
"""Config-only linear-layer shape dictionary for the non-pearl-ai sweep.

RESEARCH TOOLING: runs in /opt/pearl_keshi/.venv-research (huggingface_hub).
Fetches ONLY config.json (never weights) for a breadth-first set of popular
open checkpoints that existed around the chain's launch window, at a PINNED
revision, and derives every mineable linear-layer (n, k) pair plus its
tensor-parallel shardings. The output feeds shape-sweep-nonpearl.py, which
asks whether declared certificate dims in the DS-001 corpus match any open
checkpoint OUTSIDE the four pearl-ai reference models T2 knows.

Derivation conventions mirror extract-weights.py and internal/certclass so a
dictionary match means the same thing a T2 match means:
  - n = out-features, k = in-features of the stored (n, k) weight
  - gate_up_fused = gate|up concatenated on dim 0; qkv_fused = q|k|v
  - column-parallel layers (qkv, gate_up, expert gate_up) shard n;
    row-parallel layers (o, down) shard k; tp grid {1, 2, 4, 8}
  - sharded cells are pruned below the engagement floor n >= 256, k >= 1024
    (certclass MinN/MinK)
  - target-model column shards require every sub-projection's dim 0 to
    divide by tp (the extract-weights rule, what vLLM actually emits);
    pearl-reference exclusion rows use certclass's fused-n divisibility,
    which is a superset, so the exclusion can never under-cover T2
  - MoE expert rows are the PER-EXPERT shape (models.go convention:
    Qwen3-30B-A3B expert_gate_up_fused is 1536 x 2048), with the config's
    (num experts, top-k) recorded for trailer checks

The frozen tables in internal/certclass/models.go are NEVER edited or read
at runtime; a literal mirror below is asserted to be covered by the derived
pearl-reference entries, so drift between this script and the frozen
classifier fails loudly instead of silently.

Reproducibility: every fetched config is pinned to a resolved revision sha
recorded in the output. Re-running with --pins <previous-output> re-fetches
the exact same revisions. Repos that are gated or unreachable are recorded
as UNRESOLVED with the error, never silently dropped.

Env / args:
  KESHI_SHAPE_DICT  output path (default: docs/research/shape-dictionary-v1.json)
Usage: shape-dictionary.py [--out PATH] [--pins PREVIOUS.json]
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "docs" / "research" / "shape-dictionary-v1.json"

TPS = [1, 2, 4, 8]
MIN_N = 256   # certclass.MinN
MIN_K = 1024  # certclass.MinK

# Literal mirror of internal/certclass/models.go (frozen by PREREG-001 @
# 11a517a; do not edit models.go). Used only to assert the derived
# pearl-reference entries cover the whole T2 grid. (name, n, k, col_parallel).
MODELS_GO_ROWS = [
    ("Llama-3.1-8B/qkv_fused", 6144, 4096, True),
    ("Llama-3.1-8B/o", 4096, 4096, False),
    ("Llama-3.1-8B/gate_up_fused", 28672, 4096, True),
    ("Llama-3.1-8B/down", 4096, 14336, False),
    ("Llama-3.3-70B/qkv_fused", 10240, 8192, True),
    ("Llama-3.3-70B/o", 8192, 8192, False),
    ("Llama-3.3-70B/gate_up_fused", 57344, 8192, True),
    ("Llama-3.3-70B/down", 8192, 28672, False),
    ("Qwen3-30B-A3B/expert_gate_up_fused", 1536, 2048, True),
    ("Gemma-4-31B/gate_up_fused", 43008, 5376, True),
    ("Gemma-4-31B/down", 5376, 21504, False),
    ("Gemma-4-31B/qkv_fused", 16384, 5376, True),
    ("Gemma-4-31B/o", 5376, 8192, False),
]

# Extra pearl-reference rows outside the frozen tables, verified from the
# checkpoints themselves during DS-002b: Gemma-4-31B's 10 full_attention
# layer variants carry o at k = 16384 (safetensors inspection, 2026-08-09).
# They are pearl-checkpoint-attributable, so they belong in the exclusion.
PEARL_EXTRA_LAYERS = {
    "pearl/Gemma-4-31B": [
        {"layer": "o_full_attention", "n": 5376, "k": 16384, "axis": "row",
         "note": "10 attention-variant layers, outside the frozen tables"},
    ],
}

# Target set. role "pearl-reference" builds the exclusion set (the four
# models T2 already knows); role "target" is the non-pearl-ai increment.
# Each entry lists the primary repo first, then public mirrors tried in
# order when the primary is gated or unreachable (mirror dims are taken as
# the mirror publishes them; the resolved repo is recorded).
# Breadth: architectures published and popular around the chain's launch
# (Apr-May 2026), plus the roadmap-named third-party pearl quantization.
TARGETS = [
    # Pearl reference checkpoints (the T2-known set; exclusion).
    {"label": "pearl/Llama-3.1-8B", "role": "pearl-reference",
     "repos": ["pearl-ai/Llama-3.1-8B-Instruct-pearl"]},
    {"label": "pearl/Llama-3.3-70B", "role": "pearl-reference",
     "repos": ["pearl-ai/Llama-3.3-70B-Instruct-pearl"]},
    {"label": "pearl/Qwen3-30B-A3B", "role": "pearl-reference",
     "repos": ["pearl-ai/Qwen3-30B-A3B-Instruct-2507-pearl"]},
    {"label": "pearl/Gemma-4-31B", "role": "pearl-reference",
     "repos": ["pearl-ai/Gemma-4-31B-it-pearl"]},

    # The one known third-party pearl quantization (directly mineable by the
    # official plugin, so the strongest "moved" candidate a priori).
    {"label": "Qwen3.6-27B-heretic-pearl", "role": "target",
     "repos": ["dominant-strategies/Qwen3.6-27B-heretic-pearl"]},

    # Llama family (base, non-pearl).
    {"label": "Llama-3.1-8B-base", "role": "target",
     "repos": ["meta-llama/Llama-3.1-8B-Instruct",
               "unsloth/Meta-Llama-3.1-8B-Instruct",
               "NousResearch/Meta-Llama-3.1-8B-Instruct"]},
    {"label": "Llama-3.1-70B-base", "role": "target",
     "repos": ["meta-llama/Llama-3.1-70B-Instruct",
               "unsloth/Meta-Llama-3.1-70B-Instruct",
               "NousResearch/Meta-Llama-3.1-70B-Instruct"]},
    {"label": "Llama-3.2-3B", "role": "target",
     "repos": ["meta-llama/Llama-3.2-3B-Instruct",
               "unsloth/Llama-3.2-3B-Instruct"]},
    {"label": "Llama-4-Scout-17B-16E", "role": "target",
     "repos": ["meta-llama/Llama-4-Scout-17B-16E-Instruct",
               "unsloth/Llama-4-Scout-17B-16E-Instruct"]},

    # Mistral family.
    {"label": "Mistral-7B-v0.3", "role": "target",
     "repos": ["mistralai/Mistral-7B-Instruct-v0.3"]},
    {"label": "Mistral-Nemo-12B", "role": "target",
     "repos": ["mistralai/Mistral-Nemo-Instruct-2407"]},
    {"label": "Mistral-Small-24B", "role": "target",
     "repos": ["mistralai/Mistral-Small-24B-Instruct-2501"]},
    {"label": "Mistral-Large-2411", "role": "target",
     "repos": ["mistralai/Mistral-Large-Instruct-2411"]},
    {"label": "Mixtral-8x7B", "role": "target",
     "repos": ["mistralai/Mixtral-8x7B-Instruct-v0.1"]},
    {"label": "Mixtral-8x22B", "role": "target",
     "repos": ["mistralai/Mixtral-8x22B-Instruct-v0.1"]},

    # Qwen family.
    {"label": "Qwen2.5-7B", "role": "target", "repos": ["Qwen/Qwen2.5-7B-Instruct"]},
    {"label": "Qwen2.5-14B", "role": "target", "repos": ["Qwen/Qwen2.5-14B-Instruct"]},
    {"label": "Qwen2.5-32B", "role": "target", "repos": ["Qwen/Qwen2.5-32B-Instruct"]},
    {"label": "Qwen2.5-72B", "role": "target", "repos": ["Qwen/Qwen2.5-72B-Instruct"]},
    {"label": "Qwen3-8B", "role": "target", "repos": ["Qwen/Qwen3-8B"]},
    {"label": "Qwen3-14B", "role": "target", "repos": ["Qwen/Qwen3-14B"]},
    {"label": "Qwen3-32B", "role": "target", "repos": ["Qwen/Qwen3-32B"]},
    {"label": "Qwen3-30B-A3B-base", "role": "target", "repos": ["Qwen/Qwen3-30B-A3B"]},
    {"label": "Qwen3-235B-A22B", "role": "target", "repos": ["Qwen/Qwen3-235B-A22B"]},

    # DeepSeek family (MLA attention; projections derived accordingly).
    {"label": "DeepSeek-V2-Lite", "role": "target", "repos": ["deepseek-ai/DeepSeek-V2-Lite"]},
    {"label": "DeepSeek-V2", "role": "target", "repos": ["deepseek-ai/DeepSeek-V2"]},
    {"label": "DeepSeek-V3", "role": "target", "repos": ["deepseek-ai/DeepSeek-V3"]},

    # Gemma family (base, non-pearl).
    {"label": "Gemma-2-9B", "role": "target",
     "repos": ["google/gemma-2-9b-it", "unsloth/gemma-2-9b-it"]},
    {"label": "Gemma-2-27B", "role": "target",
     "repos": ["google/gemma-2-27b-it", "unsloth/gemma-2-27b-it"]},
    {"label": "Gemma-3-12B", "role": "target",
     "repos": ["google/gemma-3-12b-it", "unsloth/gemma-3-12b-it"]},
    {"label": "Gemma-3-27B", "role": "target",
     "repos": ["google/gemma-3-27b-it", "unsloth/gemma-3-27b-it"]},

    # Others popular in the launch window.
    {"label": "Phi-4", "role": "target", "repos": ["microsoft/phi-4"]},
    {"label": "GPT-OSS-20B", "role": "target", "repos": ["openai/gpt-oss-20b"]},
    {"label": "GPT-OSS-120B", "role": "target", "repos": ["openai/gpt-oss-120b"]},
    {"label": "Kimi-K2", "role": "target", "repos": ["moonshotai/Kimi-K2-Instruct"]},
    {"label": "GLM-4.5-Air", "role": "target",
     "repos": ["zai-org/GLM-4.5-Air", "THUDM/GLM-4.5-Air"]},
]


def gv(cfg, *names, default=None):
    for name in names:
        v = cfg.get(name)
        if v is not None:
            return v
    return default


def derive_layers(cfg: dict) -> tuple[list[dict], dict, list[str]]:
    """Derive full (n, k) linear layers from a HF config dict.

    Returns (layers, fields, notes). Every layer dict carries: layer name,
    full n, full k, axis (col/row/none), parts (dim-0 sizes of the fused
    sub-projections, col only), moe flag.
    """
    notes: list[str] = []
    if "text_config" in cfg:
        cfg = {**cfg, **cfg["text_config"]}
        notes.append("multimodal config: text_config fields take precedence")

    hidden = gv(cfg, "hidden_size")
    nh = gv(cfg, "num_attention_heads")
    if hidden is None or nh is None:
        return [], {}, notes + ["missing hidden_size/num_attention_heads, no derivation"]
    nkv = gv(cfg, "num_key_value_heads", default=nh)
    hd = gv(cfg, "head_dim", default=hidden // nh)

    layers: list[dict] = []

    def add(name, n, k, axis, parts=None, moe=False, qkv=None):
        layers.append({"layer": name, "n": int(n), "k": int(k), "axis": axis,
                       "parts": [int(p) for p in parts] if parts else None,
                       "moe": moe,
                       # qkv carries (num_heads, num_kv_heads, head_dim) so
                       # expand can apply vLLM's KV-head replication when
                       # tp > num_kv_heads, which a plain fused-n shard gets
                       # wrong.
                       "qkv": [int(x) for x in qkv] if qkv else None})

    # Attention. MLA architectures (DeepSeek V2/V3 lineage) have no standard
    # fused qkv; their projections are derived from the lora ranks instead.
    kv_lora = gv(cfg, "kv_lora_rank")
    if kv_lora is not None:
        qk_nope = gv(cfg, "qk_nope_head_dim", default=0)
        qk_rope = gv(cfg, "qk_rope_head_dim", default=0)
        v_hd = gv(cfg, "v_head_dim", default=hd)
        q_hd = qk_nope + qk_rope
        q_lora = gv(cfg, "q_lora_rank")
        if q_lora:
            add("mla_q_a", q_lora, hidden, "none")
            add("mla_q_b", nh * q_hd, q_lora, "col", parts=[nh * q_hd])
        else:
            add("mla_q", nh * q_hd, hidden, "col", parts=[nh * q_hd])
        add("mla_kv_a", kv_lora + qk_rope, hidden, "none")
        add("mla_kv_b", nh * (qk_nope + v_hd), kv_lora, "col",
            parts=[nh * (qk_nope + v_hd)])
        add("o", hidden, nh * v_hd, "row")
        notes.append("MLA attention: q/kv lora projections instead of qkv_fused")
    else:
        add("qkv_fused", (nh + 2 * nkv) * hd, hidden, "col",
            parts=[nh * hd, nkv * hd, nkv * hd], qkv=[nh, nkv, hd])
        add("o", hidden, nh * hd, "row")

    # MLP. MoE models emit PER-EXPERT expert rows (models.go convention);
    # dense rows are emitted only where the config declares dense layers.
    experts = gv(cfg, "num_local_experts", "n_routed_experts", "num_experts")
    intermediate = gv(cfg, "intermediate_size")
    moe_meta = None
    if experts:
        topk = gv(cfg, "num_experts_per_tok", "experts_per_token", default=0)
        moe_int = gv(cfg, "moe_intermediate_size", default=intermediate)
        moe_meta = {"experts": int(experts), "topK": int(topk),
                    "moeIntermediate": int(moe_int) if moe_int else None}
        if moe_int:
            add("expert_gate_up_fused", 2 * moe_int, hidden, "col",
                parts=[moe_int, moe_int], moe=True)
            add("expert_down", hidden, moe_int, "row", moe=True)
        n_shared = gv(cfg, "n_shared_experts")
        shared_int = gv(cfg, "shared_expert_intermediate_size",
                        default=moe_int * n_shared if (n_shared and moe_int) else None)
        if shared_int:
            add("shared_gate_up_fused", 2 * shared_int, hidden, "col",
                parts=[shared_int, shared_int])
            add("shared_down", hidden, shared_int, "row")
        dense_int = gv(cfg, "intermediate_size_mlp")
        if dense_int is None and intermediate and intermediate != moe_int:
            first_dense = gv(cfg, "first_k_dense_replace", default=0)
            mlp_only = gv(cfg, "mlp_only_layers", default=[])
            if first_dense or mlp_only:
                dense_int = intermediate
            else:
                notes.append("intermediate_size present but no dense layers "
                             "declared; dense mlp rows omitted")
        if dense_int:
            add("gate_up_fused", 2 * dense_int, hidden, "col",
                parts=[dense_int, dense_int])
            add("down", hidden, dense_int, "row")
    elif intermediate:
        add("gate_up_fused", 2 * intermediate, hidden, "col",
            parts=[intermediate, intermediate])
        add("down", hidden, intermediate, "row")

    fields = {"hidden_size": hidden, "num_attention_heads": nh,
              "num_key_value_heads": nkv, "head_dim": hd,
              "intermediate_size": intermediate,
              "num_hidden_layers": gv(cfg, "num_hidden_layers"),
              "moe": moe_meta,
              "quant_method": (cfg.get("quantization_config") or {}).get("quant_method")}
    return layers, fields, notes


def expand(layers: list[dict], rule: str) -> list[dict]:
    """Expand full layers over the tp grid.

    rule "parts": column shards require every fused part's dim 0 to divide
    by tp (extract-weights, physical). rule "fused": column shards require
    only the fused n to divide (certclass atTP, superset; exclusion only).
    Row shards divide k under both rules. Cells below the engagement floor
    are pruned exactly as certclass does.
    """
    out = []
    for layer in layers:
        n, k, axis = layer["n"], layer["k"], layer["axis"]
        tps = [1] if axis == "none" else TPS
        for tp in tps:
            sn, sk = n, k
            if layer.get("qkv") and tp > 1 and rule == "parts":
                # vLLM QKVParallelLinear (physical layout, targets): query
                # heads shard (nh % tp == 0 required); KV heads shard when
                # tp <= nkv (nkv % tp == 0), else each is replicated so every
                # rank carries max(1, nkv//tp) KV heads. A plain fused-n shard
                # is only correct in the first case. The "fused" rule keeps
                # the plain shard on purpose: it mirrors certclass atTP for
                # the exclusion set and must not diverge from it.
                nh, nkv, hd = layer["qkv"]
                if nh % tp:
                    continue
                if not (nkv % tp == 0 or tp % nkv == 0):
                    continue
                kv_per_rank = max(1, nkv // tp)
                sn = (nh // tp + 2 * kv_per_rank) * hd
            elif axis == "col" and tp > 1:
                parts = layer["parts"] or [n]
                if rule == "parts" and any(p % tp for p in parts):
                    continue
                if n % tp:
                    continue
                sn = n // tp
            elif axis == "row" and tp > 1:
                if k % tp:
                    continue
                sk = k // tp
            if sn < MIN_N or sk < MIN_K:
                continue
            out.append({"layer": layer["layer"], "tp": tp, "n": sn, "k": sk,
                        "moe": layer["moe"]})
    return out


def load_pins(path: str) -> dict:
    """Accept either a bare {label: {repo, revision}} map or a previous
    dictionary output (whose targets carry label/repo/revision)."""
    data = json.loads(Path(path).read_text())
    if "targets" in data:
        return {t["label"]: {"repo": t.get("repo"), "revision": t.get("revision")}
                for t in data["targets"] if t.get("revision")}
    return data


def fetch_config(repos: list[str], pin: dict | None) -> tuple[str, str, dict]:
    """Resolve (repo, revision sha, config dict), trying repos in order.
    Raises the last error if none resolves."""
    from huggingface_hub import HfApi, hf_hub_download

    if pin:
        repos = [pin["repo"]]
    last: Exception | None = None
    for repo in repos:
        try:
            revision = pin["revision"] if pin else HfApi().model_info(repo).sha
            if not revision:
                raise RuntimeError("could not resolve a revision sha")
            path = hf_hub_download(repo_id=repo, filename="config.json",
                                   revision=revision)
            return repo, revision, json.loads(Path(path).read_text())
        except Exception as e:  # noqa: BLE001 (record and try the next mirror)
            last = e
    raise last if last else RuntimeError("no repos listed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.environ.get("KESHI_SHAPE_DICT", str(DEFAULT_OUT)))
    ap.add_argument("--pins", help="previous output (or label->repo/revision map) "
                    "to re-fetch the exact same revisions")
    args = ap.parse_args()
    pins = load_pins(args.pins) if args.pins else {}

    targets_out = []
    unresolved = 0
    for t in TARGETS:
        label = t["label"]
        rec = {"label": label, "role": t["role"], "candidateRepos": t["repos"]}
        try:
            repo, revision, cfg = fetch_config(t["repos"], pins.get(label))
        except Exception as e:  # noqa: BLE001
            rec.update(status="UNRESOLVED", error=f"{type(e).__name__}: {e}")
            unresolved += 1
            targets_out.append(rec)
            print(f"UNRESOLVED {label}: {rec['error']}", file=sys.stderr)
            continue
        layers, fields, notes = derive_layers(cfg)
        layers = layers + PEARL_EXTRA_LAYERS.get(label, [])
        for extra in PEARL_EXTRA_LAYERS.get(label, []):
            notes.append(f"manual row {extra['layer']}: {extra['note']}")
        rule = "fused" if t["role"] == "pearl-reference" else "parts"
        entries = expand([{"parts": None, "moe": False, **l} for l in layers], rule)
        rec.update(status="ok" if layers else "UNRESOLVED",
                   repo=repo, revision=revision, fields=fields, notes=notes,
                   layers=[{k: v for k, v in l.items() if k not in ("parts",)}
                           for l in layers],
                   entries=entries)
        if not layers:
            unresolved += 1
        mirror = " (mirror)" if repo != t["repos"][0] else ""
        print(f"ok {label}: {repo}{mirror} @ {revision[:12]} "
              f"layers={len(layers)} entries={len(entries)}")
        targets_out.append(rec)

    # Assert the derived pearl-reference entries cover the frozen T2 grid.
    pearl_pairs = {(e["n"], e["k"])
                   for t in targets_out if t["role"] == "pearl-reference"
                   for e in t.get("entries", [])}
    missing = []
    for name, n, k, col in MODELS_GO_ROWS:
        for tp in TPS:
            sn, sk = n, k
            if col:
                if n % tp:
                    continue
                sn = n // tp
            else:
                if k % tp:
                    continue
                sk = k // tp
            if sn < MIN_N or sk < MIN_K:
                continue
            if (sn, sk) not in pearl_pairs:
                missing.append(f"{name}@tp{tp} ({sn}, {sk})")
    if missing:
        print("FATAL: derived pearl-reference entries do not cover the frozen "
              "certclass grid:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1

    out = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc)
                       .isoformat(timespec="seconds"),
        "tps": TPS, "minN": MIN_N, "minK": MIN_K,
        "conventions": "extract-weights.py fusion/sharding; certclass floor; "
                       "pearl-reference expanded with the fused rule, targets "
                       "with the per-part rule",
        "unresolved": unresolved,
        "targets": targets_out,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    resolved = sum(1 for t in targets_out if t.get("status") == "ok")
    print(f"\nwrote {out_path}: {resolved} resolved, {unresolved} unresolved, "
          f"{sum(len(t.get('entries', [])) for t in targets_out)} grid entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
