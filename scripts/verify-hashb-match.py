#!/usr/bin/env python3
"""Independently verify one weight-provenance match, straight from the chain.

This is the third-party reproduction path for a `keshictl scan-weights`
result (PREREG-002 §4). It trusts **none** of Keshi's Go code and never
touches Keshi's database: the block is fetched as raw bytes from a Blockbook
(ours by default, or any other via --blockbook), the certificate and header
are parsed here by offset arithmetic, `job_key` is derived with the
independent pip `blake3` package, and the weight buffer is read off disk.

The header slice is self-proving: SHA256d(header) must reproduce the block
id, which the script asserts before deriving anything from it.

    job_key = blake3(header[0:76] ‖ public_data[0:52])          (unkeyed)
    hash_b  = public_data[84:116]                                (on-chain)
    match  ⟺ blake3(weight_bytes, key=job_key) == hash_b

Certificate framing (pearl@v1.2.1 `node/wire`): the certificate is
serialized BEFORE the header, and V1 carries a fixed 164-byte public data
while V2 length-prefixes it.

Usage (in the research venv, which has pip blake3):
    verify-hashb-match.py --height 22816 \\
        --buffer /opt/pearl_keshi/weights/Llama-3.3-70B/gate_up_fused.tp1.s0.L000.bin

Exit code 0 on a verified match, 2 on a mismatch, 1 on any error.
"""

import argparse
import hashlib
import json
import struct
import sys
import urllib.request

import blake3

PUBLIC_DATA_V1_SIZE = 164
WIRE_HEADER_SIZE = 108
INCOMPLETE_HEADER_SIZE = 76
MINING_CONFIG_SIZE = 52


def fetch_raw_block(blockbook: str, height: int) -> tuple[str, bytes]:
    bh = json.load(
        urllib.request.urlopen(f"{blockbook}/api/v2/block-index/{height}", timeout=30)
    )["blockHash"]
    hexstr = json.load(
        urllib.request.urlopen(f"{blockbook}/api/v2/rawblock/{bh}", timeout=120)
    )["hex"]
    return bh, bytes.fromhex(hexstr)


def split_certificate(raw: bytes) -> tuple[int, bytes, int]:
    """Return (cert_version, public_data, cert_size)."""
    version = struct.unpack("<I", raw[0:4])[0]
    if version == 1:
        pub = raw[36 : 36 + PUBLIC_DATA_V1_SIZE]
        proof_len = struct.unpack("<I", raw[200:204])[0]
        return version, pub, 204 + proof_len
    # V3 (salted noise-seed fork) is byte-identical to V2 on the wire; only the
    # noise-seed derivation changes, and the salt is never serialized. hash_b is
    # still the raw keyed blake3 of B^T at public-data offset [84:116].
    if version in (2, 3):
        pd_len = struct.unpack("<I", raw[36:40])[0]
        pub = raw[40 : 40 + pd_len]
        proof_len = struct.unpack("<I", raw[40 + pd_len : 44 + pd_len])[0]
        return version, pub, 44 + pd_len + proof_len
    raise SystemExit(f"unknown certificate version {version}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--buffer", required=True, help="candidate weight .bin")
    ap.add_argument("--blockbook", default="http://127.0.0.1:9131")
    args = ap.parse_args()

    block_hash, raw = fetch_raw_block(args.blockbook, args.height)
    version, pub, cert_size = split_certificate(raw)
    header = raw[cert_size : cert_size + WIRE_HEADER_SIZE]

    block_id = hashlib.sha256(hashlib.sha256(header).digest()).digest()
    if block_id[::-1].hex() != block_hash:
        print("FAIL: SHA256d(header) does not reproduce the block id; "
              "the certificate/header split is wrong", file=sys.stderr)
        return 1

    k = struct.unpack("<I", pub[0:4])[0]
    rank = struct.unpack("<H", pub[4:6])[0]
    m = struct.unpack("<I", pub[148:152])[0]
    n = struct.unpack("<I", pub[152:156])[0]
    hash_b = pub[84:116]

    job_key = blake3.blake3(
        header[:INCOMPLETE_HEADER_SIZE] + pub[:MINING_CONFIG_SIZE]
    ).digest()

    with open(args.buffer, "rb") as f:
        buf = f.read()
    computed = blake3.blake3(buf, key=job_key).digest()

    print(f"height {args.height}  block {block_hash}")
    print(f"certificate v{version}   declared m {m}  n {n}  k {k}  rank {rank}")
    print(f"header self-check       : SHA256d(header) == block id  ✓")
    print(f"job_key                 : {job_key.hex()}")
    print(f"buffer                  : {args.buffer} ({len(buf):,} bytes)")
    print(f"on-chain hash_b         : {hash_b.hex()}")
    print(f"blake3(buffer, job_key) : {computed.hex()}")
    print()
    if computed == hash_b:
        print("MATCH: the operand this block committed IS these weight bytes.")
        print("Proves committed-operand identity only: not that inference ran,")
        print("that a customer was served, or that the computation was fresh.")
        return 0
    print("NO MATCH")
    return 2


if __name__ == "__main__":
    sys.exit(main())
