# DS-006-coverage-closure-v1 manifest

Produced by scripts/prereg3-emit.py from prereg3-scan.py outputs; PREREG-003 frozen at d2b83c55626865a1c32254e893fb731307da889c (recorded in summary.json as prereg3Commit), method by reference from PREREG-002 at d4cb529b8602f1f73bab681f4ae428ba6cfd3fff.
Generated: 2026-08-11T00:00:00Z

Populations: registered in PREREG-003 section 2 by exact filter over the pinned source datasets below. cells.json (the R1 enumeration) and searched-cells.json (the already-searched shape list) were committed before any hashing; their sha256 is pinned in summary.json and here. draws.json records the registered populations, the seeded positive-control draws, and each run's realized height list.

Row format is the DS-002 results schema (height, hash, candidate, layerIndex, shard, match), sorted by height, candidate, layer, shard. In variant runs (v1, p1, p2, colparallel buffer sets) the candidate string names the standard family; the authoritative variant label is the run's variant field in summary.json, and buffer construction is recorded per buffer set under buffers (derivedFrom) with per-file sha256. Every zero is bounded by its exact cell list, buffer set, revision pins, and block population; no zero is proof of absence.

Population sources pinned (each by its committed MANIFEST sha256):

- DS-001-classification-v1  MANIFEST.md sha256 3dc293e10f8c1a3e3a93a394f37812fefd8c49b6a2d3d5661e73d864d961783a
- DS-002-weight-scan-v1  MANIFEST.md sha256 6d28d8f4e1ab0eb77fd54f3de4b3dbcfb86f2f05cd6ff81ec2d99f7d2e1292b4
- DS-002b-gemma-v1  MANIFEST.md sha256 9264ec242c4f3741e252f97f166d105f8257c415e685d30e2b70c06c8a321ecc
- DS-002b-o-tp48-v1  MANIFEST.md sha256 981fb4ba33f3a6456ae2215992355e7376f5f3c390596fab5fd07b466e4db26a

| File | sha256 |
|---|---|
| cells.json | dc3db506d2e585b803935ca76d1d6559c9432b96aed125742b6eeda73e9a36b7 |
| searched-cells.json | e726983658d43c7a70256caa1aaa63f3b6b26cb7c8f00ac702b4649db1b345bf |
| draws.json | 11310c5bfb34ca96b728026f254aa82ecd8de320e305fd55163eb34c674d86c6 |
| runs/colparallel-70b-o-tp2.jsonl.gz | fcb11bcb286b87d7247897c98070fed3b189e3a117bca211e8708540f351aa3b |
| runs/gemma-o-k16384.jsonl.gz | 8268b75d2c724967652a5c7260c6e0072d3c4451dfd7933cd8bafb4c7fa877a2 |
| runs/qwen3-o-tp4.jsonl.gz | f8013439fd827dd7112c0260407f26d538404ffdd51251da3be4dda04c2e64e6 |
| runs/r2-ctrl-standard.jsonl.gz | 6f715fe968f33765362f2c1d5b7178a209fed2956a744bc15521fb5b81bac65d |
| runs/r2-ctrl-v1.jsonl.gz | c456a0028d0a569ffec2a134ac80876ada3434a8e6565250bb80995722ce5cce |
| runs/r2-v1-pop-70b.jsonl.gz | 4d02f03e7e9c556f96e944b05fd6a57c22332393f081b2ba5e003e6193d0f79f |
| runs/r2-v1-pop-8b.jsonl.gz | 6358249f198507e60f46ffac8fca8ef704efae4fb5ee1705af66ea3bf5e9afa3 |
| runs/r3-ctrl-p1.jsonl.gz | bbf3f0c410093ab8053e91913608015d1934a00087d2709d2358b0f4c3ac8f3d |
| runs/r3-ctrl-p2.jsonl.gz | bbf3f0c410093ab8053e91913608015d1934a00087d2709d2358b0f4c3ac8f3d |
| runs/r3-ctrl-standard.jsonl.gz | 52081a81beb024bbb760f070893ea1c458d676c0f98e34b091148ece585ac8b3 |
| runs/r3-p1-pop.jsonl.gz | 3e1196ad3496664f5968c26f998b969c2aa92cfd420506f9a2b69005618988f2 |
| runs/r3-p2-pop.jsonl.gz | 3e1196ad3496664f5968c26f998b969c2aa92cfd420506f9a2b69005618988f2 |
| runs/r4-redhat-70b.jsonl.gz | 85f30dc914e4a9b225c152d9ce788a0dc4816071e2805a244c8a57b33c8014e0 |
| runs/r4-redhat-8b.jsonl.gz | 201cb7b181b7156f476d34e44605c691903407dd3264a47009d645bd4a717594 |
| summary.json | 4ece19831d4c7f2b6835d7862a192f9fb102db25affa740601b7395afd26b930 |
This dataset is append-only: corrections ship as a new version directory with an errata note, never as an edit here.
