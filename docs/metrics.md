# Keshi metric definitions

Every number Keshi displays must be traceable to an entry here: **source, formula, window, caveats**. If a metric has no entry, it does not ship. API responses reference these definitions via `formulaRef` (the anchor slug).

## Language policy: "useful work"

Pearl's PoUW accepts any matrices that satisfy the consensus predicate; nothing on-chain proves a matrix multiplication served a real AI customer (acknowledged design property of cuPOW; empirically examined in arXiv:2606.04819, unrebutted as of 2026-08-02). Therefore:

1. Keshi labels network security throughput as **"PoUW work rate"** (or "consensus work rate"), never "AI compute", "useful compute", or "inference".
2. **EH/s** figures are always footnoted: *"matmul attempts per second: a difficulty-derived consensus measure, not a measure of AI computation performed."*
3. The whitepaper's useful-work unit (**TMADs/sec**) is a distinct quantity; if we ever display it, it gets its own definition and is never conflated with EH/s.
4. "Certified inference work" may only appear if backed by verifiable gateway/provider/workload attestation data, with methodology published here first.
5. Protocol *capability* (the same GEMM could carry inference) vs observed *utilization* (whether it does) stays explicit in all copy.

This policy is a product differentiator. Do not weaken it for marketing reasons.

## Money and units

- All monetary arithmetic in **grains** (1 PRL = 1e8 grains) as int64/BIGINT/decimal-strings. Max supply 2.1e17 grains > 2^53: **floats are forbidden** in any money path, including JSON (strings on the wire).
- PRL display values are formatting-layer only.

## Chain health

### tip-height {#tip-height}
Source: own pearld (`getbestblock`). Canonical Keshi height. Cross-checked against own Blockbook and (soft) official Blockbook.

### tip-age {#tip-age}
`now − tip.header.timestamp`. Caveat: header timestamps are miner-set (±5 min tolerance); display "block age", not "network latency".

### block-interval {#block-interval}
Windows: 1h/24h/7d/30d, computed from header timestamps of canonical blocks: `(t_last − t_first)/(n−1)` over the window. Target line: 194 s. Caveat: miner timestamps; early chain (difficulty ramp) makes lifetime averages meaningless. Never extrapolate height↔time.

### reorg-count / reorg-depth {#reorg-count}
Source: collector `reorg_events` (observed by our node; reorgs are node-local observations, labeled as such).

### mempool-count / mempool-vbytes {#mempool-count}
Source: own pearld `getmempoolinfo`/`getrawmempool`. **Per-node measure**: other explorers will disagree (observed 18 vs 133 across sites); label "our node's mempool".

## Mining & security

### work-rate {#work-rate}
**Definition:** estimated network matmul-attempt rate derived from difficulty and observed block production:
`work_rate(W) = Σ_{blocks in W} work(b) / (t_end − t_start)` where `work(b) = 2^256 / (target(b)+1)` (Bitcoin-standard expected-attempts measure applied to Pearl's BLAKE3 tile predicate).
Unit: H/s rendered as EH/s ("matmul attempts/s" footnote per policy).
**Window is a first-class, user-visible parameter** (default 200 blocks ≈ 11 h; options 50/200/1000/24h/7d). Cross-site divergence up to 26% is window-driven; we show ours, never scrape theirs.
Validation: sanity-compare against `getnetworkhashps` from our node; parity-log against PearlTrack/prlscan values at matching windows (comparison only, never source).

**Unit precision (definitional; the series is unchanged).** "Matmul attempts" is loose for what `2^256/(target+1)` counts. Pearl's accept bound scales the target by the work one attempt costs, `target · h · w · dot_len` where `dot_len = k_eff`, and one attempt performs exactly `h · w · dot_len` int8 MACs, so the factor cancels and the difficulty-derived quantity is the expected int8 MACs per block, `2^256/target`, invariant to rank, `k`, `h` and `w` ([`research/OBS-007`](research/OBS-007-rank-escalation-economics.md) §1; verified, re-read from the pinned `pearl-src` @ v1.4.1 `zk-pow/src/api/sanity_checks.rs` `difficulty_adjustment_factor` and the `jackpot/helper.rs` contraction loop, both files byte-identical to v1.3.0, which is the revision OBS-007 cites). A true attempt, one tile-predicate evaluation, is therefore the smaller unit: expected evaluations per block are `2^256/(target · h · w · dot_len)`, lower by that factor. The `+1` is the Bitcoin target-space convention and is immaterial at mainnet targets. At and after the rank-penalty fork (96,251) the bound carries the extra `128/rank` multiplier, so expected MACs per block become `(2^256/target) · (rank/128)` and the MAC reading is exact only at rank 128 (`penalized_adjustment_factor`, same file; verified).
Scope of this correction: the EH/s series, [#profit-per-work](#profit-per-work) and the parity comparison above all sum the same difficulty-derived quantity and are unaffected; only the label's precision is at issue. The unit string is served by the API responses, the OpenAPI description, the site copy and Keshi's language policy, so renaming it is a coordinated deploy, tracked separately from this entry. The ecosystem reading that other sites' EH/s figures count attempts is recorded as convention in Keshi's internal protocol notes and has not been checked against any other site's implementation: unverified.

### difficulty {#difficulty}
Source: own pearld tip header `bits` → difficulty vs max target. WTEMA adjusts every block (7-day half-life), so difficulty is a smooth series, not a step function; chart it as such.

### pool-share {#pool-share}
Coinbase output address → `pool_labels` match, windows 24h/7d/30d. Unmatched → "unattributed" (shown, never hidden or redistributed). Label provenance: `verified` (block-producing wallet cross-validated vs two independent explorers), `announced` (self-declared, no blocks; e.g. PearlNet), `heuristic` (future clustering; not in v0.1).

### pool-concentration {#pool-concentration}
Largest-1/3/5 shares and effective pool count `1/Σs_i²` (inverse HHI) over attributed blocks; note the unattributed fraction alongside. Nakamoto coefficient: min pools summing >50% **of attributed blocks** (caveat displayed).

### concentration-series {#concentration-series}
Height-binned concentration over canonical blocks (`/v1/metrics/concentration-series`; `bin` blocks per bin, default 1000, accepted 100–10000, newest 200 bins). The entity is the coinbase miner address, labeled or not: [#pool-share](#pool-share) labels play no part, because labels are sparse in early bins and label coverage drift would masquerade as concentration change. Per bin, blocks are counted per address; largest-1/3/5 shares, effective operators (inverse HHI `1/Σs_i²`) and the Nakamoto coefficient come from the shared `internal/concentration` definitions. Two bases, both reported: **attributed-only** divides by the bin's blocks with a decodable coinbase address; **all-blocks** divides by every canonical block in the bin. The unattributed fraction (blocks with no decodable coinbase address / all canonical blocks in the bin) is always returned, never hidden, never redistributed, and never entered as a pseudo-entity. A measure with no value is `null`, never 0: an empty basis, or a Nakamoto crossing that does not exist because addressed blocks never exceed half the bin. Effective operators is attributed-only (inverse HHI needs shares that sum to about one). Caveats: one operator can span several addresses, so address-based top-N shares are lower bounds and the address-based Nakamoto coefficient is an upper bound on operator concentration (the keshictl co-spend dataset measures that gap); the newest bin is still filling and is flagged partial.

### profit-per-work {#profit-per-work}
`Σ(subsidy + fees) / Σ work` over canonical blocks in a window (`/v1/metrics/profit-per-work`; windows 24h/7d/30d), where per-block work is `2^256/(target+1)` summed in NUMERIC, the same accounting as [#work-rate](#work-rate). The quotient is emitted as a decimal string in grains per matmul attempt; no float touches the money path. Denominator composition: canonical blocks in the window that carry a `chain_metric_samples` work row; the response states both that count (`blocks`) and the window's full canonical count (`windowBlocks`) and is `partial` when they differ (backfill) or the span is under two blocks. This is gross protocol revenue per unit of consensus work, not miner profit: hardware, power and payout policy are off-chain, and the work unit carries the [work-rate](#work-rate) labelling policy (matmul attempts, never "AI compute"). Pool fee drag: `Σ(coinbase_value · fee_pct/100)` rounded to whole grains over the subset of blocks whose coinbase address has a pool label with an advertised fee (`pool_labels.fee_pct`: self-declared, applied to payouts by the pool, not verifiable on chain) and that also carry a work sample (so mid-backfill this population can be smaller than all labelled-with-fee blocks in the window), reported with that subset's block count and coinbase sum as its denominator; fraction = drag / subset coinbase sum. When the window has no such block, the drag is reported unavailable (`null`), never 0.

## Economics

### subsidy-current {#subsidy-current}
`Reward(t) = floor_grains(S·H/((t+H)(t+H−1)))` at t = tip height (wraps Pearl's own `blockchain.CalcBlockSubsidy`). **Pearl coinbases pay subsidy + fees in a single output**, so `blocks.fees = coinbase_value − subsidy(h)`. Validated continuously: the collector cross-checks that derived value against prevout-resolved per-tx fee sums; mismatch = alert (would indicate a consensus change or an indexing bug).

### issuance-observed {#issuance-observed}
Σ coinbase outputs of canonical blocks ≤ tip. **This is Keshi's headline supply number.**

### issuance-theoretical {#issuance-theoretical}
`S·t/(t+H)` at tip height. Displayed alongside observed; the delta is itself informative (rounding dust, any skipped/zero coinbases; genesis pays 0).

### circulating-supply (market context only) {#circulating-supply}
CoinGecko's figure, displayed only in market panels, labeled "exchange-reported circulating (CoinGecko)", known to differ from on-chain issuance (−4.5% on 2026-08-02, unexplained). Never mixed into chain metrics.

### fees-daily / fee-subsidy-ratio {#fees-daily}
Σ(tx fees) per day from our index (`valueIn − valueOut` per non-coinbase tx, computed from resolved prevouts; Blockbook's `fees` field used only as cross-check). Ratio: fees / (fees + subsidy) per window.

### market-price / market-cap {#market-price}
Source: CoinGecko `pearl-2`, cadence ≤1/5min, isolated collector (failure never touches chain data). Market cap displayed with its supply basis stated ("price × CoinGecko circulating"). CoinEx lists PRL as ticker `PEARL`; the alias is handled in the adapter. SafeTrade ≈85% of volume: display a thin-liquidity note.

## Usage

### tx-count-daily {#tx-count-daily}
Canonical non-coinbase tx count per UTC day. Coinbase-only blocks counted as 0 txs; "% empty blocks" is its own series.

### transfer-volume {#transfer-volume}
Σ non-coinbase output values per window. Caveat displayed: includes change outputs; UTXO chains make raw volume an upper bound on economic transfer. (Change-heuristic-adjusted volume is Phase 2+, methodology TBD here first.)

### active-addresses {#active-addresses}
Distinct addresses appearing in inputs or outputs per window. Standard caveat: addresses ≠ users.

## Certificate arithmetic

Source for everything in this section: `cert_public_params` joined to canonical `blocks`, restricted to rows at the current decoder version (`chain.CertDecoderVersion`; see Keshi's internal data-model notes). The corpus is append-only, so a decoder fix changes these series only after a rebuild and re-backfill. **Declared values are what the miner CLAIMS was multiplied; proven values are what the ZK proof actually covers, at most `tileSize ≤ 256` output entries per block** (`32 ≤ h·w ≤ 256`, zk-pow `sanity_checks.rs:39-40`; the product matrix C is never emitted). Never call a declared quantity "proven", and never present either as AI work performed (the language policy above applies unchanged). `k_eff = k − (k mod rank)`. The genesis block's empty certificate (rank 0, m = n = 0) declares no computation and is skipped from the series (and shown as its own labeled bucket in the census).

### cert-rank {#cert-rank}
Noise rank r per canonical block, from the decoded certificate. API series name `rank`. Windows 50/200/1000/24h/7d/30d/all (all = newest 5,000 points). Caveats: rank is a miner-chosen proof parameter, not throughput; the v1.3.0 softfork (height 96,251, **no PIP**; see [`registry/PCCR.md`](registry/PCCR.md) PCCR-0005) rejects r < 128 and multiplies the difficulty bound by 128/r. Observed transition: [`research/OBS-001`](research/OBS-001-rank-penalty-fork-transition.md).

### declared-arithmetic {#declared-arithmetic}
`m · n · k_eff` MACs per block: the multiplication the miner asserts it performed. Unit `macs`. **Not proven**: consensus never verifies the declared matmul; the proof covers a ≤256-entry sample (see [#proven-arithmetic](#proven-arithmetic)). Windowed aggregate: Σdeclared. Computed in NUMERIC end to end (peaks near 2^64): never a float, never BIGINT, decimal strings on the wire.

### proven-arithmetic {#proven-arithmetic}
`tileSize · k_eff` MACs per block: the arithmetic the ZK certificate actually attests (the h·w opened output entries). Unit `macs`. Windowed aggregate: Σproven and `macsPerSecond = Σproven / (t_last − t_first)`, the *measured* counterpart to [#work-rate](#work-rate), published **alongside** it, never replacing it. Caveat: tile-predicate attempts are not committed multiply-accumulates; this is the attested floor of arithmetic performed, not machine throughput and not AI work.

### attestation-ratio {#attestation-ratio}
Per block: `proven / declared = tileSize / (m · n)`. `k_eff` cancels, so the per-block ratio is **purely geometric** (opened output entries over declared output entries), independent of k and rank. Point values are the NUMERIC quotient as a decimal string, never fixed-decimal rounded (which would destroy the `256 / 2^48 ≈ 9.1e-13` floor); PostgreSQL division carries ~16+ significant digits, exact through a float64 parse. Windowed aggregate: `Σproven / Σdeclared` (MAC-weighted, **not** the mean of per-block ratios; state which one is quoted). This is the flagship number: how much of the claimed computation the consensus mechanism actually verifies. Observed ≈1e-7 at block 94,748.

### cert-census {#cert-census}
Distributions over the decoded corpus in a window (`/v1/certs/census`, default window `all`): rank histogram (rank 0 = the genesis empty certificate, shown not hidden), top-20 `(m, n, k, rank, tile h×w)` shapes by block count, MoE certificate count (`moe_e > 0`), and a per-pool rank crosstab via coinbase-address labels (the [#pool-share](#pool-share) provenance ladder; the unattributed remainder is always shown, never redistributed). Canonical blocks only: orphaned blocks' certificates are retained in the corpus but excluded here.

### cert-search {#cert-search}
Filtered listing over the decoded corpus (`/v1/certs/search`): canonical blocks at the current decoder version whose declared certificate parameters match every applied filter (`shapeClass`, `rank`, `m`, `moe`; filters AND together, all matches exact), newest first with a keyset height cursor (`before`/`nextBefore`, same pagination as `/v1/blocks`). `shapeClass` is the frozen PREREG-001 class, evaluated with the same `internal/certclass` semantics the block detail endpoint serves, so the filter and the block page always agree; the coarse `blocks.cert_class` column (`dense`/`moe`/`none`/`unknown`, the wire taxonomy) plays no part. `matchedBlocks` is exact: canonical blocks with a decoded certificate at the current decoder version satisfying the filter (unit: blocks; the page is a subset of that population). Binding language, unchanged from PREREG-001 and the policy above: every class is a statement of shape consistency with the published mining stack and frozen model tables; no class or filter result shows that real inference occurred or that the declared matmul ran; `minerAddress` is a coinbase address, not an entity.

### pool-cert-profile {#pool-cert-profile}
Per-pool certificate-geometry profile (`/v1/pools/{name}/cert-profile`; the path segment is the URL-encoded `pool_labels.pool_name`, and an unknown name is a 404). The pool is a label NAME: several `pool_labels` addresses can carry one name and the profile aggregates all of them, the same matching [#pool-share](#pool-share) uses. Labels are addresses, not entities; one operator can span several labels. Everything is computed in one repeatable-read snapshot whose tip the response names.

Populations, each stated with its figures: `blocks.attributed` counts canonical blocks at heights 0..tip whose coinbase miner address carries the label (unit: blocks; share denominator `snapshot.totalBlocks`, all canonical blocks 0..tip). `blocks.decoded` is the subset with a `cert_public_params` row at the current decoder version: the population every census below reads. The two differ only mid-backfill, which sets `meta.partial`. The non-EMPTY population (decoded blocks minus the EMPTY class) is the denominator for the model-consistent, MoE and tile-signature shares, because the genesis empty certificate declares no computation.

- **shapeClassCounts**: blocks per frozen PREREG-001 class over decoded blocks, computed by the same `internal/certclass` classifier the block detail endpoint and [#cert-search](#cert-search) serve, so no two surfaces can disagree about a block's class. `modelConsistentShare` = OFFICIAL_CONSISTENT / non-EMPTY decoded blocks.
- **rankHistogram**: decoded blocks per declared noise rank; rank 0 is the genesis empty certificate, shown not hidden (the [#cert-census](#cert-census) convention). `boundaryHugging` = rank-128 blocks declaring exactly k = 2,048 (the legal minimum configuration after the v1.3.0 rank-penalty softfork, OBS-001) / the pool's rank-128 decoded blocks. Convergence to a constraint boundary describes a population optimizing its configuration against the rule; it is a neutral measurement, never a judgement (roadmap 14.3).
- **tileSignatureCounts**: non-EMPTY decoded blocks per (tileH, tileW, rank, officialBytes) cell, where officialBytes means both 6-byte swizzle patterns byte-match the official sm90 wgmma fragment (the classifier's T1 rows/cols byte tests, single source of truth; roadmap 14.4). Signatures identify mining SOFTWARE, never an operator and never honesty: mimicry in both directions is observed, so `officialBytesShare` (officialBytes blocks / non-EMPTY decoded blocks) is an upper bound on the unmodified stack.
- **moeShare**: blocks declaring experts (`moe_e > 0`) / non-EMPTY decoded blocks. A declared parameter, not evidence of expert computation.

Every share carries its exact numerator, denominator and basis; a share with an empty denominator is `null`, never 0. Binding language (PREREG-001 §0 and the policy above): every figure states consistency of declared certificate geometry with the published mining stack and frozen model tables, never proof that real inference occurred or that a declared matmul ran. Deliberately absent: the per-pool operational-hygiene block (empty-block rate, template staleness, propagation lag, orphan contribution) is gated on right of reply (roadmap 9.4 / 14.5); the response says it is out of scope rather than omitting it silently.

## Weight provenance (research)

These definitions gate the DS-002 weight-provenance results (PREREG-002, OBS-005). They are research metrics: published in dated notes and frozen datasets, not served by live API endpoints, so a published figure can never drift.

### weight-provenance-match {#weight-provenance-match}
Per (block, candidate buffer): a match iff `blake3(buffer_bytes, key = job_key)` equals `cert_public_params.hash_b`, byte-exact, no tolerance (PREREG-002 §4). `job_key = blake3(header[0:76] ‖ mining_config[0:52])`, both halves on-chain. The derivation is hard-checked per block (SHA256d header self-check plus the raw-certificate mining_config cross-check) and any failure aborts the run. A match attests that the committed operand equals a published tensor; it does not prove inference ran, was served, or was fresh. Any rate over matches states its denominator stratum (candidate blocks at the run's model/tp selection, a fixed-m stratum, or the varying-m population) and its unit of analysis (blocks, distinct coinbase addresses, or effective operators as 1/HHI). Source: the frozen dataset family, each carrying extract plus full pair results and never only the hits: DS-002 (the main scan), DS-002b (the Gemma and `o` tp4/tp8 coverage runs), DS-006 (the PREREG-003 coverage closure and layout-variant probes) and DS-007 (the era-stratified control redraw).

### matched-share-series {#matched-share-series}
Matched candidate blocks over scanned candidate blocks per height bin, with the bin width stated as a parameter: peaks are bin-width dependent (9.31% at 5,000-block bins vs 24.27% at 1,000 in DS-002). Never quoted against an all-blocks denominator: candidate eligibility falls from roughly 100% of blocks to about 4% over the chain's life, so matched/all-blocks measures the eligibility filter, not behaviour. Composition caveat: the candidate universe is several distinct populations (constant-m mass points plus a varying-m tail), and the aggregate series mostly tracks their mix; the stratified table is the primary presentation.

### tensor-coverage {#tensor-coverage}
Distinct (model, layer family, tp, shard, transformer layer index) tensors matched, matches per tensor, and per-family layer coverage (in DS-002: 293 distinct tensors, gate_up tp1 at 80 of 80 layer indices). Tests the tile-reuse caveat. One `hash_b` can match at most one distinct-bytes buffer, so per-block uniqueness is a data-integrity check, not statistical evidence; the evidence is the keyed match, the clean negative control, and the independent raw-bytes reproduction.

### attested-model-weight-mining {#attested-model-weight-mining}
The finding label, binding here and in PREREG-002: a byte-exact `hash_b` match is "attested model-weight mining", never "certified inference" or "proof of inference". It proves committed-operand identity for public static checkpoints only. Because `job_key` is derived per block, weight reuse is undetectable, and private models, fine-tunes, requantized variants, training runs and synthetic matrices are mutually indistinguishable on chain. Negative results are bounded by the exact search space of PREREG-002 §5 and PREREG-003 §2 (the coverage-closure cell enumeration and the control redraw) plus each run's recorded coverage (`snapshotTip`, `unscannedCandidates`, `unhashedBlocks` in `summary.json`) and never support a claim about useful work in general.

## Attestation feed

### metric-feed {#metric-feed}
The KMS-003 attestation feed (roadmap 13.1): `keshictl metric-feed --out DIR` emits `feed.json.gz`, one schema-stable envelope carrying the named series frozen at one corpus snapshot. Read-only; no HTTP endpoint serves it and nothing in the live API changes with it.

**Snapshot anchoring.** Every series is computed inside one REPEATABLE READ, READ ONLY transaction, and the envelope records that transaction's canonical tip (`snapshot.tipHeight`, `snapshot.tipHash`, display order). The run refuses unless canonical block count, decoded-params count and height span agree and the corpus starts at genesis (the DS-003 gate), so a stated denominator of "all canonical blocks at heights 0 through tipHeight" is never a silent undercount.

**Series** (each states its own denominator in a `basis` member):
- `rankDistribution`: blocks per decoded rank value, the [#cert-census](#cert-census) rank histogram over all canonical blocks at heights 0..tip (unit: blocks; rank 0 is the genesis empty certificate, shown not hidden).
- `attestationRatio`: Σdeclared and Σproven MACs plus the MAC-weighted ratio Σproven/Σdeclared per [#attestation-ratio](#attestation-ratio), over the rank > 0 subset (`countedBlocks`) of all canonical decoded blocks at heights 0..tip. NUMERIC decimal strings end to end; the ratio is `null` when Σdeclared is zero, never 0. The feed carries the exact NUMERIC quotient string; `/v1/metrics` casts the same quotient to float8 for its JSON number, so a verifier comparing the two must expect the API value to be a rounding of the feed value, not a disagreement (the summed operands are identical).
- `attribution`: attributed vs unattributed blocks over all canonical blocks at heights 0..tip (attributed = coinbase miner address carries a pool label, the [#pool-share](#pool-share) ladder; the remainder is shown, never redistributed). Shares are NUMERIC decimal strings over that block count.
- `difficulty`: the [#difficulty](#difficulty) value at the snapshot tip, read from the tip block's own sample (pinned by `tipHash`, height cross-checked), byte-equal to the `/v1/metrics/difficulty` point at that height (same table, same text cast).

**Canonical form.** The envelope is one compact JSON line plus a trailing newline, gzipped with the default header (zero ModTime, no name). Member order is fixed: `message`, `signingScheme`, `messageDigest`, `pubkey`, `signature`, `signingStatus`. The message is serialized with Go `encoding/json`: struct field order as declared in `cmd/keshictl/metricfeed_emit.go`, no insignificant whitespace, `encoding/json` string escaping (HTML escaping included). Two runs over one snapshot are byte-identical, whole gzipped file included.

**Digest preimage (exact).** `messageDigest` is the lowercase-hex sha256 over exactly the bytes of the `message` member's value as they appear in the emitted (decompressed) file: from its opening `{` to its closing `}` inclusive, nothing more. The emitter embeds the canonical bytes verbatim, so a verifier gunzips, slices the `message` value out of the envelope, and hashes it; no re-serialization is required or permitted.

**Signing seam (deferred, deliberately).** `signingScheme` declares BIP-340 (Schnorr over secp256k1); the object a signature will cover is the 32-byte `messageDigest`. Which key signs and where it is held is an operator decision that has not been taken, so `pubkey` and `signature` are `null` and `signingStatus` is `"unsigned: pending operator key"`. When the operator provisions a key, `pubkey` (32-byte x-only key, hex) and `signature` (64-byte BIP-340 signature, hex) are filled and `signingStatus` changes; the message and digest do not move. The repository generates no key and contains no signing code (`crypto/sha256` only). The publication calendar and the market-conduct rules (published cadence, position disclosure, no trading around releases) are policy, not code: the command emits, it does not announce.

## Emission milestones
25% at t = H/3 ≈ 216,742; 50% at 650,226; 75% at 3H ≈ 1,950,678; 90% at 9H ≈ 5,852,034 (from Emitted(t)=t/(t+H)). Projected dates use the **current windowed block interval**, clearly labeled as projections that shift with hashrate.
