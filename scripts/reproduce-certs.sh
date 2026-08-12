#!/usr/bin/env bash
# reproduce-certs.sh: third-party reproduction of Keshi's certificate corpus.
#
# For a list of heights: fetch the raw block from YOUR OWN pearld, decode the
# certificate with the Python reference decoder (scripts/parse-certificate.py's
# layout), and diff the result against what a Keshi API reports. Nothing here
# trusts Keshi: the block bytes come from your node, the decode runs locally.
#
#   PEARL_RPC_URL=http://127.0.0.1:44107 \
#   PEARL_RPC_USER=... PEARL_RPC_PASS=... \
#   KESHI_API=https://keshi.loeffler.house \
#   scripts/reproduce-certs.sh 71935 91630 94748
#
# Requirements: curl, jq, python3. Your pearld needs txindex and plain-HTTP or
# TLS RPC reachable at PEARL_RPC_URL.
#
# Exit code: 0 when every height matches, 1 otherwise.
set -euo pipefail

PEARL_RPC_URL="${PEARL_RPC_URL:-http://127.0.0.1:44107}"
KESHI_API="${KESHI_API:-http://127.0.0.1:8081}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

[[ $# -ge 1 ]] || { echo "usage: $0 HEIGHT [HEIGHT...]" >&2; exit 1; }
: "${PEARL_RPC_USER:?set PEARL_RPC_USER}"
: "${PEARL_RPC_PASS:?set PEARL_RPC_PASS}"

rpc() {
    curl -sf --user "${PEARL_RPC_USER}:${PEARL_RPC_PASS}" \
        -H 'Content-Type: application/json' \
        -d "{\"jsonrpc\":\"1.0\",\"id\":\"reproduce\",\"method\":\"$1\",\"params\":$2}" \
        "$PEARL_RPC_URL" | jq -r '.result'
}

fail=0
for height in "$@"; do
    hash="$(rpc getblockhash "[${height}]")"
    rawhex="$(rpc getblock "[\"${hash}\", 0]")"

    # Local decode: the certificate is the raw block's prefix. Hex goes via
    # stdin: raw blocks can exceed the argv size limit.
    local_json="$(printf '%s' "$rawhex" \
        | python3 "${SCRIPT_DIR}/parse-certificate.py" --hex - --json)"

    # Keshi's view of the same block.
    keshi_json="$(curl -sf "${KESHI_API}/v1/blocks/${height}" \
        | jq -c '.block.certificate.params
                 | {k, rank, tileH, tileW, m, n, tRows, tCols, hashA, hashB}')"
    mine_json="$(jq -cn --argjson j "$local_json" \
        '{k: $j.common_dim_k, rank: $j.rank_r,
          tileH: $j.tile_h, tileW: $j.tile_w,
          m: $j.m, n: $j.n, tRows: $j.t_rows, tCols: $j.t_cols,
          hashA: $j.hash_a, hashB: $j.hash_b}')"

    if [[ "$keshi_json" == "$mine_json" ]]; then
        echo "height ${height}: MATCH"
    else
        echo "height ${height}: MISMATCH" >&2
        echo "  local: ${mine_json}" >&2
        echo "  keshi: ${keshi_json}" >&2
        fail=1
    fi
done
exit "$fail"
