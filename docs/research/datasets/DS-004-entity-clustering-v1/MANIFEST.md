# DS-004 entity-clustering manifest

Produced by keshictl cospend-cluster (41310cac02bf-wb1bbc97), the Phase 14.1 multi-input
co-spend clustering over the miner population.
Generated: 2026-08-09T22:45:56Z

Snapshot: canonical tip height 97734, hash ebb3107d2ad9edfd6e61217eaaf5c6e7951d874ee75a64a710d30dab664f581e (REPEATABLE READ; the entire
walk describes exactly this chain state). Miner population bounded to
height 97734; the co-spend graph is the whole snapshot (a co-spend can spend
an output from any height, so bounding it would silently drop real linkage).

Coverage: the tx graph contributed 6582885 non-coinbase inputs (whole snapshot),
of which 0 could not be resolved to a funding address; each unresolved
input is a co-spend edge the clustering could not see. The miner population
is 97735 canonical blocks up to the bound, of which 97734 carry a decoded coinbase
payout address; only those 97734 blocks enter the block-share denominators
on both the entity and the address basis.

Clusters are lower bounds on linkage, never identities.

| File | sha256 |
|---|---|
| clusters.json | 25283705098e7d0104aadfed436e915890ad35976627763f4027cba5a555aa63 |
| summary.json | 1ea3a0af3d4ed8d2a9e662a8d40cb01fd0e763651167036a05bf87efa2046c76 |
This dataset is append-only: corrections ship as a new version directory
with an errata note, never as an edit here.
