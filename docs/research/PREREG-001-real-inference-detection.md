# PREREG-001: real-inference detection over the certificate corpus

Pre-registration, drafted 2026-08-06. Roadmap Phase 8.2
([`ROADMAP-certificate-intelligence.md`](../ROADMAP-certificate-intelligence.md));
governed by the Verification standard §4: the hypotheses, tests, thresholds
and the interpretation of **every possible outcome** are fixed here, before
the analysis runs at scale. After this document's commit hash is recorded in
the dataset manifest, nothing in §§2–7 may change; corrections ship as a
PREREG-002 with a stated reason, never as an edit.

**Binding language (applies to every downstream artifact).** All findings are
statements of the form "consistent with" or "inconsistent with" a
pre-registered shape signature. Nothing in this analysis can prove that
inference occurred, that a model was actually served, or that any computation
was fresh. The phrase "was real inference" is prohibited except in this
sentence. Per-block accusations are never made; strata are pools and eras,
and pools are aggregators of unknown fleets.

> **Typographic erratum 2026-08-07.** This document was edited on
> 2026-08-07 for typography only: em dashes were rewritten into commas,
> colons and sentence breaks. **No hypothesis, test, threshold, table value,
> number, or interpretation changed.** The freeze is unaffected and stays
> verifiable rather than merely asserted: the exact bytes this document had
> when DS-001 was produced are retrievable at the commit its manifest pins,
> and the diff is inspectable with
> `git diff 11a517a02cedfb97360da95bfaf8e4f114374dfd..d4cb529b8602f1f73bab681f4ae428ba6cfd3fff -- docs/research/PREREG-001-real-inference-detection.md`.
>
> **Reconciling manifests across this edit.** Datasets are append-only, so
> DS-001's manifest still records `preregCommit: 11a517a02ced` and that
> remains the correct pointer to the document its run implemented. Manifests
> written after 2026-08-07 record `d4cb529b8602` instead. The two hashes name
> the same rules: the only differences are the typography above and this
> erratum, which is why the pointer was allowed to move at all. A reader
> reconciling an old dataset with a new one should expect exactly two values
> here and can confirm their equivalence with the diff command above. Any
> future change to §§2-7 ships as PREREG-002-style new document, never as a
> further pointer move.

## 1. Question and hypotheses

Pearl's official miner is a vLLM plugin: real inference where quantized
linear layers double as proof-of-work, recording the true GEMM dimensions in
the certificate ([`pearl-notes.md`](../pearl-notes.md) §The mining stack).
Synthetic miners choose dimensions freely. The corpus therefore admits
shape-level discrimination.

- **H1**: some portion of the chain's certificates is consistent with the
  *unmodified official stack* mining *published `pearl-ai` models*.
- **H2**: some portion is *provably not* the unmodified official stack
  (T1-fail is a hard falsifier; the reverse direction proves nothing).
- **H3**: within official-pattern traffic, per-stratum `(k, n)` frequencies
  match the MAC-share mixture a single served model predicts (the roadmap's
  T3): "a distributional fingerprint a synthetic miner cannot cheaply fake,
  because faking it means actually doing the layer mix").

## 2. Population, eras, strata

- **Population**: canonical blocks with a decoded `cert_public_params` row at
  decoder version 1. Orphaned blocks' rows are **excluded** (pre-registered;
  they remain in the corpus for other work). Height 0 is class `EMPTY` and is
  excluded from all denominators.
- **Eras** (activation-at-height semantics, from `chaincfg` +
  [`registry/PCCR.md`](../registry/PCCR.md)):
  E1 `pre-moe` 1–71,934 · E2 `moe-window` 71,935–91,629 ·
  E3 `dense-only` 91,630–96,250 · E4 `rank-penalty` 96,251–tip-at-snapshot.
  The v1.2.1 `IsMoE` semantic fix has no height and no effect here (MoE-ness
  is `moe_e > 0` on decoded params; inconsistent tails already fail the
  Phase 6 parse). Recorded as a caveat, not a boundary.
- **Strata**: pool × era. Pool from the coinbase address against
  `pool_labels`; the unattributed remainder is its own stratum, always shown,
  never redistributed.

## 3. T1: official-stack byte test (per block, binary)

T1 passes iff ALL of:

1. `rank ∈ {64, 128}`, the only noise ranks compiled in the published
   kernels (`pearl-gemm-build-utils/.../default_compiled_kernels.py`).
2. `rows_pattern == 0x070100000000` **byte-exact**, decoding to
   (stride 8, len 2),(16,1),(16,1): two rows 8 apart, one sm90 wgmma
   accumulator fragment.
3. `cols_pattern == 0x0001031f0000` **byte-exact**, decoding to
   (1,2),(8,32),(256,1): 32 stride-8 pairs = 64 columns.
4. `m ≥ 1024 ∧ n ≥ 256 ∧ k ≥ 1024`, the vLLM miner's engagement floor
   (`vllm-miner/config.yaml`).

**Span matching is prohibited.** The fork-census window alone carries **five
distinct byte encodings** with h·w = 128, including a contiguous 2×64 pattern
(`rows 0x000100000000, cols 0x003f00000000`; e.g. height 96,334) produced by
a *different* kernel; only the exact bytes identify the published fragment.

Era note: in E4 (rank-penalty), rank 64 is consensus-invalid, so E4 T1 blocks
necessarily carry rank 128. That is expected, not an anomaly.

**Asymmetric semantics (binding):** because `MINER_*` environment variables
can override rank, patterns and tiles, **T1-fail proves the block was not
produced by the unmodified published stack; T1-pass proves nothing.**

## 4. T2: layer-geometry test (per block)

A block matches layer row `(model, layer, tp)` iff its `(n, k)` equals the
row's pair after tensor-parallel division. Column-parallel layers
(`qkv_fused`, `gate_up_fused`) divide **n** by tp; row-parallel layers (`o`,
`down`) divide **k** by tp, with `tp ∈ {1, 2, 4, 8}` and the divided pair
still satisfying `n ≥ 256 ∧ k ≥ 1024` (rows pruned by the floor at a given
tp simply do not enter the grid at that tp). Dense rows additionally require
`moe_e = 0`; the Qwen3 expert row requires `(moe_e, moe_top_k) = (128, 8)`.
T2 passes iff the match set is non-empty. **Ambiguity is recorded, never
resolved**: every match (with its provenance tag) is emitted per block; a
multi-match block counts once as "any-model consistent".

### Frozen layer tables (tp = 1; n = out-features, k = in-features, per `gemm_operators.py`)

Provenance tags: **anchored** (dimension pair observed dominating the chain
and/or derivable from verified config), **documented** (stated in
[`pearl-notes.md`](../pearl-notes.md) F4), **derived** (computed from
documented architecture, not independently verified).

| Model | Layer | n | k | Parallelism | Prov |
|---|---|---|---|---|---|
| Llama-3.1-8B | qkv_fused | 6144 | 4096 | col | anchored |
| Llama-3.1-8B | o | 4096 | 4096 | row | anchored |
| Llama-3.1-8B | gate_up_fused | 28672 | 4096 | col | anchored |
| Llama-3.1-8B | down | 4096 | 14336 | row | anchored |
| Llama-3.3-70B | qkv_fused | 10240 | 8192 | col | anchored |
| Llama-3.3-70B | o | 8192 | 8192 | row | anchored |
| Llama-3.3-70B | gate_up_fused | 57344 | 8192 | col | **anchored** (the chain's top shape, 15,902 blocks, OBS-003) |
| Llama-3.3-70B | down | 8192 | 28672 | row | anchored |
| Qwen3-30B-A3B | expert_gate_up_fused (MoE, trailer 128/8) | 1536 | 2048 | col | anchored |
| Gemma-4-31B | gate_up_fused | 43008 | 5376 | col | derived |
| Gemma-4-31B | down | 5376 | 21504 | row | documented |
| Gemma-4-31B | qkv_fused | 16384 | 5376 | col | documented† |
| Gemma-4-31B | o | 5376 | 8192 | row | documented† |

† Gemma attention dims verified live from the published HF config on
2026-08-06 (`text_config`: heads 32 × head_dim 256 → attn 8192; kv heads 16 →
2×4096; qkv_fused n = 8192 + 8192 = 16384). An earlier dossier draft listed
o as (5376, 5376), which is wrong, since Gemma-4's attention dimension (8192) differs
from its hidden size (5376). Whether Gemma's attention layers are in the INT7
group is assumed by analogy with the Llama models and NOT independently
verified. These two rows affect T2 class shares only (Gemma is T3-excluded)
and are filterable by tag.

Deliberate exclusions, with reasons: Qwen3 expert `down` (2048, 768), an FP8
block-scaled path, not INT7-mined, and k = 768 < 1024 regardless; Qwen3
attention layers, INT7 membership unverified (a non-classifying sensitivity
table reports qkv (5120, 2048) and o (2048, 4096) counts separately). Fused
pairs are used for the Llama
models because vLLM's `QKVParallelLinear` / `MergedColumnParallelLinear`
execute fused GEMMs. The dossier's unfused F4 listing is corrected by
errata in the same commit as this document.

## 5. Classification (per block)

| | T2 pass | T2 fail |
|---|---|---|
| **T1 pass** | `OFFICIAL_CONSISTENT` | `OFFICIAL_PATTERN_NONMODEL` |
| **T1 fail** | `MODEL_SHAPED_CUSTOM` | `CUSTOM` |

plus `EMPTY` (genesis only). Reported per stratum as counts and shares.

## 6. T3: layer-mixture test (per stratum × hypothesis)

- **Decision statistic: total-variation distance**, an effect size with
  pre-registrable thresholds. Chi-square/G reject any point null at corpus
  sample sizes on trivial deviations; the G-statistic
  `G = 2·Σ O_c·ln(O_c/E_c)` is computed and reported **descriptively only**.
- **Hypothesis grid, fixed**: H = {Llama-3.1-8B, Llama-3.3-70B} × tp
  {1, 2, 4, 8}, plus Qwen3-30B-A3B × tp {1, 2, 4} (its expert row prunes at
  tp = 8: n = 192 < 256). Gemma is **T3-excluded** (its attention rows'
  INT7 membership is assumed, not verified → no defensible mixture).
  **Every grid cell is reported for every stratum**: no best-fit selection,
  no post-hoc hypotheses. That is the forking-paths control.
- **Per-cell support and pruning**: a grid cell's category support is the
  model's layer rows that survive the min-dims floor at that tp, and the
  expected vector q is **renormalized over the surviving support**. Concretely
  the only Llama pruning is (8B, tp = 8), where `o` drops (k = 512 < 1024)
  and q renormalizes to gate_up 0.5833 / down 0.2917 / qkv 0.1250.
- **Base population** `B_s` = T1-passing blocks of stratum s; `N = |B_s|`.
  `N < 200` → verdict `INSUFFICIENT_SAMPLE`.
- **Primary form**: categories = support(H) ∪ {OTHER}; observed
  `p̂(c) = count(c)/N`; expected `q(c)` = MAC shares with `q(OTHER) = 0`;
  `TV = ½·Σ|p̂ − q|`.
- **Conditional form** (mixed-fleet view): restrict to support(H),
  renormalize; requires matched count ≥ 200. Both forms always reported.
- **Expected MAC shares, frozen arithmetic**: per-token MACs of layer l are
  `n_l · k_l`; every mined layer executes once per token per shard, so token
  counts and tp cancel: `share_l = n_l·k_l / Σ n·k` (tp-invariant **except**
  where the min-dims floor prunes a layer at a given tp, in which case q
  renormalizes over the survivors as defined above). If block yield were ∝
  `m·n·k_eff` instead of per-token MACs, the prediction is unchanged for T1
  blocks: `k_eff = k` exactly at rank ≤ 128 for every table layer (all k are
  multiples of 128, the same `k_eff` the v1.3.0 bound multiplier
  `(k_eff/rank)·128` uses, pearl-notes §rank-penalty rule).

| Model | gate_up_fused | down | qkv_fused | o |
|---|---|---|---|---|
| Llama-3.1-8B | **0.5385** | 0.2692 | 0.1154 | 0.0769 |
| Llama-3.3-70B | **0.5490** | 0.2745 | 0.0980 | 0.0784 |
| Qwen3-30B-A3B | 1.0 (single category) | | | |

Qwen3 semantics, fixed: with a single category the **primary** form is well
defined and applies normally, with `TV_primary = 1 − p̂(expert pair)`, so
`TV ≤ 0.10` means ≥90% of the stratum's T1 blocks carry (1536, 2048) with the
(128, 8) trailer, which CAN trigger outcome row 1. The **conditional** form is
degenerate (always 0) and is reported as `DEGENERATE`, never as a verdict.

- **Thresholds (frozen)**: `TV ≤ 0.10` → `MIXTURE_CONSISTENT`;
  `0.10 < TV ≤ 0.25` → `INDETERMINATE`; `TV > 0.25` →
  `MIXTURE_INCONSISTENT`. Justification: under a true mixture,
  `E|p̂−p| ≈ √(2p(1−p)/(πN))` per category, giving E[TV] ≈ 0.043 at N = 200
  for the Llama share vectors, so the 0.10 line sits ≈2.3× above null
  expectation (≈0.019 at N = 1000).

### Outcome → interpretation table (copied verbatim into OBS-004)

Quantifier rule: `DEGENERATE` and `INSUFFICIENT_SAMPLE` values are excluded
from every "for some H" / "for all H" quantification below.

| Outcome | Pre-registered interpretation |
|---|---|
| `TV_primary ≤ 0.10` for some H | The stratum's official-pattern traffic is **consistent with** single-model official-stack mining of model M at tp t. Not a claim that inference occurred or was served. |
| `TV_primary > 0.25` for all H but `TV_cond ≤ 0.10` for some H | Consistent with a **mixed fleet**: a model-consistent sub-population plus unrelated official-pattern traffic. |
| Both forms `> 0.25` for all H | Mixture **inconsistent with** every pre-registered model/tp; consistent with synthetic shape selection or an unpublished model. **Not proof of synthetic mining.** |
| `INDETERMINATE` (either form) | No verdict; the value is reported as-is. |
| `INSUFFICIENT_SAMPLE` | No verdict; N reported. |
| Multiple H consistent | Ambiguous between the listed hypotheses; never resolved to one. |
| Qwen3 cells | Primary form applies normally (TV = 1 − expert-pair share) and can trigger the rows above; the conditional form is reported as `DEGENERATE` and never drives a verdict. |

## 7. T4: m-variability (per stratum; base = T1∧T2 blocks; N ≥ 50)

Report per stratum: distinct-m share `|{m}|/N`; mode-m share;
power-of-two-m share; share with `m > 16,384`. Flags: `CONSTANT_M` iff
mode-m share ≥ 0.90; `POW2_M` iff pow2 share ≥ 0.90.

**Pre-written caveat (binding):** vLLM chunked prefill yields constant
power-of-two m at configuration values (2048/4096/8192/16384), so
`CONSTANT_M` at a plausible chunk size is *weak* evidence of anything.
Constant m at non-chunk values, or dominant `m > 16,384`, is stronger but
still configuration-dependent (`max_num_batched_tokens` is operator-chosen).
MoE routing thins per-expert m in ways this analysis does not model, a
documented unknown.

## 8. Procedure, dataset, and freeze mechanics

1. This document commits first; its git hash is the freeze reference.
2. `internal/certclass` implements §§3–7 as pure functions; its constants
   cite this document's sections, and a unit test asserts the computed MAC
   shares equal the frozen literals above, including the renormalized
   (8B, tp = 8) vector 0.5833/0.2917/0.1250 (table drift = test failure).
3. `keshictl classify` refuses to run unless the corpus is complete
   (`certParams missing = 0`) and walks one REPEATABLE READ snapshot,
   emitting **DS-001** (`docs/research/datasets/DS-001-classification-v1/`):
   `blocks.jsonl.gz` (per block: height, hash, pool, era, class, per-test
   results, matches with provenance tags), `summary.json` (per-stratum class
   counts, the full T3 grid, T4 stats; thresholds and versions echoed),
   `MANIFEST.md` (sha256s, snapshot tip height+hash, tool + decoder + prereg
   commit). Byte-determinism is a tested property.
4. DS-001 is append-only per roadmap §6.5: re-runs are `-v2` with an errata
   note, never edits.
5. **OBS-004** fills §6's interpretation table with measured numbers. Any
   observation not derivable from the pre-registered tables goes in a clearly
   labeled "Exploratory (post-hoc)" section. Adversarial review precedes
   publication (roadmap 8.6); negative-control obligations (8.5) apply before
   any registry or API surface ships.

## 9. Known limitations (stated in advance)

- Attribution is single-known-wallet per pool; proxy payouts misattribute.
- The layer tables cover four published models; an unpublished or fine-tuned
  model with different dims lands in `OFFICIAL_PATTERN_NONMODEL`/`CUSTOM` by
  construction. Negative results are coverage-bounded, never proof of
  absence.
- T1's engagement floor and T4's chunk sizes come from the *default* config;
  operators can change both.
- Gemma rows are partially derived; they affect T2 class shares only and are
  filterable in re-analysis via provenance tags.
- The corpus records shapes, not tensors: nothing here verifies weights
  (that is Phase 8.3/8.4, `hash_b` recomputation).
- **Deliberate mimicry defeats this analysis at zero marginal cost.** Under
  the yield model above, a synthetic miner drawing table shapes in MAC
  proportions with the official bytes, rank 128 and power-of-two m lands
  `OFFICIAL_CONSISTENT` and `MIXTURE_CONSISTENT` while sacrificing nothing.
  Shape consistency is therefore evidence only against the *current,
  non-adversarial* population; only weight-commitment verification
  (`hash_b`, Phase 8.3/8.4) resists mimicry.
