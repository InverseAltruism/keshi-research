# DS-003 network-state manifest

Produced by keshictl network-state (2cbc61a7f302-wb1bbc97), decoder v1, per PLAN-002 SS9.1.
Generated: 2026-08-09T21:10:24Z

Snapshot: canonical tip height 97710, hash b9767036f910907470174c94c65a70986e17fb1045c6ce8b7d356c4b3f3e25eb (REPEATABLE READ; the entire
walk describes exactly this chain state). Bounded to height 97710.
Bin widths: 500 (bins.json), 1000 (bins-1000.json).
Blocks aggregated: 97711.

Population: every canonical block. The run refuses unless canonical block
count, decoded-cert params count and height span all agree, so "blocks" is
the count of all canonical blocks in a bin, never a decoded-only subset.
Denominators are explicit: modelShaped is the T2-passing subset of blocks;
the DS-002 extinction rate (matched / scanned candidates) is not recomputed
here, it lives in DS-002 and is checked by scripts/ds003-reconcile.py.

Matched-blocks overlay folded in from (each pinned by its own MANIFEST sha256):

- DS-002-weight-scan-v1  MANIFEST.md sha256 6d28d8f4e1ab0eb77fd54f3de4b3dbcfb86f2f05cd6ff81ec2d99f7d2e1292b4
- DS-002b-gemma-v1  MANIFEST.md sha256 9264ec242c4f3741e252f97f166d105f8257c415e685d30e2b70c06c8a321ecc
- DS-002b-o-tp48-v1  MANIFEST.md sha256 981fb4ba33f3a6456ae2215992355e7376f5f3c390596fab5fd07b466e4db26a

| File | sha256 |
|---|---|
| bins.json | fe44d024a704f40ebf036860143038a5f5813b28820beaa0c14fd3647957dc07 |
| bins-1000.json | 7b6c60b5cf23fbb3123d2dd88435e9cf9d475fd365e87eae65e3ede4aedb172b |
| summary.json | 9541b0e8c57eca5526606ab505ec4e61a2f0553b44c456f2914a65b248f117c8 |
This dataset is append-only (roadmap SS6.5): corrections ship as a new
version directory with an errata note, never as an edit here.
