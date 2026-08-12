# DS-004 entity-clustering manifest

Produced by keshictl cospend-cluster (0705b6376718-we92ca47), the Phase 14.1 multi-input
co-spend clustering over the miner population.
Generated: 2026-08-10T07:20:27Z

Snapshot: canonical tip height 97900, hash 526e0eb90df95ebfabccf9a6069857ad1799c6a9f132a4bbfe6c787c3c598407 (REPEATABLE READ; the entire
walk describes exactly this chain state). Miner population bounded to
height 97900; the co-spend graph is the whole snapshot (a co-spend can spend
an output from any height, so bounding it would silently drop real linkage).

Coverage: the tx graph contributed 6603055 non-coinbase inputs (whole snapshot),
of which 0 could not be resolved to a funding address; each unresolved
input is a co-spend edge the clustering could not see. The miner population
is 97901 canonical blocks up to the bound, of which 97900 carry a decoded coinbase
payout address; only those 97900 blocks enter the block-share denominators
on both the entity and the address basis.

Clusters are lower bounds on linkage, never identities.

Full cluster membership is persisted in members.jsonl.gz: one JSON line per
miner address, {address, entity, blocks}, where entity is the representative
(lexicographically smallest member) address of the union-find cluster, the
same representative clusters.json uses, sorted by (entity, address). The
address-basis distribution and every cluster's full membership are
reproducible from that file alone.

| File | sha256 |
|---|---|
| clusters.json | 4bf21129301f44f10982d0366b981e31495c074cbb6092a46779f54a730c184b |
| members.jsonl.gz | c5fa86c33104043f3c98f1486778dc587141925aac7af69973c7d14fba71bafc |
| summary.json | f2e6552b59913f4128b29d21100b28cda64a6bca5639a2579827c823b90f3aba |
This dataset is append-only: corrections ship as a new version directory
with an errata note, never as an edit here.
