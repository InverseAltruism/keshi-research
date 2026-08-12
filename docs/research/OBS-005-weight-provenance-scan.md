# OBS-005: Attested model-weight mining on Pearl: the weight-provenance scan

Dated observation note, grading the pre-registered weight-provenance scan.
Recorded 2026-08-09. This note grades PREREG-002 (frozen at
`d4cb529b8602f1f73bab681f4ae428ba6cfd3fff`, compiled into the scan tool as
`prereg2Commit`) over dataset
[`DS-002-weight-scan-v1`](datasets/DS-002-weight-scan-v1/MANIFEST.md);
the DS-002b coverage completion (the phase P2 remainder plus phase P3) is
folded in as §9. Every number
in this note regenerates from the committed datasets via
`scripts/ds002-reproduce.sh` (sections 1, 2, 2b, 3 need only the dataset;
4 and 5 need a Keshi API or an emitted address artifact), and each table
below names the script that produced it. Definitions:
[`metrics.md#weight-provenance-match`](../metrics.md#weight-provenance-match),
[`#matched-share-series`](../metrics.md#matched-share-series),
[`#tensor-coverage`](../metrics.md#tensor-coverage),
[`#attested-model-weight-mining`](../metrics.md#attested-model-weight-mining).

Label discipline: a byte-exact `hash_b` match is **attested model-weight
mining**, never "certified inference". A match proves facts about the
committed operand and the sampled computation (§0.2); it does not prove
inference occurred end to end, was fresh, or served anyone.

The DS-002b coverage runs (completing phase P2's remaining o tp4/tp8 grid
and running phase P3, Gemma) completed 2026-08-09 the same day and are
graded in §9; their datasets are
[`DS-002b-o-tp48-v1`](datasets/DS-002b-o-tp48-v1/MANIFEST.md) and
[`DS-002b-gemma-v1`](datasets/DS-002b-gemma-v1/MANIFEST.md), every file
sha256-verified against its MANIFEST after copy.

## 0. What is knowable at all (read before any number)

### 0.1 The verifiability ceiling

`job_key = blake3(header[0:76] ‖ mining_config[0:52])` includes the
coinbase-dependent merkle root, so `hash_b` is per-block: identical weights
hash to different values in different blocks, and an observer can verify a
weight commitment only by guessing the exact bytes and recomputing the
keyed root per (candidate, block). Consequences, stated before the result
so the result cannot be over-read:

1. Only **public, static checkpoints are externally verifiable**. Private
   models, customer fine-tunes, locally requantized variants, evolving
   training weights, and synthetic noise are mutually indistinguishable on
   chain. This scan therefore measures *verifiable public-checkpoint
   mining*, a **lower bound** on whatever useful work exists.
2. No negative result in this note supports a "no useful work" claim. A
   zero in a stratum means "not these exact published bytes", nothing more.
   A locally requantized 70B, or a training run, is not excluded by any
   zero below.
3. Weight *reuse* across blocks is undetectable by construction. Nothing
   here fingerprints an operator's model over time.

### 0.2 What a match proves (source-verified claim ladder)

Verified 2026-08-09 against the pinned Pearl source at v1.2.1 and v1.3.0
(the `zk-pow/src/v1` verifier that governs every matched-era block is
byte-identical between the two tags). Mainnet consensus accepts a block
only after a Plonky2 recursion over the Pearl STARK verifies against
public inputs taken from the header-committed certificate
(`node/blockchain/validate.go:333`). Inside that proof the opened strips
of A and B are authenticated against the certificate's `hash_a`/`hash_b`
by in-circuit keyed-BLAKE3 Merkle recomputation
(`v1/circuit/pearl_air.rs:91-103`), and the same strip values, plus noise
the verifier derives as `b_noise_seed = blake3(job_key ‖ hash_b)`, feed
the folded transcript that must hash below target. Therefore a
consensus-accepted block whose `hash_b` equals the keyed root of a
published tensor supports, beyond operand identity:

> the sampled output entries verified by consensus were computed from
> strips of that tensor, after a publicly-derivable rank-r perturbation.

Residuals bounding the strong form: the multiplied operands are the noised
strips, not the pristine ones the root commits to; each strip enters
products over `dot_product_length = k - (k mod r)` of its entries; values
are int7 range-checked; row/column semantics are a labeling outside
consensus; and nothing binds `hash_a` to real activations, so the
attestation is one-sided toward the weights operand. The matched era is
verified by the V1 path, which enforces `h·w ≥ 32` sampled output entries
with no explicit upper bound (the 32-256 bound is V2-only); per-block
`h·w` is read from the on-chain mining config. Full cites in
`docs/pearl-notes.md` §Certificate internals.

### 0.3 The unit of analysis is operators, not blocks

The 1,066 matched blocks resolve to 46 distinct coinbase addresses with an
effective operator count (1/HHI) of **4.27**, and 656 of 1,066 matches
(62%) fall on a single calendar day (§4). N = 1,066 is block-level
pseudo-replication; every claim below is therefore phrased as what a
handful of operators did during launch weeks, not as 1,066 independent
observations. Addresses are not entities either: the co-spend clustering
that would bound entity counts is open work (roadmap Phase 14.1).

## 1. What was run

`keshictl scan-weights` (binary `609cf9f90191-wb58f7a2`, PREREG-002
compiled in, `preregFrozen: true` in `summary.json`) over the certificate
corpus frozen at snapshot tip **96,774**: 53,717 candidate blocks (every
T2-passing block, both `OFFICIAL_CONSISTENT` and, via
`--include-model-shaped`, `MODEL_SHAPED_CUSTOM`) plus the 1,000-block
negative control fixed by §2 of the prereg (first 1,000 CUSTOM blocks in
(height, hash) order). Candidate buffers: 840 tensors from the two
published Llama checkpoints (revisions and byte counts pinned in the
MANIFEST; 102.0 GB by the manifest totals). **4,401,184 (block, buffer)
pairs hashed** (`summary.json`), which is ~1.47 PB of keyed BLAKE3
computed as pairs times manifest buffer bytes, over 25.5 h on
2026-08-07/08 by the run log timestamps.

Per-block derivation proofs ran at extract time for all 54,717 blocks
(SHA256d header reconstruction equals the block id; the 52-byte
mining_config rebuilt from decoded params byte-equals the raw
certificate): **zero failures**, so PREREG-002 §6's "derivation check
failure" row is not applicable, which is itself positive evidence that the
decoder and the population are sound. Determinism across worker counts and
across resume is a tested property of the tool.

Coverage gap declared by the run: 386 candidate blocks were recorded but
never hashed (343 shaped as 70B `o_proj` tp4/tp8 shards, 43 shaped as
Gemma-4-31B tensors), because those buffers were not in the DS-002 weights
root. §9 closes this gap as DS-002b (the phase P2 remainder plus phase
P3).

## 2. The outcome table, graded

Copied verbatim from PREREG-002 §6 and graded in place. Applicable rows in
bold; the interpretations are the frozen text, unedited.

| Outcome | Pre-registered interpretation | Grade |
|---|---|---|
| ≥1 match, control clean | Cryptographic evidence of attested model-weight mining, **the first we are aware of on any chain**: the committed operand equals published tile T. Report per pool/era with counts. Still not proof that inference occurred or was served. **The attribution alternatives below apply and must be stated alongside any such result.** | **APPLIES: 1,066 matched blocks (DS-002; 1,109 combined with DS-002b, §9), 0 hits in 840,000 control pairs (2,130,000 across the three runs).** §11 states the alternatives. |
| Matches concentrated in one pool/era, control clean | As above, plus a measured heterogeneity; report shares with the unattributed remainder always shown, never redistributed. | **APPLIES for era and operator structure** (§3, §4, §9): all matches are pre-MoE, heights 21,068-60,881 (DS-002; combined to h62,319), ~4.3 effective operators (48 addresses combined). Per-pool shares are not testable (§6): 100% of matched blocks are unattributed. |
| Zero matches, control clean, full phase completed | **No block in the scanned set committed to any searched tile.** Coverage-bounded per §5. This is not proof of absence, and it does not establish that mining was synthetic. Publish the exact search space alongside the result. | Applies per-stratum: 0 of 50,049 scanned m=32,768 blocks matched any searched tile (§3), within PREREG-002 §5's coverage bounds and the §0.1 ceiling. |
| Zero matches, phases incomplete | Report as inconclusive with the exact phases run; no inference about the unscanned space. | Does not apply: P1 and the bulk of P2 ran as DS-002; DS-002b completed P2's remaining o tp4/tp8 grid and ran P3, Gemma (§9), with exact populations of 343 and 43 candidate blocks. |
| Any control match | **Implementation defect. The run is void**, not a finding. Fix, re-run, and record the void run in the errata. | Did not occur: 0 of 840,000 control pairs (DS-002), 0 of 330,000 (DS-002b Gemma), 0 of 960,000 (DS-002b o tp4/tp8). |
| Derivation check failure | Run aborts; treated as a data/decoder defect and investigated before any scan result is reported. | Did not occur: 0 failures across 54,717 blocks. |

## 3. The finding, in three claims with all denominators

The candidate universe is not one population. Bucketing the 53,331 scanned
candidates by their declared batch dimension m
(`scripts/ds002-strata.py`):

| Stratum | Scanned candidates | Matched | Rate |
|---|---|---|---|
| varying m (m ∉ {8,192, 32,768}) | 1,179 | 1,016 | **86.17%** |
| m = 8,192 constant | 2,103 | 50 | 2.38% |
| m = 32,768 constant | 50,049 | 0 | 0.00% |
| total | 53,331 | 1,066 | |

An earlier internal headline ("an extinction curve of matched share vs
height") is largely a composition artifact of these strata: the per-bin
rate mostly tracks each bin's varying-m share. The claims that survive,
each with its denominator:

1. **Separation.** 86.17% of blocks with live-traffic-like varying batch
   dimensions committed byte-exactly to published checkpoint tensors,
   while 0 of 50,049 constant-m=32,768 blocks did. Two structurally
   different workloads coexisted on the chain from its first days, and
   only one of them is attested model-weight mining (the other is "not
   these exact published bytes", §0.1).
2. **Within-stratum decline.** Inside the fixed m=8,192 stratum, the match
   rate falls from 49/1,532 (3.20%) at or below the boundary h54,972 to
   1/571 (0.18%) above it; two-sided Fisher exact P = 2.96e-06. Caveat:
   addresses churn across the boundary too (28 distinct below, 9 above,
   only 4 in common), so this is not a clean within-operator comparison,
   and no causal reading is attached. (A review-session figure of
   "P ≈ 1e-7" did not reproduce from the committed script and is
   superseded by the value here.)
3. **The population disappeared.** The varying-m population itself
   vanishes: its last scanned candidate is h56,473 (DS-002 population;
   DS-002b's Gemma-shaped candidates extend the combined tail to h62,319,
   §9). The scan cannot distinguish "these operators stopped committing
   published weights" from "these operators stopped producing blocks";
   both are consistent with every number here.

The table above is the DS-002 population; the Gemma-shaped stratum that
DS-002b added (phase P3) is graded in §9 and matched at 43/43,
including 23/23 at m = 8,192, so the m = 8,192 row here is a fact about
Llama-shaped declarations, not about the batch dimension itself.

Struck claims, recorded so they are never reused: "zero matches in
~36,000 blocks to the tip" (the truth, all datasets combined, is 3,556
scanned candidates above h54,972 with 3 matches, §9; candidate eligibility
is height-correlated, ~100% of the first 20,000 heights vs ~4% near the
tip, so matched/all-blocks measures the eligibility filter, not a match
rate).
The headline peak is bin-width dependent and is never quoted without one:
9.31% at 5,000-block bins (h20,000+), 24.27% at 1,000-block bins
(h24,000+).

## 4. Who and when (`scripts/ds002-operator-structure.py`, `ds002-deep-checks.py`)

All 1,066 matched blocks are unattributed (no coinbase pool tag). They
resolve to **46 distinct addresses**; the top address mined 432 of them
(40.5%), the top three 76%; effective operators (1/HHI) **4.27**. The
match-days tell the story: 21 distinct days (calendar days in the API's
UTC+2 block-time offset), **656 of 1,066 matches (62%) on 2026-04-29**,
the chain's third day (genesis 2026-04-27); steady decay through
mid-May; last cluster 2026-05-17 (h54,972); one straggler 2026-05-25
(h60,881). Height range 21,068-60,881; h21,068 is 2026-04-28, roughly
genesis plus one day (the chain's first ~20,000 blocks compressed into
its first ~36 hours and match nothing).

The m=32,768 stratum is structurally different on addresses too: a
600-block sample resolves to 457 distinct addresses (diffuse) vs 46 in
1,066 (concentrated), and the address overlap between the two populations
is **zero**. Two disjoint fleets.

Reading, within §0.3's limits: this is **launch-week adoption of the
reference stack by a handful of operators, wound down within three weeks
with a thin tail to 2026-05-27 (§9)**, not a network-wide practice that
decayed. The checkpoint repositories were
created on genesis day and never modified (revision shas pinned in the
MANIFEST), which cuts both ways per the frozen attribution text (§11).

## 5. Pre-registered analyses of the matched population (PREREG-002 §6.1-6.4)

### 5.1 Extinction curve and correlates (`ds002-aggregate.py`, `ds002-strata.py`)

Matched blocks per 5,000-block bin, combined across all three datasets
(`ds002-strata.py --combine` over DS-002 plus both DS-002b runs): the
numerator is the union of matches (1,109), the denominator all 53,717
recorded candidate blocks, and across the three runs every recorded
candidate has been hashed against its family's buffers, so no known match
sits in a zero row. The stratified §3 table is the honest headline; this
series is reported with both its numerator and denominator per bin:

| Height bin | Matched / candidates | Rate |
|---|---|---|
| 0-19,999 | 0 / 19,999 | 0.0% |
| 20,000+ | 465 / 4,995 | 9.3% |
| 25,000+ | 221 / 4,954 | 4.5% |
| 30,000+ | 72 / 4,843 | 1.5% |
| 35,000+ | 105 / 4,183 | 2.5% |
| 40,000+ | 71 / 4,362 | 1.6% |
| 45,000+ | 122 / 4,141 | 2.9% |
| 50,000+ | 50 / 2,692 | 1.9% |
| 55,000+ | 1 / 1,333 | 0.1% |
| 60,000+ | 2 / 610 | 0.3% |
| 65,000 - tip | 0 / 1,605 | 0.0% |

Correlates at the boundary, as the prereg requires:

- Consensus changes are refuted as a confound, the strongest defensive
  result here. All three of Pearl's consensus changes (MoE fork 71,935;
  dense-only 91,630; rank-penalty 96,251; `registry/PCCR.md`) post-date
  the boundary h54,972 by 16,963 blocks, and even the last matched block
  (h62,319, combined) by 9,616. The clean pre-fork window h54,973-71,934
  contains, combined across the three datasets, 2,507 recorded candidates
  with exactly 3 matches (h56,217, h60,881, h62,319; DS-002 alone: 2,505
  scanned candidates, 1 match). Nothing in consensus changed at or near
  the boundary. (A review-session count of 2,612 for the DS-002 window
  did not reproduce; 2,505 is the committed script's value.)
- **Calendar**: boundary 2026-05-17; DS-002's straggler 2026-05-25; the
  combined last attested block 2026-05-27 (h62,319, §9). The entire
  matched era is the chain's first month.
- **The second extinction**: candidate eligibility itself (blocks whose
  declared shape matches any published-model tensor) falls from ~100% of
  blocks in the first 20,000 heights to ~4% near the tip (per-bin
  candidates over bin width, table above). Both extinctions are reported;
  they are different facts with different denominators.
- **Difficulty** (live API on the recording date): 755 at the onset
  h21,068, 2,796,565 at the boundary h54,972, 3,372,839 at the last
  varying-m candidate h56,473, 5,962,295 at the straggler h60,881. The
  matched era spans a ~3,700-fold difficulty rise; the population faded as
  the work got expensive. Correlate, not cause.
- **First appearance of each labeled pool**
  (`scripts/pool-first-appearance.py`, full sweep at tip 97,605 on the
  recording date; pools are named here as neutral public chain facts under
  the roadmap 9.4 disclosure split, and nothing in this row is a conduct
  claim): PearlHash h46,963 (2026-05-08), Pearl Fortune h51,473
  (2026-05-13), LuckyPool h57,963 (2026-05-22), Hero Miners h66,836
  (2026-06-03), Kryptex h67,675 (2026-06-04). The first labeled pools
  arrive in the two weeks straddling the boundary: attested model-weight
  mining ended as public pool infrastructure emerged. Correlate, not
  cause; the matched blocks themselves are all unattributed, before and
  after.

### 5.2 Corrected layer mixture (`ds002-mixture-tv.py`)

Over matched blocks, observed layer-family frequencies against MAC-share
expected vectors built from the checkpoints' own quantization config
(gate_up and o over all 80 layers, qkv over layers 40-79 only, down
excluded as FP8, per PREREG-002 §3):

- Llama-3.3-70B, N = 1,034: observed gate_up 0.7737 / o 0.1364 /
  qkv 0.0899 vs expected 0.8116 / 0.1159 / 0.0725. **TV = 0.0379,
  MIXTURE_CONSISTENT** (threshold 0.10).
- Llama-3.1-8B, N = 32: **INSUFFICIENT_SAMPLE** (N < 200; the frozen
  verdict is reported, not the statistic).

The matched population looks like full forward passes, not a single
reused tile. This does not settle the stronger alternative in §12
(iterating a downloaded checkpoint without inference); §0.2's language is
held either way.

### 5.3 Batch-size trace (`ds002-deep-checks.py`)

Matched-block m: modes 16,384 (152 blocks), 8,192 (50), 14,000 (46), then
a long irregular tail (1,281, 6,689, 1,111, 8,932, 7,305, 14,138, ...).
**171 of 1,066 matched blocks (16.0%) declare m > 16,384**, so the pilot's
"matched population is 100% m ≤ 16,384" claim did not replicate and is
recorded in §10. m is operator-configurable; no configuration is inferred.

### 5.4 Tensor coverage (`ds002-tensor-coverage.py`)

1,066 matches land on **293 distinct tensors**: matches per tensor median
2, mean 3.64, max 16; 127 tensors matched exactly once. 70B gate_up tp1
alone covers **80 of 80 layer indices**. Per-family distinct layers:
70B gate_up tp1 80, o tp1 64, gate_up tp2 50 (both shards), qkv tp1 35,
o tp2 20, qkv tp2 9; 8B gate_up 17, qkv 3, o 1. Nine of the ten populated
DS-002 candidate families matched (8B gate_up tp2, 11 candidates, did
not); with DS-002b the count is twelve of fifteen (three Gemma families
matched completely, o tp4 and tp8 scanned to zero, §9). The "one tile
reused indefinitely" caveat is refuted for this population.

## 6. H2 (per-pool concentration) is NOT_TESTABLE, with a premise erratum

PREREG-002 §2 chose the scan set expecting labeled-pool traffic inside
`MODEL_SHAPED_CUSTOM`. The data contradict the premise: all 53,717
candidate blocks are unattributed, so no per-pool grading is possible, and
H2 is **NOT_TESTABLE** rather than silently dropped. (The controls do
carry labels, PearlHash 69 and Pearl Fortune 24 among the 1,000, so the
attribution join itself works; the candidates simply have no labeled
members. A 2,400-block API sample across five labeled pools, recorded
2026-08-08, found 0% model-shaped blocks.)

## 7. The 14 MODEL_SHAPED_CUSTOM matches, presented unsmoothed

Fourteen matched blocks fail PREREG-001's T1 (tile patterns outside the
unmodified official stack) while matching published weights byte-exactly
(`ds002-deep-checks.py`): heights 48,782-54,950 plus the straggler 60,881;
12 of the 14 declare m = 8,192 exactly, the other two m = 5,806 and
m = 6,858; all rank 128 with official minimum dims; families gate_up tp1
(11) and qkv tp1 (3). The frozen classifier and the cryptography disagree
about these blocks, and the disagreement is the finding: **tile patterns
identify mining software, not honesty**. Custom or reconfigured software
committed genuine published weights. (This also seeds roadmap 14.4's
software census; it is not smoothed into either neighboring class.)

## 8. Controls, specificity, and the positive control

- **Negative control**: 0 matches in 840,000 control pairs (1,000 CUSTOM
  blocks × 840 buffers). Scope honestly stated: the control blocks span
  heights 41,237-52,280 only, and §1 of the prereg itself limits the
  control to an implementation canary; it has no power against false
  negatives and no power in the post-boundary region.
- **Post-boundary positive control (spike-in)**, closing that gap:
  `scripts/ds002-spikein-control.py` doctors the first three post-boundary
  candidate records (h54,973, h54,980, h54,981) in a scratch copy of the
  extract, setting each `hashB` to the keyed BLAKE3 of a real buffer
  (three distinct tensors) under that block's own on-chain-derived
  `job_key`, then runs the production Go hash stage (release binary
  `eb3b7989dfa1-wb73d662`) over the copy: **3 of 3 detected, 0 false
  extras** (run 2026-08-09). The pipeline detects post-boundary matches by
  construction when they exist. The spike-in exercises the hash stage
  (manifest loading, keyed BLAKE3, match comparison, result emission), not
  the extract stage, whose derivation proofs are checked per block in §1.
- **Specificity framing (binding)**: "every matched block commits to
  exactly one of 293 distinct tensors" is a data-integrity check, not
  statistical evidence (one `hash_b` can only ever match one
  distinct-bytes buffer; the MANIFEST records zero byte-identical
  buffers). The evidence for any single match is the keyed-BLAKE3
  equality, the clean control, and the independent reproduction path:
  `scripts/verify-hashb-match.py` re-derives everything from raw
  Blockbook bytes and pip blake3, trusting no Keshi code. Reproduced on
  the recording date: block 22,816 (70B gate_up L000, DS-002), block
  56,217 (Gemma-4-31B gate_up L007) and block 62,319 (Gemma-4-31B gate_up
  L032), the last attested block on the chain (DS-002b, §9), all green
  with the header self-check passing.

## 9. DS-002b closes the coverage gap (P2 remainder + P3), and finds a third species

Two matched coverage runs, executed 2026-08-09 on release binary
`eb3b7989dfa1-wb73d662` (which emits the §10 coverage fields; both
summaries record snapshot tip 97,590, scan bound `toHeight` 96,774, and
their unscanned counts, and neither has any assigned candidate id without
a buffer), both pinned to DS-002's snapshot tip with `--to 96774`, both
with the same deterministic 1,000-block control (the prereg fixes control
selection, so this is the same control as DS-002, not a second one):

- **Run 3a, 70B `o_proj` tp4/tp8** (960 sliced buffers, byte-checked
  against the DS-002-era tp1 buffers and golden-checked against the
  reference miner before launch): 343 candidate blocks (338 tp4-shard
  shaped, 5 tp8), all below the boundary. **1,071,360 pairs, 0 matches, 0
  control hits.** This independently confirms a reviewer's out-of-band
  hash of the same 343 blocks (also 0), and closes the last unvalidated
  layout family with a clean zero: every populated 70B family is now
  either matched on-chain (tp1, tp2) or scanned to zero (o tp4/tp8).
- **Run 3b, Gemma-4-31B gate_up + o at tp 1,2** (330 buffers at pinned
  revision `f1dfba688ce6343b0433de57ca4dc0f3d1c5baa5`; the checkpoint's 10
  attention-variant layers carry `o` at k = 16,384, a shape outside the
  frozen tables, excluded as a declared exclusion): 43 candidate blocks.
  **333,200 pairs; all 43 of 43 matched; 0 control hits; no block matched
  more than one tensor.** Every family matched completely: gate_up tp1
  32/32, gate_up tp2 9/9, o tp2 2/2, across 34 distinct tensors.

The Gemma result upgrades the coverage story into a finding of its own:

- A third model species, at a 100% rate over its searched universe: every
  block whose declared shape matched a searched Gemma tensor committed
  byte-exactly to the published Gemma-4-31B weights, 43 of 43. The
  searched universe is bounded by PREREG-002 §5's declared exclusions (the 10
  attention-variant `o` layers and the FP8 families are not searched, so
  a block declaring those shapes would not be a candidate here). Within
  the 43: 20 of 20 varying-m and 23 of 23 m = 8,192 blocks matched
  (contrast the Llama-shaped m = 8,192 stratum at 2.38%, §3).
- The tail extends: matched heights run 26,883 (2026-04-29, the
  launch-spike day) through **62,319 (2026-05-27)**, which replaces
  h60,881 as the last attested model-weight block on the chain. Two of the
  43 sit above the boundary: h56,217 (2026-05-19) and h62,319. Both are
  independently reproduced from raw chain bytes (§8).
- The operator cluster is the same one, not a new phenomenon: the 43
  blocks resolve to 4 addresses, effective operators (1/HHI) 1.15, with
  one address mining 40 of 43 (h39,763-47,350). Two of the four also
  appear in DS-002's matched set: the address behind the §7
  MODEL_SHAPED_CUSTOM cluster (15 Llama-matched blocks, h48,782-54,950)
  mined Gemma h56,217, and an early two-block Llama address mined the
  first Gemma match h26,883. The combined matched population is 1,109
  blocks over 48 addresses; the addresses were resolved per block from
  the API on the recording date (same method as §4,
  `ds002-operator-structure.py`).
- The classifier disagreement recurs, stronger: 40 of the 43 are
  MODEL_SHAPED_CUSTOM under the frozen classifier and 3 OFFICIAL_CONSISTENT;
  with §7's 14, the cryptography now contradicts the tile-pattern class on
  54 blocks across two model families. Tile patterns identify software,
  never honesty.

Combined tail, all datasets, stated with its denominators: above the
boundary h54,972 there are 3,556 scanned candidates (3,554 DS-002 + 2
DS-002b Gemma + 0 o tp4/tp8) and exactly **3 matched blocks** (h56,217,
h60,881, h62,319); zero matches from h62,320 to the frozen tip 96,774.
The attested era runs 2026-04-28 to 2026-05-27, the chain's first month.

Even after DS-002b, "zero unscanned" remains false and is never claimed:
zero records in DS-002's extract carry a Qwen3 candidate id (checked by
grep over the committed dataset on the recording date), so Qwen3 needs a
sentence, not a scan; MoE expert-stacked layouts were never in the
candidate universe (PREREG-002 declares the extraction problem open); and
§0.1's ceiling bounds everything.

## 10. Errata, dated

- 2026-08-09: **DS-002 violates PREREG-002 §7.2 and §2**: `summary.json`
  and `MANIFEST.md` record neither the snapshot tip nor the unscanned
  count. The dataset is append-only and is not edited; the values are
  recorded here (snapshot tip 96,774; 386 unscanned candidates) and the
  tool now emits both (plus per-family unhashed accounting) in every later
  run, DS-002b included. Policy: `ERRATA-POLICY.md`.
- 2026-08-09: the pilot claim "matched population is 100% m ≤ 16,384" did
  not replicate on the full run (171/1,066 above the bound), §5.3.
- 2026-08-09: the review-session statistics "P ≈ 1e-7" (m=8,192 decline)
  and "2,612 candidates in the clean pre-fork window" (DS-002 population)
  did not reproduce from the committed scripts; the values in §3 and §5.1
  (P = 2.96e-06; 2,505 for DS-002, 2,507 combined) supersede them.
- Struck and never reused: "zero matches in ~36,000 blocks to the tip";
  any matched/all-blocks rate quoted as a match rate; any peak rate
  without its bin width.

- 2026-08-11: **Consolidated post-audit errata (PREREG-003 coverage
  closure and control redraw; datasets DS-006 and DS-007).** An audit
  dated 2026-08-10 found never-scanned certificate cells and a
  mis-specified negative control in the original OBS-005 / DS-002 work.
  The registered coverage-closure and control-redraw scans are now
  committed as DS-006 (coverage closure) and DS-007 (stratified
  control), and the corrections they support are recorded here in one
  dated block per `ERRATA-POLICY.md`. The deposited version-1 copy
  retains the original text; the external artifact gains a version
  naming this block (ADR-0014 decision 3). Section references are to
  this note.

  1. **The last attested block is h68,332 (2026-06-05), not h62,319.**
     §9's statements "zero matches from h62,320 to the frozen tip
     96,774" and "h62,319 replaces h60,881 as the last attested
     model-weight block" are superseded. The h68,332 match (Gemma
     attention-variant `o`, n 5,376, k 16,384, layer 53) was found by
     the post-publication shape sweep, recorded first as a roadmap
     erratum, and has now been re-derived into a committed results file
     under PREREG-003 R1 (DS-006-coverage-closure-v1; 1 match in 10
     pairs; independently reproduced from raw block bytes). §5.1's
     "65,000 - tip | 0 / 1,605" row is likewise superseded: with the
     DS-006 closure scan folded in, the band holds 1 attested block
     among 1,606 scanned, the added scanned block being h68,332 itself.
     The two era sentences that read the old end date as a calendar
     month are superseded the same way: §5.1's "the entire matched era
     is the chain's first month" and §9's "the attested era runs
     2026-04-28 to 2026-05-27, the chain's first month". On the combined
     basis the attested era runs 2026-04-28 (h21,068) to 2026-06-05
     (h68,332), 39 days after the 2026-04-27 genesis, so the era is the
     chain's first six weeks, not its first month. Wherever this note
     and the sections disagree on the era, this note governs.

  2. **Three never-scanned certificate populations are now closed
     (PREREG-003 R1, DS-006):** two cells the frozen classifier omitted
     against PREREG-002 §3's implied-mineable table (the Qwen3-30B
     attention `o` tp4 cell and the Gemma attention-variant `o` cell),
     plus one clearly labeled exploratory alternative-sharding cell (the
     70B `o` column-parallel tp2 layout hypothesis). The counts, over
     DS-001's span (heights 0 to 96,405): the Qwen3-30B attention `o`
     tp4 cell (2,048, 1,024), 10 blocks, **0 matches in 1,920 pairs**;
     the 70B `o` column-parallel tp2 cell (4,096, 8,192), 371 blocks,
     **0 matches in 59,360 pairs**; the Gemma attention-variant `o`
     cell, 1 block, 1 match (item 1); 28 of the 31 enumerated cells hold
     0 corpus blocks. Both zeros are layout-conditional in the
     PREREG-002 §5 sense.

  3. **The negative control's composition is disclosed and its stated
     null was wrong.** PREREG-002 §1 described control blocks as
     committing to differently-shaped operands. In fact 10 of the 1,000
     control blocks declare the Qwen3 `o` tp4 shape (a published
     checkpoint shape), the control has exactly 7 distinct (n, k) with
     824 of 1,000 at one shape, and the same 1,000 blocks were reused
     across all three runs, so "0 hits in 2,130,000 control pairs across
     the three runs" describes 1,000 distinct blocks against 2,130
     distinct buffers, never 2.13 million independent trials. The counts
     themselves stand; item 2's scan establishes that the 10
     checkpoint-shaped members do not commit to that checkpoint's
     tensors, so no contamination occurred, and the count "0 in 840,000
     control pairs" remains literally correct (those pairs never
     included a Qwen3 attention buffer). A redrawn, era-stratified
     control with a corrected shape-exclusion null is registered as
     PREREG-003 R5 and committed as DS-007. R5 drew 952 blocks
     stratified by era (200 each from the pre-boundary, post-boundary,
     MoE-window, and dense-only strata; 152 from the shorter
     rank-penalty stratum), each block's declared shape absent from
     every searched cell, and hashed them with the shape filter disabled
     against all seven searched buffer sets (the 70B, 8B, and Gemma
     reference sets plus the o tp4/tp8, Qwen3 attention, column-parallel,
     and Gemma attention-variant sets): 0 matches in 2,372,384 pairs.
     The corrected control reproduces the clean canary the original was
     meant to provide, now with a null that holds by construction.

  4. **The o-family byte-order hypothesis for the unmatched varying-m
     residue: refuted for the registered population.** 162 of the 163
     unmatched varying-m candidates are `o`-family shapes; PREREG-003 R2
     probed the column-major byte-order variant (V1) with a built-in
     positive control: the 20 control blocks, drawn by the registered
     seed from the 144 matched `o` blocks, matched 20 of 20 under the
     standard convention, each at exactly the tensor DS-002 had recorded
     for it, and 0 of 1,680 pairs under V1, which validates the variant
     pipeline in both directions. Over the population, V1 produced 0
     matches in 3,040 pairs for the 95 8B `o` tp1 blocks and 0 matches
     in 10,160 pairs for the 67 70B `o` blocks (7 tp1, 60 tp2). A
     transposed byte-order commitment to these checkpoints' `o` tensors
     is excluded for all 162 blocks at the pinned revisions; the residue
     remains unmatched and unexplained. PREREG-003 R3 likewise probed
     the two registered gate_up tp2 layout variants (P1, `up|gate`
     concatenation order; P2, slicing the already-fused tensor per rank)
     over the 1,905 unmatched gate_up tp2 blocks, with the same built-in
     positive control (20 of 20 matched gate_up tp2 blocks re-matched
     under the standard convention, 0 of 20 under each variant): 0
     matches in 304,800 pairs for P1 and 0 in 304,800 for P2. Neither
     alternative fusion or shard layout explains that residue either.

  4a. **No block committed to either third-party int8 artifact that was
     scanned (PREREG-003 R4).** The population is the 2,216 unmatched
     candidates outside the m 32,768 stratum, which is not a
     non-constant-m residue: 2,053 of the 2,216 declare constant m
     8,192 and only 163 vary (counts over DS-002's extract). It was
     scanned against a published third-party W8A8 quantization of the
     70B architecture (0 matches in 326,080 pairs) and an 8B candidate
     (0 in 3,744), at the revisions pinned in DS-006. Verified: the 496
     buffers built for R4 (400 for the 70B artifact, 96 for the 8B) are
     byte-distinct from every buffer any earlier run searched, 0 sha256
     in common with the 2,130 DS-002 and DS-002b reference buffers and 0
     with all 3,148 non-R4 buffers recorded in DS-006, so R4 put new
     operands in front of these blocks rather than re-searching the
     pearl-ai bytes. Inferred: different quantization grids produce
     different int8 codes, which is the reason to expect a third-party
     requantization of the same architecture to be a distinct operand
     rather than a re-encoding. The only checkpoints any block attested
     to remain the published pearl-ai ones.

     What R4 does not cover. PREREG-003 R4 named two 70B candidates as
     verified eligible before the freeze. The RedHat W8A8 artifact was
     retrieved and scanned, as above; the second named candidate was not
     retrieved in the session that produced this note and so was never
     scanned. Whether its int8 buffers are byte-equivalent to the
     scanned artifact is unverified, and no claim is made either way.
     The R4 zero therefore bounds the two artifacts named in DS-006 at
     their pinned revisions, one 70B and one 8B, and says nothing about
     third-party int8 quantization in general.

  5. **Effective sample size, restated at the honest unit.** The
     combined 1,109 matched blocks resolve to 48 addresses; effective
     addresses (1/HHI) 4.59; effective match-days 2.73; effective
     (address, day) units **5.40**; 657 of 1,109 (59.2%, combined
     basis) fall on 2026-04-29 via 7 addresses, and the top address
     mined 430 of its 432 matches on that one day. §0.3's "62%" is the
     DS-002-only basis (656 of 1,066) and §0.3's 4.27 is the DS-002-only
     effective-address figure; both reproduce on the DS-002 basis, and
     the basis for each is stated here so the DS-002-only and combined
     figures are not conflated. Including item 1's h68,332, whose
     address is new, the attested population is 1,110 blocks over 49
     addresses (effective addresses 4.60).

  6. **"0 of 50,049" is a three-shape statement.** The constant-m 32,768
     stratum comprises exactly three declared shapes from two
     checkpoints at tp1: (57,344, 8,192) x 31,831, (28,672, 4,096) x
     16,530, and (10,240, 8,192) x 1,688. The zero excludes those exact
     published bytes for those shapes and nothing broader.

  7. **§9's phrase "closes the last unvalidated layout family with a
     clean zero" is withdrawn.** A zero cannot validate a layout. The 8B
     gate_up tp2, 70B `o` tp4, and 70B `o` tp8 layouts remain
     golden-checked only, exactly as PREREG-002 §5 warned; their zeros
     are layout-conditional. Separately, the layouts that did match are
     now also conformance-tested by a second, from-specification
     extractor implementation (six buffers spanning the six matched
     layout kinds, gate_up, qkv, and o at tp1 and tp2, on the 70B
     checkpoint, byte-exact against the recorded dataset hashes;
     `scripts/independent-extract.py`).

  8. **§3 claim 2's Fisher test is address-confounded.** One address
     mined 811 of the 1,483 below-boundary unmatched m 8,192 candidates
     (811 of the stratum's 2,053 unmatched candidates overall; heights
     33,777 to 49,675) and has exactly one match of its own (h37,772),
     so both arms of the 3.20% versus 0.18% comparison are dominated by
     a handful of addresses and the two-sided P of 2.96e-06 over blocks
     overstates the evidence. Full-population address counts for the
     unmatched stratum are 43 distinct below the boundary and 9 above, 5
     in common; §3's parenthetical (28, 9, 4) was computed on seeded
     300-block samples and is superseded by these. The crosstab stands;
     the P is withdrawn as the headline statistic.

  Every figure above was produced by commands against the committed
  datasets on 2026-08-11, with the combined-basis address and day
  figures resolved per block from the API: items 5 and 8 need the
  per-block minerAddress that the committed operator sidecar does not
  carry at the 1,110 basis. The PREREG-003 runs are frozen at commit
  d2b83c55626865a1c32254e893fb731307da889c and their datasets carry that
  hash. Corrections to this block, if ever needed, ship as a further
  dated block, never as edits.

## 11. Attribution alternatives (frozen text, verbatim)

A match identifies **weights, not a miner**. These readings are written
down now so that whichever the data supports is not a post-hoc rescue:

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

## 12. Threats to validity, and what would falsify this

- **Composition, not decline**: §3 exists because the aggregate curve
  mostly tracks stratum shares. Any reader quoting a single rate from this
  note without its stratum and denominator is misquoting it.
- **Eligibility filter**: candidate share falls ~100% to ~4% with height
  (§5.1); nothing here says what ineligible blocks computed.
- **Address churn**: the §3 claim-2 comparison is across different address
  sets (28/9/4); it is a population statement, not an operator statement.
- **Pseudo-replication**: §0.3; the effective sample is ~4.3 operators.
- **Control scope**: negative control spans h41,237-52,280 (canary only);
  post-boundary detection power is demonstrated by the §8 spike-in, not by
  the control.
- **Coverage bounds**: §9's exact search space, plus §0.1's ceiling; every
  zero is "not these exact bytes".
- **The stronger alternative left open**: a miner iterating a downloaded
  checkpoint without serving inference is consistent with §5's mixture,
  batch, and coverage results. Nothing in this note distinguishes real
  serving from replaying checkpoint layers; §0.2's claim is exactly what
  is proven, no more.
- **What would falsify the finding**: any control match (voids the run by
  the frozen table); failure of the independent raw-bytes reproduction on
  any published match; byte-identical buffers in the manifest (would void
  the specificity integrity check); a derivation-proof failure on a
  matched block; the spike-in failing to detect doctored records. As of
  the recording date, all five checks pass.

## 13. Prior art

The one adjacent measurement paper (arXiv:2606.04819, retrieved
2026-08-08) analyzes miner economics on the dominant pool binary; it never
touches certificates, `hash_b`, or checkpoint matching, and it lists
workload provenance as unsolved future work requiring an external PKI. Its
artifact repository is unreachable (404) and it has no academic citations
we could find. On that basis, and per the frozen outcome table's own
wording, this is the first cryptographic evidence of attested model-weight
mining on any chain that we are aware of. External review (roadmap 8.6)
is invited before publication; the review window and invitations are
logged in `OUTREACH-log.md`.

## 14. Reproduction

- Dataset-only: `KESHI_DS002_DIR=<dir> scripts/ds002-reproduce.sh`
  regenerates every table above (sections 1-3 offline; 4-5 with a Keshi
  API or an emitted address artifact). Datasets under
  `docs/research/datasets/DS-002-weight-scan-v1/` (and `DS-002b-*` per
  §9), each with sha256 MANIFESTs; licence and field-by-field schema in
  `DATA-LICENCE.md`.
- Any single match, trusting no Keshi code:
  `verify-hashb-match.py --height H --buffer <tensor.bin>` (raw Blockbook
  block, pip blake3, header self-check).
- The positive control: `ds002-spikein-control.py --out <scratch> --run`.
