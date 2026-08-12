#!/usr/bin/env python3
"""Non-LLM (vision / audio / embedding) shape screen over DS-001 (C4 rider).

The C4 sweep (shape-sweep-nonpearl.py) bounds the "moved to a known public
LLM checkpoint" branch of the ended-vs-moved question. This companion
bounds the analogous non-LLM branch: declared certificate (n, k) dims that
match the linear-layer geometry of popular open vision, audio, and
text-embedding checkpoints. As in the sweep, a shape match is necessary
but never sufficient (only a hash_b weight match proves mining), and a
non-match says nothing about private or custom models.

Dims are read from each pinned checkpoint's safetensors headers over HTTP
range requests, never from config defaults, so per-layer dim variants
would be caught (the h68,332 lesson). Layer expansion mirrors the shape
dictionary's target conventions: fused serving layout (qkv_fused, o,
mlp_in, mlp_out; DINOv2's fused SwiGLU weights_in is the gate_up_fused
analogue), at tp = 1 only. These encoders are served whole or replicated,
not tensor-parallel sharded; the LLM sweep's tp grid covers the sharded
regime.

Every distinct (n, k) hypothesis is classified before counting:
  PROTOCOL_EXCLUDED  fails the consensus shape floor (k >= 1,024 and
                     k % 64 == 0, zk-pow sanity_checks.rs via
                     docs/pearl-notes.md) or the engagement floor
                     n >= 256 (certclass MinN). No certificate with these
                     dims can exist, so the absence of such models from
                     the chain is a protocol artifact, not evidence.
  PEARL_SHADOWED     equals a pearl-reference dictionary pair; blocks
                     declaring it are already counted pearl-shaped, so
                     the hypothesis has zero discriminating power.
  TESTED             counted against every non-empty DS-001 block by
                     exact ordered (n, k) equality; overlap with a
                     non-pearl LLM dictionary pair is reported inline.

Env / args mirror the other ds00x scripts:
  KESHI_DS001_DIR   DS-001 dataset dir (default: the committed copy)
  KESHI_SHAPE_DICT  dictionary path    (default: docs/research/shape-dictionary-v1.json)
Usage: nonllm-shape-check.py [--json OUT.json]
"""

import argparse
import gzip
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DS001 = HERE.parent / "docs" / "research" / "datasets" / "DS-001-classification-v1"
DEFAULT_DICT = HERE.parent / "docs" / "research" / "shape-dictionary-v1.json"

# Consensus shape floor (zk-pow sanity_checks.rs, cited in
# docs/pearl-notes.md: rank and tile rules omitted, they do not constrain
# (n, k) hypotheses) plus the vLLM engagement floor MinN (certclass).
MIN_K = 1024
K_MULTIPLE = 64
MIN_N = 256

BOUNDARY = 54_972
FORKS = (71_935, 91_630, 96_251)
SEGMENTS = [
    ("S1", 1, BOUNDARY),
    ("S2", BOUNDARY + 1, FORKS[0] - 1),
    ("S3", FORKS[0], FORKS[1] - 1),
    ("S4", FORKS[1], FORKS[2] - 1),
    ("S5", FORKS[2], 1 << 62),
]

# Checkpoints pinned by revision sha (resolved 2026-08-10). Families:
# vision, audio, embedding. Labels are subject-matter identifiers.
PINS = [
    {"label": "CLIP-ViT-L-14", "family": "vision+embedding",
     "repo": "openai/clip-vit-large-patch14",
     "revision": "32bd64288804d66eefd0ccbe215aa642df71cc41", "style": "clip"},
    {"label": "CLIP-ViT-H-14", "family": "vision+embedding",
     "repo": "laion/CLIP-ViT-H-14-laion2B-s32B-b79K",
     "revision": "1c2b8495b28150b8a4922ee1c8edee224c284c0c", "style": "clip"},
    {"label": "SigLIP-So400m", "family": "vision+embedding",
     "repo": "google/siglip-so400m-patch14-384",
     "revision": "9fdffc58afc957d1a03a25b10dba0329ab15c2a3", "style": "clip"},
    {"label": "DINOv2-giant", "family": "vision",
     "repo": "facebook/dinov2-giant",
     "revision": "611a9d42f2335e0f921f1e313ad3c1b7178d206d", "style": "dinov2"},
    {"label": "InternViT-6B", "family": "vision",
     "repo": "OpenGVLab/InternViT-6B-448px-V1-5",
     "revision": "03e138c81d3fd538c77439fd43a42c067d827427", "style": "internvit"},
    {"label": "Whisper-large-v3", "family": "audio",
     "repo": "openai/whisper-large-v3",
     "revision": "06f233fe06e710322aca913c1bc4249a0d71fce1", "style": "whisper"},
    {"label": "BERT-large", "family": "embedding",
     "repo": "google-bert/bert-large-uncased",
     "revision": "6da4b6a26a1877e173fca3225479512db81a5e5b", "style": "bert"},
    {"label": "BGE-large-en-v1.5", "family": "embedding",
     "repo": "BAAI/bge-large-en-v1.5",
     "revision": "d4aa6901d3a41ba39fb536a557fa166f842b0e09", "style": "bert"},
    {"label": "BERT-base", "family": "embedding",
     "repo": "google-bert/bert-base-uncased",
     "revision": "86b5e0934494bd15c9632b12f734a8a67f723594", "style": "bert"},
]

# Tensor-name recognizers per checkpoint style: map a 2-D weight to
# (tower, layer index, part). Parts q/k/v fuse to qkv_fused per
# (tower, layer, attention block); qkv is a header-fused qkv (InternViT).
STYLES = {
    "clip": re.compile(
        r"^(?P<tower>text_model|vision_model)\.encoder\.layers\.(?P<idx>\d+)\."
        r"(?:self_attn\.(?P<attn>q|k|v|out)_proj|mlp\.fc(?P<fc>[12]))\.weight$"),
    "dinov2": re.compile(
        r"^(?P<tower>encoder)\.layer\.(?P<idx>\d+)\."
        r"(?:attention\.attention\.(?P<attn>query|key|value)|"
        r"attention\.output\.(?P<o>dense)|mlp\.weights_(?P<fc>in|out))\.weight$"),
    "internvit": re.compile(
        r"^(?P<tower>encoder)\.layers\.(?P<idx>\d+)\."
        r"(?:attn\.(?P<attn>qkv|proj)|mlp\.fc(?P<fc>[12]))\.weight$"),
    "whisper": re.compile(
        r"^model\.(?P<tower>encoder|decoder)\.layers\.(?P<idx>\d+)\."
        r"(?:(?P<blk>self_attn|encoder_attn)\.(?P<attn>q|k|v|out)_proj|"
        r"fc(?P<fc>[12]))\.weight$"),
    "bert": re.compile(
        r"^(?:bert\.)?(?P<tower>encoder)\.layer\.(?P<idx>\d+)\."
        r"(?:attention\.self\.(?P<attn>query|key|value)|"
        r"attention\.output\.(?P<o>dense)|"
        r"(?P<fc>intermediate\.dense|output\.dense))\.weight$"),
}

QKV_PART = {"q": "q", "k": "k", "v": "v",
            "query": "q", "key": "k", "value": "v"}
MLP_IN = {"1", "in", "intermediate.dense"}


def fetch(url, headers=None, attempts=4):
    req = urllib.request.Request(url, headers=headers or {})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)


def st_header(repo, rev, fname):
    url = f"https://huggingface.co/{repo}/resolve/{rev}/{fname}"
    n = struct.unpack("<Q", fetch(url, {"Range": "bytes=0-7"}))[0]
    return json.loads(fetch(url, {"Range": f"bytes=8-{8 + n - 1}"}).decode())


def st_files(repo, rev):
    try:
        idx = json.loads(fetch(
            f"https://huggingface.co/{repo}/resolve/{rev}/model.safetensors.index.json"))
        return sorted(set(idx["weight_map"].values()))
    except urllib.error.HTTPError:
        return ["model.safetensors"]


def derive_hypotheses():
    """Return {(n, k): set of attribution strings}, plus per-pin tensor
    counts for the report."""
    hyp: dict[tuple[int, int], set] = defaultdict(set)
    stats = []
    for pin in PINS:
        rx = STYLES[pin["style"]]
        parts = defaultdict(dict)   # (tower, idx, blk) -> part -> (n, k)
        matched = 0
        for f in st_files(pin["repo"], pin["revision"]):
            for name, spec in st_header(pin["repo"], pin["revision"], f).items():
                if name == "__metadata__" or len(spec.get("shape", [])) != 2:
                    continue
                m = rx.match(name)
                if not m:
                    continue
                matched += 1
                g = m.groupdict()
                n, k = spec["shape"]
                tower, idx = g["tower"], int(g["idx"])
                blk = g.get("blk") or "attn"
                who = f"{pin['label']}/{tower}"
                xattn = "xattn_" if g.get("blk") == "encoder_attn" else ""
                if g.get("attn") in QKV_PART:
                    parts[(tower, idx, blk)][QKV_PART[g["attn"]]] = (n, k)
                elif g.get("attn") == "qkv":
                    hyp[(n, k)].add(f"{who}/qkv_fused")
                elif g.get("attn") in ("out", "proj") or g.get("o"):
                    hyp[(n, k)].add(f"{who}/{xattn}o")
                elif g.get("fc") in MLP_IN:
                    hyp[(n, k)].add(f"{who}/mlp_in")
                else:
                    hyp[(n, k)].add(f"{who}/mlp_out")
        for (tower, idx, blk), p in parts.items():
            if set(p) == {"q", "k", "v"} and len({v[1] for v in p.values()}) == 1:
                nf = sum(v[0] for v in p.values())
                xattn = "xattn_" if blk == "encoder_attn" else ""
                hyp[(nf, p["q"][1])].add(
                    f"{pin['label']}/{tower}/{xattn}qkv_fused")
        stats.append((pin["label"], pin["repo"], pin["revision"], matched))
        print(f"  {pin['label']:<18} {pin['repo']} @ {pin['revision'][:12]} "
              f"({matched} linear tensors)")
    return hyp, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ds001", default=os.environ.get("KESHI_DS001_DIR", str(DEFAULT_DS001)))
    ap.add_argument("--dict", default=os.environ.get("KESHI_SHAPE_DICT", str(DEFAULT_DICT)))
    ap.add_argument("--json", help="write the structured result here")
    args = ap.parse_args()

    d = json.loads(Path(args.dict).read_text())
    pearl_pairs, llm_pairs = set(), defaultdict(set)
    for t in d["targets"]:
        for e in t.get("entries", []):
            if t["role"] == "pearl-reference":
                pearl_pairs.add((e["n"], e["k"]))
            elif t["role"] == "target":
                llm_pairs[(e["n"], e["k"])].add(t["label"])

    print("checkpoint dims from safetensors headers (pinned revisions):")
    hyp, stats = derive_hypotheses()

    rows = []
    for (n, k), who in sorted(hyp.items()):
        if n < MIN_N or k < MIN_K or k % K_MULTIPLE:
            reasons = []
            if k < MIN_K:
                reasons.append(f"k={k} < {MIN_K}")
            if k % K_MULTIPLE:
                reasons.append(f"k % {K_MULTIPLE} == {k % K_MULTIPLE}")
            if n < MIN_N:
                reasons.append(f"n={n} < {MIN_N}")
            cls, why = "PROTOCOL_EXCLUDED", "; ".join(reasons)
        elif (n, k) in pearl_pairs:
            cls, why = "PEARL_SHADOWED", "equals a pearl-reference pair"
        else:
            cls, why = "TESTED", ""
            if (n, k) in llm_pairs:
                why = "also an LLM dictionary pair: " + ", ".join(sorted(llm_pairs[(n, k)]))
        rows.append({"n": n, "k": k, "class": cls, "note": why,
                     "sources": sorted(who),
                     "blocks": 0, "bySegment": [0] * len(SEGMENTS), "m": Counter()})
    by_pair = {(r["n"], r["k"]): r for r in rows}

    blocks_path = Path(args.ds001) / "blocks.jsonl.gz"
    tip = total = 0
    with gzip.open(blocks_path, "rt") as f:
        for line in f:
            r = json.loads(line)
            h = r["height"]
            if h == 0 or r.get("class") == "EMPTY":
                continue
            tip = max(tip, h)
            total += 1
            row = by_pair.get((r["n"], r["k"]))
            if row is None:
                continue
            row["blocks"] += 1
            for i, (_, lo, hi) in enumerate(SEGMENTS):
                if lo <= h <= hi:
                    row["bySegment"][i] += 1
                    break
            row["m"][r["m"]] += 1

    n_tested = sum(1 for r in rows if r["class"] == "TESTED")
    n_shad = sum(1 for r in rows if r["class"] == "PEARL_SHADOWED")
    n_excl = sum(1 for r in rows if r["class"] == "PROTOCOL_EXCLUDED")
    hits = [r for r in rows if r["class"] == "TESTED" and r["blocks"]]

    print(f"\ncorpus: {blocks_path} (non-empty blocks h1-{tip}, n={total})")
    print(f"hypotheses: {len(rows)} distinct (n, k) pairs from "
          f"{len(PINS)} pinned checkpoints; {n_tested} TESTED, "
          f"{n_shad} PEARL_SHADOWED, {n_excl} PROTOCOL_EXCLUDED")
    hdr = f"{'(n, k)':<16}{'class':<20}{'blocks':>7}  sources / note"
    print("\n" + hdr)
    print("-" * 100)
    for r in sorted(rows, key=lambda r: (r["class"] != "TESTED",
                                         r["class"], r["n"], r["k"])):
        src = "; ".join(r["sources"])
        note = f"  [{r['note']}]" if r["note"] else ""
        seg = "/".join(str(c) for c in r["bySegment"])
        mtop = (" m: " + ", ".join(f"{m}x{c}" for m, c in r["m"].most_common(3))
                if r["m"] else "")
        print(f"({r['n']}, {r['k']})".ljust(16)
              + f"{r['class']:<20}{r['blocks']:>7}  {src}{note}"
              + (f"\n{'':36}by-era {seg}{mtop}" if r["blocks"] else ""))
    print(f"\nResult: {len(hits)} of {n_tested} TESTED hypotheses have any "
          f"DS-001 block declaring their exact (n, k)"
          + (": " + "; ".join(f"({r['n']},{r['k']}) {r['blocks']}" for r in hits)
             if hits else "."))
    print("Bounds: PROTOCOL_EXCLUDED hypotheses are untestable on this "
          "chain (their absence is a protocol artifact); PEARL_SHADOWED "
          "hypotheses have zero discriminating power; a TESTED zero bounds "
          "only these exact serving geometries at tp = 1.")

    if args.json:
        out = {
            "dictionary": str(args.dict), "ds001": str(blocks_path),
            "tip": tip, "nonEmptyBlocks": total,
            "floors": {"minK": MIN_K, "kMultiple": K_MULTIPLE, "minN": MIN_N},
            "boundary": BOUNDARY, "forks": list(FORKS),
            "checkpoints": [{"label": l, "repo": r, "revision": v,
                             "linearTensors": c} for l, r, v, c in stats],
            "hypotheses": [{**r, "m": dict(r["m"].most_common())} for r in rows],
            "tested": n_tested, "pearlShadowed": n_shad,
            "protocolExcluded": n_excl, "testedWithHits": len(hits),
        }
        Path(args.json).write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
