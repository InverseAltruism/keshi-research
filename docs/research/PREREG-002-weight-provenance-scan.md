# PREREG-002: weight-provenance scan over the certificate corpus

Pre-registration, drafted 2026-08-07. Roadmap Phase 8.4 / 13.2
([`ROADMAP-certificate-intelligence.md`](../ROADMAP-certificate-intelligence.md),
[ADR-0013](../decisions/ADR-0013-unilateral-track-no-adoption-bets.md));
governed by the Verification standard §4: hypotheses, tests, thresholds and
the interpretation of **every possible outcome** are fixed here, before the
analysis runs at scale. Once this document's commit hash is recorded in the
dataset manifest, nothing in §§2–7 may change; corrections ship as a
PREREG-003 with a stated reason, never as an edit.

**Non-normative pointer (added 2026-08-11, no frozen text changed).**
[`PREREG-003`](PREREG-003-coverage-closure-and-control-redraw.md) registers
the coverage-closure scans, the layout and quantization probes, and the
control redraw that follow from this document's executed runs. It does not
amend §§2–7, which continue to govern DS-002 and DS-002b as written; where
the two differ, PREREG-003 states the difference and its reason. The
corrections themselves are recorded in the OBS-005 §10 errata block dated
2026-08-11.

**Binding language.** A byte-exact `hash_b` match proves that the operand a
miner committed equals a specific published weight tile, which we call
"attested model-weight mining". It does **not** prove that inference occurred, that a
customer was served, that the computation was fresh, or that the block's
declared arithmetic was performed. A non-match proves nothing beyond the
searched space, which §5 fixes explicitly. Per-block accusations are never
made.

## 0. Why this is possible without cooperation, hardware, or permission

`hash_b = blake3(B_t, key=job_key)` where
`job_key = blake3(incomplete_header[76] ‖ mining_config[52])`. Both preimage
halves are on-chain, `hash_b` is in the certificate, and the published
`pearl-ai` checkpoints supply candidate `B_t`. The commitment is a plain
keyed BLAKE3 over the raw tensor bytes (measured against the reference
implementation on 2026-08-07; see
[`../fixtures/scanhash/MANIFEST.md`](../fixtures/scanhash/MANIFEST.md) and
the ADR-0013 erratum. The earlier "padded buffer" reading was wrong except
at exact 1024-multiples). Everything therefore runs on CPU from data Keshi
already stores plus public weights.

## 1. Question and hypotheses

- **H1**: some canonical block's `hash_b` equals the keyed BLAKE3 of a
  published `pearl-ai` INT7 weight tile under that block's own `job_key`.
- **H2**: the rate of such matches differs across pools and eras.
- **H0 (control)**: blocks that cannot plausibly carry a published tile
  (class `CUSTOM`) never match. A control match falsifies the
  implementation, not the null. The run is void and is re-run after a fix.

**What the control can and cannot do (stated in advance).** Control blocks
commit to differently-shaped operands, so absent a bug any match is a
2⁻²⁵⁶ event. The control is therefore an **implementation canary** against
gross false-positive machinery (an inverted comparison, a truncated
memcmp, a mis-wired buffer) and nothing more. It has **no power against
false negatives**, which are indistinguishable from true negatives by
construction. The real specificity evidence is (a) that a matching block
matches exactly one of ~80 identically-shaped layer tensors, and (b) the
independent reproduction path (`scripts/verify-hashb-match.py`: raw block
from Blockbook, offsets parsed independently, pip `blake3`, no Keshi code).
Both are reported for every published match.

## 2. Population and candidate universe

- **Population**: canonical blocks with a decoded `cert_public_params` row
  at `chain.CertDecoderVersion` = 1, frozen at the extract-stage snapshot
  tip (recorded in the dataset manifest). Orphans excluded, as in
  PREREG-001 §2.
- **Scan set**: blocks whose declared `(n, k)` equals a published layer's
  sharded dims: **T2-passing blocks, whether or not they pass T1**.
  T2 is the necessary condition for any tile of that layer to hash to
  `hash_b`; T1 is not. Two strata, both scanned and reported separately:
  `OFFICIAL_CONSISTENT` (T1 ∧ T2) and `MODEL_SHAPED_CUSTOM` (¬T1 ∧ T2,
  34,195 blocks, run with `--include-model-shaped`).
  **Restricting to T1 would decide H2 before hashing:** no labeled pool has
  any `OFFICIAL_CONSISTENT` block (OBS-004 §2), so a T1-only scan could
  never match a pool, and "pools never matched" would be an artifact of the
  selection rather than a measurement. A modified stack mining genuine
  published weights lands in `MODEL_SHAPED_CUSTOM` by construction, and
  that is where every labeled pool's traffic lives.
- **Control set**: the first `--control N` (default 1000) `CUSTOM`-class
  blocks in `(height, hash)` order, so there is no sampling randomness.
- **Candidate buffers**: (model, layer, tp, transformer-layer-index, shard)
  from §3's corrected tables, materialized by
  [`../../scripts/extract-weights.py`](../../scripts/extract-weights.py) and
  pinned by HF revision sha + per-buffer sha256 in the dataset manifest.
- **Phases** (declared in advance, so restriction is not post-hoc):
  P1 pilot ≤1,000 candidate blocks, an engineering shakedown whose
  **results are not interpreted** and pilot control size is discretionary; P2
  Llama-3.3-70B **and Llama-3.1-8B** across both strata, `--control ≥1000`;
  P3 remaining published models (Gemma-4-31B; Qwen3-30B-A3B needs the MoE
  expert-stacked layout, which is not implemented and is therefore **not
  claimed as covered**). Any phase not run is reported as not run.
- **Unscanned candidates are counted, never silent.** A block whose layer
  matches are all filtered out by the run's `--models`/`--tp` selection is
  recorded in the extract and reported in `summary.json`, so partial
  coverage can never read as scanned-and-clean.

## 3. Which layers are actually mineable: a correction to PREREG-001's tables

**Verified 2026-08-07** from the published checkpoints' own
`quantization_config` and safetensors headers (byte-range reads of the
tensor headers; no full download required):

| Model | INT7 (I8-stored, mineable) | FP8 / not mineable |
|---|---|---|
| Llama-3.3-70B | `gate_proj`, `up_proj` (all 80 layers), `o_proj` (all 80), `q/k/v_proj` **layers 40–79 only** | `down_proj` (**F8_E4M3**), `q/k/v_proj` layers 0–39 |
| Llama-3.1-8B | `gate_proj`, `up_proj`, `o_proj` (all 32), `q/k/v_proj` **layers 16–31 only** | `down_proj`, `q/k/v_proj` layers 0–15 |
| Qwen3-30B-A3B | expert `gate_proj`, `up_proj`; attention `q/k/v/o_proj` | expert `down_proj` |
| Gemma-4-31B | `Linear` (INT7 default group) | `q/k/v/qkv_proj`, `mlp.down_proj`; vision tower ignored |

Directly observed for Llama-3.3-70B layer 50:
`mlp.gate_proj.weight` **I8** `[28672, 8192]`, `mlp.up_proj.weight` **I8**
`[28672, 8192]` (fused → `[57344, 8192]`, the chain's single most common
declared shape), `self_attn.o_proj.weight` **I8** `[8192, 8192]`,
`self_attn.q_proj.weight` **I8** `[8192, 8192]`, and
`mlp.down_proj.weight` **F8_E4M3** `[8192, 28672]`.

**Consequence, stated before the scan runs.** PREREG-001's frozen tables
treat `down` as an INT7 layer for the Llama models and assign it a
**27.5%** (70B) / **26.9%** (8B) expected MAC share in the T3 mixture, and
treat all `qkv` layers as INT7. Neither holds for the published
checkpoints: a `down_proj` GEMM is FP8 and therefore **cannot** produce an
INT7 NoisyGEMM certificate, and only half of each model's `qkv` layers are
INT7. OBS-004 §5 measured exactly this, the (28672, 8192) down pair at
**0.0% observed against 27.5% predicted**, and attributed it, in a clearly
labelled post-hoc section, to declared-MAC-maximizing shape selection. The
checkpoint configuration supplies a simpler mechanism. An erratum is filed
against OBS-004; PREREG-001 is **not** edited (it is frozen, and its T1
result is unaffected, since T1 never used the layer tables).

This document therefore does **not** re-run T3. The corrected mixture is a
separate question, and it will be pre-registered on its own terms if it is
pursued. What is fixed here is only the **candidate set for hashing**:
FP8-quantized layers are excluded because they cannot be INT7 operands, and
per-layer-index restrictions are respected.

## 4. Test (per block × candidate buffer, binary)

A pair matches iff the 32 bytes of `blake3(buffer, key=job_key)` equal the
32 bytes of `cert_public_params.hash_b` exactly. No fuzzy matching, no
prefix matching, no tolerance.

Derivations are proven per block before any hashing, and **any failure
aborts the whole run** (these indicate a defect, never a result):

1. `SHA256d(reconstructed 108-byte header) == blocks.hash`, with the merkle
   root recomputed from stored txids.
2. `MiningConfigBytes(decoded params) == raw_certificate[public data][0:52]`.

Implementation: `keshictl scan-weights`, pinned by golden vectors minted
from the reference miner (`docs/fixtures/scanhash/`) and by
`TestScanHeaderRoundTripFixture` over the four committed mainnet fixtures.

## 5. Search space (fixed; any negative result is bounded by exactly this)

Models and HF revisions as recorded in the dataset manifest; INT7 layers per
§3; tensor-parallel degrees `tp ∈ {1, 2, 4, 8}` filtered to shards meeting
the engagement floor; shard index over `0..tp-1`; every transformer layer
index in the mineable range; row-major contiguous int8 bytes of the fused
tensor in vLLM's concatenation order (`q|k|v`, `gate|up`).

**Layout risk, disclosed in advance.** The byte layout above is derived from
vLLM's source, not confirmed by a match, except for `gate_up_fused` at
tp = 1, which the pilot confirmed empirically. Specifically:

- **Merged column-parallel layers at tp > 1** (`gate_up_fused`,
  `qkv_fused`) shard **each sub-projection and concatenate per rank**:
  rank *r* holds `gate[r-th slice] ‖ up[r-th slice]`, not a slice of the
  already-fused tensor. An earlier extractor build did the latter and so
  produced the raw unfused projections under a `tp2` label; those buffers
  could never match and were regenerated. Corrected buffers are re-derived
  and re-hashed.
- **Layouts confirmed by the P1 pilot** (engineering validation, not a
  research result): `gate_up_fused` tp1, `qkv_fused` tp1 (q‖k‖v order and
  GQA head dims), and `o` tp2 (row-parallel contiguous k-split) all
  produced byte-exact matches, so those four conventions are established
  empirically rather than by source reading alone.
- **Still unvalidated: merged column-parallel layers at tp > 1**
  (`gate_up_fused`, `qkv_fused`). The corrected per-projection sharding has
  no match yet, because the pilot ran the defective buffers, so a negative there
  cannot distinguish "no miner used this shard layout" from "our bytes are
  still wrong." OBS-005 must say so wherever it reports one.

Explicitly **not** searched: FP8 layers; non-published or fine-tuned
weights; requantized copies; any padding, transposition or interleaving
convention other than the one above; MoE expert-stacked layouts (Qwen3),
which are not implemented.

## 6. Outcome → interpretation table (copied verbatim into OBS-005)

| Outcome | Pre-registered interpretation |
|---|---|
| ≥1 match, control clean | Cryptographic evidence of attested model-weight mining, **the first we are aware of on any chain**: the committed operand equals published tile T. Report per pool/era with counts. Still not proof that inference occurred or was served. **The attribution alternatives below apply and must be stated alongside any such result.** |
| Matches concentrated in one pool/era, control clean | As above, plus a measured heterogeneity; report shares with the unattributed remainder always shown, never redistributed. |
| Zero matches, control clean, full phase completed | **No block in the scanned set committed to any searched tile.** Coverage-bounded per §5. This is not proof of absence, and it does not establish that mining was synthetic. Publish the exact search space alongside the result. |
| Zero matches, phases incomplete | Report as inconclusive with the exact phases run; no inference about the unscanned space. |
| Any control match | **Implementation defect. The run is void**, not a finding. Fix, re-run, and record the void run in the errata. |
| Derivation check failure | Run aborts; treated as a data/decoder defect and investigated before any scan result is reported. |

### Pre-registered analyses of the matched population

Declared now so they are not post-hoc. Each runs only over blocks that
matched, and each is reported with its own N:

1. **Extinction curve.** Matched share of T2-passing blocks against height
   over the whole corpus. If real-weight mining ceases, report the boundary
   height, whether the decline is sharp or gradual, and what co-occurs
   (difficulty level, fork heights from `registry/PCCR.md`, first
   appearance of each labeled pool). **This is the primary result of the
   full run**: the trajectory of demonstrable useful work over a PoUW
   chain's life is the question the corpus uniquely answers. No causal
   claim is made from co-occurrence; the boundary is reported as a
   measurement with its correlates listed.
2. **Corrected layer mixture on matched blocks.** Observed frequencies of
   (layer family) against MAC shares over the layers the published
   checkpoints can actually mine: `gate_up` and `o` across all 80 layers,
   `qkv` across layers 40–79 only, `down` excluded as FP8 (§3). Same TV
   statistic and thresholds as PREREG-001 §6. This tests whether the
   matched population looks like full forward passes rather than a single
   reused tile; it is a *different* population from PREREG-001's T3 (which
   ran over all T1 blocks with a since-corrected expected vector), and it
   does not revise that frozen document.
3. **Batch-size trace.** The (height, m) series of matched blocks, with the
   distribution of m and its relation to vLLM's `max_num_batched_tokens`
   default. Reported as an observed distribution; the batch bound is
   operator-configurable, so no configuration is inferred from it.
4. **Tensor coverage.** Count of distinct (model, layer, tp, shard, layer
   index) tensors matched, and matches per tensor, the direct test of the
   "a miner can reuse one tile indefinitely" caveat in §0.

### Attribution alternatives for any positive result (pre-registered)

A match identifies **weights, not a miner**. These readings are written down
now so that whichever the data supports is not a post-hoc rescue:

1. **Operator bootstrap fleet.** Matches concentrated early, in the
   unattributed stratum, are consistent with Pearl Research Labs (or an
   affiliate) mining its own published checkpoints to bootstrap the chain.
   The published checkpoint's own repository timeline is recorded in the
   dataset manifest for exactly this reason, and it **cuts both ways**: a
   checkpoint available from genesis is equally available to anyone.
2. **Third-party miners** running the published stack on public weights.
3. **Mimicry.** Anyone can download the same weights and mine them; a
   match proves the operand, never the identity or intent of the operator.

**Keshi does not name a party.** No coinbase-based attribution beyond the
existing `pool_labels` ladder enters this analysis, and the unattributed
stratum stays unattributed. Where the strata cannot distinguish these
readings, OBS-005 says so explicitly rather than choosing one.

**What remains measurable regardless of which reading is true:** *when*
real-weight mining occurred, in what volume, in which strata, and, if it
declines, when it stopped. That trajectory is the finding; the identity of
the miner is not ours to assert.

## 7. Procedure and freeze mechanics

1. This document commits first; its git hash is the freeze reference and is
   compiled into `cmd/keshictl/scanweights.go` as `prereg2Commit`.
2. `keshictl scan-weights` emits **DS-002**
   (`docs/research/datasets/DS-002-weight-scan-v1/`): `extract.jsonl.gz`
   (frozen population with per-block job keys), `results/*.jsonl.gz` (every
   pair scanned, match or not, never only the hits), `summary.json`,
   `MANIFEST.md` (sha256s, tool version, decoder version, snapshot tip, HF
   revisions, per-buffer sha256s). Append-only: re-runs are a new version
   directory with an errata note.
3. Determinism is a tested property (identical output across worker counts
   and across resume).
4. **OBS-005** fills §6's table with measured numbers. Anything not
   derivable from this document goes in a labelled "Exploratory (post-hoc)"
   section.
5. Adversarial review (roadmap 8.6) precedes publication; the negative
   control (8.5) is built into every run.

## 8. Known limitations (stated in advance)

- Attribution is single-known-wallet per pool; proxy payouts misattribute.
- A miner running privately requantized or fine-tuned weights produces no
  match by construction; absence of matches is not evidence of synthesis.
- The scan covers weights only. `hash_a` commits to activations, which are
  not public and are not scannable.
- Byte-layout assumptions (§5) are frozen from the reference implementation
  and the published checkpoints; a layout Pearl changes later would need a
  new pre-registration.
- Compute is bounded: the full grid is large, and phases are declared in §2
  precisely so that stopping early is a disclosed limitation rather than a
  silent truncation.
