# OBS-001: The rank-penalty softfork transition (height 96,251)

Dated observation note. Recorded 2026-08-06, ~5.5 hours after activation.
Method and caveats below; raw per-block JSON alongside the numbers.

**Status: preliminary** (94 post-fork blocks). Re-run at +1,000 and +5,000
blocks before publishing anything externally.

## What was measured

Certificate public data for heights **96,151–96,344** (194 blocks: 100 pre-fork,
94 post-fork; 96,345 excluded for a fetch race at the then-tip), parsed from raw
blocks served by our own Blockbook (`/api/v2/rawblock/`), layout per
Keshi's internal protocol notes (Certificate internals). Pool attribution
via coinbase payout address against the known wallets in
Keshi's internal protocol notes (Known pools); the unattributed remainder is
shown, never redistributed. Reproduce with `scripts/fork-census.py <lo> <hi> <out.json>`.

Consensus rule under test (v1.3.0, activation 96,251): reject `rank < 128`;
difficulty bound multiplier `128/rank` (neutral at 128, 8× tighter at 1024).

## Findings

**1. The network snapped to the penalty-neutral point within the first blocks.**

| rank | pre (n=100) | post (n=94) |
|---|---|---|
| 64 | 4 | - |
| 128 | 9 | **79 (84%)** |
| 256 | 14 | 4 |
| 512 | 24 | 7 |
| 1024 | **49 (49%)** | 4 |

`k` collapsed with it: pre-fork mode 32,768; post-fork **k = 2,048 in 59/94**,
which is exactly `16·rank`, the *minimum* legal `k` for rank 128. Miners moved to
the cheapest-valid configuration, not merely a valid one.

**2. Zero invalid-under-new-rules blocks on the canonical chain.** No post-fork
certificate shows `rank < 128`. The transition was clean chain-side. (Whether any
miner *produced* such a block and had it rejected is unrecorded: the v1.2.1
fork-observer was declined; see ROADMAP §P0b.)

**3. Pool block share shifted sharply across the boundary** (windows of ~5.4 h
pre / ~5.2 h post; small n, so treat as indicative):

| pool | pre share | post share | post-fork ranks |
|---|---|---|---|
| Kryptex | 57/100 | 26/94 (28%) | 128×17, **512×4, 1024×4, 256×1** |
| PearlHash | 20/100 | 44/94 (47%) | 128×43, 512×1 |
| PearlFortune | 9/100 | 8/94 | 128×7, 512×1 |
| LuckyPool | 3/100 | 6/94 | 128×2, 256×3, 512×1 |
| HeroMiners | 3/100 | 3/94 | 128×3 |
| unattributed | 8/100 | 7/94 | 128×7 |

Kryptex mined **rank 1024 in 43 of its 57 pre-fork blocks** and was still
submitting 4–8×-penalized ranks (512/1024) in ~35% of its post-fork blocks,
consistent with slow fleet reconfiguration, and consistent with (but not proof
of) the share collapse being self-inflicted by the penalty. PearlHash, already
mostly at low rank pre-fork, absorbed the share. This is the per-pool migration
latency Phase 9.2 predicted would be measurable.

**4. Corpus-hygiene invariants held on all 194 blocks:** reserved 28-byte
trailer all-zero everywhere (no covert channel), `mma_type = 0`, zero MoE
certificates (`e = 0` throughout, consistent with the MoE-was-never-used
hypothesis), `cert_version = 2` throughout.

> **Errata 2026-08-06 (OBS-003):** the "consistent with MoE-was-never-used"
> inference above was unsound: this note's window is entirely after the
> dense-only fork, where zero MoE is consensus-required and supports no usage
> inference. The full-corpus census found **1,929 MoE certificates** inside
> the 71,935–91,630 window: the capability WAS used in production.

**5. Shape-provenance signals (feeds Phase 8, not conclusions):**

- A tile pattern `h·w = 144` appears (2 pre, 2 post), a **third** kernel
  variant, outside both the official fragment (128) and the 256 seen in the
  fixture blocks. The n=3 fixture sample undercounted kernel diversity.
- `m`/`n` values are dominated by exact powers of two and, notably, **2^t + 1**
  values (513, 1025, 4097, 8193, 32769, 65537, 131073, …, 8388609 = 2^23+1).
  Live-batch token counts do not look like this. No `(n, k)` pair in either
  window matches any published `pearl-ai` model layer.
- Blocks passing the loose official-stack screen (rank ∈ {64,128} ∧ h·w = 128 ∧
  m ≥ 1024): 3/100 pre-fork → 17/94 post-fork. Caveat: post-fork rank 128 is
  *forced*, so this screen weakens after the fork by construction; the exact
  `[0,8]`/stride-8 fragment check (T1 proper) is what matters and needs the
  full-pattern comparison, not just the span.

## Caveats

- 94 post-fork blocks ≈ 5 hours. Shares at this n have wide variance; the rank
  crosstab is hard data, the share-shift interpretation is not settled.
- Attribution is single-known-wallet per pool; proxy-payout arrangements would
  misattribute.
- Chain-side only: no orphan, reject, or peer-version data was captured for the
  transition window (the live watch did not run; observer declined).
- Parsed via the prototype decoder path, not yet the dual-decoder discipline
  Phase 6 requires. Treat as provisional until the Go decoder + golden vectors
  reproduce it.

## Data

- `fork-census-96151-96345.json` (per-block parsed certificates + attribution),
  produced 2026-08-06 from the local Blockbook; script `scripts/fork-census.py`.

---

## Re-run at +1,000 blocks (2026-08-09)

Pre-committed follow-up per PLAN-001 Step 6, executed at tip 97,530 (the
+1,000 point h97,251 was reached earlier than the plan's ≈08-11 estimate;
measured post-fork block interval 3.80 min over 96,251→97,530). Same script,
window **96,151–97,250** (100 pre-fork + 1,000 post-fork); data:
`fork-census-96151-97250.json`. Reproducibility check: the re-parsed
pre-fork window is identical to the original tables above (rank distribution
and pool shares match exactly).

**1. Convergence deepened; violations stayed at zero.** Post-fork rank
distribution (n = 1,000): **128 → 949 (94.9%)**, 256 → 21, 512 → 12,
1024 → 18, vs 84% at the +94 preliminary. `rank < 128` (invalid): **0**.
Penalized ranks (>128) total 51/1,000 (5.1%), concentrated early (first
96,263, median 96,454) but not extinct; the last is at 97,249. Kryptex:
23 penalized of its 445 blocks, all but **one** before h96,851 (the
exception: h97,218), refining the 2026-08-08 audit's "fully compliant by
96,851" to "compliant with one later exception in this window".

**2. First per-pool boundary-hugging measurement (Phase 14.3).** Share of
post-fork blocks at the *exact legal minimum* configuration
(rank = 128 ∧ k = 2,048 = 16·rank): **471/1,000 (47.1%)** overall:

| pool | at legal minimum | share |
|---|---|---|
| PearlFortune | 34/35 | 97% |
| PearlHash | 335/354 | 95% |
| HeroMiners | 31/64 | 48% |
| LuckyPool | 11/44 | 25% |
| unattributed | 11/58 | 19% |
| Kryptex | 49/445 | **11%** |

Two distinct legal optimization profiles coexist: PearlHash/PearlFortune sit
at the k-minimum; Kryptex mines rank 128 with k up to the legal *maximum*
for that rank (k ≤ 4r² = 65,536; its post-fork k mode is 4,096–8,192).
Measured fact only; which profile is economically favored feeds the
roadmap's open rank-economics question, and no mechanism is asserted here.

**3. Pool shares over the 1,000-block window** (~2.6 days): Kryptex 445
(44.5%, recovered from 28% in the +94 window), PearlHash 354 (35.4%),
HeroMiners 64, LuckyPool 44, PearlFortune 35, unattributed 58 blocks across
**33 distinct addresses** (5.8%).

**4. Shape and software fingerprints.**

- Tile fragments post-fork: (16,16) 653 · (8,16) 241 · **(2,64) 79** (the
  official wgmma fragment, 7.9%) · (8,32) 14 · (6,24) 11 · (12,12) 1 ·
  (32,8) 1. The "h·w = 144" variant first seen in the preliminary resolves
  into **two distinct patterns**: (6,24) and (12,12), so the window holds
  at least seven fragment geometries ≈ a lower bound on distinct mining
  software (feeds Phase 14.4; tile patterns identify software, not honesty).
- The 70B fused gate/up shape (m 32,768 · n 57,344 · k 8,192) persists at
  **37/1,000**, of which 31 carry the official (2,64) fragment, and **all
  37 are unattributed** (30 distinct addresses; zero from labeled pools).
  The official-pattern fleet survives at a few percent, entirely in the
  diffuse unattributed stratum.
- Synthetic dimension signatures persist: post-fork `m` is 70.4% exact
  powers of two and 23.8% `2^t + 1` (94.2% combined); `n` is 45.0% + 24.4%.
  New dominant synthetic shape: **n = 516,096 (m 4,096, k 2,048), 130/1,000
  blocks**: 124 from PearlHash, 6 from one unattributed address.
- Hygiene invariants held on all 1,100 blocks: reserved trailer all-zero,
  `moe_e = 0` throughout (consensus-required post-91,630; usage inference
  lives in [OBS-006](OBS-006-moe-retraction.md), not here), zero post-fork
  `rank < 128`.

Numbers in this section were computed 2026-08-09 from
`fork-census-96151-97250.json`; the official-fingerprint screen retains the
preliminary's caveat (rank 128 is consensus-forced post-fork, so the loose
screen weakens by construction; the exact-fragment comparison is the
meaningful one). Next re-run: +5,000 (h101,251), ETA ≈ **2026-08-19** at the
measured 3.80 min interval.
