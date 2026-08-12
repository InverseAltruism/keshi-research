# OBS-012: Declared certificate arithmetic across the salted noise-seed fork (plan item A4)

Dated observation note. Recorded 2026-08-12 against our own live index
(`http://localhost:8081`), index tip 99,083 at 2026-08-12T00:34:35+02:00 on the
run that produced the figures. **Status: observational measurement, not
pre-registered.** No frozen hypothesis governs it. Every figure below comes from
one pinned pull against the live index in this session (§9, marked LIVE), with
the ratios between two such figures computed in exact rational arithmetic over
the same pull and rounded where quoted. Nothing is carried over from an earlier
probe and nothing is derived by hand. Consensus-code facts were read in the same
session from the pinned repository copy at
`github.com/pearl-research-labs/pearl@v1.4.1` (marked SRC, cites inline).

The windows are pinned by height, so the tip moving does not move the figures.
The run was repeated at index tips 99,079, 99,081 and 99,083 and its output was
byte-identical outside the line that prints the tip.

Unit of analysis throughout: canonical blocks, one certificate per block. A
share of blocks is never a share of operators, of coinbase addresses or of
hashrate.

Naming rule for this note (binding): no party is named. Coinbase payout
addresses are counted as chain facts and never labelled, and an address is not
an entity: one operator can hold several, and a pool address can pay for many
machines.

The declared-arithmetic definition is the one the index serves
([`docs/metrics.md#declared-arithmetic`](../metrics.md#declared-arithmetic)):

```
declared MACs = m * n * (k - (k mod rank)),  k = common_dim
```

undefined at rank 0 (the genesis empty certificate), which does not occur in any
window here. The formula was cross-checked against the index's own
`/v1/metrics/declared-arithmetic` series, a rolling 200-point window: on the
heights that series shared with this pull at the run tip (198 of them), 0
mismatches (LIVE, §9). The number of shared heights moves with the tip because
the series is a rolling window; the zero-mismatch agreement does not.

## 1. The finding

| | |
|---|---|
| Fork under test | PCCR-0007 salted noise-seed hard fork, V3 certificates, mainnet height 99,000 (`node/chaincfg/params.go:371` @ v1.4.1, SRC; boundary confirmed on chain below, LIVE) |
| Post-fork material available | **80 blocks over 10.039 h**, heights 99,000–99,079. A full post-fork day does not exist yet |
| Primary comparison | block-count matched: 80 V2 blocks (98,920–98,999) against 80 V3 blocks (99,000–99,079), with two larger pre-fork windows as a base check |
| Median block's declared arithmetic | **unchanged**: median declared MACs 17,593,326,899,200 in the count-matched V2 window against 17,592,186,044,416 in the V3 window (0.0065% apart); against the 10 h and 24 h V2 windows the median moves by exactly one factor of two, 35,184,372,088,832 to 17,592,186,044,416 |
| Over-declaration tail | **truncated**: blocks declaring max(m, n) above 2^20 are 34 of 80, 267 of 631 and 347 of 994 in the three V2 windows, and **0 of 80** in the V3 window (95% CI [0.00%, 4.51%]) |
| Ceiling in the V2 tail | pre-fork declared dimensions run to the consensus cap: max declared m and n reach 16,777,216 = 2^24, the `sanity_checks.rs:48-49` limit (SRC), against max declared m = 131,072 and max declared n = 1,015,808 post-fork |
| Mean declared MACs | reported in §5 as a tail artifact, never as a headline. The mean-based reading of this fork is wrong |
| What the fork establishes | the declared m and n are self-consistent with the noise seed the block actually mined under, so they cannot be chosen after a solution is found (SRC, §2) |
| What it does not establish | that a real matrix multiplication ran, that a real model was evaluated, or that the declared m, n and k describe any computation that happened. Nothing binds `hash_a` to real activations, and the proof still opens at most `tile_size` output entries |

## 2. What the fork binds, and what it leaves alone (SRC, @ v1.4.1)

The noise seeds are derived from a job key and the two matrix commitment roots.
The job key is `blake3(block_header || mining_config)` (`proof_utils.rs:348-353`).
`MiningConfiguration` is the 52-byte structure holding `common_dim` (k), `rank`,
`mma_type`, the row and column patterns and the MoE trailer (`proof.rs:63-72`).
It does not hold m or n: those are separate wire fields that follow the roots
(`proof.rs:79`, `:99-100`). So before this fork, k and rank were already inside
the pre-image the search ran against, while m and n were inside nothing.

V3 changes one step. Each root is first bound to its own declared dimension,
then the unchanged seed chain runs (`seed.rs:20-25`, `:51-59`; called at
`proof_utils.rs:362-363`):

```
bound_a = blake3(hash_a || m_le32 || 0^28, key = blake3("pearl/cert-v3/noise-seed/A"))
bound_b = blake3(hash_b || n_le32 || 0^28, key = blake3("pearl/cert-v3/noise-seed/B"))
```

The upgrade guide shipped in the same release states the same mechanism and the
same two lines (`docs/salted-seed-fork-upgrade-guide.md:14-16`, `:83-95`, SRC).
The wire layout is unchanged and the salt is never serialized.

Three things the fork does not do, each verified in the same read:

1. It adds no magnitude cap. `m <= 2^24` and `n <= 2^24` are pre-existing:
   the two `ensure!` lines are byte-identical at v1.2.1 (`sanity_checks.rs:45-46`)
   and v1.4.1 (`:48-49`). The k cap `k <= 2^16` is likewise identical at v1.2.1
   (`:30`) and v1.4.1 (`:33`). A post-fork block may still declare m and n at the
   cap; it must simply have mined under the seed those values produce.
2. It does not put m or n into the acceptance threshold. The difficulty bound is
   computed from the mining configuration alone
   (`extract_difficulty_bound(nbits, &public_params.mining_config)`,
   `sanity_checks.rs:150`, signature at `:229`), so declared m and n move the
   declared arithmetic without moving the work needed to find a block. This was
   true before the fork and is true after it.
3. It does not bind either root to real activations or real weights. V3 is a
   self-consistency bind on the declared shape, not an honesty bind on the
   content. Pearl is model-blind by design and remains so.

The only claim in this note about the mechanism is therefore narrow: after
height 99,000, a block's declared m and n are the values the block's own search
was run against. Whether anything of that shape was computed is not addressed by
the fork and is not addressed here.

## 3. Boundary, denominators and windows

Boundary (LIVE, this session). The pull walks heights 98,006 to 99,079 block by
block and reads the certificate version our own parser decodes. Of the 994
blocks below 99,000, 994 carry version 2 and 0 carry version 3. Of the 80 blocks
at or above 99,000, 80 carry version 3 and 0 carry version 2. Block 98,999 is the
last V2, timestamped 2026-08-11T14:03:11+02:00 (12:03:11 UTC), and block 99,000
the first V3, timestamped 2026-08-11T14:03:43+02:00 (12:03:43 UTC). This agrees
with the boundary already recorded in
[`registry/PCCR.md`](../registry/PCCR.md) PCCR-0007.

Denominator composition, identical in all four windows: canonical blocks with a
decoded certificate at the current decoder version. Over the whole pulled range
of 1,074 heights there are 0 non-canonical rows, 0 rows without decoded
parameters, 0 rows at rank 0 and 0 MoE rows (`moe_e > 0`), so declared MACs is
defined for every block in every window and no block is dropped from any
denominator. Unit of analysis: blocks.

| window | heights | blocks | first and last timestamp | span | mean interval | cert versions | distinct coinbase addresses | difficulty across the window |
|---|---|---|---|---|---|---|---|---|
| W-V3 | 99,000–99,079 | 80 | 2026-08-11T14:03:43+02:00 .. 2026-08-12T00:06:03+02:00 | 36,140 s = 10.039 h | 457.5 s/block | {3: 80} | 6 | 26,088,382 → 25,255,423 |
| W-V2c | 98,920–98,999 | 80 | 2026-08-11T13:01:39+02:00 .. 2026-08-11T14:03:11+02:00 | 3,692 s = 1.026 h | 46.7 s/block | {2: 80} | 5 | 25,558,354 → 26,079,718 |
| W-V2t | 98,369–98,999 | 631 | 2026-08-11T04:02:51+02:00 .. 2026-08-11T14:03:11+02:00 | 36,020 s = 10.006 h | 57.2 s/block | {2: 631} | 13 | 22,458,838 → 26,079,718 |
| W-V2d | 98,006–98,999 | 994 | 2026-08-10T14:03:59+02:00 .. 2026-08-11T14:03:11+02:00 | 86,352 s = 23.987 h | 87.0 s/block | {2: 994} | 18 | 21,644,878 → 26,079,718 |

W-V3 is every V3 block in the index at the pinned tip. W-V2c matches it on block
count. W-V2t matches it on wall clock: the pre-fork blocks whose timestamps fall
inside a span of the same 36,140 s, cut at 2026-08-11T04:01:23+02:00. W-V2d is
the 24 h of V2 blocks ending at the fork, cut at 2026-08-10T14:03:43+02:00.

The plan item asked for a day on each side. A day of V3 does not exist: the fork
was 10.039 h old at this tip. Block count and wall clock cannot both be matched,
because the pre-fork chain was producing blocks far faster (46.7 to 87.0 s per
block against 457.5 s per block in W-V3), so both matchings are reported and the
count-matched pair is the primary one. W-V2c covers only 1.026 h of wall clock
and 5 coinbase addresses, which is a thin base for a tail statistic; W-V2t and
W-V2d exist so that the pre-fork tail level can be seen to be stable across
windows of 80, 631 and 994 blocks rather than a property of the last hour.

## 4. The pre-fork population is a body plus a tail

The V2 declared-dimension population is not one population, and no single
average describes it. Blocks with max(m, n) above each power of two, as counts
over the stated denominator (unit: blocks):

| threshold on max(declared m, declared n) | W-V3 (n=80) | W-V2c (n=80) | W-V2t (n=631) | W-V2d (n=994) |
|---|---|---|---|---|
| > 2^17 = 131,072 | 12 (15.0%) | 56 (70.0%) | 432 (68.5%) | 617 (62.1%) |
| > 2^18 = 262,144 | 12 (15.0%) | 52 (65.0%) | 387 (61.3%) | 551 (55.4%) |
| > 2^19 = 524,288 | 2 (2.5%) | 44 (55.0%) | 320 (50.7%) | 422 (42.5%) |
| > 2^20 = 1,048,576 | 0 (0.0%) | 34 (42.5%) | 267 (42.3%) | 347 (34.9%) |
| > 2^21 = 2,097,152 | 0 (0.0%) | 23 (28.8%) | 210 (33.3%) | 270 (27.2%) |
| > 2^22 = 4,194,304 | 0 (0.0%) | 17 (21.2%) | 139 (22.0%) | 179 (18.0%) |
| > 2^23 = 8,388,608 | 0 (0.0%) | 10 (12.5%) | 60 (9.5%) | 83 (8.4%) |
| > 2^24 = 16,777,216 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |

The last row is the consensus cap (§2). No block anywhere in the pull declares
above it, and the pre-fork tail reaches it exactly: max declared m and max
declared n are both 16,777,216 = 2^24 in W-V2t and W-V2d. In W-V3 the maxima are
131,072 for m and 1,015,808 for n, against a cap that did not move.

The same shape appears in the declared MACs, again as counts over blocks:

| threshold on declared MACs | W-V3 (n=80) | W-V2c (n=80) | W-V2t (n=631) | W-V2d (n=994) |
|---|---|---|---|---|
| > 2^46 = 70,368,744,177,664 | 8 (10.0%) | 34 (42.5%) | 252 (39.9%) | 368 (37.0%) |
| > 2^48 = 281,474,976,710,656 | 0 (0.0%) | 27 (33.8%) | 180 (28.5%) | 258 (26.0%) |
| > 2^50 = 1,125,899,906,842,624 | 0 (0.0%) | 15 (18.8%) | 125 (19.8%) | 186 (18.7%) |
| > 2^54 = 18,014,398,509,481,984 | 0 (0.0%) | 4 (5.0%) | 54 (8.6%) | 79 (7.9%) |
| > 2^58 = 288,230,376,151,711,744 | 0 (0.0%) | 3 (3.8%) | 11 (1.7%) | 15 (1.5%) |
| > 2^62 = 4,611,686,018,427,387,904 | 0 (0.0%) | 0 (0.0%) | 1 (0.2%) | 1 (0.1%) |

The single largest V2 declaration in the pulled range is block 98,463:
m = 16,777,089, n = 8,388,593, k = 65,536, rank = 128, giving
9,223,285,725,316,841,472 declared MACs in one block. The largest V3 declaration
in W-V3 is block 99,017: m = 131,072, n = 131,072, k = 16,384, rank = 128,
giving 281,474,976,710,656.

## 5. What moved and what did not

Order statistics (nearest rank, no interpolation, so every quantile printed is a
value some block actually declared). Unit: blocks; denominators in the header.

| statistic | W-V3 (n=80) | W-V2c (n=80) | W-V2t (n=631) | W-V2d (n=994) |
|---|---|---|---|---|
| declared m, p25 / p50 / p75 | 8,192 / 16,384 / 131,072 | 2,049 / 131,072 / 524,289 | 4,096 / 32,769 / 524,289 | 4,096 / 32,769 / 262,145 |
| declared m, p99 / max | 131,072 / 131,072 | 16,777,089 / 16,777,089 | 8,388,609 / 16,777,216 | 16,777,089 / 16,777,216 |
| declared n, p25 / p50 / p75 | 131,072 / 131,072 / 131,072 | 8,193 / 131,072 / 524,289 | 16,385 / 131,072 / 1,048,576 | 32,768 / 131,072 / 524,289 |
| declared n, p99 / max | 1,015,808 / 1,015,808 | 8,388,609 / 8,388,609 | 8,388,609 / 16,777,216 | 8,388,609 / 16,777,216 |
| declared k, p25 / p50 / p75 | 2,048 / 8,192 / 8,192 | 4,096 / 4,096 / 4,096 | 4,096 / 4,096 / 4,096 | 4,096 / 4,096 / 4,096 |
| declared MACs, p25 | 8,796,093,022,208 | 2,199,224,586,240 | 2,199,224,586,240 | 4,329,327,034,368 |
| declared MACs, p50 | 17,592,186,044,416 | 17,593,326,899,200 | 35,184,372,088,832 | 35,184,372,088,832 |
| declared MACs, p75 | 68,169,720,922,112 | 562,954,785,263,616 | 281,509,370,007,552 | 281,479,540,117,504 |
| declared MACs, p99 | 281,474,976,710,656 | 4,611,643,137,535,836,160 | 1,152,911,677,735,895,040 | 1,152,911,196,697,722,880 |
| declared MACs, max | 281,474,976,710,656 | 4,611,643,137,535,836,160 | 9,223,285,725,316,841,472 | 9,223,285,725,316,841,472 |

The median block is where it was. Against W-V2c the median declared MACs ratio
is 1.000065 (17,593,326,899,200 to 17,592,186,044,416, a difference of 0.0065%);
against W-V2t and W-V2d it is exactly 2, one power of two. Inside that median,
two moves offset: the median m*n falls by a factor of 2.000130
(4,295,245,825 to 2,147,483,648 against W-V2c and W-V2d) and 2.000490
(4,296,019,969 to 2,147,483,648 against W-V2t), while the median k_eff doubles,
4,096 to 8,192, against all three V2 windows. k was already inside the seed
pre-image before the fork (§2), so the k side of that trade is a configuration
change and not a change in what could be forged (inferred from the mechanism,
not measured).

The upper quartile and above is where the fork shows, and the lower quartile
moves the other way. p75 of declared MACs is 8.2581 times higher in W-V2c and
4.1295 and 4.1291 times higher in W-V2t and W-V2d than the 68,169,720,922,112 of
W-V3; p99 is 16,383.8477 times higher in W-V2c and 4,095.9651 and 4,095.9634
times higher in W-V2t and W-V2d than the 281,474,976,710,656 of W-V3. p25 is lower
before the fork than after it: 2,199,224,586,240 in W-V2c and W-V2t and
4,329,327,034,368 in W-V2d, against 8,796,093,022,208 in W-V3. The distribution
did not shift bodily; its right tail was removed.

The mean is the number to distrust here, and it is stated once so it can be
dismissed with its arithmetic in view. Mean declared MACs per block, as the
window's summed declared MACs over its block count, integer part:
76,187,989,178,504,704 in W-V2c (sum 6,095,039,134,280,376,320 over 80 blocks),
49,186,054,793,382,605 in W-V2t (sum 31,036,400,574,624,423,936 over 631),
38,344,162,126,569,385 in W-V2d (sum 38,114,097,153,809,969,152 over 994),
against 41,376,050,629,836 in W-V3 (sum 3,310,084,050,386,944 over 80). Those
are ratios of 1,841.35x, 1,188.76x and 926.72x. All three are driven by the
handful of blocks in the last two rows of the second table in §4, they disagree
with each other by nearly a factor of two (1,841.35x against 926.72x) depending
only on which pre-fork window is chosen, and they describe no block. An earlier
probe in
this session, over a window of a few dozen blocks, reported a large collapse; it
was reading this artifact. The declared arithmetic of the typical block did not
collapse; the tail was cut off.

The same trap sits in the attestation ratio. The per-block median ratio
`tile_size / (m*n)` is unchanged at 5.96e-08 in all four windows (5.960e-08 in
W-V3, 5.959e-08 in W-V2c and W-V2t, 5.960e-08 in W-V2d), while the MAC-weighted
aggregate `sum(proven) / sum(declared)` moves from 2.409e-11 (W-V2c), 4.743e-11
(W-V2t) and 7.081e-11 (W-V2d) to 3.215e-08 (W-V3), a factor of 1,335.0, 678.0
and 454.1 respectively. The aggregate moved because its denominator lost the
tail, not because any block is better attested. Quoting the MAC-weighted figure
across this fork without the per-block median attached would repeat the same
error in the flagship metric.

## 6. The tail counted three ways

Three tail definitions, each stated as a count over its denominator, with an
exact Clopper-Pearson 95% interval. The interval treats blocks as independent
draws, which they are not: a run of blocks from one coinbase address is one
configuration choice observed several times, so the true uncertainty on the
pre-fork shares is wider than printed. The interval is included for the zero
counts, where it is the honest way to say that 0 of 80 is not 0 of a day.

| definition | W-V3 | W-V2c | W-V2t | W-V2d |
|---|---|---|---|---|
| TAIL-D, max(m, n) > 2^20 | 0 of 80 = 0.0%, CI [0.00%, 4.51%] | 34 of 80 = 42.5%, CI [31.51%, 54.06%] | 267 of 631 = 42.3%, CI [38.42%, 46.28%] | 347 of 994 = 34.9%, CI [31.94%, 37.96%] |
| TAIL-M, declared MACs > 2^50 | 0 of 80 = 0.0%, CI [0.00%, 4.51%] | 15 of 80 = 18.8%, CI [10.89%, 29.03%] | 125 of 631 = 19.8%, CI [16.77%, 23.14%] | 186 of 994 = 18.7%, CI [16.33%, 21.28%] |
| TAIL-T, m mod tile_h or n mod tile_w nonzero | 0 of 80 = 0.0%, CI [0.00%, 4.51%] | 72 of 80 = 90.0%, CI [81.24%, 95.58%] | 476 of 631 = 75.4%, CI [71.88%, 78.75%] | 564 of 994 = 56.7%, CI [53.59%, 59.85%] |
| TAIL-U, in at least one of the three | 0 of 80 = 0.0%, CI [0.00%, 4.51%] | 72 of 80 = 90.0%, CI [81.24%, 95.58%] | 497 of 631 = 78.8%, CI [75.36%, 81.89%] | 616 of 994 = 62.0%, CI [58.87%, 65.00%] |

TAIL-D and TAIL-M are magnitude thresholds; the exceedance tables in §4 let a
reader pick a different one. TAIL-T is a geometric marker, not a rule violation:
consensus requires only `m <= 2^24`, `n <= 2^24`, `t_rows + pattern_max < m` and
`t_cols + pattern_max < n` (`sanity_checks.rs:48-49`, `:57-58`, SRC), and never
requires m or n to be a multiple of the declared tile dimensions. Pre-fork, 72
of 80 blocks in W-V2c, 476 of 631 in W-V2t and 564 of 994 in W-V2d declared a
matrix whose row or column count is not a whole number of declared tiles, and in
68, 435 and 488 of those blocks respectively the offending dimension is exactly
one above a power of two. Post-fork that count is 0 of 80.

Complement, stated because the tail is only part of the population: the number
of blocks in none of the three tails is 8 of 80 in W-V2c, 134 of 631 in W-V2t,
378 of 994 in W-V2d, and 80 of 80 in W-V3.

The V3 declared shapes are not new. Of the 20 distinct declared
(m, n, k, rank) combinations in W-V3, 16 already appear in W-V2d, and 76 of the
80 W-V3 blocks carry a shape that some block in the 24 h before the fork also
declared. The post-fork window is the pre-fork body without the pre-fork tail,
not a different configuration space.

## 7. Composition: the tail did not simply leave

The obvious confound is that the miners who declared the tail stopped producing
blocks at the fork, in which case the tail's absence would say nothing about the
rule. Measured against it, on coinbase payout addresses (addresses, not
entities, and never labelled here):

- W-V2c: 5 distinct addresses, 4 of which also mined in W-V3. The 34 TAIL-D
  blocks come from 4 addresses; 32 of those 34 come from the 3 addresses that
  also mined in W-V3. Those 3 addresses mined 55 of the 80 W-V3 blocks, of which
  0 are TAIL-D.
- W-V2t: 13 distinct addresses, 4 of which also mined in W-V3. The 267 TAIL-D
  blocks come from 8 addresses; 250 of those 267 come from the 3 addresses that
  also mined in W-V3, which mined 55 of the 80 W-V3 blocks, of which 0 are
  TAIL-D.
- W-V2d: 18 distinct addresses, 4 of which also mined in W-V3. The 347 TAIL-D
  blocks come from 9 addresses; 328 of those 347 come from the 3 addresses that
  also mined in W-V3, which mined 55 of the 80 W-V3 blocks, of which 0 are
  TAIL-D.

So the majority of post-fork blocks were mined by addresses that were declaring
the tail hours earlier, and none of those post-fork blocks is in the tail. That
rules out the pure exit explanation for the addresses concerned (verified as a
count of blocks per address). It does not establish the mechanism: address
turnover is real (18 distinct addresses in W-V2d against 6 in W-V3), an address
is not an operator, and a behavioural change and a rule change land at the same
height and cannot be separated by this design (inferred).

## 8. Limits

1. The post-fork window is 80 blocks and 10.039 h, not a day. Every V3 figure
   rests on that denominator. The zero tail counts carry a 95% upper bound of
   4.51% per block, so a pre-fork-sized tail is excluded by this data but a
   small one is not. This note should be re-run once a full post-fork day and
   then a week exist; the script in §9 is pinned only by the two height
   constants.
2. Block production slowed sharply across the fork: 457.5 s per block in W-V3
   against 46.7, 57.2 and 87.0 s per block in the three V2 windows, while
   difficulty moved from 26,088,382 at height 99,000 to 25,255,423 at 99,079,
   a fall of 3.19%. A large hashrate loss that the difficulty control has not
   yet absorbed is the natural reading (inferred, not measured here; the
   retargeting behaviour and the hashrate series are a separate measurement).
   The population that mines V3 blocks is therefore not the population that
   mined V2 blocks, and §7 bounds but does not eliminate that confound.
3. Comparing V2 and V3 windows cannot separate the rule from everything else
   that changed at height 99,000, including the software upgrade the fork forced
   on every miner. This is an interrupted time series with one interruption and
   no control chain. Testnet and testnet2 activated the same fork at their own
   heights (SRC, PCCR-0007) and would make a control worth building.
4. Everything measured here is a declared parameter. A certificate's m, n and k
   are numbers a miner put on the wire. The proof covers at most `tile_size`
   opened output entries, so no figure in this note shows that a matrix
   multiplication of any declared size was performed, and none of it is evidence
   about inference, models or weights.
5. TAIL-D, TAIL-M and TAIL-T are thresholds this note chose after seeing the
   data, not pre-registered ones. The exceedance tables in §4 give a ladder of
   thresholds so the choice can be checked, and the three definitions disagree
   with each other about which pre-fork blocks are in the tail (34, 15 and 72
   blocks respectively in W-V2c) while agreeing exactly on the V3 window.
6. Shares here are shares of blocks. They are not shares of operators, of
   addresses or of hashrate, and a single address producing many blocks moves
   them.
7. Nothing in the note is an accusation. Choosing declared parameters that
   consensus permits and that no rule checked is a configuration choice, and it
   is described here as a measurement of what the certificates say.

## 9. Reproduction

The figures come from one pinned pull of heights 98,006 to 99,079 against the
live index, driven by a 239-line pull-and-count script that reads `/v1/status`
and then `/v1/blocks/{height}` for each height, and prints the window table, the
order statistics, the tail counts with their intervals, the exceedance ladders,
the composition counts, the exact ratios in rational arithmetic and the
cross-check. The script is not committed: it holds no state, the commands below
regenerate it, and a one-off puller in the tree would be a second thing to keep
in sync with the endpoints.

Boundary and tip:

```bash
curl -s localhost:8081/v1/status
for h in 98999 99000; do
  curl -s localhost:8081/v1/blocks/$h | python3 -c \
    'import sys,json; b=json.load(sys.stdin)["block"]; \
     print(b["height"], b["time"], b["certificate"]["version"])'
done
```

Windows, distributions and tails (self-contained, no local state):

```bash
python3 - <<'PY'
import json, math, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor
API="http://localhost:8081"; FORK=99000; LO,HI=98006,99079
g=lambda p: json.load(urllib.request.urlopen(API+p, timeout=30))
def one(h):
    b=g(f"/v1/blocks/{h}")["block"]; p=b["certificate"]["params"]
    return {"h":h,"t":b["time"],"v":b["certificate"]["version"],"m":p["m"],"n":p["n"],
            "k":p["k"],"r":p["rank"],"th":p["tileH"],"tw":p["tileW"],"a":b["minerAddress"]}
with ThreadPoolExecutor(max_workers=8) as ex:
    rows=sorted(ex.map(one, range(LO,HI+1)), key=lambda r:r["h"])
by={r["h"]:r for r in rows}; T=lambda h: dt.datetime.fromisoformat(by[h]["t"])
mac=lambda r: r["m"]*r["n"]*(r["k"]-(r["k"]%r["r"]))
Q=lambda v,p: sorted(v)[max(0,math.ceil(p/100*len(v))-1)]
post=[r for r in rows if r["h"]>=FORK]; N=len(post)
span=(T(HI)-T(FORK)).total_seconds()
W=[("W-V3",post),
   ("W-V2c",[r for r in rows if FORK-N<=r["h"]<FORK]),
   ("W-V2t",[r for r in rows if r["h"]<FORK and T(r["h"])>=T(FORK)-dt.timedelta(seconds=span)]),
   ("W-V2d",[r for r in rows if r["h"]<FORK and T(r["h"])>=T(FORK)-dt.timedelta(hours=24)])]
print("V3 below fork:",sum(1 for r in rows if r["h"]<FORK and r["v"]==3),
      "| V2 at/above:",sum(1 for r in rows if r["h"]>=FORK and r["v"]==2))
for nm,S in W:
    d=[mac(r) for r in S]
    print(f"{nm} n={len(S)} h={min(r['h'] for r in S)}..{max(r['h'] for r in S)} "
          f"median={Q(d,50):,} mean={sum(d)//len(d):,} "
          f"maxm={max(r['m'] for r in S):,} maxn={max(r['n'] for r in S):,} "
          f"TAIL-D={sum(1 for r in S if max(r['m'],r['n'])>2**20)} "
          f"TAIL-M={sum(1 for r in S if mac(r)>2**50)} "
          f"TAIL-T={sum(1 for r in S if r['m']%r['th'] or r['n']%r['tw'])}")
PY
```

That block runs in 0.70 s against a warm index and reproduces the window
heights, block counts, medians, means, maxima and the three tail counts in §5
and §6 exactly. The intervals in §6 are standard exact Clopper-Pearson at 95%
and follow from the counts and denominators printed in the same table; the
implementation used here self-tests on every run against the textbook values
cp(0, 10) = [0, 0.3085] and cp(3, 10) = [0.0667, 0.6525].

Cross-check of the declared-MAC formula against the index's own series
(`/v1/metrics/declared-arithmetic?window=200`, a rolling window): 198 heights in
common with the pull at the run tip, 0 mismatches (LIVE). The shared-height
count moves with the tip; the zero-mismatch result does not.

## 10. Data

No frozen dataset is warranted at this size. The material is 1,074 blocks read
from endpoints that serve them by height, the windows are pinned by two height
constants, and the note's own commands regenerate every figure in under a
minute. A frozen dataset becomes worth cutting when the post-fork side reaches a
week, when the comparison is worth publishing outside these notes, or when the
same measurement is wanted on testnet as a control (limit 3), and at that point
it should be a DS directory with the same append-only discipline as DS-005 and a
manifest of sha256 hashes, not an edit to this note. Corrections to anything
here ship as a new numbered note, never as a change to this one.
