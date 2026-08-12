# OBS-007: Rank-escalation economics (Open question 4)

Dated observation note. Recorded 2026-08-10. **Exploratory measurement, not
pre-registered**, on the same footing as OBS-001/003/006: no frozen
hypothesis preceded it, and the two candidate readings it decides between
were written down in the roadmap's Open questions before the data was in.
Sources: the consensus bound arithmetic in `pearl-src` @ v1.3.0 (cites
inline, re-read on the recording date), the frozen datasets
[DS-001](datasets/DS-001-classification-v1/) (classification, coverage to h96,405, snapshot tip 96,452)
and [DS-003](datasets/DS-003-network-state-v1/) (network state, tip 97,710),
and [OBS-001](OBS-001-rank-penalty-fork-transition.md)'s +1,000-block
post-fork census. Every dataset figure below was regenerated on the
recording date by running `scripts/rank-economics.py` against the committed
datasets; §3 states how each number was verified.

The question (Keshi's internal roadmap, Open
questions): the network escalated noise rank 128 to 256 to 1024 (the
protocol maximum) while the reference default was 32. The *economic* reading
held that the pre-fork difficulty normalization was imperfect, that a higher
rank unlocked a higher `k` (via `k <= 4r^2`) and therefore real advantage,
and that the v1.3.0 `128/rank` penalty was the correction. The *neutral*
reading held that difficulty was already work-normalized and the escalation
bought nothing.

Unit of analysis throughout: canonical blocks. "Reward-per-MAC" means
expected block reward per real int8 MAC spent on jackpot attempts, from the
bound arithmetic; it prices only the sampled arithmetic (the `h x w` opened
tile over the `dot_product_length` contraction depth). A proof attests that
sampled arithmetic, never the declared `m x n x k` job, so nothing in this
note assumes any declared work happened.

## 1. The finding

| | |
|---|---|
| Verdict on Open question 4 | **NEUTRAL; the economic reading is REFUTED** |
| Pre-fork accept bound, per jackpot attempt | `target * h * w * dot_product_length` (`zk-pow/src/api/sanity_checks.rs:190-192`, V1 form `v1/api/sanity_checks.rs:86-102`) |
| Real work per attempt | exactly `h * w * dot_product_length` int8 MACs (`zk-pow/src/circuit/chip/jackpot/helper.rs:21-33`, the full contraction loop) |
| Expected MACs per block | the factor cancels: `2^256 / target`, invariant to rank, `k`, `h`, `w` |
| Post-fork (h >= 96,251) | bound multiplier `128/rank` (`sanity_checks.rs:194-196`; height `node/chaincfg/params.go:353`); reward-per-MAC 1.0 at rank 128, 0.5 at 256, 0.125 at 1024 |
| Decisive constant | `4 * 128^2 = 65,536 = 2^16` = the global `k` cap (`sanity_checks.rs:33,35`), so no legal `k` requires rank > 128 |
| Over-ranked share | **21,368 of 21,368 (100%)**: every DS-001 block declaring rank > 128 carries a `k` that rank 128 (or lower) already admits (denominator: canonical blocks, heights 1–96,405, rank > 128; unit: blocks) |
| Where the escalation lives | the MoE / dense-only windows (71,935–96,250), entirely CUSTOM-class (§2) |

Pre-fork, difficulty was already work-normalized: the accept bound and the
per-attempt cost carry the same `h * w * dot_product_length` factor, so it
cancels and expected reward per real MAC was identical at every legal rank,
`k`, `h`, `w`. Escalating rank could not buy reward. The economic reading's
causal chain (higher rank required for higher `k`, higher `k` an advantage)
breaks at its first link: `4 * 128^2` equals the global `k` cap, so rank 128
already admits every legal `k`, and in the data 100% of the 21,368 rank>128
blocks declare a `k` needing no rank above 128 (largest `k` observed
anywhere in DS-001: 51,200, admitted by rank 128). Post-fork the `128/rank`
multiplier makes high rank strictly worse per MAC: a new disincentive, not
the removal of an advantage that never existed.

## 2. What the escalation was instead

- **Localization** (DS-003, whole 500-block bins; denominators are blocks
  per era): rank > 128 appears in 0 of 52,000 blocks below height 52,000;
  2,485 of 19,500 (12.7%) at 52,000–71,934; 14,749 of 19,500 (75.6%) in the
  MoE window 71,935–91,629; 3,271 of 4,000 (81.8%) in the dense-only window
  91,630–96,250; 33 of 1,211 (2.7%) after the rank penalty. Rank 1024
  specifically: 12 blocks before the MoE fork, 3,426 inside the window.
- **Software, not gaming.** The official kernel compiles only R64 and R128
  (`pearl-gemm-build-utils/.../default_compiled_kernels.py:16-56`,
  Keshi's internal protocol notes, The mining stack), so no rank>128
  block can come from the shipped kernel, and DS-001's classifier places the
  entire rank>128 population in the CUSTOM classes. The escalation curve is
  the custom-mining-software adoption curve.
- **High rank cost extra, uncredited.** Noise and denoise work scale as
  `2r/m + 2r/n + 2r/k` of the base MACs (source pass, `pearl-notes.md` §The
  mining stack), and none of it is credited by the bound. Escalators paid
  for rank; they did not earn from it.
- **Per-pool corroboration** (OBS-001 +1,000 census, n = 1,000 post-fork
  blocks at tip 97,530; unit: blocks per pool): a min-k-hugging cluster sits
  at the exact legal minimum (rank 128, k = 2,048), PearlFortune 34/35
  (97%), PearlHash 335/354 (95%), while Kryptex runs rank 128 at `k` well
  above it (49/445 = 11% at the minimum) and LuckyPool 11/44 (25%). Under a
  work-normalized bound both profiles earn the same per MAC, and they
  coexist at large share; a real max-k edge would have bled the min-k pools'
  share, and it did not. The same split appears in miniature in DS-001's 155
  post-fork blocks (script §4).

## 3. How each number was verified on the recording date

- **Bound, penalty, `k` constraints, work per attempt, fork height**: re-read
  today from the pinned `pearl-src` clone @ v1.3.0 at the cites in §1
  (`difficulty_adjustment_factor`, `penalized_adjustment_factor`, the
  `k <= 2^16` and `k <= 4r^2` ensures, the `compute_jackpot` contraction
  loop, `RankPenaltyForkHeight: 96251`). The cancellation and the
  `4 * 128^2 = 2^16` identity are arithmetic; the script recomputes and
  prints both.
- **21,368 and 100%**: `scripts/rank-economics.py` §2 over DS-001
  `blocks.jsonl.gz`, run today; per-era split 2,675 (pre-MoE) + 14,895 (MoE
  window) + 3,777 (dense-only) + 21 (post-penalty) = 21,368, each era 100%
  over-ranked.
- **Trajectory counts and shares**: script §3 over DS-003 `bins.json`, run
  today. Whole bins only, so era denominators (52,000 / 19,500 / 19,500 /
  4,000 / 1,211) exclude the fork-edge bins; DS-001's era counts differ
  slightly for that reason.
- **Per-pool minimum-hugging**: quoted from OBS-001's committed appendix
  (+1,000 re-run, recorded 2026-08-09, `fork-census-96151-97250.json`); the
  DS-001 miniature is script §4, run today.

## 4. Boundaries (marked open)

1. **Reward-per-MAC is not reward-per-GPU-second.** Rank changes the
   contraction chunking (`dot_product_length = k - (k mod r)`) and memory
   behavior; wall-clock per attempt on mining hardware is unmeasured. A
   wall-clock rank effect is not excluded, only unpriced by the bound. OPEN.
2. **Miner intent is unread.** This note measures configurations and their
   bound arithmetic; whether escalators believed rank bought an advantage is
   not knowable from chain data. The verdict refutes the advantage, not the
   belief.
3. The verdict prices real MACs executed on the sampled arithmetic. It says
   nothing about whether any declared job ran (binding scope in the header).
4. DS-001's post-fork tail is 155 blocks; the per-pool split rests on
   OBS-001's n = 1,000 census.
5. "Localizes to the MoE / dense-only windows" describes the bulk and the
   512/1024 escalation; ranks above 128 already appear in 12.7% of blocks
   (2,485 of 19,500) in the pre-MoE era.

## 5. Reproduction

```bash
python3 scripts/rank-economics.py   # reads the committed frozen datasets
# KESHI_DS001_DIR / KESHI_DS003_DIR override the dataset locations
```

Regenerates every dataset figure in this note via scripts/rank-economics.py
from the frozen DS-001/DS-003 (sections: reward-per-MAC table, k-gating,
trajectory, post-fork pool split). Exit 0 always; it is a measurement, not a
check.

## 6. Data

No new dataset. Reads DS-001-classification-v1 and DS-003-network-state-v1,
both frozen and committed; the per-pool corroboration quotes OBS-001's
committed appendix. The roadmap's Open questions entry carries this verdict
with the same date.
