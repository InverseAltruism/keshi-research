# KMS-002: keshi-attest v0, the weight-provenance disclosure standard

- Series: KMS-002 in the Keshi methodology spec series (KMS-003 is the
  signed metric feed, [`../metrics.md#metric-feed`](../metrics.md#metric-feed)).
- Status: **methodology spec, v0, draft, not published.**
- Date: 2026-08-10.
- Authorization and blast radius: roadmap Phase 8.3, resolved spec-only by
  the operator on 2026-08-10
  (Keshi's internal roadmap). Everything adoption-dependent stays
  shelved per
  Keshi's unilateral-track decision:
  no attestation anchoring, no inference receipts, no reserved-bytes PIP,
  no registry, no outreach, no adoption pitch. This document defines a
  verification methodology. It stands up no infrastructure and creates no
  obligation on anyone.

## 1. Purpose and scope

keshi-attest standardizes one narrow, mechanically checkable disclosure:

> For each block in a stated set S, the weight operand the miner committed
> on-chain as `hash_b` is tensor T (layer family, tensor-parallel degree,
> shard index, transformer layer index) of published model M at pinned
> revision R.

Any third party can verify the claim from public data alone: the raw block
bytes and the published checkpoint. No cooperation from the discloser, the
network, or Keshi is required, and nothing in the claim is taken on trust;
a reader recomputes.

The verification primitive this spec fixes already exists and has run at
corpus scale: it is the keyed-root recomputation executed as the DS-002 /
DS-002b weight-provenance scans and graded in
[OBS-005](../research/OBS-005-weight-provenance-scan.md), under the frozen
method of [PREREG-002](../research/PREREG-002-weight-provenance-scan.md).
This spec names the conventions so that a claim made by anyone is
verifiable by anyone, in either direction:

- **Retroactive verification** (no discloser): a verifier scans historical
  blocks against candidate public tensors. This is what Keshi ran.
- **Voluntary disclosure** (this spec's addition): a miner publishes a
  signed claim over its own blocks, and verifiers check it. Whether anyone
  ever does so is outside this document's concern (ADR-0013 records why no
  adopter is expected today); the methodology is identical either way.

Terminology: the party publishing a claim is the **discloser**; the party
checking it is the **verifier**; one (block, tensor) pair inside a claim is
an **assertion**.

## 2. Boundaries: what a verified disclosure attests, and what it cannot

Read this section before using any result. The finding label for a
verified assertion is **attested model-weight mining**, never "certified
inference" (binding:
[`../metrics.md#attested-model-weight-mining`](../metrics.md#attested-model-weight-mining),
PREREG-002 "Binding language", Keshi's language policy).

### 2.1 What a match attests (verified against Pearl source)

The source-verified claim ladder, from
Keshi's internal protocol notes, Certificate internals ("What
consensus enforces") and OBS-005 §0.2: mainnet consensus accepts a block
only after a Plonky2 recursion over the Pearl STARK verifies against
public inputs taken from the header-committed certificate
(`node/blockchain/validate.go:333`). Inside that proof the opened strips
of A and B are authenticated against the certificate's `hash_a`/`hash_b`
by in-circuit keyed-BLAKE3 Merkle recomputation
(`v1/circuit/pearl_air.rs:91-103`), and the same strip values, plus noise
the verifier derives from the commitments, feed the folded transcript that
must hash below target. Therefore a consensus-accepted block whose
`hash_b` equals the keyed root of a published tensor attests, beyond
operand identity:

> the sampled output entries verified by consensus were computed from
> strips of that tensor, after a publicly-derivable rank-r perturbation.

Residuals bounding the strong form (same sources): the multiplied operands
are the noised strips, not the pristine ones the root commits to; each
strip enters products over `dot_product_length = k - (k mod r)` of its
entries; values are int7 range-checked; row/column semantics are a
labeling outside consensus; and nothing binds `hash_a` to real
activations, so the attestation is one-sided toward the weights operand.

### 2.2 What a match can never attest

1. **The activation side.** `hash_a = blake3(A, key=job_key)` commits to
   the activation operand, which is private input data, never published,
   and therefore not matchable against anything
   (`../pearl-notes.md` §Certificate internals, offset table entry
   `hash_a`; PREREG-002 §8). The batch dimension m and everything about
   what A contained are unattested. A keshi-attest claim is a claim about
   B only.
2. **That inference was served.** A match proves the committed operand and
   the sampled computation of §2.1, never that a forward pass completed,
   that output was returned to anyone, that a customer existed, or that
   the computation was fresh (PREREG-002 "Binding language"; OBS-005 §0.2
   and §12, which leaves open a miner iterating a downloaded checkpoint
   without serving anything).
3. **That the declared matmul ran.** Consensus proves at most the `h·w`
   sampled output entries per block: the V2 path enforces
   `32 ≤ h·w ≤ 256`, and the V1 path, which governs every block below the
   MoE fork at height 71,935, enforces only `h·w ≥ 32` with indirect
   upper bounds (`../pearl-notes.md` §Certificate internals, "What the
   proof actually covers", citing `api/sanity_checks.rs:39-40` and
   `v1/api/sanity_checks.rs:39`). The declared `m × n × k` arithmetic is
   never verified; the observed proven/declared ratio is about 1e-7 at
   block 94,748
   ([`../metrics.md#attestation-ratio`](../metrics.md#attestation-ratio)).
   Never describe a verified assertion as proving the declared matmul.
4. **Anything about non-public weights.** Verification recomputes
   `blake3(tensor_bytes, key=job_key)`, so it needs the exact bytes.
   Private models, fine-tunes, locally requantized variants, evolving
   training weights, and synthetic matrices are mutually indistinguishable
   on chain (OBS-005 §0.1). Only public, static checkpoints are checkable.
5. **Weight reuse or identity across blocks.** `job_key` includes the
   coinbase-dependent merkle root, so `hash_b` is per-block: identical
   weights hash to different values in different blocks, no precomputed
   lookup table exists, and nothing fingerprints an operator's model over
   time (`../pearl-notes.md` §Certificate internals, "What consensus
   enforces", final sentences; OBS-005 §0.1).
6. **Who mined.** A match identifies weights, not a miner; anyone can
   download the same public weights and mine them (PREREG-002,
   "Attribution alternatives"). The disclosure signature of §4 binds a
   claim to a key, not to an entity, and a payout key may belong to a
   pool or custodian rather than the machine operator.

## 3. The verification primitive

### 3.1 The on-chain commitment (verified, Pearl source via `../pearl-notes.md`)

All byte coordinates below are source-verified and validated against real
mainnet blocks (`../pearl-notes.md` §Certificate internals; the genesis
certificate round-trips to the known genesis hash).

- Certificate public data carries, at fixed offsets: `hash_a` at
  `[52:84]`, defined as `blake3(A, key=job_key)`, a keyed Merkle root
  over the activation operand; `hash_b` at `[84:116]`, defined as
  `blake3(Bᵀ, key=job_key)`, a keyed Merkle root over the transposed
  weight operand; the declared dims `k` at `[0:4]`, `m` at `[148:152]`,
  `n` at `[152:156]` (offset table, `../pearl-notes.md` §Certificate
  internals).
- The key is the job key:
  `job_key = blake3(block_header ‖ mining_config)`
  (`zk-pow/src/api/proof_utils.rs:347`, via `../pearl-notes.md` §Key
  derivations). Concretely, and as measured against the reference
  implementation:
  `job_key = blake3(header_bytes[0:76] ‖ cert_public_data[0:52])`, an
  unkeyed BLAKE3 over the 76-byte incomplete header concatenated with the
  52-byte mining config prefix of the public data. Both preimage halves
  are on-chain (ADR-0013 §Context; PREREG-002 §0).
- The commitment reaches the block id:
  `ProofCommitment = SHA256d(cert_version_LE ‖ PublicData)` is a header
  field and block id `= SHA256d(header)`, so the public data, `hash_b`
  included, is committed into the block id and secured by all subsequent
  work (`../pearl-notes.md` §Key derivations). Noise seeds derive from
  the commitments (`b_noise_seed = blake3(job_key ‖ hash_b)`, same
  section), so operands are committed before the noise is knowable; that
  ordering is the protocol's anti-grinding structure and is what gives
  §2.1 its strong form.
- The Merkle root reduces to a flat keyed hash:
  `MatrixMerkleTree.root == blake3(raw_tensor_bytes, key=job_key)` over
  the raw, unpadded int8 bytes, asserted by Pearl's own tests at three
  levels and measured against minted fixtures
  ([`../fixtures/scanhash/MANIFEST.md`](../fixtures/scanhash/MANIFEST.md));
  the tree's zero padding is internal leaf storage only, and real weight
  tensors are exact 1024-byte multiples anyway (ADR-0013 §Context,
  including the 2026-08-07 erratum). The tree commits to the pristine
  pre-noise int8 weights in native (N, K) row-major layout; no
  requantization, scales, or repacking enter the hash (ADR-0013
  §Context).

The transposition convention costs nothing in practice: the checkpoint
stores each weight tensor as (n, k) row-major, which is exactly the `Bᵀ`
the commitment hashes, so the buffer is the tensor's stored bytes and no
transposition step exists in the pipeline (ADR-0013 §Context; PREREG-002
§5).

### 3.2 The candidate buffer (weights side), by reference to DS-002

The buffer construction conventions are frozen in PREREG-002 §5 and
implemented by
[`../../scripts/extract-weights.py`](../../scripts/extract-weights.py);
this spec adopts them by reference rather than restating them:

- buffer bytes = row-major contiguous int8 of the (n, k) tensor at the
  pinned checkpoint revision;
- fused layers concatenate along dim 0 in vLLM order (`q|k|v`,
  `gate|up`);
- column-parallel layers (`qkv`, `gate_up`) shard n; row-parallel (`o`)
  shards k; one buffer per (layer family, tp degree, shard index,
  transformer layer index);
- layer eligibility is read from the checkpoint's own
  `quantization_config` cross-checked against stored safetensors dtypes:
  int8-stored INT7 layers are candidates, FP8 (`F8_E4M3`) layers can
  never be an INT7 operand and are excluded (PREREG-002 §3).

Epistemic status of the layouts, marked per the house rule: the
conventions for `gate_up_fused` tp1/tp2, `qkv_fused` tp1/tp2, and `o`
tp1/tp2 are confirmed by byte-exact on-chain matches (OBS-005 §5.4 and
§9 report matched blocks in each of those families); `o` tp4/tp8 buffers
are golden-checked against the reference miner but have no on-chain match
(OBS-005 §9, run 3a); MoE expert-stacked layouts (the published Qwen3
checkpoint) are not implemented and are outside every claim this spec can
express (PREREG-002 §2, §5).

Updated 2026-08-11 from the PREREG-003 coverage-closure round (DS-006;
OBS-005 §10, the 2026-08-11 block). The Gemma attention-variant `o`
layout at k 16,384 is now match-confirmed rather than golden-checked
only: h68,332 matched it, 1 of 10 pairs under R1, independently
reproduced from raw block bytes. Two further cells were scanned to zero
and remain layout-conditional in the PREREG-002 §5 sense: the Qwen3
attention `o` tp4 cell, 0 of 1,920 pairs over 10 blocks, and the
exploratory 70B column-parallel `o` tp2 layout hypothesis, 0 of 59,360
pairs over 371 blocks. The column-major byte-order variant of `o` is
refuted for this corpus, 0 of 13,200 pairs, against a positive control
that matched 20 of 20 under the standard convention and 0 of 1,680 under
the variant (PREREG-003 R2), so the variant pipeline is validated in
both directions.

### 3.3 The match predicate

An assertion (block H, tensor T) is verified iff the 32 bytes of
`blake3(buffer_bytes(T), key=job_key(H))` equal the 32 bytes of that
block's `hash_b` exactly. No fuzzy matching, no prefix matching, no
tolerance (PREREG-002 §4). Because `job_key` is per-block (§2.2 item 5),
verification cost is one keyed BLAKE3 over the full tensor per
(assertion), roughly the tensor's byte size in hashing work; there is no
shortcut and no reusable table.

## 4. The disclosure document

A disclosure is one self-contained JSON document. Design goals, in order:
minimal, self-verifying, offline-checkable. Everything a verifier needs is
either in the document or derivable from public data it names. The schema
below is a design decision of this spec (inferred/authored here, not a
chain fact), modeled on the canonical-form discipline of the KMS-003
metric feed ([`../metrics.md#metric-feed`](../metrics.md#metric-feed)).

### 4.1 Fields

```json
{
  "keshiAttest": "v0",
  "claim": {
    "statement": "attested model-weight mining disclosure per KMS-002 v0",
    "model": {
      "repo": "pearl-ai/Llama-3.3-70B-Instruct-pearl",
      "revision": "6cc401caab46ffa688dea3553b2f55d3dfc1d0aa"
    },
    "recipe": {
      "spec": "KMS-002 v0 §3.2 (PREREG-002 §5 conventions)",
      "reference": "keshi scripts/extract-weights.py"
    },
    "tensors": [
      {
        "id": "gate_up_fused.tp1.s0.L000",
        "family": "gate_up_fused",
        "tp": 1,
        "shard": 0,
        "layer": 0,
        "bytes": 469762048,
        "sha256": "<64-hex sha256 of the extracted buffer>"
      }
    ],
    "assertions": [
      {
        "height": 22816,
        "blockHash": "<64-hex block id>",
        "tensor": "gate_up_fused.tp1.s0.L000"
      }
    ]
  },
  "signingScheme": "BIP-340 (Schnorr over secp256k1)",
  "messageDigest": "<64-hex sha256 of the claim member bytes>",
  "pubkey": "<64-hex x-only key: the coinbase payout key of the claimed blocks>",
  "signature": "<128-hex BIP-340 signature over messageDigest>"
}
```

The `bytes` value above is n·k of the fused 70B gate/up tensor
(57,344 × 8,192, dims per PREREG-002 §3; product recomputed at spec-writing
time). Block 22,816 is a real matched instance, independently reproduced
from raw chain bytes in OBS-005 §8; hash placeholders are left
unpopulated because this example is illustrative, not a disclosure.

Field rules:

- `model.revision` is the checkpoint repository's commit sha, pinning the
  exact bytes; a claim without a pinned revision is not verifiable and is
  rejected as malformed.
- `tensors[].sha256` is the sha256 of the extracted buffer, so
  verifier-side extraction defects are separable from match failures: if
  the verifier's buffer hash differs, the disagreement is about
  extraction, not about the chain.
- `assertions[]` may reference any tensor in `tensors[]`; one block
  carries exactly one `hash_b`, so one assertion per block.
- Nothing in the document names any operator, pool, or entity. The only
  identity present is the discloser's own key. Self-attribution by a
  discloser is that party's statement about itself; it licenses no
  Keshi-side naming of anyone else.

### 4.2 Canonical form and signature

The signed message is the exact bytes of the `claim` member's value as
they appear in the document, from its opening `{` to its closing `}`
inclusive; `messageDigest` is the lowercase-hex sha256 of those bytes,
and the signature is BIP-340 over the 32-byte digest. A verifier slices
the `claim` value out of the document and hashes it; no re-serialization
is required or permitted. This mirrors the KMS-003 digest discipline
([`../metrics.md#metric-feed`](../metrics.md#metric-feed)).

The signing key is the coinbase payout key of the claimed blocks
(roadmap 8.3's deliverable definition): Pearl addresses are Taproot-only,
witness v1, 32-byte program (`../pearl-notes.md` §Network / ports /
address model), so the natural v0 binding is the x-only output key of the
coinbase payout output, and every claimed block's coinbase must pay that
key for the disclosure to be a miner disclosure. What the signature
proves, exactly: control of the payout key at signing time, and that the
key's controller endorses the claim. It does not prove the signer
physically mined the blocks (pools and custodians hold payout keys), and
it contributes nothing to the truth of the assertions, which stand or
fall on §3.3 alone. An unsigned document can still be verified as a set
of assertions; it is then an anonymous claim, not a disclosure.

### 4.3 Malformed documents

Missing revision, a tensor outside §3.2's implemented layouts, an
assertion referencing an undeclared tensor, or a digest that does not
match the claim bytes make the document malformed. Malformed is a
document-level state, distinct from every per-assertion verdict in §5.

## 5. Third-party verification procedure

The reference single-assertion implementation is
[`../../scripts/verify-hashb-match.py`](../../scripts/verify-hashb-match.py),
which trusts no Keshi code: raw block from any Blockbook-compatible
source, offsets parsed by independent arithmetic, pip `blake3`, exit 0 on
match, 2 on mismatch, 1 on error. A v1.0 of this spec requires that the
verifier be reimplementable from the spec text alone and that a second
independent implementation exist (roadmap 8.5); v0 has one reference
implementation, this text, and a second, from-specification
implementation of the §3.2 buffer construction
([`../../scripts/independent-extract.py`](../../scripts/independent-extract.py)),
conformance-tested byte-exact against the recorded DS-002 buffer hashes
on six buffers spanning every match-confirmed family
([`../fixtures/independent-extract-conformance.json`](../fixtures/independent-extract-conformance.json)).
The remaining v1.0 gap is a second independent implementation of the
§5.1 block-side steps.

### 5.1 Per-assertion steps

1. **Fetch and self-check the block.** Obtain the raw block bytes for
   `height`. The certificate is serialized before the header
   (`node/wire/msgheaders.go:27`, via `../pearl-notes.md` §Framing);
   split off the certificate, then assert
   `SHA256d(header) == blockHash`. The header slice is thereby
   self-proving; nothing downstream depends on trusting the data source.
2. **Extract the commitment.** Read the certificate public data; take
   `hash_b = public_data[84:116]` and the declared dims (`k` at `[0:4]`,
   `n` at `[152:156]`). Optionally re-derive
   `ProofCommitment = SHA256d(cert_version_LE ‖ PublicData)` and compare
   against the header field (§3.1).
3. **Shape precondition.** Check the block's declared (n, k) equals the
   claimed tensor's sharded dims. Shape equality is the necessary
   condition for any tile of that layer to hash to `hash_b`
   (PREREG-002 §2); a mismatch fails the assertion without hashing.
4. **Derive the key.**
   `job_key = blake3(header_bytes[0:76] ‖ public_data[0:52])`, unkeyed
   (§3.1).
5. **Materialize the buffer** for the claimed tensor per §3.2 at the
   pinned revision; compute its sha256 and compare to the document's
   `tensors[].sha256`. A disagreement here is an extraction dispute, not
   a chain verdict; stop and report it as such.
6. **Compare.** Compute `blake3(buffer_bytes, key=job_key)` and compare
   all 32 bytes to `hash_b`.
7. **Check the signature** (once per document, not per assertion) per
   §4.2. Report signature validity separately from assertion verdicts:
   the two axes are claim authenticity and claim truth, and they never
   substitute for one another.

### 5.2 Verdicts

Each assertion ends in exactly one verdict:

- **match**: step 6 equality holds. The assertion is verified; §2 governs
  what that does and does not mean, and the finding label is attested
  model-weight mining.
- **no-match**: step 3 or step 6 fails. The assertion as stated is
  refuted for exactly the named (tensor, revision, layout); nothing more.
  A no-match never establishes what the block did commit.
- **not-checkable**: the assertion cannot be evaluated: the model's
  weights are not public, the layer is FP8-quantized (PREREG-002 §3), the
  layout is outside §3.2's implemented set (MoE expert stacking), or the
  pinned revision is no longer retrievable. Not-checkable is reported as
  such, never folded into either other verdict.

Aggregate reporting states counts per verdict with the denominator's
composition (which blocks, which tensors, which strata), per the
provenance rules in
[`../metrics.md#weight-provenance-match`](../metrics.md#weight-provenance-match).

### 5.3 Negative-result discipline (binding)

Any published no-match, and any aggregate zero, ships with its exact
search space, never as proof of absence (PREREG-002 §5 and §6; OBS-005
§0.1, §9). The search-space statement enumerates at minimum:

- model repositories and pinned revisions searched;
- layer families and transformer-layer index ranges, with the FP8 and
  other declared exclusions;
- tensor-parallel degrees and shard indices;
- the byte-layout conventions used (row-major int8, fusion order, shard
  axis, no padding, native (n, k) storage as the transposition
  convention), and which of those are match-confirmed versus
  source-derived (§3.2);
- the block population evaluated and how it was selected.

A zero bounded this way reads "not these exact published bytes, under
these conventions, in these blocks" and licenses no claim about useful
work in general
([`../metrics.md#attested-model-weight-mining`](../metrics.md#attested-model-weight-mining)).

### 5.4 Controls for scanning verifiers

A verifier evaluating many assertions (or scanning retroactively) runs a
negative control: blocks whose declared shapes cannot carry any searched
tensor must produce zero matches, as an implementation canary against
gross false-positive machinery; any control match voids the run as a
defect, never a finding (PREREG-002 §1 and §6). The executed instance: 0
matches in 840,000 control pairs in DS-002, and 0 in 2,130,000 control
pairs combined across the three runs (840,000 + 330,000 + 960,000, all over
the same deterministic 1,000 control blocks reused per buffer set, not three
independent controls; OBS-005 §2, §8, §9). PREREG-003 discloses that
control's composition, which PREREG-002 §1 had described only as
differently-shaped operands: the 1,000 blocks carry exactly 7 distinct
declared (n, k), 824 of them at one shape, and 10 declare the Qwen3 `o`
tp4 shape, a published-checkpoint shape not searched at the time. Those
10 were scanned under PREREG-003 R1 and matched nothing (0 of 1,920
pairs), so no contamination occurred. PREREG-003 R5 registers the
redrawn control: 952 blocks stratified by era, each declaring a shape
absent from every searched cell, hashed with the shape filter disabled
against all seven searched buffer sets, 0 matches in 2,372,384 pairs
(DS-007). Detection power in
sparse regions is demonstrated by a spike-in positive control, not by the
negative control (OBS-005 §8). Single-assertion verification needs no
control; its evidence is the keyed equality plus the independent
reproduction path.

## 6. Relationship to Keshi's shipped artifacts

- **DS-002 / DS-002b and OBS-005 are a Keshi-run instance of this
  verification**, with Keshi as verifier and no discloser: a retroactive
  scan of 53,717 candidate blocks against 840 Llama-checkpoint buffers
  (DS-002), completed by the DS-002b coverage runs and then by the
  PREREG-003 closure round over 382 further blocks, yielding 1,110
  matched blocks combined (1,109 in DS-002 and DS-002b, plus h68,332 in
  DS-006), every published match independently
  reproducible from raw chain bytes (OBS-005 §1, §2, §8, §9, §10;
  datasets under
  [`../research/datasets/`](../research/datasets/DS-002-weight-scan-v1/MANIFEST.md),
  including
  [DS-006](../research/datasets/DS-006-coverage-closure-v1/MANIFEST.md)
  and
  [DS-007](../research/datasets/DS-007-stratified-control-v1/MANIFEST.md);
  reproduction via `scripts/ds002-reproduce.sh`). Those documents, not
  this spec, carry the findings and their caveats.
- **The KMS-003 signed metric feed**
  ([`../metrics.md#metric-feed`](../metrics.md#metric-feed)) is the
  separate signed-metric surface: Keshi-computed corpus series under
  Keshi's own signature. keshi-attest is the inverse arrangement, a
  third party's claim under the third party's signature, checked by
  anyone.
- **Keshi's role**: Keshi authors this standard and verifies claims made
  under it. Keshi operates no registry, maintains no list of disclosers,
  makes no market in attestations, and solicits none (ADR-0013; roadmap
  8.3's registry deliverable is shelved, and the operator decision of
  2026-08-10 authorizes only this document).

## 7. Non-goals and exclusions (explicit)

1. No attestation anchoring on-chain, no reserved-bytes PIP, no on-chain
   slot of any kind (ADR-0013 decision 1; the shelved 11.1/13.3 items).
2. No inference receipts and no receipt sidecar (ADR-0013 decision 1,
   Phase 12).
3. No registry, scorecard, or "attested share" surface; those 8.3
   deliverables are not authorized and are not part of v0.
4. No adoption pitch, no outreach, no naming of any mining operator,
   pool, or entity as a party to any finding. Model names appear only as
   the object of a provenance claim (the published checkpoint being
   matched), which is the subject matter of the standard.
5. No "certified inference" language, anywhere, under any verdict
   (ADR-0011; `../metrics.md` language policy). Shape or class statements
   are consistency statements, never proof.
6. No claim about the activation side, batch contents, or service to any
   customer (§2.2).
7. This document is not published and confers no publication decision;
   publication of anything in this line is held (ADR-0013 gates;
   operator decision 2026-08-10).

## 8. Versioning

v0 is a draft methodology artifact. Changes before v1.0 edit this file
with a dated changelog entry below; the freeze-and-errata discipline of
the research documents (frozen pre-registrations, corrections as new
numbered documents) applies from v1.0 onward, and v1.0 additionally
requires the second independent verifier implementation of §5. The
schema's `keshiAttest` field carries the version a document claims.

Changelog:

- 2026-08-10: v0 initial draft.
- 2026-08-10: recorded the from-specification second implementation of
  the §3.2 buffer construction and its byte-exact conformance fixture
  (§5 head). Layout epistemic-status and control-composition updates
  from PREREG-003 are pending the DS-006 / DS-007 dataset commits and
  the OBS-005 errata; they ship as a later dated entry.
- 2026-08-11: the entry the 2026-08-10 note deferred, now that DS-006,
  DS-007 and the OBS-005 §10 errata block are committed. §3.2 records
  the Gemma attention-variant `o` layout as match-confirmed by h68,332
  and adds the two layout-conditional zeros and the refuted column-major
  byte-order variant. §5.4 discloses the executed control's composition
  and registers the era-stratified redraw (R5, DS-007). §6 restates the
  combined matched count as 1,110 and points at DS-006 and DS-007.

## 9. References

- Keshi's internal protocol notes, Certificate internals
  (public-data offsets; key derivations; what the proof covers; what
  consensus enforces) and §The mining stack. Primary source coordinates
  cited there: `zk-pow/src/api/proof_utils.rs:347` (job_key),
  `node/blockchain/validate.go:333` (certificate verification in
  consensus), `v1/circuit/pearl_air.rs:91-103` (in-circuit strip
  authentication), `api/sanity_checks.rs:39-40` and
  `v1/api/sanity_checks.rs:39` (sampled-entry bounds),
  `node/wire/msgheaders.go:27` (certificate-before-header framing).
- [PREREG-002](../research/PREREG-002-weight-provenance-scan.md): frozen
  method, search space, outcome table, binding language.
- [PREREG-003](../research/PREREG-003-coverage-closure-and-control-redraw.md):
  the frozen coverage-closure, layout-probe and control-redraw runs
  behind §3.2 and §5.4 (datasets DS-006 and DS-007).
- [OBS-005](../research/OBS-005-weight-provenance-scan.md): the executed
  verification at corpus scale, controls, reproduction paths.
- Keshi's unilateral-track decision:
  what is shelved and why; the CPU-only verification basis and the
  raw-bytes erratum.
- Keshi's language policy and
  [`../metrics.md`](../metrics.md): language policy and the
  weight-provenance metric definitions.
- [`../fixtures/scanhash/MANIFEST.md`](../fixtures/scanhash/MANIFEST.md):
  minted hash vectors pinning the primitive.
- [`../../scripts/verify-hashb-match.py`](../../scripts/verify-hashb-match.py),
  [`../../scripts/extract-weights.py`](../../scripts/extract-weights.py),
  [`../../scripts/ds002-reproduce.sh`](../../scripts/ds002-reproduce.sh):
  reference implementations.
