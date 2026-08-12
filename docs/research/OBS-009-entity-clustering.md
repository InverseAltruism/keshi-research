# OBS-009: Entity clustering over the full miner population (Phase 14.1, DS-004)

Dated observation note. Recorded 2026-08-10 against the frozen dataset
[`datasets/DS-004-entity-clustering-v1/`](datasets/DS-004-entity-clustering-v1/MANIFEST.md)
(generated 2026-08-09T22:45:56Z at snapshot tip **97,734**, hash
`ebb3107d2ad9edfd6e61217eaaf5c6e7951d874ee75a64a710d30dab664f581e`,
REPEATABLE READ). Method:
`keshictl cospend-cluster` (`cmd/keshictl/cospend.go`, tool version
`41310cac02bf-wb1bbc97`). The run and the finding were both independently
reviewed; the fleet decomposition in §3 was independently reproduced by the
finding review. Committed context: Keshi's internal roadmap §14.1
(FULL RUN DONE 2026-08-10).

**Status: internal research record, exploratory (not pre-registered).**
Publication is a separately held decision; nothing here is written for
release. §2 separates what is frozen in DS-004 from what is not.

**Status revision, 2026-08-11.** The held-publication sentence above is
superseded: an operator decision re-scoped publication to the site package, and this
note ships inside it. The exploratory, not-pre-registered status and every
boundary in §5 are unchanged.

Unit of analysis throughout: **blocks with a decoded coinbase payout
address**. The snapshot holds 97,735 canonical blocks up to the bound, of
which **97,734** carry a decoded coinbase payout address; only those enter
every share and coefficient below, on both bases.

Summary sentence, with the era qualifier it must always carry: on the
all-time cumulative basis, the second-largest block-producing entity in the
chain's history is an unattributed genesis-era fleet of 107 uniform workers
that mined roughly 29% of blocks up to height 30,768, went dark, and still
holds about 27.6M PRL; address-basis figures hide it, and the full-network
Nakamoto coefficient falls from 50 (addresses) to 12 (entities) on its
account alone.

## 1. The finding

Method in one line: union-find every set of addresses that co-spend in a
non-coinbase transaction into one entity (the standard multi-input
heuristic; coinbase inputs excluded), over one repeatable-read snapshot,
then map each block's coinbase payout address to its entity. Tx-graph
coverage was complete: **6,582,885** non-coinbase inputs walked, **0**
unresolved (each unresolved input would be a co-spend edge the clustering
could not see).

| | |
|---|---|
| Miner addresses | **9,559** distinct coinbase payout addresses over the 97,734 blocks |
| Entities | **9,301** after clustering |
| Address basis (denominator 97,734 blocks) | Nakamoto **50** · effective units (1/HHI) **37.06** · top-1 **11.08%** |
| Entity basis (denominator 97,734 blocks) | Nakamoto **12** · effective units (1/HHI) **28.34** · top-1 **11.08%** |
| Top-1 on both bases | the same single PearlHash address, **10,829 / 97,734 blocks**; it fuses with nothing, so the top-1 share is basis-invariant |
| The one cluster that matters | unattributed, **107 addresses**, **8,931 / 97,734 blocks (9.14%)**, second-largest entity, zero labeled-pool addresses fused |
| Labeled-pool cross-fusions | `multiPoolEntities = 0`; no clustering step fused two labeled pools |

The 50 to 12 collapse is driven entirely by that one cluster. Counterfactual
(non-frozen; re-derived from the live index during the finding review):
fusing only the 107-address cluster and no other merge already gives
Nakamoto 12; applying every other merge but not that one gives 46.

## 2. Frozen versus non-frozen, and how each number was checked

**Frozen (DS-004-entity-clustering-v1; sha256 in the MANIFEST):**

- Every figure in the §1 table comes from `summary.json` and
  `clusters.json`, re-read from the frozen files on the recording date.
- Entity-basis **Nakamoto 12** recomputes from `clusters.json` alone: sort
  the persisted entities by blocks and cumulate; the top 12 sum to 49,408
  blocks, which exceeds 97,734 / 2 = 48,867, and the top 11 (48,471) do
  not. Rechecked against the frozen file on the recording date.
- Top-1 **11.08%** = 10,829 / 97,734; fleet share **9.14%** = 8,931 /
  97,734. Both denominators are the 97,734 blocks with a decoded coinbase
  payout address; recomputed from the frozen files on the recording date.

**Non-frozen (API/Blockbook re-derivation; not reproducible from the frozen
artifact):**

- All per-address fleet figures in §3 (first-mined heights, per-address
  block counts, the ~29% share to height 30,768, the 10 lifetime spends,
  the 28.08M PRL received and its 98.2% residual). They were independently
  reproduced by the finding review against the live index and API, and are
  re-derivable there, but DS-004 does not contain them.
- The address basis (Nakamoto 50, effective 37.06) is frozen as a value in
  `summary.json`, but its re-derivation from the address distribution cannot
  be recomputed from the frozen artifact alone, because `clusters.json`
  persists only the top-100 entities (§7); it needs a live index.
- The §1 counterfactual (fleet-only merge already gives Nakamoto 12; every
  other merge but not the fleet gives 46) is NON-FROZEN: it is recorded only
  here, from the finding review's live-index re-derivation, not in any frozen
  artifact.

## 3. The 107-address fleet

**Verified behavior** (reproduced independently by the finding review;
non-frozen per §2):

- All 107 addresses first mined within the chain's first **157 blocks**.
- Per-address lifetime block counts are **66-108** (median 83): the
  signature of roughly 107 concurrently running, equally weighted workers
  started together.
- The fleet won roughly **29%** of blocks up to height 30,768 (unit blocks;
  denominator canonical blocks up to that height; approximate,
  API-derived), then went dark: **0 blocks after 30,768** through the
  snapshot tip.
- The entire 107-address fusion rests on **10 lifetime non-coinbase
  spends**: round integer-PRL principals to fresh one-use addresses, change
  to one shared address each time.
- **98.2%** of the **28.08M PRL** it received in coinbase payouts is still
  unspent (unit PRL; denominator the fleet's total coinbase receipts),
  about 27.6M PRL.

**Inferred reading:** this is single-wallet behavior. The alternative that
would make the cluster an artifact rather than an entity, a shared service
such as an exchange deposit path, predicts heterogeneous start times and
volumes, frequent hot-wallet sweeps, and near-zero residual balances; every
one of those signatures is absent here, and no labeled-pool address is
fused anywhere in the run (`multiPoolEntities = 0`, frozen). The inference
stops at one wallet controlling the payouts; §5 binds what may and may not
be said beyond that.

**Era qualifier (load-bearing):** the fleet is a historical fact about the
chain's first weeks. It stopped producing at height 30,768 and
current-window concentration is unaffected. Any restatement of this finding
must carry that qualifier; the all-time cumulative basis is the only basis
on which the fleet ranks second.

## 4. What this bears on, and what it does not

- **Revises:** full-network all-time address-basis decentralization. The
  address count overstates the entity count, and the entity-basis Nakamoto
  of 12 is itself an **upper bound** on the true value, because clustering
  is a lower bound on linkage: merges the heuristic cannot see would only
  lower it further.
- **Does not touch:** the shipped `/v1/pools` labeled-pool concentration
  coefficient. Different unit (labeled pools, not clustered entities) and a
  24h window, not all-time cumulative.
- **Does not touch:** OBS-005's 4.27 effective operators. That figure is
  over the 46 matched addresses of the weight-provenance scan on the
  DS-002-only basis (the combined basis is 48 addresses and 4.59; OBS-005
  §10 item 5). Either way the matched addresses are disjoint from the 107
  fleet addresses (checked by grep across the research trees on the run
  date).

## 5. Boundaries (binding)

1. Clusters are **lower bounds on linkage, never identities**. A coinbase
   paid straight into a shared custodial path would cluster onto the
   custodian; §3 records why that reading fails every signature here, but
   the ceiling on the claim is unchanged.
2. Report the fleet only as **one wallet controlling 8,931 blocks'
   payouts**. Never a named party, never a characterized party.
3. The heuristic cannot decide whether the key-holder **owned the hashpower
   or coordinated it for others**; an unlabeled private pool paying its
   workers from the same wallet looks identical on every measurement in
   this note. No claim either way is made.
4. The ~29% era share and all §3 per-address figures are approximate,
   API-derived, and non-frozen (§2); they are cited from the finding
   review's independent reproduction, not re-derived here.
5. Exploratory. No pre-registration constrains this analysis; it shipped as
   a roadmap phase (14.1) with a stated method and a frozen output, and its
   numbers should be treated accordingly.

## 6. Reproduction

- Frozen concentration figures: read
  `datasets/DS-004-entity-clustering-v1/summary.json` (sha256 pinned in the
  MANIFEST alongside the snapshot tip and hash).
- Entity-basis Nakamoto: from `clusters.json`, cumulate `blocks` over the
  persisted entities in descending order until the sum exceeds 48,867
  (= 97,734 / 2); the crossing is at entity 12 (cumulative 49,408).
- Full re-run: `keshictl cospend-cluster --out <new version dir>` against a
  live index (`cmd/keshictl/cospend.go`; the tool refuses to overwrite an
  existing dataset directory, per the append-only rule).
- Fleet decomposition: non-frozen; re-derive per-address histories via the
  local Blockbook/API over the cluster's member addresses. Note that the
  membership list itself is not in the frozen artifact (only the
  representative address and counts are), so this path also needs the live
  index.

## 7. Data

`datasets/DS-004-entity-clustering-v1/` (`summary.json`, `clusters.json`,
`MANIFEST.md`), frozen, append-only. Known limitation, to fix in a future
append-only version: `clusters.json` persists only the **top-100 entities**,
so full cluster membership and the address-basis figures are not
reproducible from the frozen artifact alone (both re-derive from a live
index). A DS-004 v2 should persist full membership; corrections and
extensions ship as a new version directory, never as an edit to v1.

## 8. Correction 2026-08-10: DS-004-v2 supersedes the v1 basis

Dated correction block per `ERRATA-POLICY.md`: an incomplete dataset is
never edited in place; the fix is a new version directory plus this note.
Everything above this section is the original v1-basis record and stays as
written.

**The new basis.** The §7 limitation is closed by the append-only follow-up
[`datasets/DS-004-entity-clustering-v2/`](datasets/DS-004-entity-clustering-v2/MANIFEST.md)
(generated 2026-08-10T07:20:27Z at snapshot tip **97,900**, hash
`526e0eb90df95ebfabccf9a6069857ad1799c6a9f132a4bbfe6c787c3c598407`,
REPEATABLE READ, tool `0705b6376718-we92ca47`), which adds
`members.jsonl.gz`: one JSON line per miner address
(`{address, entity, blocks}`, sha256 pinned in the v2 MANIFEST). v2 is this
note's basis from this date; v1 stays in place unedited.

**Refreshed figures.** Unit of analysis unchanged: blocks with a decoded
coinbase payout address. The v2 snapshot holds 97,901 canonical blocks up
to the bound, of which **97,900** carry one; those 97,900 blocks are the
denominator of every share below, on both bases. Tx-graph coverage:
6,603,055 non-coinbase inputs walked, 0 unresolved. The v2 column is
recomputed from the v2 committed files on the correction date (commands
below); the v1 column is re-read from the v1 frozen files the same day.

| | v1 (denominator 97,734 blocks) | v2 (denominator 97,900 blocks) |
|---|---|---|
| Miner addresses | 9,559 | **9,561** |
| Entities | 9,301 | **9,303** |
| Address basis: Nakamoto | 50 | **49** |
| Address basis: effective units (1/HHI) | 37.06 | **36.90** |
| Address basis: top-1 | 11.08% | **11.09%** |
| Entity basis: Nakamoto | 12 | **12** |
| Entity basis: effective units (1/HHI) | 28.34 | **28.28** |
| Top-1 on both bases | 10,829 / 97,734 | **10,861 / 97,900**; the same single PearlHash address, fused with nothing |
| The 107-address fleet | 8,931 / 97,734 (9.14%) | **8,931 / 97,900 (9.12%)**; still the second-largest entity |
| Labeled-pool cross-fusions | 0 | **0** |

**What changed.** The address-basis Nakamoto moved from 50 to 49, verified
by recomputation from `members.jsonl.gz`: the top 49 addresses cumulate
48,982 blocks, which exceeds 97,900 / 2 = 48,950, and the top 48 (48,874)
do not. §1's "falls from 50 (addresses) to 12 (entities)" therefore reads
**49 to 12** on the v2 basis. The entity-basis Nakamoto stays 12 (top 12
cumulate 49,570; top 11 give 48,633). The fleet's block count is unchanged
at 8,931; its share moves from 9.14% to 9.12% only because the denominator
grew by 166 blocks. Every other shift is small drift from those 166 blocks
and 2 additional addresses.

**Previously non-frozen, now frozen-reproducible from the committed v2
artifact alone.** Of §2's three non-frozen bullets, the second and third
close fully and the first closes in part:

- The address-basis re-derivation (Nakamoto 49, effective units 36.90,
  top-1 11.09%). In v1 the values were stored in `summary.json` but could
  not be re-derived from the artifact; they now recompute from
  `members.jsonl.gz`.
- The §1 counterfactual: merging only the 107-address fleet and nothing
  else gives Nakamoto **12**; applying every other merge but not the fleet
  gives **46**. The same values the finding review derived from the live
  index on the v1 basis; both now reproduce from the committed file.
- The fleet's full membership (107 addresses, representative
  `prl1p05tqqdf8tlzxlpt0vxmqp3ky9v76lh0egjejzjhcwwffq98j723q0gyl7t`) and
  its per-address lifetime block counts: range **66-108**, median **83**,
  matching §3.

All of the above from the committed files, run at the repository root:

```sh
cd docs/research/datasets/DS-004-entity-clustering-v2 && python3 - <<'EOF'
import json, gzip, statistics
rows = [json.loads(l) for l in gzip.open('members.jsonl.gz', 'rt')]
tot = sum(r['blocks'] for r in rows)
ent = {}
for r in rows:
    ent.setdefault(r['entity'], []).append(r['blocks'])
def nakamoto(counts):
    s = 0
    for i, b in enumerate(sorted(counts, reverse=True), 1):
        s += b
        if s > tot / 2:
            return i, s
def eff(counts):
    return 1 / sum((b / tot) ** 2 for b in counts)
addr = [r['blocks'] for r in rows]
entc = [sum(v) for v in ent.values()]
print('addresses', len(addr), 'entities', len(ent), 'blocks', tot)
print('address basis: nakamoto %d (cum %d)' % nakamoto(addr),
      'eff %.2f' % eff(addr), 'top1 %d/%d = %.4f' % (max(addr), tot, max(addr) / tot))
print('entity basis:  nakamoto %d (cum %d)' % nakamoto(entc),
      'eff %.2f' % eff(entc), 'top1 %d/%d = %.4f' % (max(entc), tot, max(entc) / tot))
frep, fleet = next((k, v) for k, v in ent.items() if len(v) == 107)
print('fleet', frep, 'addresses', len(fleet), 'blocks', sum(fleet),
      'share %.4f' % (sum(fleet) / tot), 'per-address %d-%d median %g'
      % (min(fleet), max(fleet), statistics.median(fleet)))
only_fleet = [r['blocks'] for r in rows if r['entity'] != frep] + [sum(fleet)]
all_but = [sum(v) for k, v in ent.items() if k != frep] + fleet
print('counterfactuals: fleet-only merge nakamoto %d (cum %d);' % nakamoto(only_fleet),
      'all merges except the fleet nakamoto %d (cum %d)' % nakamoto(all_but))
EOF
```

Output on the correction date:

```
addresses 9561 entities 9303 blocks 97900
address basis: nakamoto 49 (cum 48982) eff 36.90 top1 10861/97900 = 0.1109
entity basis:  nakamoto 12 (cum 49570) eff 28.28 top1 10861/97900 = 0.1109
fleet prl1p05tqqdf8tlzxlpt0vxmqp3ky9v76lh0egjejzjhcwwffq98j723q0gyl7t addresses 107 blocks 8931 share 0.0912 per-address 66-108 median 83
counterfactuals: fleet-only merge nakamoto 12 (cum 49570); all merges except the fleet nakamoto 46 (cum 49044)
```

**Still non-frozen, re-derived on the correction date** against the local
Blockbook (query-time tip 98,135), now walked over the frozen v2 membership
instead of a live cluster listing. The walk ties itself to the artifact:
the per-address coinbase counts equal the frozen `blocks` values for all
107 addresses, and the distinct coinbase txids total 8,931.

- Fleet first block at height **2**, last at height **30,768**; the latest
  per-address first-mined height is **157**, matching §3's "first 157
  blocks"; **0** fleet blocks above height 30,768 through the live tip.
- **10** lifetime non-coinbase spend txs (distinct txids with any fleet
  address on the input side), matching §3.
- Coinbase receipts **28,083,736 PRL**; still unspent **27,580,034 PRL**;
  unspent share **98.21%** (unit PRL; denominator the fleet's total
  coinbase receipts), matching §3's ~98.2% of 28.08M PRL.
- The ~29% era share to height 30,768 keeps its §3 wording: approximate,
  live-derived, non-frozen.

Command (live index required):

```sh
cd docs/research/datasets/DS-004-entity-clustering-v2 && python3 - <<'EOF'
import json, gzip, urllib.request
def get(p):
    return json.load(urllib.request.urlopen('http://127.0.0.1:9131' + p, timeout=60))
rows = [json.loads(l) for l in gzip.open('members.jsonl.gz', 'rt')]
ent = {}
for r in rows:
    ent.setdefault(r['entity'], []).append(r)
fleet = next(v for v in ent.values() if len(v) == 107)
print('live tip at query time', get('/api/v2/')['blockbook']['bestHeight'])
heights, firsts, spends, cb_tx = [], [], set(), set()
recv = unspent = mismatches = 0
for m in fleet:
    a, txs, page, pages = m['address'], [], 1, 1
    while page <= pages:
        d = get('/api/v2/address/%s?details=txs&pageSize=1000&page=%d' % (a, page))
        pages = d.get('totalPages', 1); txs += d.get('transactions', []); page += 1
    mine = {}
    for t in txs:
        if any('coinbase' in v for v in t['vin']):
            val = sum(int(v['value']) for v in t['vout'] if a in (v.get('addresses') or []))
            if val: mine[t['txid']] = (t['blockHeight'], val)
        elif any(a in (v.get('addresses') or []) for v in t['vin']):
            spends.add(t['txid'])
    mismatches += (len(mine) != m['blocks'])
    hs = [h for h, _ in mine.values()]
    heights += hs; firsts.append(min(hs)); cb_tx |= set(mine)
    recv += sum(v for _, v in mine.values())
    unspent += sum(int(u['value']) for u in get('/api/v2/utxo/' + a) if u['txid'] in mine)
print('coinbase-count mismatches vs frozen members', mismatches,
      '; distinct coinbase txids', len(cb_tx))
print('first height', min(heights), '; last height', max(heights),
      '; max per-address first-mined', max(firsts),
      '; blocks above 30768:', sum(h > 30768 for h in heights))
print('lifetime non-coinbase spend txs', len(spends))
print('coinbase received %.2f PRL; unspent %.2f PRL; unspent share %.4f'
      % (recv / 1e8, unspent / 1e8, unspent / recv))
EOF
```

Output on the correction date:

```
live tip at query time 98135
coinbase-count mismatches vs frozen members 0 ; distinct coinbase txids 8931
first height 2 ; last height 30768 ; max per-address first-mined 157 ; blocks above 30768: 0
lifetime non-coinbase spend txs 10
coinbase received 28083736.35 PRL; unspent 27580034.05 PRL; unspent share 0.9821
```

§5's boundaries are unchanged and bind this correction as they bind the
original text.
