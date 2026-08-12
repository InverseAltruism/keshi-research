# Pearl Consensus Change Register (PCCR)

An independent, dated, code-evidenced ledger of every consensus change on
Pearl Network mainnet. Maintained by Keshi as part of its research track; facts sourced
from Keshi's internal protocol notes with per-row code evidence.

**Why this exists.** Pearl has shipped four consensus changes with no PIP: the
dense-only softfork (PCCR-0003), the `IsMoE` semantic fix (PCCR-0004), the
rank-penalty softfork (PCCR-0005) and the salted noise-seed hard fork
(PCCR-0007). One activated change carries a PIP, the MoE hard fork (PCCR-0002,
PIP-2). The PIP repository contains three documents, PIP-1 (process), PIP-2 and
PIP-3 (`PIPS/pip-0001.md`, `pip-0002.md`, `pip-0003.md`; 3P, listed 2026-08-11).
The code, not the PIPs, is the de-facto governance record, and nobody else keeps
this ledger. The register states verifiable facts about public repositories and
the presence or absence of documentation; it attributes no motive and describes
no low-level protocol mechanism (disclosure discipline per
Keshi's internal disclosure policy).

**Counting rule** (stated once; it governs every count in this register). The
unit is an activated mainnet consensus change, one per entry. Activation is
height-gated (PCCR-0002, 0003, 0005, 0007) or release-gated (PCCR-0004); both
count. The genesis baseline (PCCR-0001) is a rule set rather than a change and
is excluded. An entry that has not activated (PCCR-0006, Draft) is excluded
until it does. Testnet and testnet2 activations are recorded inside the
entries and in the Release review log, and are never counted. On that rule the
register holds five activated mainnet consensus changes as of 2026-08-11
(PCCR-0002, 0003, 0004, 0005, 0007), four of them with no PIP.

*Correction (2026-08-11):* the "Why this exists" paragraph above read "three consensus changes
with no PIP" until this date. That count was correct through PCCR-0005 and
became four when PCCR-0007 activated at height 99,000.

*Note (2026-08-10).* Keshi authored three PIP drafts, committed at
[`../research/outreach/`](../research/outreach/): weight-identity
commitments (Standards Track / Consensus), weight-provenance disclosure and
verification (Standards Track / Applications), and consensus-change
documentation and activation notice (Process; it draws on this register's
record). All three are labeled Draft and have not been submitted. Under
Keshi's site-first publication policy
they publish on Keshi's own site as clearly labeled drafts; submission to
the upstream PIP repository is a separate operator decision. The register
itself is unchanged by this: it records what Pearl ships, with evidence,
independent of any proposal Keshi drafts.

**Maintenance rules.**
- Entries are **append-only** and never renumbered. Corrections ship as dated
  errata lines inside the entry, never as silent edits.
- Every claim carries code evidence in the form `file:line @ tag` against the
  `pearl-research-labs/pearl` repository, or a PIP reference.
- `Observed` links Keshi's own measurement of the change where one exists.
- A new pearld release triggers a review of `chaincfg`, `wire`, `blockchain`
  and `zk-pow` diffs for candidate entries. Automated since 2026-08-07 by
  [`scripts/pearl-release-watch.py`](../../scripts/pearl-release-watch.py)
  (daily timer): it flags unreviewed releases and may append `REVIEW
  PENDING` placeholder rows to the Release review log below. It never
  authors entries and never fills a Result; humans do the review.

Confidence legend: SRC (pinned
source), WP (whitepaper), LIVE (observed on chain/infrastructure), 3P
(third party).

---

## PCCR-0001: Genesis consensus baseline

| | |
|---|---|
| Activation | Height 0, 2026-04-27 (genesis time 1777280400) |
| Kind | Baseline (not a change) |
| Shipped in | pearl v1.0.x |
| PIP | None (predates the PIP process; PIP-1, the process document, is dated 2026-05-17 in the `pearl-research-labs/pips` repo; 3P) |
| Evidence | `node/chaincfg/params.go` @ v1.2.1 (genesis block, `PowLimitBits=0x1B00FFFF`, `TargetTimePerBlock=3m14s`); genesis hash `a18d3093…dadd7` round-trips through `BlockHeader.BlockHash()` (SRC+LIVE) |

The launch rule set: V1 certificates, dense-only PoUW (tiled INT8 matmul,
BLAKE3 tile predicate, Plonky2 proof), WTEMA difficulty, smooth ~1/t² emission
with no halvings, Taproot-only outputs, OP_CAT and OP_CHECKXMSSSIG active in
tapscript from block 0.

## PCCR-0002: MoE hard fork (V2 certificates)

| | |
|---|---|
| Activation | Height **71,935** |
| Kind | **Hard fork**: V2 certificates required; MoE (grouped-GEMM) proofs become legal |
| Shipped in | pearl v1.1.x |
| PIP | **PIP-2, Final**: the only activated consensus change with a PIP |
| Evidence | `node/chaincfg/params.go` `MoEForkHeight` @ v1.2.1 (SRC); `node/wire/certificate_v2.go` (SRC) |
| Observed | Keshi fixture `block-71935.hex` (first V2 block). Whether the MoE window (71,935–91,630) contains any production MoE certificate is answerable from `cert_public_params` (`moe_e > 0` over that height range), a research query, since the census API's `window` cannot express height bounds |

*Update (2026-08-09):* answered: **1,929** MoE certificates
in the window
([OBS-003](../research/OBS-003-phase7-acceptance-and-corpus-census.md) §2);
governance note [OBS-006](../research/OBS-006-moe-retraction.md).

## PCCR-0003: Dense-only softfork (MoE retracted)

| | |
|---|---|
| Activation | Height **91,630** |
| Kind | **Softfork**: MoE proofs rejected again |
| Shipped in | pearl v1.2.0 (initially height 91,600; delayed to 91,630 in v1.2.1) |
| PIP | **None.** No PIP documents this change |
| Evidence | `node/chaincfg/params.go` `DenseOnlyForkHeight` @ v1.2.1 (SRC) |
| Observed | Keshi fixture `block-91630.hex` |

The capability introduced by PCCR-0002 was retracted ~19,700 blocks
(≈44 days) after activation, without a PIP in either direction beyond PIP-2
itself.

*Precision (2026-08-09):* measured from the two activation
block timestamps (`/v1/blocks/{71935,91630}`), the window is **19,695 blocks
and 41.0 days** (2026-06-12 → 2026-07-23); "≈44 days" above was a
block-count × target-time estimate. Usage measurement and governance note:
[OBS-006](../research/OBS-006-moe-retraction.md).

## PCCR-0004: `IsMoE` semantic fix

| | |
|---|---|
| Activation | Release-gated (no height): pearl **v1.2.1** |
| Kind | Consensus-adjacent semantic change: `IsMoE` predicate changed from `PublicDataLen != 164` to `> 164`, keeping zero-length template placeholders valid |
| PIP | **None** |
| Evidence | `node/wire/certificate_v2.go` `IsMoE()` @ v1.2.1 vs v1.2.0 (SRC) |

Small, but it changes which serialized certificates a node classifies as MoE.
It is recorded because classification feeds validity under PCCR-0003.

## PCCR-0005: Rank-penalty softfork

| | |
|---|---|
| Activation | Height **96,251** (activated 2026-08-06) |
| Kind | **Softfork**: reject `rank < 128`; multiply the difficulty bound by `(k_eff/rank)·128` (net `128/rank`: neutral at 128, 8× tighter at 1024) |
| Shipped in | pearl **v1.3.0**, released 2026-08-05 15:45 UTC, ~18.5 hours before activation |
| PIP | **None.** The third undocumented consensus change |
| Evidence | `node/chaincfg/params.go:353` @ v1.3.0 (`RankPenaltyForkHeight`); `zk-pow/src/api/sanity_checks.rs:164` @ v1.3.0 (`PENALTY_BASE_RANK = 128`) (SRC) |
| Observed | [`../research/OBS-001-rank-penalty-fork-transition.md`](../research/OBS-001-rank-penalty-fork-transition.md): the network snapped from rank 1024 (49% of blocks) to rank 128 (84%) at the boundary; k collapsed to the legal minimum 2,048; zero invalid blocks on the canonical chain; visible pool-share shift (LIVE) |

Testnet activations: testnet 36,761; testnet2 80,627; regtest 1.

*Precision (2026-08-11):* the "~18.5 hours" in the Shipped-in row is wrong.
Recomputed from the two endpoints: v1.3.0 was published 2026-08-05 15:45:09 UTC
(GitHub release `publishedAt`, 3P) and block 96,251 carries timestamp
2026-08-06 03:59:44 UTC (05:59:44+02:00 on our index, LIVE), a difference of
44,075 s = **12 h 14 m 35 s**, about 12h15m. The 18.5-hour figure is not
reproducible from these timestamps. The original row stands unedited per the
maintenance rules.

## PCCR-0006: PIP-3, V3 FP8 certificates (DRAFT)

| | |
|---|---|
| Activation | **None assigned** (Draft status) |
| Kind | **Hard fork** (proposed): V3 FP8 certificates; hardware whitelist (Hopper/Blackwell only); bit-exact architecture-dependent verification; advance hardware declaration |
| PIP | **PIP-3, Draft** (2026-07-30) |
| Evidence | `pearl-research-labs/pips` `pip-0003` (3P) |
| Notes | The draft contains no centralization analysis despite whitelisting two NVIDIA generations. Keshi's schema versions certificates; an unknown version raises a loud alert, never a silent skip |

*Erratum (2026-08-11):* certificate version 3 was consumed by the salted
noise-seed hard fork (PCCR-0007), activated at mainnet height 99,000 on
2026-08-11. `node/wire/certificate.go:84` @ v1.4.1 defines
`CertificateVersionV3 = 3` as the salted-seed certificate (SRC) and block 99,000
carries it (LIVE). PIP-3's proposed "V3 FP8" numbering is therefore stale as of
that date: the number is taken, so an FP8 certificate would need a different
one. The draft's substance is untouched by this, and PIP-3 remains Draft with no
activation height. Nothing in the shipped V3 is FP8; the two are separate
changes that collided on a version number.

## PCCR-0007: Salted noise-seed hard fork (V3 certificates)

| | |
|---|---|
| Activation | Height **99,000** (activated 2026-08-11) |
| Kind | **Hard fork**: V3 certificates required. Each matrix commitment root is bound to its declared dimension (`m` for A, `n` for B) before the noise-seed chain runs, so the declared `m` and `n` enter the seed derivation. The wire layout is unchanged from V2 |
| Shipped in | pearl **v1.4.1**, published 2026-08-11 10:29:47 UTC (3P). v1.4.0 first scheduled the same fork at height 98,900 and was superseded before that height was reached; it has no GitHub release object |
| PIP | **None.** The fourth activated mainnet consensus change with no PIP, and the first hard fork whose change to the seed derivation invalidates unchanged mining software (the MoE path also derives the A-side seed differently, replacing hash_a with hash_activations, but left old miners producing valid shares; the operational contrast is in the note below) |
| Evidence | `node/chaincfg/params.go:371` @ v1.4.1 (mainnet `SaltedSeedForkHeight: 99000`); `node/chaincfg/params.go:322-324` (`IsSaltedSeedForkActive`) and `:331-333` (`RequiredCertVersion` returns V3 at and above the height); `node/wire/certificate_v3.go:13-15` (`CertificateV3` embeds `CertificateV2`) and `:22-23` (`ProofCommitment` hashes version 3); `node/wire/certificate.go:84` (`CertificateVersionV3 = 3`); `zk-pow/src/api/seed.rs:20-25` (`SeedDerivation::bind_roots`, `Legacy` versus `Salted`); `node/blockchain/validate.go:539-543` (strict cutover: a block's certificate version must equal `RequiredCertVersion(height)`) (SRC, all @ v1.4.1) |
| Observed | Keshi index: block 98,999 is the last V2 certificate (2026-08-11 12:03:11 UTC) and block 99,000 the first V3 (2026-08-11 12:03:43 UTC), versions decoded by our own parser (LIVE) |

Other networks at v1.4.1 (SRC): testnet **38,648** (`params.go:565`), testnet2
**83,109** (`params.go:661`), regtest **1** (`params.go:455`), simnet **1**
(`params.go:744`). The counting rule keeps these on the record and out of the
count.

**Notice window: 1 h 33 m 56 s** (about 1h34m), from the v1.4.1 release
publication, 2026-08-11 10:29:47 UTC (GitHub release `publishedAt`, 3P), to the
timestamp of block 99,000, 2026-08-11 12:03:43 UTC (our index, LIVE). The basis
is the release carrying the height that actually activated. v1.4.0 carried the
fork at a different height and produced no release event to measure from: `gh
release view v1.4.0` returns "release not found", and the tag ref resolves to
commit `fc5ca65a`, committer date 2026-08-11 08:54:49 UTC (3P), which is
3 h 08 m 54 s before block 99,000. Both bases are shorter than PCCR-0005's,
restated in the precision note there as 12 h 14 m 35 s.

Three mainnet heights appear in the public record for this fork. PR #280's body
as opened at 2026-08-11 07:51:21 UTC gave MainNet `98830`; the body was edited
at 2026-08-11 08:36:07 UTC to `98900` (GitHub body edit history via the GraphQL
`userContentEdits` field, 3P). `98900` is the value in the v1.4.0 code and in
the upgrade guide at that tag. PR #282 (opened 10:17:16 UTC, merged 10:19:28
UTC) moved the mainnet height to `99000`, bumped the version to v1.4.1 and
updated the guide. Block 98,900 was mined at 2026-08-11 10:47:07 UTC carrying a
V2 certificate (LIVE), 17 m 20 s after v1.4.1 was published, so the replacement
height shipped before the height it replaced was reached.

Documentation state at v1.4.1 (SRC): the repository's `docs/` directory holds
two files, `moe-fork-upgrade-guide.md` and `salted-seed-fork-upgrade-guide.md`
(108 lines). The latter gives the fork heights per network and upgrade steps for
nodes, proving code and miners, and states that mining software deriving seeds
the old way produces invalid shares from the fork height on, which is the
operational difference from PCCR-0002, where old miners kept working. The v1.4.1
release notes body is a heading plus a changelog link (3P). No PIP.

*Observed (2026-08-12):* [OBS-012](../research/OBS-012-salted-seed-declared-arithmetic.md)
measures the fork's effect on declared certificate arithmetic. On a
count-matched 80-block window each side (a full post-fork day does not exist
yet), the declared over-declaration tail truncated while the median block's
declared arithmetic is unchanged. A metering-integrity effect, the declared m
and n are now self-consistent with the mined seed and cannot be chosen after a
solution is found; it is not evidence that useful work or real inference
occurred.

---

*Register opened 2026-08-06. Entries PCCR-0001…0006 seeded from the verified
facts dossier as of pearld v1.3.0.*

*PCCR-0007 added 2026-08-11 from the v1.4.0/v1.4.1 review, against pearld
v1.4.1.*

## Release review log

Every pearld release is reviewed for consensus-relevant diffs
(`chaincfg`, `wire`, `blockchain`, `zk-pow`) per the maintenance rules.
Releases producing no mainnet entry are logged here so "no entry" is
distinguishable from "not reviewed".

| Release | Reviewed | Result |
|---|---|---|
| v1.3.1 (2026-08-05) | 2026-08-07 | **No mainnet consensus change.** Full diff = 2 files: `node/chaincfg/params.go` (+1 −1: testnet2 `DenseOnlyForkHeight` 75,122 → 80,051, PR #276) + `version/version.go`. **First observed *retroactive* fork-height edit**: the testnet2 fleet was never upgraded for the dense-only fork, so 12 MoE blocks (78,309–80,050) were accepted after the shipped height, leaving canonical testnet2 unsyncable from genesis on current builds; the fix legalizes them after the fact. PR merged by its author ~2 minutes after opening, 0 reviews, 0 comments (process facts from the public PR). Testnet2-only → no mainnet entry; recorded because the mechanism (fork shipped, fleet not upgraded, height moved retroactively) is a governance datum |
| v1.4.0 (2026-08-11) | 2026-08-11 | **Mainnet consensus change, superseded before it could activate → no entry of its own; the activated change is PCCR-0007.** Diff vs v1.3.1: 2 commits, 75 files, 32 of them on the consensus surface (`node/chaincfg/`, `node/wire/`, `node/blockchain/`, `zk-pow/`), 24 non-test and 8 test files, per a release-watch run on 2026-08-11. It adds `SaltedSeedForkHeight` and `wire.CertificateVersionV3`, sets mainnet 98,900 with testnet 38,648, testnet2 83,109, regtest and simnet 1, and bumps the P2P protocol version to 2 (`node/wire/protocol.go:15` @ v1.4.1, SRC). **No GitHub release object exists for the tag**: `gh release view v1.4.0` returns "release not found" while the tag ref resolves to commit `fc5ca65a` (committer date 2026-08-11 08:54:49 UTC, 3P), so this version reached the public as a git tag with no release event. Mainnet 98,900 was replaced by 99,000 in v1.4.1 before block 98,900 was mined (2026-08-11 10:47:07 UTC, V2 certificate, LIVE) |
| v1.4.1 (2026-08-11) | 2026-08-11 | **Mainnet consensus change → PCCR-0007** (salted noise-seed hard fork, V3 certificates, height 99,000). Full diff vs v1.4.0 = 1 commit, 3 files: `node/chaincfg/params.go` (+1 −1, mainnet `SaltedSeedForkHeight` 98,900 → 99,000), `version/version.go` (+1 −1) and `docs/salted-seed-fork-upgrade-guide.md` (+2 −2, height and node version), from PR #282 (opened 10:17:16 UTC, merged 10:19:28 UTC; 3P, compare API). Published 10:29:47 UTC, 1 h 33 m 56 s before block 99,000. Keshi's collector moved to the v1.4.1 `wire` module because an earlier build rejects the version outright (`node/wire/certificate.go:155` @ v1.2.1, `unsupported certificate version`, SRC) |
