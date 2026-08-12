# DS-007-stratified-control-v1 manifest

Produced by scripts/prereg3-emit.py from prereg3-scan.py outputs; PREREG-003 frozen at d2b83c55626865a1c32254e893fb731307da889c (recorded in summary.json as prereg3Commit), method by reference from PREREG-002 at d4cb529b8602f1f73bab681f4ae428ba6cfd3fff.
Generated: 2026-08-11T00:00:00Z

R5 era-stratified negative control, registered in PREREG-003 section 2. draw.json records the seeds, the excluded shape list (the committed cells.json plus searched-cells.json shapes), and the per-stratum draws; eligibility is shape-only by design. Controls are hashed with the no-shape-filter mode against every listed buffer set; a shape-mismatched buffer cannot match, which is the canary. Any match here voids the affected run per PREREG-003 section 4 rule 3.

Population sources pinned (each by its committed MANIFEST sha256):

- DS-001-classification-v1  MANIFEST.md sha256 3dc293e10f8c1a3e3a93a394f37812fefd8c49b6a2d3d5661e73d864d961783a

| File | sha256 |
|---|---|
| draw.json | 49fd1bb1da14229388804d7f50105ded94996f902233815cc6c78e5a50139534 |
| runs/r5-ctrl-70b.jsonl.gz | f82d3f4b77bb14c8bd0c0a015dbc75ab39d702d427eba63fc97b4c5f233ada13 |
| runs/r5-ctrl-8b.jsonl.gz | 9db49eecb49903782a239ab5f699292a197a5d5f8a5b3cb9c3c0107ab9145daf |
| runs/r5-ctrl-colpar.jsonl.gz | d8c46ef638561afc2df899345c02afbd8732a68521c46c25de5b331734517863 |
| runs/r5-ctrl-gemma.jsonl.gz | a1618cc275668921f6afa31bb839c955f6565a6f1f4a66762ebbf434de504299 |
| runs/r5-ctrl-gemmak16.jsonl.gz | 0f6731b1bc637bca77d87119fa830b80f400cf6b0bf453eb0e4faf3e1f28f3fa |
| runs/r5-ctrl-otp48.jsonl.gz | 1c26312cea0bd3d6c1376fb4e9687be3d50f85f299025783c5efd0f50fcc57b8 |
| runs/r5-ctrl-qwen3.jsonl.gz | 65e37615d3d91b40a6a442e1eda437ba573b349b0bae1da44360a56c604845ab |
| summary.json | d198c1691398df96351bf1f134dd12bc904f86046bb2bb02ccb37206bd9b6102 |
This dataset is append-only: corrections ship as a new version directory with an errata note, never as an edit here.
