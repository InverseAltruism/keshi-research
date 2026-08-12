# DS-008 shape-sweep manifest

Produced by scripts/shape-sweep-nonpearl.py (sha256
a4d1fd10edad489d729769d6504100311195addb13fb538e334918878ef4e6f7) and
scripts/nonllm-shape-check.py (sha256
ae22d6c5a051f9aee9f8d409d11fc1b36f49ec400f7c6836e3a21f60b98528ac), repo
commit fa02e5cb9011e8a5c400c881f6394c61babeec5c, per roadmap C4
(PLAN-002 SS9.3 item 5: ended vs moved). Written up as OBS-010.
Generated: 2026-08-10T18:22:22Z

Population: every non-empty DS-001 block, heights 1-96,405, n = 96,405
(the genesis EMPTY certificate is excluded). Both tools read the same
two frozen, committed inputs and are byte-deterministic given them; the
committed reports are the tools' stdout verbatim.

Inputs pinned by sha256:

- docs/research/shape-dictionary-v1.json  sha256 c8c445e7ce8b303084612e31e98c104185677ecd7afe1166d124995b5249f89b
  (generated 2026-08-09T21:43:01+00:00; 36 checkpoints: 4
  pearl-reference, 32 non-pearl targets; 603 grid entries; floors
  minN 256, minK 1,024, tp in {1, 2, 4, 8})
- DS-001-classification-v1  blocks.jsonl.gz sha256 ce741aad7f00e2450f0b5e34b59fa33fcf68b0c51f2718407a5e6054f7db4a04
  (equals the sha256 in that dataset's MANIFEST.md, itself sha256
  3dc293e10f8c1a3e3a93a394f37812fefd8c49b6a2d3d5661e73d864d961783a)

The non-LLM screen additionally reads nine checkpoints' safetensors
headers over HTTP range requests at the revision shas pinned inside
scripts/nonllm-shape-check.py; nonllm.json records each label, repo,
revision, and matched linear-tensor count.

| File | sha256 |
|---|---|
| sweep.json | 6a2860799999283d65eeec1f53777e500adf512f7a418c32719f7367c33f028b |
| sweep-report.txt | e07044f2120fafb5af9073803b960c0159c2d0300b2acd9e7d7e772bc3664dd5 |
| nonllm.json | f16f2bb77a3c53f83363ddc5716d162621dad1c5b43975f373a51c43d2406352 |
| nonllm-report.txt | aff674ab42c7f142b923e979578a366431cd4465f5bbbce1f5c5849a0596bc54 |
| summary.json | fa81add25d2aa4f8cbfe939e3162e707811f35908a00ff6c0b1d56aee2ad11d5 |
This dataset is append-only (roadmap SS6.5): corrections ship as a new
version directory with an errata note, never as an edit here.
