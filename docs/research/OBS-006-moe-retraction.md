# OBS-006: The MoE window and its undocumented retraction

Dated observation note. Recorded 2026-08-09 at census tip **97,530**, corpus
complete (`/v1/status` → `certParams.expected = parsed = 97,530`,
`missing = 0`, checked the same day). Sources:
[`registry/PCCR.md`](../registry/PCCR.md) (consensus events, per-row code
evidence), [OBS-003](OBS-003-phase7-acceptance-and-corpus-census.md) (the
in-window count), and the live census API
([`metrics.md#cert-census`](../metrics.md#cert-census)) queried on the
recording date. No new computation was required; §2 states how each number
was re-verified on the day of writing.

Terminology, per the label discipline in `metrics.md`: a "MoE certificate"
is a canonical block whose certificate public data declares `moe_e > 0`
(the V2 grouped-GEMM tail). That is a *declared and committed* MoE-shaped
job. Nothing in this note claims expert inference ran, was fresh, or served
anyone.

## 1. The finding

| | |
|---|---|
| MoE proofs legalized | height **71,935** (2026-06-12): PCCR-0002, **hard fork**, V2 certificates |
| Documented by | **PIP-2 (Final)**, the only *activated* consensus change in Pearl's history with a PIP |
| Production usage | **1,929 MoE certificates**: 9.8% of the window's 19,695 blocks (§2) |
| MoE proofs rejected again | height **91,630** (2026-07-23): PCCR-0003, **softfork**; shipped in v1.2.0 at height 91,600, delayed to 91,630 in v1.2.1 |
| Documented by | **Nothing.** No PIP documents the retraction, in either direction, beyond PIP-2 itself |
| Window | 19,695 blocks, from activation at 71,935 up to (not including) dense-only activation at 91,630; **41.0 days** measured from block timestamps |
| MoE certificates after 91,630 | **0**, through tip 97,530 (§2) |
| MoE blocks, last 24h / 7d | **0** of 462 · **0** of 2,857 (census, 2026-08-09) |

A capability introduced by the chain's only PIP-documented fork, genuinely used in
roughly one block in ten while legal, was withdrawn 41 days later by a
softfork no document proposes, explains, or announces.

(Precision note: PCCR-0003 and roadmap §9.5 previously carried "≈44 days",
a blocks × target-time estimate. The measured duration between the two
activation block timestamps is 41.0 days; a dated precision line was added
to PCCR-0003 today.)

## 2. How each number was verified on the recording date

- **Consensus events and heights**: PCCR-0002/0003 rows, code evidence
  `node/chaincfg/params.go` (`MoEForkHeight`, `DenseOnlyForkHeight`) and
  `node/wire/certificate_v2.go` @ v1.2.1 (SRC). Calendar dates from
  `/v1/blocks/{71935,91630}` block timestamps, fetched today.
- **1,929**: OBS-003 measured it on 2026-08-06 (tip 96,397) from
  `cert_public_params` (`moe_e > 0`) over the window height range; the
  census `window` parameter cannot express height bounds, so the in-window
  figure is a research query, not a census call. Today's whole-corpus census
  at tip **97,530** returns `moeBlocks = 1,929` (identical), so zero MoE
  certificates entered the corpus between the two measurements, and
  OBS-003's placement of all 1,929 inside the window carries over unchanged.
- **0 after 91,630**: two independent lines. Rule: MoE certificates are
  consensus-invalid outside the window under PCCR-0003, with PCCR-0004
  (v1.2.1) fixing the `IsMoE` predicate that feeds that validity check.
  Measurement: the whole-corpus count is unchanged at 1,929 (previous
  bullet), and the 24h / 7d windows measured today contain 0 of 462 and
  0 of 2,857 blocks respectively.
- **9.8%**: 1,929 / 19,695; denominator = canonical blocks at heights
  71,935–91,629 inclusive. Census figures count canonical blocks only
  (orphaned certificates are retained in the corpus but excluded).

## 3. Why this matters

**Pearl distributes a checkpoint its own consensus cannot validate work
for.** `Qwen3-30B-A3B-Instruct-2507-pearl`, one of the four checkpoints
Pearl publishes, and the reference stack's end-to-end-tested MoE model, is
mixture-of-experts (128 experts, top_k 8; config verified live 2026-08-05,
`pearl-notes.md` F4). Since height 91,630 the network rejects any proof for
that architecture.

**The unmineable class is the class the ecosystem is moving toward.** Much
of the current open-weight frontier is mixture-of-experts; this note
asserts the architecture only for Pearl's own published checkpoint, whose
config we verified. For any named third-party model the claim is
conditional: *if* it is MoE, *then* it is unmineable under PCCR-0003.

**Dense models remain mineable, and that constraint is economic, not
architectural.** Roughly two-thirds of a dense model's linear arithmetic is
INT7-mineable (PREREG-002 §3: `down_proj` is FP8 and excluded; only half
the attention layers qualify).

**The retraction also removed the chain's richest attestation surface.**
The V2 MoE tail is the only certificate region that ever committed to
routing (`hash_routing`, expert index and routing offsets, `pearl-notes.md`
§Certificate internals, SRC). Since 91,630 no Pearl certificate commits to
any routing decision. Per the terminology above: committed routing *data*,
not evidence that routing served anyone.

## 4. Governance reading (facts; no motive)

- Of the mainnet consensus changes in the register (PCCR-0002…0005 plus the
  release-gated PCCR-0004), exactly one has a PIP, and it is the one that
  was reversed.
- No public document explains the withdrawal. That absence is recorded as
  an absence. We do not assert a motive; if the retraction was a response to
  a defect, mechanism detail would fall under the roadmap §9.4 disclosure
  split, and nothing constructive is described here.
- The code, not the PIP repository, is Pearl's de-facto governance record;
  the independent ledger is [`registry/PCCR.md`](../registry/PCCR.md).

## 5. Boundaries

1. We measure that MoE proofs are rejected and that MoE blocks are zero. We
   do **not** know why the capability was withdrawn, and this note asserts
   no reason.
2. The 1,929 count is declared-and-committed MoE-shaped jobs (accepted by
   consensus under the window's rules). It is not a claim that expert
   inference occurred or served anyone.
3. Dense models remain mineable (§3); nothing here says Pearl "cannot mine
   models", only that it rejects proofs for this architecture class.
4. Named third-party models must not be asserted MoE or unmineable without
   checking their published configs; the defensible claim is conditional
   (§3).
5. PCCR-0004 (v1.2.1's `IsMoE` predicate change, `PublicDataLen != 164` →
   `> 164`) alters which serialized certificates count as MoE and therefore
   interacts with PCCR-0003 validity; it is part of this note's evidence
   chain.

## 6. Reproduction

```bash
curl -s localhost:8081/v1/status | jq .certParams        # corpus completeness
curl -s  localhost:8081/v1/certs/census                | jq '{blocks, moeBlocks}'  # 97530 / 1929 (2026-08-09)
curl -s 'localhost:8081/v1/certs/census?window=7d'     | jq '{blocks, moeBlocks}'  # 2857 / 0
curl -s 'localhost:8081/v1/certs/census?window=24h'    | jq '{blocks, moeBlocks}'  # 462 / 0
```

Consensus events: `registry/PCCR.md` entries PCCR-0002, PCCR-0003,
PCCR-0004 (each row carries `file:line @ tag` code evidence). In-window
count: OBS-003 §2, from `cert_public_params` (`moe_e > 0`) over heights
71,935–91,629, a DB query, because the census `window` parameter cannot
express height bounds. Every census figure in this note is gated by
[`metrics.md#cert-census`](../metrics.md#cert-census); the note introduces
no new metric (confirmed against `metrics.md` on the recording date, per
PLAN-001 Step 1A's gate).

## 7. Data

No new dataset. Census responses as quoted (`computedAt`
2026-08-09T12:59Z / 13:22Z); consensus evidence in PCCR; the in-window
measurement is OBS-003's. Web presentation: the annotated timeline strip is
specified as PLAN-002 §9.2 figure N2 and needs no chart library.
