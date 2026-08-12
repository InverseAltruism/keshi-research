# OBS-010: Non-pearl-ai shape sweep, ended vs moved

Dated observation note, internal research record. Recorded 2026-08-10.
**Status: necessary-condition screen, exploratory, not pre-registered.**
**Status revision, 2026-08-11:** "internal research record" is superseded
as to publication only. ADR-0014 re-scoped publication to the site
package and this note ships inside it; the exploratory,
not-pre-registered status and §2's coverage bounds are unchanged.
Covers roadmap C4 (the "ended vs moved" question; PLAN-002 §9.3 item 5,
STATUS-2026-08-09 §5 item 6). **Verdict: ENDED within §2's bounds**, and
the verdict criterion is computed in code, never eyeballed: the tool
itself prints a per-(model, era) PASS/FAIL with reasons and the summary
line quoted in §4. Everything regenerates from two frozen committed
inputs via `scripts/shape-sweep-nonpearl.py` plus the companion
`scripts/nonllm-shape-check.py`; both tools' outputs are committed
verbatim as [DS-008](datasets/DS-008-shape-sweep-v1/MANIFEST.md), and
every number in this note is read from those committed artifacts or from
a command stated inline.

Sources: frozen [DS-001](datasets/DS-001-classification-v1/MANIFEST.md)
(declared per-block m, n, k, class; non-empty blocks h1-96,405,
n = 96,405, genesis EMPTY excluded);
[`shape-dictionary-v1.json`](shape-dictionary-v1.json) (generated
2026-08-09, config-derived at pinned revisions: 36 checkpoints, of which
4 pearl-reference and 32 non-pearl targets, 603 grid entries); the
committed DS-002/DS-002b results for the era-boundary verification (§3);
Keshi's internal protocol notes (Certificate internals) for the
consensus shape floor; nine further checkpoints pinned by revision sha
inside `nonllm-shape-check.py` (§6). Unit of analysis throughout:
blocks, one certificate per block. Checkpoint names below are
subject-matter identifiers.

Label discipline, per [`metrics.md`](../metrics.md) §4: only a
byte-exact `hash_b` match is "attested model-weight mining", and nothing
is ever "certified inference". A shape match is strictly weaker than
either: it is a necessary condition, never sufficient, and this note
contains no new weight attestations at all.

## 1. Question

OBS-005/DS-002 established that attested model-weight mining was a
launch-week phenomenon of a handful of operators. Its scan could only
test the four `pearl-ai` reference checkpoints, so the standing "~96%
of current blocks declare dims matching no reference model"
(STATUS-2026-08-09 §2, current-window blocks) meant "not shaped like
those four". Two hypotheses fit
that record: real-weight mining ENDED, or it MOVED to weights the scan
never searched. This sweep bounds the one branch of "moved" that
declared data can reach: moved to a KNOWN PUBLIC checkpoint whose
linear-layer geometry is in the dictionary. It reads only declared
certificate dims, which are free choices; consensus never checks them
against any model (`pearl-notes.md` §Certificate internals).

## 2. What the verdict can and cannot mean

Stated before the result so the result cannot be over-read.

1. A shape match is necessary for real mining of a dictionary
   checkpoint under the standard serving layouts, and nothing more.
   Only a `hash_b` weight match proves committed operands (OBS-005
   §0.2). A shape match here would have justified a targeted weight
   scan, not a finding.
2. A non-match proves nothing about private models, fine-tunes,
   requantized variants, training runs, or synthetic work. Those are
   mutually indistinguishable on chain by construction (OBS-005 §0.1,
   the verifiability ceiling), and §7 restates what that does to the
   "moved" hypothesis.
3. The screen assumes whole-layer tiles under the dictionary's fusion
   and tensor-parallel sharding conventions. A miner slicing
   nonstandard tiles from a known checkpoint would evade it (inferred
   bound; the same genus as PREREG-003's byte-order probes).
4. Coverage is finite and partially shadowed (§5): "any known public
   checkpoint" means the 36 dictionary checkpoints minus the shadowing
   losses, nothing broader.

## 3. Method

Dictionary: for each checkpoint, every mineable linear layer expanded
in the fused serving layout (`qkv_fused`, `o`, `gate_up_fused`, `down`,
MoE variants with their (experts, topK) trailer) across tp in
{1, 2, 4, 8}, keeping entries with n >= 256 and k >= 1,024 (the
dictionary floors; `minN`/`minK` in the dictionary header). The k floor
coincides with the consensus floor; the n floor is the vLLM miner
engagement floor (`certclass.go` MinN), so sub-256-n declarations are
consensus-legal but out of dictionary scope. Dims are config-derived at
pinned revisions; per-tensor variants invisible in a config are a known
blind-spot class. The one known instance, the Gemma-4-31B
full-attention o variant (5376, 16384) found at h68,332, is present in
this dictionary build (verified by command against the committed
dictionary), and PREREG-003 R1 closes the class for the pearl
checkpoints by reading safetensors headers.

Matching mirrors the frozen T2 semantics: exact ordered (n, k) equality;
dense rows require an empty MoE trailer, expert rows the exact trailer
(trailer-inconsistent hits are reported separately, never counted). Any
pair a pearl-reference checkpoint can produce (57 distinct pairs) is
excluded from the non-pearl increment wherever it also appears,
leaving 241 distinct non-pearl pairs. Cross-checks from the run: 0
DS-001 T2-matched blocks fall outside the pearl exclusion set (the
wanted value is 0), and 11 blocks are pearl-shaped here without being
DS-001 T2-matched (expected: config-derived rows the frozen classifier
lacked, h68,332 among them).

Era split: the attested-mining extinction boundary h54,972, then the
three fork heights 71,935 / 91,630 / 96,251. The boundary's meaning was
re-verified by command over the committed DS-002, DS-002b-gemma and
DS-002b-o-tp48 results (1,109 matched rows, 1,109 distinct heights):
the last matched height at or below 54,972 is exactly 54,972, and only
three matched heights sit above it (56,217 and 62,319 in the Gemma
results, 60,881 in DS-002), plus the h68,332 match recorded in the
roadmap §8.4 erratum note (source: ROADMAP.md, "the last attested
model-weight block moves ... to h68,332"). All four stragglers declare
pearl-reference pairs (verified by command against DS-001 and the
dictionary), so they sit in S2's pearl column below and cannot leak
into the non-pearl increment. "Post-extinction" in this note therefore
means "after the contiguous attested era", with exactly these four
known attested stragglers inside S2.

Specificity bar, computed in code per (model, era): PASS only if the
model matched at least 2 distinct (n, k) pairs from its grid in that
era, or exactly one pair that is simultaneously dictionary-unique (no
other target shares it), has neither dim a power of two, and shows
varying m (more than one m value, and not the constant m == n
signature). Everything else is compatible with coincidence. The
constant m == n reading as a dims-grinder rather than batched inference
is inferred, not proven; the bar only demands that a "moved" candidate
look unlike one.

## 4. Result

The tool's per-era table, verbatim from the committed
`sweep-report.txt` (denominators in the legend):

```
Per-era table. Denominators: blocks = all non-empty DS-001 blocks in the segment; p% over blocks; m%np and p2%np over NON-pearl-shaped blocks in the segment; pow2n counts non-pearl blocks whose declared n is a power of two; none = matches no dictionary shape at all.
segment                                   blocks   pearl     p%  match     m%   m%np  trlr   pow2n  p2%np    none
-----------------------------------------------------------------------------------------------------------------
S1 attested era        h1-54,972           54972   50171  91.27    371   0.67   7.73     0    4592  95.65    4430
S2 post-extinction     h54,973-71,934      16962    2508  14.79      0   0.00   0.00     0   13606  94.13   14454
S3 moe-window          h71,935-91,629      19695     808   4.10     71   0.36   0.38     0   14881  78.79   18816
S4 dense-only          h91,630-96,250       4621     226   4.89      9   0.19   0.20     0    2906  66.12    4386
S5 rank-penalty        h96,251-              155       3   1.94      0   0.00   0.00     0      71  46.71     152
```

Reading it, all figures from the committed run:

- S2, the cleanest window (16,962 blocks, of which 14,454
  non-pearl-shaped): zero dictionary hits of any kind.
- S5 (155 blocks, 152 non-pearl-shaped): zero hits.
- S3 + S4 carry 80 raw hits out of 24,316 blocks in those two segments
  (23,282 of them non-pearl-shaped); across all of S2-S5 that is 80 of
  41,433 non-empty post-extinction blocks. Every one of the 80 is a
  coincidence by the computed bar; they reduce to two shapes:
  - (5120, 4096), 68 blocks, h75,253-93,837: shared by 6 grid cells of
    5 different models (o and down cells of Mistral-Small-24B,
    Llama-4-Scout-17B-16E, Mistral-Nemo-12B, Qwen3-32B, DeepSeek-V2),
    one dim a power of two, and every block at constant m = 5120 = n.
  - (12288, 4096), 12 blocks, h75,309-93,087: Qwen3-8B gate_up tp2,
    one dim a power of two, every block at constant m = 12288 = n.
- S1's 371 hits are (4096, 8192), all at constant m = 4096 = n, both
  dims powers of two, nominally Qwen3-235B-A22B o at tp1. Same
  verdict: coincidence-compatible, and inside the attested era anyway.
- Trailer-inconsistent shape hits: 0 in every segment. The third-party
  pearl-quantized Qwen3.6-27B-heretic checkpoint: 0 blocks in any era.
- All-era raw hits: 451 blocks; every (model, era) candidate fails the
  bar, each with its printed reason (constant m == n, power-of-two
  dims, or a shape shared across models).

The tool's committed summary line:

> Bar summary: 0 (model, era) pairs PASS the specificity bar across all
> eras. A zero here is the 'ENDED (no move to a known public
> checkpoint)' verdict.

**ENDED, exactly this much:** in 41,433 non-empty post-extinction
blocks, no model in the dictionary shows a signature that survives the
specificity bar; the clean windows S2 and S5 show zero raw hits over
14,454 and 152 non-pearl-shaped blocks respectively. Useful-work mining
of a known public checkpoint's standard serving geometry did not resume
under a different model family within the dictionary's coverage (§5).
The verdict says nothing about weights the chain cannot verify (§7),
and it is falsifiable by future blocks: two post-extinction
certificates matching distinct cells of one target's grid, or a single
certificate on a dictionary-unique cell with neither dim a power of two
and m unequal to n, would flip the bar to PASS.

## 5. Coverage and shadowing caveats

The pearl exclusion protects the increment from false attribution and
costs coverage; both losses are printed by the run.

- Fully shadowed targets, 5 of the 32 non-pearl targets: every grid
  cell equals a pearl-reference pair, so the sweep has zero
  discriminating power for Llama-3.1-8B-base, Llama-3.1-70B-base,
  Mistral-7B-v0.3, Mixtral-8x7B, and Qwen3-30B-A3B-base (dimension
  twins of the pearl set). Mining of these is indistinguishable from
  pearl-reference-shaped traffic by geometry alone.
- Partially shadowed targets, 16 of the 32 (shadowed cells / grid
  cells): DeepSeek-V2 2/29, DeepSeek-V2-Lite 5/26, DeepSeek-V3 4/30,
  GLM-4.5-Air 3/26, Gemma-2-9B 3/15, Gemma-3-27B 14/15, Kimi-K2 4/30,
  Llama-3.2-3B 1/14, Llama-4-Scout-17B-16E 4/23, Mistral-Nemo-12B
  1/15, Mistral-Small-24B 2/15, Mixtral-8x22B 1/15, Qwen2.5-72B 8/16,
  Qwen3-235B-A22B 6/13, Qwen3-32B 2/16, Qwen3-8B 9/15. Gemma-3-27B is
  the worst case, screened at 1 of its 15 cells.
- Honest coverage statement: the non-pearl screen genuinely covers 27
  of its 32 target checkpoints, and of those 27, 11 at their full grid
  and 16 only partially. Counting the 4 pearl-reference checkpoints,
  which the table tracks in the pearl column rather than the increment
  (as a set; their shared pairs are not attributable to one of the
  four), 31 of the 36 dictionary checkpoints remain geometrically
  trackable. Shorthand: 31 of 36, partially.
- Dictionary floors: entries need n >= 256 and k >= 1,024 over tp in
  {1, 2, 4, 8}, so sub-floor cells of covered checkpoints are absent
  by construction (this is why per-target grids differ in size, e.g.
  Llama-3.2-3B at 14 cells).
- Unresolved dictionary targets in this build: 0 (the tool prints any).

## 6. The non-LLM screen: vision, audio, embedding

The dictionary is LLM-only, so a companion screen
(`scripts/nonllm-shape-check.py`, committed output `nonllm.json` /
`nonllm-report.txt` in DS-008) tests the same necessary condition for
nine popular non-LLM checkpoints. Dims are read from each pinned
checkpoint's safetensors headers over HTTP range requests, never from
config defaults, across all layers; expansion uses the same fused
serving conventions at tp = 1 only, so the screen bounds unsharded
serving geometry and nothing else. Checkpoints (pinned by revision sha
in the script and recorded in `nonllm.json`): CLIP-ViT-L-14,
CLIP-ViT-H-14, SigLIP-So400m, DINOv2-giant, InternViT-6B (vision),
Whisper-large-v3 (audio), BERT-large, BGE-large-en-v1.5, BERT-base
(embedding).

The nine checkpoints yield 24 distinct (n, k) hypotheses; the committed
run classifies them before counting:

| Class | Pairs | DS-001 blocks declaring them |
|---|---|---|
| TESTED (discriminating) | 18 | 0 |
| PEARL_SHADOWED | 2 | 0 |
| PROTOCOL_EXCLUDED | 4 | 0 |

- 20 of the 24 pairs are protocol-legal hypotheses; zero of the 96,405
  non-empty DS-001 blocks declare any of them (and the 4 excluded
  pairs also appear in zero blocks, as consensus requires).
- The 2 pearl-shadowed pairs, (4096, 1024) and (1536, 4096), equal
  pearl-reference pairs (Llama-3.1-8B o tp4 and qkv_fused tp4), so
  they would have had zero discriminating power even with hits; they
  happen to have none.
- Consensus k-floor caveat, binding for interpretation: the verifier
  enforces k >= 1,024 and k % 64 == 0
  (`zk-pow` `sanity_checks.rs:24-55`, cited via `pearl-notes.md`
  §Certificate internals), so 4 hypothesis pairs cannot appear in any
  certificate: the k = 768 geometries of BERT-base and the
  CLIP-ViT-L-14 text tower (3 pairs), and SigLIP-So400m's mlp_out
  (1152, 4304) with k % 64 == 16. The absence of small vision and text
  encoders below the floor is therefore partly a protocol artifact,
  not evidence about miner behavior; for the 768-class the exclusion
  is partial, since its mlp output pair (768, 3072) is legal, was
  tested, and is also absent. Geometry that clears the floor (all 20
  legal pairs, from the 768-class mlp output through every class at
  hidden size 1,024 and up) is genuinely absent from all 96,405
  blocks' declared dims.
- Bounds: nine checkpoints, fused layout, tp = 1. This is a spot
  screen of the most-deployed encoder geometries, not a census of
  non-LLM models; sharded or otherwise nonstandard tilings of these
  checkpoints are untested (§2, item 3).

## 7. What this does not establish

- No statement about useful work in general. Per the OBS-005 §0.1
  ceiling, `job_key` is per-block, so only public static checkpoints
  are externally verifiable; private models, customer fine-tunes,
  locally requantized variants, evolving training weights and
  synthetic noise remain mutually indistinguishable on chain. "Moved
  to weights the chain cannot verify" is untestable by design, and
  this sweep neither supports nor damages it.
- Not proof of synthetic work. The 37,888 post-extinction
  non-pearl-shaped blocks match no dictionary shape (or only
  coincidence-compatible ones), which bounds what they are not; it
  does not identify what they are.
- Not a weight attestation. No `hash_b` was computed here; a shape
  match, had one survived the bar, would itself have proven nothing
  without a subsequent scan.
- Not proof of absence beyond the search space: 36 LLM checkpoints
  minus the §5 shadowing losses, 9 non-LLM checkpoints, standard fused
  layouts, tp grid {1, 2, 4, 8} (LLM) and tp = 1 (non-LLM), floors
  n >= 256 / k >= 1,024. A checkpoint outside the dictionary, or a
  nonstandard tiling of one inside it, is not excluded.

## 8. Reproduction

From the repo root; both tools are byte-deterministic given the frozen
inputs (re-runs this session produced byte-identical JSON and reports):

```
python3 scripts/shape-sweep-nonpearl.py --json /tmp/sweep.json
diff /tmp/sweep.json docs/research/datasets/DS-008-shape-sweep-v1/sweep.json

python3 scripts/nonllm-shape-check.py --json /tmp/nonllm.json
diff /tmp/nonllm.json docs/research/datasets/DS-008-shape-sweep-v1/nonllm.json
```

The non-LLM tool fetches safetensors headers for the pinned revisions
over the network; everything else is offline against the committed
inputs. `--census 7d` on the sweep adds a live-API cross-check, labeled
LIVE and NOT frozen, and is not part of DS-008. File hashes:
[DS-008 MANIFEST](datasets/DS-008-shape-sweep-v1/MANIFEST.md). The
dataset is append-only; corrections ship as a new version directory
with an errata note, per `ERRATA-POLICY.md`.
