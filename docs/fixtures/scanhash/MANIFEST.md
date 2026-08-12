# scanhash golden vectors

Minted 2026-08-07 by `scripts/mint-hashb-vectors.py`
in `/opt/pearl_keshi/.venv-research` against the **reference implementation**:
py-pearl-mining built with maturin from the pinned Go-module copy of
`pearl-research-labs/pearl@v1.2.1` (the tree the decoder is pinned to).

Every tree-root vector was verified `MerkleTree(data, key).root ==
blake3(data, key)` (the keyed BLAKE3 of the **raw unpadded** input) with
the independent pip `blake3` package before writing. This corrects an
earlier planning note ("of the padded buffer"): the tree's zero padding is
internal leaf storage only, and the flat-digest form matches the miner's own
`blake3_digest(b_col_major, job_key)` (`zk-pow/src/ffi/mine.rs:402`).
Every job_key vector's preimages come from the reference `to_bytes()`
serializers (`zk-pow/src/api/proof_utils.rs:347,443,514` @ v1.2.1) and the
job_key was recomputed independently. Build sanity: mine+verify OK (root cc8c69365a89b4e7…).

Files:

| File | sha256 |
|---|---|
| `hashb-vectors.json` | `0d98e83db43fd5f6b6f27bf7b1bb98816465ad342e8e530c778f42ec096dfb9e` |

Consumed by `internal/chain/scanhash_test.go` (TestHashBGoldenVectors,
TestJobKeyGoldenVectors). Append-only once pinned: regenerate only together
with a fixture version bump and a re-run of the Go golden tests.
