# OBS-011: Coinbase-tag census over the full chain (plan item 2.2, DS-005)

Dated observation note. Recorded 2026-08-10 against the frozen dataset
[`datasets/DS-005-coinbase-tags-v1/`](datasets/DS-005-coinbase-tags-v1/MANIFEST.md)
(generated 2026-08-10T19:43:27Z, tool commit `7eed53a2`, heights 0 to 97,000
inclusive, 97,001 canonical blocks, 0 parse errors). **Status: observational
census, not pre-registered.** No frozen hypothesis governs it, and it is not on
the pre-registration track the hash-scan work follows; it is a descriptive pass
over the coinbase scriptSig of every block. Every figure below is
command-produced from the frozen dataset and marked verified; nothing is
re-derived by hand.

Naming rule for this note (binding): coinbase tag strings and payout addresses
are neutral chain facts and are stated as such. Where a tag family maps onto a
payout address that the pool-label seed (`migrations/0001_core.sql`) already
names, that is stated as a cross-validation of the seed label and nothing more.
No operational conduct is inferred, and no party is named beyond the seed labels
the repository already carries.

## 1. What a coinbase scriptSig is and how the census reads it

Every block's first transaction is its coinbase, and the coinbase has one input
with no real previous output: its previous outpoint is 32 zero bytes followed
by the index 0xffffffff. That input's signature script (the coinbase scriptSig)
spends nothing, so the miner is free to place arbitrary bytes in it, subject
only to a length cap and the one consensus rule below. The census reads that
field for every height and archives the full scriptSig hex, the 4-byte sequence
value that follows it, the printable ASCII runs inside it, a derived tag family,
and the coinbase's first payout address from the block JSON.

Isolation is prevout-anchored. The parser locates the 36-byte coinbase outpoint
(32 zero bytes plus 0xffffffff) directly, then reads the scriptSig as the
varint-length payload that follows, and the 4-byte sequence field after that.
Offsets are never computed from certificate sizes; on this chain naive cert-size
arithmetic overshoots the scriptSig start by about 7 bytes, so the anchor is
located by search and the height-push check rejects any false anchor.

Validation is by the BIP34 height push. The coinbase scriptSig begins with the
block's own height as a data push: OP_1 through OP_16 for heights 1 to 16, and a
little-endian minimally-encoded integer push above that. The census decodes that
leading push and keeps the row only when it equals the requested height;
anything else is written as a parse-error row rather than guessed. Genesis is the
one special case: the height-0 coinbase carries no height push (its scriptSig is
the pre-BIP34 launch text), so it is validated instead by its fixed 04ffff001d
prefix. Over heights 0 to 97,000 the census records 0 parse errors across all
97,001 canonical blocks (verified), so every non-genesis block carried a correct
height push and genesis matched its prefix.

Family classification is by longest known substring over the raw scriptSig bytes
viewed as latin-1. Leading push and non-printable bytes match no known string,
so they are effectively ignored. A block whose scriptSig contains none of the
known family strings is classed `other-ascii` when it still holds a printable run
of four or more bytes, and `none` when it holds no such run.

## 2. Tag families over the full chain

Denominator for every share in this section: the 97,001 parse-valid blocks,
which here are all 97,001 archived canonical blocks in heights 0 to 97,000 (0
parse errors). Unit of analysis: blocks, one coinbase per block.

| tag family | blocks | share of parse-valid | first height | last height |
|---|---|---|---|---|
| /P2SH/pearld/ | 83,431 | 86.01% | 1 | 96,991 |
| pool.kryptex.com | 5,118 | 5.28% | 67,675 | 96,999 |
| other-ascii | 3,844 | 3.96% | 0 | 96,963 |
| /pearl-pool/ | 3,161 | 3.26% | 57,963 | 97,000 |
| none | 1,447 | 1.49% | 55,752 | 96,997 |

`/P2SH/pearld/` is the string the stock node emits by default and it dominates
the chain. `pool.kryptex.com` and `/pearl-pool/` are the two pool self-labels
(§3). `other-ascii` collects any other printable coinbase string, including the
genesis launch message; 3,472 of the 3,844 `other-ascii` blocks pay the address
the seed labels PearlHash (verified from the frozen crosstab), so the coinbases
paying that address hold a printable string outside the three known family tags.
`none` collects blocks whose scriptSig carries no printable run of four or more
bytes after the height push.

A minor structural fact: 792 of the 97,001 archived rows carry a sequence field
other than 0xffffffff (verified). The sequence value is the 4 bytes following the
scriptSig; it is reported as read, with no meaning attached.

## 3. Voluntary coinbase tagging is established practice

The coinbase scriptSig is discretionary space, and on this chain it is used.
86.01% of the 97,001 parse-valid blocks (the 83,431 `/P2SH/pearld/` blocks) carry
the stock node template, so the default software announces itself on the great
majority of blocks. Two pools go further and place their own label in the
coinbase, and in both cases the self-label maps one-to-one onto the payout
address the seed already names:

- Kryptex: all 5,118 blocks carrying the `pool.kryptex.com` domain string pay a
  single payout address, and that address is the one the seed
  (`migrations/0001_core.sql`, sourced to a 2026-08-02 attribution) labels
  Kryptex (verified: 5,118 of 5,118 blocks, one distinct payout address; the
  string appears on no block outside this family, 0 occurrences, §6). The self-declared domain and
  the independently-seeded address label carry the same name and partition the
  same blocks, which cross-validates the seed label.
- LuckyPool: all 3,161 blocks carrying the `/pearl-pool/` string pay a single
  payout address, and that address is the one the seed labels LuckyPool
  (verified: 3,161 of 3,161 blocks, one distinct payout address; the string
  appears on no block outside this family, 0 occurrences, §6). The tag string does not itself spell
  the pool name, so the cross-validation here is the exact address partition
  rather than the name.

Both statements are neutral chain facts: a string appears in a coinbase, and
every block carrying it pays one seed-labeled address. Nothing about who operates
either pool is asserted beyond the label the repository already held.

## 4. Tag birth and death spans

The family spans (first and last height a family appears, from the table in §2)
are chain facts and place each label in time:

- `/P2SH/pearld/` runs from height 1 to 96,991, the stock template present from
  the first mined block after genesis.
- `pool.kryptex.com` first appears at height 67,675 and last at 96,999.
- `/pearl-pool/` first appears at height 57,963 and last at 97,000.
- `none` first appears at height 55,752, so coinbases with no printable tag are a
  later-chain phenomenon on this data.

These are appearance bounds within heights 0 to 97,000, not claims about activity
outside the archived span.

## 5. Limits

1. A coinbase tag is voluntary and self-declared. It is bytes the miner chose to
   place, checked by no consensus rule beyond the leading height push, so it
   identifies software or a self-chosen string and never proves who mined a
   block.
2. The stock template is the default, so its 86.01% share (§2) measures how many
   blocks ran software that emits the default string, not how many operators
   exist and not their sizes. Within the 83,431 `/P2SH/pearld/` blocks the payout
   address takes 9,444 distinct values, and 65,815 of those blocks pay addresses
   the seed does not label (both reproduced in §6), so the family is spread across many payout
   addresses and is uninformative about operator identity on its own.
3. The two pool self-labels (§3) cross-validate seed labels that already existed;
   they add a second independent signal, not a new accusation. A pool that chose
   not to tag, or that changed payout addresses, would not appear as itself here.
4. Pool-label attribution in the crosstab is single-payout-address matching
   against the seed. Proxy-payout or address-rotation arrangements would
   misattribute, the same caveat OBS-001 and OBS-008 carry.
5. `other-ascii` and `none` are residual buckets defined by the classifier, not
   pool identities; they collect whatever printable or non-printable coinbase
   content does not match a known family string.

## 6. Reproduction

```bash
scripts/coinbase-tag-census.py --out <archive>.jsonl --to 97000 --summarize
scripts/coinbase-tag-census.py --out <archive>.jsonl --to 97000 --summarize --json
```

Both read the append-only JSONL archive and refetch nothing. The frozen dataset
was produced by `scripts/coinbase-tag-census.py --emit`, which refuses unless
every height 0 to 97,000 is present exactly once; its file hashes are pinned in
[`datasets/DS-005-coinbase-tags-v1/MANIFEST.md`](datasets/DS-005-coinbase-tags-v1/MANIFEST.md).

The derived figures that `--summarize` does not print are reproduced directly
from the frozen `blocks.jsonl.gz` (each verified 2026-08-10 against the frozen
dataset):

- Tag exclusivity (§3): the `/pearl-pool/` byte string appears on 0 blocks
  classified outside the `/pearl-pool/` family, and `pool.kryptex.com` on 0
  blocks outside its family; because the classifier assigns the longest
  matching string, this scan over the raw `scriptSigHex` is what establishes
  the claim, not the family partition alone.
- Distinct payout addresses within `/P2SH/pearld/` (§5): 9,444, over the
  83,431 blocks of that family; 65,815 of those blocks pay an address the seed
  table does not label.

Command (frozen archive, distinct-address and exclusivity counts):

```bash
python3 - <<'PY'
import gzip, json
P="datasets/DS-005-coinbase-tags-v1/blocks.jsonl.gz"
pp="/pearl-pool/".encode().hex(); kx="pool.kryptex.com".encode().hex()
stock=set(); ppx=kxx=0
for l in gzip.open(P,"rt"):
    r=json.loads(l); h=r.get("scriptSigHex","") or ""; f=r.get("tagFamily")
    if pp in h and f!="/pearl-pool/": ppx+=1
    if kx in h and f!="pool.kryptex.com": kxx+=1
    if f=="/P2SH/pearld/" and r.get("payoutAddress"): stock.add(r["payoutAddress"])
print("outside-family /pearl-pool/:",ppx,"pool.kryptex.com:",kxx,
      "distinct stock addrs:",len(stock))
PY
```

## 7. Data

Frozen dataset [DS-005-coinbase-tags-v1](datasets/DS-005-coinbase-tags-v1/MANIFEST.md):
`blocks.jsonl.gz` (one JSON row per height, sorted, deterministic),
`summary.json` (family counts with denominators, per-family spans and top payout
addresses, the family-by-pool-label crosstab, parse-error count), and
`MANIFEST.md` (sha256 table). The dataset is append-only from creation;
corrections would ship as a new version directory with an errata note, never as
an edit.
