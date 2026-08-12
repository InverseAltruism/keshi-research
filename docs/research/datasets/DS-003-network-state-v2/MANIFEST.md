# DS-003 network-state manifest

Produced by keshictl network-state (0705b6376718-we92ca47), decoder v1, per PLAN-002 SS9.1.
Generated: 2026-08-10T07:18:06Z

Snapshot: canonical tip height 97899, hash afa6727e948098ad5830607bf416a9fd7833af5ad9b38dc0ccbb0570272b79e5 (REPEATABLE READ; the entire
walk describes exactly this chain state). Bounded to height 97899.
Bin widths: 500 (bins.json), 1000 (bins-1000.json).
Blocks aggregated: 97900.

Population: every canonical block. The run refuses unless canonical block
count, decoded-cert params count and height span all agree, so "blocks" is
the count of all canonical blocks in a bin, never a decoded-only subset.
Denominators are explicit: modelShaped is the T2-passing subset of blocks;
the DS-002 extinction rate (matched / scanned candidates) is not recomputed
here, it lives in DS-002 and is checked by scripts/ds003-reconcile.py.

Bin record format 2: each bin also carries poolConfig (per pool: blocks,
rank128k2048, rank128kAboveMin, and the rank-128 k histogram; the roadmap
14.3 per-pool boundary-hugging series) and tileSignatures (blocks per
(tileH, tileW, rank, officialBytes) signature, the roadmap 14.4 software
census; officialBytes is the certclass official sm90 fragment byte test).
poolConfig includes the genesis EMPTY certificate, so its blocks share the
poolShares denominator and sum to a bin's blocks; tileSignatures excludes
the genesis EMPTY certificate, so its counts sum to blocks minus
emptyClassBlocks. The pool-config-census script excludes EMPTY from every
denominator, so its bin-0 14.3 figures differ from poolConfig by the one
genesis block. Both fields are appended after every v1 field.

Matched-blocks overlay folded in from (each pinned by its own MANIFEST sha256):

- DS-002-weight-scan-v1  MANIFEST.md sha256 6d28d8f4e1ab0eb77fd54f3de4b3dbcfb86f2f05cd6ff81ec2d99f7d2e1292b4
- DS-002b-gemma-v1  MANIFEST.md sha256 9264ec242c4f3741e252f97f166d105f8257c415e685d30e2b70c06c8a321ecc
- DS-002b-o-tp48-v1  MANIFEST.md sha256 981fb4ba33f3a6456ae2215992355e7376f5f3c390596fab5fd07b466e4db26a

| File | sha256 |
|---|---|
| bins.json | 6037e0e16e644c4b08e0d363beda80f212db8743adf20a789672533c93253f7a |
| bins-1000.json | 3a85e16172e9179e1b17f5581b3adc7449bfaf905ec391a1305329aadaf84245 |
| summary.json | 559c9f13e5c158328833bda1fbc8d9c426eeb29acefb96881232bbf26bc77ae5 |
This dataset is append-only (roadmap SS6.5): corrections ship as a new
version directory with an errata note, never as an edit here.
