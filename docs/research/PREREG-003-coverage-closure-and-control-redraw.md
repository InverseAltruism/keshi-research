# PREREG-003: coverage closure, layout probes, and the control redraw

- Status: **FROZEN at the commit that introduces this file.** Amendments
  ship as later numbered documents, never as edits here.
- Date: 2026-08-10. Revised same day after an adversarial soundness
  review (18 findings applied before the freeze).
- Relationship to PREREG-002: that document stays frozen and governs the
  executed DS-002 / DS-002b runs. Per ERRATA-POLICY's pointer-line rule,
  PREREG-002's preamble (outside its frozen sections 2-7) gains one
  clearly marked non-normative pointer to this document, shipped in a
  commit after this file's freeze commit.
- Method by reference: buffer construction conventions, the match
  predicate, and the reproduction path are PREREG-002 §4 and §5 and
  KMS-002 §3, unchanged. This document registers populations, variants,
  a new control, and verdict rules.

## 1. Why these runs

The 2026-08-10 audit established, from the committed datasets:

1. The frozen candidate classifier (`internal/certclass/models.go`)
   omits layer families that PREREG-002 §3 declares mineable. The known
   consequence: 10 corpus blocks declaring (n 2,048, k 1,024), which is
   the Qwen3-30B attention `o_proj` shard at tp4, were never scanned
   against the tensor family their declared shape implies (as control
   members they were hashed only against Llama buffers), and all 10 sit
   inside DS-002's 1,000-block negative control. One previously
   excluded cell was chased outside this document: the Gemma
   attention-variant `o` at k 16,384 produced a byte-exact match at
   h68,332, recorded as a dated erratum in the roadmap; that match is
   not reproducible from any committed results file, and the sweep that
   found it is committed as its own dataset before R1 results are
   reported.
2. DS-002's negative control does not satisfy the null PREREG-002 §1
   stated for it ("commit to differently-shaped operands"): 10 of its
   1,000 members declare a published-checkpoint shape, its diversity is
   exactly 7 distinct (n, k) with 824 of 1,000 at one shape, and the
   same 1,000 blocks were reused across all three runs.
3. The unmatched residue of the matched era clusters in ways that
   suggest convention rather than weight differences: 162 of the 163
   unmatched varying-m candidates are `o`-family shapes, and 1,904 of
   the 2,053 unmatched constant-m 8,192 candidates are the 70B
   `gate_up` tp2 shape in a family whose standard layout is
   match-validated.

## 2. Registered runs and populations

All populations are defined over the committed, frozen datasets by
exact filter, so every population is reproducible by command before any
new hashing starts. Notation: `matched` is the set of heights with
`match == true` in any DS-002 or DS-002b results file; `extract` is
DS-002's `extract.jsonl.gz`; the span is DS-001's, heights 1 to 96,405
(DS-002's frozen candidate tip is the later 96,774; the difference is
the classification snapshot, stated here so no reader reconciles them
silently).

**R1, coverage closure.** Enumerate every (model, layer family,
tensor-parallel degree, shard) cell implied by PREREG-002 §3's mineable
table that the frozen classifier omits. Dims are read per tensor from
each pinned checkpoint's safetensors headers, never from config
defaults, and per-layer dim variants are enumerated as distinct cells
(the h68,332 class, an attention-variant dim invisible in the config,
is exactly what config-derived enumeration re-misses). The enumeration
also includes, clearly labeled exploratory, the alternative-sharding
cells for `o` (column-parallel shard shapes) for EVERY pinned
checkpoint, Llama included, since a miner using that convention would
declare those shapes rather than the row-parallel ones. The buffer for
an exploratory column-parallel cell at rank r of tp is the contiguous
row block [r n/tp, (r+1) n/tp) of the row-major (n, k) tensor.
Procedure (executor: `scripts/prereg3-cells.py`, named here so the
freeze is auditable): expand each family to sharded (n, k) shapes under
the PREREG-002 §5 conventions with tp in {1, 2, 4, 8}; all dims come
from safetensors headers, and the kv-head replication boundary comes
from the config, which is a sharding-rule parameter rather than a dim;
drop cells violating the frozen shape floors (k at least 1,024 and n at
least 256, certclass MinK/MinN, with the sharded dim divisible by tp;
the enumerator additionally requires k divisible by 64, which drops no
cell in the pinned checkpoints); subtract cells the classifier or the
executed scans already carry, supplied as a mandatory input that is
exactly the cells recorded in the DS-002 and DS-002b MANIFESTs
(extraction manifests for not-yet-hashed buffers are excluded, as is
the C4 sweep cell) and is committed alongside cells.json, making it
identical to the executed-scan set R5's eligibility names; emit every
remaining cell as its own row (no shape-level deduplication; sampled
height lists are labeled as samples), with counts, as
`DS-006-coverage-closure-v1/cells.json`, **committed before any
hashing**; scan every nonzero cell. A family whose headers are not I8
is not enumerated, and that outcome is reported as a correction to
PREREG-002 §3's table, never as a silently empty enumeration. Known in
advance: the Qwen3-30B attention cells (o full (2,048, 4,096); fused
qkv (5,120, 2,048); per-tp shards accordingly), of which the o-at-tp4
cell has the 10 blocks of §1.1; and the exploratory 70B o
column-parallel tp2 cell (4,096, 8,192), which holds 371 DS-001 blocks,
all OFFICIAL_PATTERN_NONMODEL at constant m 4,096, none in DS-002's
control, never scanned. The Qwen3 checkpoint is pinned at revision
751fd1052d4b25faf16072173493b15097a12901.

**R2, o byte-order probe.** Population, by exact filter: extract
records with `control == false`, `candidates` nonempty, height not in
`matched`, `m` not in {8,192, 32,768}, and candidate family `o`
(162 blocks; the 163rd varying-m residual, h48,687, is gate_up tp2 and
is probed in R3). One variant, fixed here: **V1, column-major
byte order** of the canonical buffer (the bytes of the transposed
matrix laid out in the declared (n, k) shape; a framework storing the
tensor transposed would commit exactly these bytes). V1 preserves the
declared shape for every population member, square or not. Built-in
positive control: 20 blocks drawn from the 144 matched `o` blocks
(120 70B tp1, 21 70B tp2, 1 8B tp1, 2 Gemma tp2), hashed under the
standard convention (must match) and under V1 (must not match); any
deviation voids the variant run. Reversed-shard-order and
column-parallel buffer variants are deliberately absent: every shard
index of every searched family was already hashed in DS-002/DS-002b, so
shard-order permutations cannot produce a new match, and
column-parallel sharding implies different declared shapes, which R1's
exploratory cells cover instead.

**R3, gate_up tp2 permutation sweep.** Population, by exact filter:
extract records with `control == false`, height not in `matched`,
`candidates == ["Llama-3.3-70B/gate_up_fused/tp2"]`, and
(`m == 8192` or `height == 48687`): 1,905 blocks, the 1,904 constant-m
members plus the one varying-m block of the same shape, so no residual
is orphaned between R2 and R3.
Permutation set, fixed here: **P1** `up|gate` concatenation order
(standard is `gate|up`); **P2** slicing the already-fused tensor per
rank (standard, per PREREG-002 §5, shards each sub-projection first and
concatenates per rank; P2 is the historically plausible defective
layout). Positive control: 20 blocks drawn from the 80 matched gate_up
tp2 blocks, same must-match / must-not-match rule as R2.

**R4, third-party quantization scan.** Population: the 2,216 unmatched
candidates outside the m 32,768 stratum: R2's 162, R3's 1,905, plus the
remaining 149 unmatched m 8,192 candidates (137 70B `o` tp1, 11 8B
gate_up tp2, 1 70B `o` tp2). Candidates: published checkpoints of
the same architectures whose quantization stores int8 weight tensors
for the relevant families, pinned by revision at execution. Two
verified eligible before this freeze:
RedHatAI/Llama-3.3-70B-Instruct-quantized.w8a8 and
CalamitousFelicitousness/Llama-3.3-70B-Instruct-W8A8-INT8; 8B
candidates are screened by the same rule (config-declared int8
symmetric weight storage) before download. Buffers follow PREREG-002 §5
applied to the third-party checkpoint. Self-requantization from base
weights is out of scope: checked 2026-08-10, the published source tree
carries only a runtime GPU activation-quantization kernel, no offline
checkpoint recipe, and the base checkpoints are gated.

**R5, control redraw.** A new negative control replacing DS-002's for
all runs registered here: per era stratum (pre-boundary h1-54,972;
post-boundary pre-MoE 54,973-71,934; MoE window 71,935-91,629;
dense-only 91,630-96,250; rank-penalty 96,251-96,405), draw 200 blocks,
or every eligible block where a stratum holds fewer than 200 (the
rank-penalty stratum holds 155 blocks in total before exclusions); the
realized per-stratum n is reported. Eligibility: the block's declared
(n, k) appears neither in the committed `cells.json` (R1's enumerated
list, including the exploratory cells) nor among the cells recorded in
the DS-002 and DS-002b MANIFESTs; **the R5 draw therefore runs only
after the `cells.json` commit.** The draw's shape composition is
reported, not forced, and this null differs from PREREG-002 §1's by
design: eligibility is shape-only rather than class-restricted, so the
eligible pool includes model-shaped and official-consistent blocks
whose declared shapes match no searched cell, which is sufficient for
the canary purpose (an unsearched shape cannot match) and is stated
here so nobody reconciles the two nulls silently. The spike-in positive
control is rerun in a scratch copy of the R5 extract, as in OBS-005 §8,
so the recorded run is unaffected.

Randomness: `seed = 0x50524733 + offset`, with offset 2 for R2's
positive-control draw, 3 for R3's, and 5 + i for R5 stratum i (i = 0..4
in the order listed above). Each draw is
`random.Random(seed).sample(heights_sorted_ascending, k)` with
`k = min(target, len(eligible))`, under CPython 3.11 or later. A run's
variants share one draw (R2's V1 uses the offset-2 draw; R3's P1 and P2
share the offset-3 draw).

## 3. Predictions, stated before running

- R1: no directional prediction for the 10 Qwen3 o-tp4 blocks; both
  outcomes are informative (a match triggers the §4 contamination
  branch; a zero bounds the cell, layout-conditionally per §6). For all
  other enumerated cells the expectation from the corpus record is zero
  or near-zero matches, with one exception: the Gemma attention-variant
  o cell (5,376, 16,384), whose one block h68,332 is a known match
  being re-derived into a committed results file; a non-match there
  falsifies the roadmap erratum and is reported as exactly that.
- R2/R3: exploratory. A hit is a layout-convention discovery about
  buffer construction, never a new-weights finding, and reclassifies
  the affected non-matches; the correction ships as a new numbered
  note.
- R4: expectation is zero (different quantization grids should not
  produce byte-identical int8 codes); a hit is a new attested-species
  finding.
- R5: expectation is zero matches; see §4 for the rule.

## 4. Verdict rules, including the pre-decided contamination branch

PREREG-002 §6 rules "any control match: implementation defect, the run
is void". That rule presumed a correctly specified control. For the
runs here:

1. A byte-exact match on a member of DS-002's ORIGINAL control under R1
   is **control contamination**: a finding about the control's
   specification, not a scanner defect and not a voiding event. It is
   verified through the independent raw-bytes reproduction path before
   being reported. What it corrects is precisely stated: DS-002's
   "0 matches in 840,000 control pairs" remains literally true (those
   pairs never included a Qwen3 attention buffer); what falls is
   PREREG-002 §1's specification premise ("control blocks commit to
   differently-shaped operands") and the canary interpretation resting
   on it. The correction ships as a dated errata block in OBS-005, and
   the external deposit gains a new version naming the errata, per
   ERRATA-POLICY. A new numbered note is written only if a central
   finding of OBS-005 reverses, which this branch by itself does not.
2. An R1 match on a block that is NOT an original-control member is an
   ordinary positive result under PREREG-002 §6's first row: attested
   model-weight mining, extended to a new cell.
3. A match inside the NEW R5 control is an implementation defect and
   voids the affected run, exactly as PREREG-002 §6 intended, because
   R5's null is specified against the full searched cell set.
4. An R4 match is a new attested-species finding, reproduced per §5 and
   shipped as its own numbered note; it voids nothing.
5. R2/R3 variant hits reclassify; they do not void. A variant that
   fails its built-in positive control is itself void (wrong variant
   implementation), reported as such.
6. Every zero is reported with its exact cell list, buffer set,
   revision pins, and block population, never as proof of absence.
7. Ordering: the OBS-005 §10 dated errata block recording the h68,332
   correction lands before any PREREG-003 run reports anything about
   the extinction tail.

## 5. Artifacts and freeze mechanics

- Results are emitted append-only into
  `docs/research/datasets/DS-006-coverage-closure-v1/` (R1-R4,
  including `cells.json`) and
  `docs/research/datasets/DS-007-stratified-control-v1/` (R5), each
  with MANIFEST sha256 lists, the emitting tool identity, and this
  document's commit hash recorded in the summary as `prereg3Commit`.
- The commit that adds this file is its freeze point. The PREREG-002
  pointer line and the `cells.json` commit both come after it.
- Every new match is independently reproduced from raw Blockbook bytes
  (`scripts/verify-hashb-match.py`) before it is reported anywhere.

## 6. Known limitations, stated in advance

- R1 dims for Qwen3 attention derive from safetensors headers and
  fused-layer conventions source-derived from the mining stack; no
  Qwen3 attention layout is match-validated in advance. A zero in those
  cells is layout-conditional, exactly as PREREG-002 §5 warns for
  unvalidated layouts, and is reported with that caveat.
- R4 covers only checkpoints that publish int8 weight storage; GPTQ
  packed formats and FP8 storage are out of scope by construction.
- Nothing here changes the structural ceiling: private, requantized,
  training, or synthetic operands remain mutually indistinguishable on
  chain, and no zero below supports a claim about useful work in
  general.
