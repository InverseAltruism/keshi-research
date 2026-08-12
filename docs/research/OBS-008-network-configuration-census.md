# OBS-008: Network-configuration and mining-software census

Dated observation note, internal research record. Recorded 2026-08-10.
**Status: exploratory, not pre-registered.** Covers roadmap Phases 14.3
(configuration at the legal boundary) and 14.4 (mining-software census by
tile-pattern fingerprint); the committed verdict paragraphs live in
Keshi's internal roadmap (§14.3/§14.4), dated 2026-08-10. Everything regenerates via
`scripts/pool-config-census.py` from frozen DS-001 (live section
NON-FROZEN).

Sources: frozen [DS-001](datasets/DS-001-classification-v1/MANIFEST.md)
(96,406 blocks, heights 0..96,405, snapshot tip 96,452; the genesis EMPTY
certificate is excluded from every denominator, leaving 96,405 blocks;
span and counts re-verified against the manifest on the recording date);
the committed DS-002/DS-002b scan datasets for the weight-matched
cross-reference; the live keshi API for the tip window, queried by the
census run on 2026-08-10. Unit of analysis throughout: blocks, one
certificate per block. Numbers are the census run's committed outputs
(verified by that run); nothing in this note is re-derived here.

Framing, binding for every number below: everything measured is legal
on-chain behavior. Sitting at a constraint boundary (minimum rank, minimum
or maximum k) is an operator configuration choice and is reported as
stated, never as a violation. Tile patterns identify mining software,
never honesty (§3).

## 1. Boundary-hugging (14.3): three legal profiles, not two

Rule under measurement: the v1.3.0 rank-penalty softfork (mainnet
activation h96,251) made rank 128 the legal minimum, with legal k at that
rank from 2,048 (16·rank) to 65,536 (4·rank²). "At the minimum" below
means exactly (rank 128, k 2,048), the cheapest legal configuration.

Three legal optimization profiles coexist post-fork:

| profile | pool | measurement |
|---|---|---|
| minimum-k huggers | PearlHash, Pearl Fortune | 94% and 97% of the pool's own blocks at exactly (128, 2,048) |
| intermediate k band | Kryptex | rank 128 with k mode 4,096; ~86% of its blocks above the minimum; almost never at the maximum |
| maximum-k | LuckyPool | at the legal maximum k = 65,536 in ~31% of its blocks |

Denominators: each per-pool share is of that pool's own blocks in the live
post-fork window (h96,251 up to the chain tip at the 2026-08-10 census
run; coinbase-tag attribution, unattributed is its own row and is never
redistributed). These per-pool shares are NON-FROZEN. The LuckyPool
maximum-k profile emerged after OBS-001's +1k window (which ends at
h97,250) closed, so it cannot appear in any frozen window this project
holds; it is a live-window fact by construction.

Overall share at the minimum: ~43% of blocks in the live post-fork window
(NON-FROZEN), 62% of the 155 post-fork blocks in DS-001's frozen tail
(h96,251..96,405).

History: the (128, 2,048) pair predates the rule that made it the
minimum. In the frozen per-1,000-block bin series over DS-001 it first
appears in the bin starting h41,000 and peaks at 65.7% of a bin's blocks
mid-chain, long before the fork. Post-fork convergence deepened an
existing configuration; it did not create one.

## 2. Correction to OBS-001's working clue

[OBS-001](OBS-001-rank-penalty-fork-transition.md)'s +1k re-run
(2026-08-09) wrote that Kryptex "mines rank 128 with k up to the legal
maximum for that rank (mode 4,096-8,192)". The census confirms that mode
(it sharpens to 4,096) and retires only the "up to the legal maximum"
reading: Kryptex's rank-128 k distribution is an intermediate band and it
almost never sits at 65,536. The pool literally at the legal maximum is
LuckyPool (§1), a profile that emerged after OBS-001's window closed. No
numeric value in OBS-001 changes; the correction is to the interpretation,
recorded here per the errata policy rather than by editing OBS-001.

## 3. Tile-software census (14.4)

Signature: (tileH, tileW, rank, byte-exactness of the certificate's
rows/cols patterns against the official sm90 wgmma fragment bytes).
tileH/tileW are products of pattern lengths, so distinct byte patterns can
share a geometry; the byte-exact flag splits them where DS-001 records it.
The official signature is tile (2,64), byte-exact, rank 64 or 128, the
only ranks compiled in the published kernels.

Findings, over DS-001's frozen span (h1..96,405; denominator 96,405
non-EMPTY blocks) unless marked live:

- **36 distinct signatures** over the frozen span. This is a lower bound
  on distinct mining software: geometry aggregates byte patterns, and the
  live window resolves 23 raw-byte (rowsPattern, colsPattern, rank)
  tuples where geometry gives 17 signatures (NON-FROZEN).
- **Official signature: 24.8%** of the 96,405 blocks. It is absent for
  the chain's first 21k blocks (custom software ran from h1), peaks at
  ~97-99% of a bin's blocks in the constant-m fleet era, and still runs
  at ~7% of blocks in the live tail window h96,251-97,725 (the last 1,000
  blocks give 71/1,000; NON-FROZEN).
- **Mimicry runs in both directions**, quantified over the frozen span:
  official (2,64) geometry with non-official bytes, 2,207 blocks;
  official bytes at the non-compiled ranks 256/512/1024, 1,767 blocks.

Binding interpretation: tile patterns identify software, never honesty.
All 54 MODEL_SHAPED_CUSTOM weight-matched blocks sit on one non-official
signature, (2,48), and committed genuine published weights (DS-002/DS-002b
keyed-hash matches), so non-official software demonstrably did
real-weight work. Conversely, MINER_* environment overrides let custom
software emit the official pattern, so the official-signature share is
only an upper bound on the unmodified-stack share (unit: blocks), never a
measurement of it.

## 4. Boundaries

1. Every configuration measured is consensus-legal. Boundary residence is
   an optimization profile, not a violation, and no mechanism or motive is
   asserted for any pool's choice of profile.
2. Signatures classify software, not operators and not honesty (§3). A
   non-official signature never implies synthetic work; an official
   signature never proves the unmodified stack.
3. 36 signatures is a lower bound on distinct stacks; the geometry-level
   census undercounts wherever byte patterns collide (§3, first bullet).
4. Pool attribution is single-known-wallet coinbase tagging; proxy-payout
   arrangements would misattribute (OBS-001's caveat carries over).
5. Live-window figures move with the chain tip and are marked NON-FROZEN;
   only the frozen-DS-001 figures reproduce byte-for-byte.

## 5. Reproduction

```bash
scripts/pool-config-census.py            # frozen sections + live section
scripts/pool-config-census.py --skip-live  # byte-reproducible subset only
```

Frozen sections read only DS-001
(`docs/research/datasets/DS-001-classification-v1/`) plus the committed
DS-002/DS-002b scan datasets for the matched cross-reference, and include
an identity check tying the per-bin (128, 2,048) counts to DS-003's
`rank128k2048` field. The live section reads the keshi API and is
NON-FROZEN. Legality guards (no post-fork rank < 128, no k above the
rank-128 maximum) fail the run loudly rather than shipping a violated
window.

## 6. What remains

The web time-series needs two DS-003-v2 fields that DS-003-v1 bins do not
carry: a per-pool configuration crosstab and a per-bin tile-byte
histogram; until those land, the per-pool and signature series regenerate
only from DS-001 plus the live API.

## 7. Data

No new dataset. Inputs are the committed DS-001, DS-002/DS-002b, and
DS-003 datasets; the census verdicts this note records were committed in
the roadmap §14.3/§14.4 on 2026-08-10.
