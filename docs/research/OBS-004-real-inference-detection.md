# OBS-004: Real-inference detection results

Dated observation note, 2026-08-06. This note fills the pre-written
interpretation table of
[`PREREG-001`](PREREG-001-real-inference-detection.md), as frozen for this
run at `11a517a02cedfb97360da95bfaf8e4f114374dfd`, with the measured numbers from
dataset [`DS-001`](datasets/DS-001-classification-v1/): 96,406 canonical
certificates at heights 0–96,405 (the run pinned `--to 96405`), decoder v1. Nothing in §§1–4 below
is an interpretation not written into the prereg before the run; anything
else is confined to §5 "Exploratory (post-hoc)".

That commit is what DS-001 was produced under and what its manifest records.
The document has since taken a dated typography erratum (2026-08-07) that
changed no hypothesis, test, threshold or table value; the erratum itself
carries the command to diff the two versions. Read the hash here as the
provenance of this run, not as a claim about the document's current bytes.

**Binding language (PREREG-001 §0):** every statement is shape *consistency*.
No result here proves inference occurred, that a model was served, or that any
computation was fresh. Per-block accusations are not made.

## 1. Class distribution

| Class | Blocks | Share |
|---|---|---|
| `CUSTOM` (¬T1 ∧ ¬T2) | 38,387 | 39.8% |
| `MODEL_SHAPED_CUSTOM` (¬T1 ∧ T2) | 34,195 | 35.5% |
| `OFFICIAL_CONSISTENT` (T1 ∧ T2) | 19,510 | 20.2% |
| `OFFICIAL_PATTERN_NONMODEL` (T1 ∧ ¬T2) | 4,313 | 4.5% |
| `EMPTY` (genesis) | 1 | excluded |

Per era (activation-at-height strata):

| Era | n | OFFICIAL_CONSISTENT | OFFICIAL_PATTERN_NONMODEL | MODEL_SHAPED_CUSTOM | CUSTOM |
|---|---|---|---|---|---|
| pre-moe (1–71,934) | 71,934 | **26.0%** | 5.5% | 47.2% | 21.3% |
| moe-window (71,935–91,629) | 19,695 | 3.1% | 1.3% | 1.0% | **94.6%** |
| dense-only (91,630–96,250) | 4,621 | 4.2% | 1.7% | 0.7% | **93.4%** |
| rank-penalty (96,251–96,405) | 155 | 1.3% | 5.8% | 0.6% | **92.3%** |

Official-pattern traffic (T1-pass, 23,823 blocks = 24.7% of the chain) is
concentrated in the **pre-MoE** era; from the MoE fork onward the chain is
≥92% `CUSTOM`.

## 2. T1 (hard falsifier): no labeled pool is model-consistent, ≥99.5% provably not the unmodified stack

T1's binding asymmetry (PREREG-001 §3): failure proves a block was **not**
produced by the unmodified published stack; a pass proves nothing (env
overrides). So T1 licenses two statements about the labeled pools, one hard,
one about model-consistency:

| Pool | Blocks | OFFICIAL_CONSISTENT | T1-pass (any class) | CUSTOM |
|---|---|---|---|---|
| unattributed | 67,304 | 29.0% | 35.3% | 13.9% |
| PearlHash | 10,422 | **0.0%** | 1 block | 100.0% |
| Pearl Fortune | 8,183 | **0.0%** | 40 blocks | 99.5% |
| Kryptex | 4,838 | **0.0%** | 23 blocks | 99.5% |
| LuckyPool | 3,139 | **0.0%** | 0 | 100.0% |
| Hero Miners | 2,519 | **0.0%** | 0 | 100.0% |

Two facts, stated precisely:

1. **≥99.5% of every labeled pool's blocks are provably not the unmodified
   published stack** (T1-fail; ~29,100 attributed blocks, only 64 T1-pass).
2. **Zero labeled-pool blocks are model-consistent** (`OFFICIAL_CONSISTENT`).
   The 64 T1-pass labeled blocks are all `OFFICIAL_PATTERN_NONMODEL` (official
   bytes, non-model dims): Pearl Fortune 40, Kryptex 23, PearlHash 1. Those
   64 cannot be falsified by T1 (a pass proves nothing), so statement 1 is a
   near-universal, not a clean universal.

**Era-confound checked and refuted.** This is not an artifact of pools
appearing late: in the **pre-MoE** era, where unattributed traffic is 30%
`OFFICIAL_CONSISTENT`, PearlHash mined 4,313 blocks (0 `OFFICIAL_CONSISTENT`),
Pearl Fortune 3,314 (0), Kryptex 230 (0). Within the same era and the same
consensus rules, labeled pools produce essentially no official-fragment blocks
while unattributed miners produce thousands. This is a pool-level difference,
not an era one.

(For the relationship to arXiv:2606.04819's pool-binary claim, a
non-pre-registered reading, see §5.)

## 3. T3 (mixture): pre-registered verdicts

Only three strata reach the N ≥ 200 T1-base floor, all unattributed:

| Stratum | N (T1-base) | Best cell | TV_primary | TV_conditional | Verdict |
|---|---|---|---|---|---|
| unattributed · pre-moe | 22,685 | Llama-3.3-70B @tp1 | 0.436 | 0.430 | both forms > 0.25 ∀H |
| unattributed · moe-window | 808 | Llama-3.3-70B @tp1 | 0.446 | 0.444 | both forms > 0.25 ∀H |
| unattributed · dense-only | 262 | Llama-3.3-70B @tp1 | 0.451 | (n/a) | primary > 0.25 ∀H |

Every other stratum is `INSUFFICIENT_SAMPLE`. **No stratum × hypothesis cell
reached `MIXTURE_CONSISTENT` or `INDETERMINATE`.**

**Pre-registered interpretation (PREREG-001 §6, outcome row "both forms >
0.25 for all H", copied verbatim):** *"Mixture inconsistent with every
pre-registered model/tp; consistent with synthetic shape selection or an
unpublished model. Not proof of synthetic mining."*

So even the official-pattern, 70B-layer-shaped traffic does **not** appear in
the MAC-share proportions a served model predicts. Both strata that clear the
matched-count floor (pre-moe, moe-window) fail the primary *and* the
conditional form; dense-only fails the primary form (its conditional is
`INSUFFICIENT_SAMPLE`, matched 193 < 200).

## 4. T4 (m-variability): pre-registered flags

| Stratum | N (T1∧T2) | mode m | mode share | pow2 share | m > 16,384 | flags |
|---|---|---|---|---|---|---|
| unattributed · pre-moe | 18,712 | 32,768 | 0.81 | 0.95 | 0.82 | `POW2_M` |
| unattributed · moe-window | 603 | 32,768 | 0.98 | 1.00 | 0.98 | `CONSTANT_M`, `POW2_M` |
| unattributed · dense-only | 193 | 32,768 | 1.00 | 1.00 | 1.00 | `CONSTANT_M`, `POW2_M` |

The dominant m is **32,768, above vLLM's typical `max_num_batched_tokens`
(~16k)**, in 82–100% of these strata's model-shaped blocks. Per the
pre-written caveat (PREREG-001 §7), dominant `m > 16,384` is "stronger but
still configuration-dependent" (the batch bound is operator-set), and constant
power-of-two m at a chunk size is weak on its own. The prereg does not license
calling this synthetic; it is a flag, not a verdict.

## 5. Exploratory (post-hoc): the mechanism behind the inconsistency

*Not pre-registered; presented as characterization, not as a graded finding.*

Why is the largest official-pattern stratum `MIXTURE_INCONSISTENT` despite
71.3% of its T1 blocks matching a 70B layer pair? The `(k, n)` distribution is
a near point-mass on the single highest-MAC layer:

| (k, n) | Share of T1 blocks | 70B layer | Predicted share |
|---|---|---|---|
| (8192, 57344) | **69.8%** | fused gate/up (tp1) | 54.9% |
| (8192, 28672) | 8.7% | fused gate/up (tp2) | - |
| (8192, 32768) | 5.3% | none (not a model pair) | - |
| (8192, 8192) | 1.1% | o (tp1) | 7.8% |
| (8192, 10240) | 0.4% | qkv (tp1) | 9.8% |
| (28672, 8192) | **0.0%** | **down (tp1)** | **27.5%** |

A real forward pass emits all four layers in MAC proportion; this traffic is
overwhelmingly the one shape with the largest `n·k` (gate/up, at tp1 and tp2 =
78.5% combined) while the down-projection (the second-largest predicted
layer, 27.5%) is **entirely absent**. That is the shape a declared-MAC-
maximizing miner would select, and it is what "synthetic shape selection"
(§3's pre-registered interpretation) looks like mechanically. It does **not**
prove synthetic mining; a partial or non-standard serving configuration is
not excluded. But it is why the mixture test rejects every served-model
hypothesis.

> **Erratum 2026-08-07: a simpler mechanism, and it qualifies §3.**
> The published checkpoints' own `quantization_config` and safetensors
> headers (verified directly:
> [`PREREG-002`](PREREG-002-weight-provenance-scan.md) §3) show that
> `down_proj` is quantized **FP8 (F8_E4M3)**, not INT7, in every Llama
> checkpoint: Llama-3.3-70B layer 50's `mlp.down_proj.weight` is
> `F8_E4M3 [8192, 28672]` while `gate_proj`/`up_proj` are `I8 [28672, 8192]`.
> An FP8 layer does not flow through NoisyGEMM and therefore **cannot
> produce an INT7 certificate at all**. The 0.0%-vs-27.5% gap above is not
> miner behaviour; it is a property of the published model. The same source
> shows only **half** of each model's `qkv` layers are INT7 (70B: layers
> 40–79; 8B: 16–31), so the qkv share was also overstated.
>
> **What this changes.** PREREG-001's frozen Llama MAC-share vectors
> (gate_up 0.549 / down 0.275 / qkv 0.098 / o 0.078 for the 70B) do not
> describe what the published stack can mine, so §3's `MIXTURE_INCONSISTENT`
> verdicts are substantially an artifact of a mis-specified expected
> distribution and **must not be read as evidence of synthetic shape
> selection**. The §5 paragraph above stands only as the description of an
> observed distribution, not as a mechanism.
>
> **What this does not change.** §2's T1 result is untouched: T1 is a
> byte-exact test on rank and tile patterns and never used the layer tables.
> "No labeled pool is model-consistent, and ≥99.5% of every labeled pool's
> blocks are provably not the unmodified published stack" stands as
> reported, as does the era-confound refutation.
>
> PREREG-001 is frozen and is **not** edited. A corrected mixture test, if
> pursued, ships as its own pre-registration; PREREG-002 uses the corrected
> layer set only to bound the weight-scan candidate space.

**Relationship to arXiv:2606.04819** (also post-hoc). The paper argues the
dominant *pool* mining binary contains no inference code. §2's T1 result (no
labeled pool is model-consistent, ≥99.5% provably not the unmodified stack)
points the same way from certificate geometry, and does so independently of
the paper's method. But geometry is weaker than the paper's claim: T1-fail
proves "not the unmodified published stack", which a *modified* stack running
real inference with different kernels would also fail. So this is directional
corroboration of the paper's conclusion, not a proof that pool binaries lack
inference code. And it leaves Pearl's *published* vLLM miner untouched: that
is different software (see Keshi's internal protocol notes, The mining
stack).

## 6. Summary (within the pre-registered frame)

- The chain divides sharply: official-pattern traffic is early and almost
  entirely unattributed; from the MoE fork on it is ≥92% custom.
- **No labeled pool is model-consistent, and ≥99.5% of every labeled pool's
  blocks are provably not the unmodified official stack** (T1, era-confound
  refuted). This is statistics-free, subject only to the 64 unfalsifiable
  T1-pass labeled blocks.
- The official-pattern traffic that exists is **inconsistent with every
  published model's served-inference mixture** (T3), and its m-distribution
  triggers the pre-registered T4 flags (dominant m > 16,384: "stronger but
  configuration-dependent"). Per the prereg, this is "consistent with
  synthetic shape selection or an unpublished model. Not proof of synthetic
  mining." **Superseded in part by the 2026-08-07 erratum in §5: the T3
  expected distributions counted layers the published checkpoints quantize
  FP8 and therefore cannot mine, so the T3 rejections do not support a
  synthetic-selection reading. T1's results are unaffected.**

## Limitations (PREREG-001 §9, unchanged)

Attribution is single-wallet per pool. Shape consistency is evidence only
against a non-mimicking population: deliberate mimicry defeats it at zero
marginal cost; only `hash_b` weight-commitment verification (Phase 8.3/8.4)
resists it. Negative results are coverage-bounded across the four published
models. The corpus records shapes, not tensors: nothing here verifies
weights. The rank-penalty (E4) stratum is small (155 blocks) and its rank is
consensus-constrained (≥128) post-fork, so E4 shares are read cautiously.
Independent review (8.6) and the negative control (8.5) precede any registry
or API surface.
