# Dataset licence and schema

## Licence

The repository's code is MIT (see `/LICENSE`). The research datasets under
`docs/research/datasets/` are separately licensed **CC BY 4.0**
(https://creativecommons.org/licenses/by/4.0/): reuse freely with
attribution. Suggested citation:

> InverseAltruism (Keshi), "DS-002: weight-provenance scan over the Pearl
> certificate corpus", 2026. https://doi.org/10.5281/zenodo.21863620

The named author is the project's sole author and maintainer; "Keshi" is
the project, not a second party. Cite the concept DOI rather than the
repository URL where the citation needs to be stable: the DOI always
resolves to the latest deposited version, and a repository can move.

Zenodo deposits of dataset versions carry the same licence and a DOI; cite
the DOI where one exists. The underlying facts (block headers, certificate
public data) are public blockchain data; what these datasets add is the
frozen population selection, derived job keys, and the exhaustive pair
results.

## Data availability

Small artifacts (`extract.jsonl.gz`, `summary.json`, `MANIFEST.md`,
`extract-meta.json`) verify every headline number and are fetchable as
pinned blobs. The full pair results ship in-repo (append-only) and as a
zipped Zenodo deposit. `scripts/ds002-reproduce.sh` regenerates every
published table from the dataset alone: no API, no database, no host
assumptions.

## Schema

All files are newline-delimited JSON, gzip-compressed where named `.gz`.
Hex strings are lowercase. Block `hash` is display-order (big-endian, as
explorers show it).

### extract.jsonl.gz (one record per selected block)

| Field | Type | Meaning |
|---|---|---|
| `height` | int | Canonical block height |
| `hash` | hex string | Block id, display order |
| `pool` | string | Coinbase-label attribution ("unattributed" when unknown) |
| `attributed` | bool | Whether `pool` is a labeled pool |
| `era` | string | Consensus era of the height (pre-moe / moe / dense-only / rank-penalty) |
| `class` | string | Frozen classifier verdict (OFFICIAL_CONSISTENT / MODEL_SHAPED_CUSTOM / CUSTOM) |
| `control` | bool | True for negative-control blocks (first N CUSTOM blocks in (height, hash) order) |
| `jobKey` | hex string (32 B) | `blake3(header[0:76] ‖ mining_config[0:52])`, derivation hard-checked per block |
| `hashB` | hex string (32 B) | The certificate's weight-side commitment |
| `m`, `n`, `k` | int | Declared GEMM dimensions |
| `candidates` | string array | Candidate ids (`model/layer/tp`) this block is eligible for; empty array = recorded but filtered by the run's model/tp selection (counted as unscanned) |

### results/*.jsonl.gz (one record per block x buffer pair; every pair, never only hits)

| Field | Type | Meaning |
|---|---|---|
| `height` | int | Block height |
| `hash` | hex string | Block id, display order |
| `candidate` | string | Candidate id (`model/layer/tp`) |
| `layerIndex` | int | Transformer layer index of the buffer |
| `shard` | int | Tensor-parallel shard index |
| `match` | bool | `blake3(buffer, key=jobKey) == hashB`, byte-exact |

One part file per (candidate id, layerIndex, shard) buffer.

### summary.json

| Field | Type | Meaning |
|---|---|---|
| `toolVersion` | string | Build that produced the run (`<go-sha>-w<web-sha>`) |
| `preregCommit`, `preregFrozen` | string, bool | PREREG-002 freeze reference compiled into the tool |
| `decoderVersion` | int | Certificate decoder version of the corpus rows |
| `models` | array | Per model: HF repo, pinned revision sha, buffer count |
| `candidateBlocks` | object | Candidate id to eligible-block count |
| `controlBlocks` | int | Negative-control block count |
| `pairsScanned`, `matches` | int | Totals over all part files |
| `snapshotTip` | int, optional | Corpus tip at extract time (absent = run predates the field; see ERRATA-POLICY) |
| `toHeight` | int, optional | Upper bound the scan was pinned to |
| `unscannedCandidates` | int, optional | Blocks recorded with an empty candidate list (filtered by model/tp) |
| `unhashedBlocks` | int | Blocks none of whose candidate ids had a buffer in this run's weights root |
| `unhashedByCandidate` | object, optional | Candidate id to block count, for ids with no buffer |
| `bufferSha256` | object | Buffer path to sha256 |

### extract-meta.json

Extract-stage sidecar carrying `snapshotTip`, `toHeight`,
`candidateBlocks`, `controlBlocks`, `unscannedCandidates`,
`includeModelShaped`. Present for runs after DS-002; its values are folded
into `summary.json` by the hash stage.

### MANIFEST.md

Human-readable: tool and decoder versions, prereg freeze commit, coverage
paragraph (tip, bounds, unscanned and unhashed counts), weight revisions,
and the sha256 of every file in the dataset. The MANIFEST is the integrity
root: verify files against it before using the dataset.
