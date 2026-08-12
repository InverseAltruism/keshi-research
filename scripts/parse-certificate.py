#!/usr/bin/env python3
"""Parse Pearl block certificate public data from raw block hex.

RESEARCH PROTOTYPE: the authoritative decoder is now the Go implementation in
internal/chain/certparams.go (Phase 6), whose golden vectors pin the same
fixtures this script validates. This script stays as the independent second
implementation: scripts/reproduce-certs.sh uses it so a third party can check
Keshi's published values without running any Keshi code.

Default mode reads the committed fixtures in docs/fixtures/node/ and needs no
node and no database; --hex/--json parse arbitrary raw-block hex for scripting.

    python3 scripts/parse-certificate.py
    ... | python3 scripts/parse-certificate.py --hex - --json

Correctness anchor: the genesis certificate must decode as an empty V1 whose
hash byte-reverses to a18d3093b7ff618f0cdd073fa3d10374e2e0105fe7ef53ff48b55f41c58dadd7.
If that holds, the offsets below are right.

Layout, constraints, and the fork schedule are documented in docs/pearl-notes.md
(sections "Certificate internals" and "The mining stack"). The roadmap that uses
this is docs/ROADMAP-certificate-intelligence.md.


Verified against pearl v1.2.1 source:
  wire/msgheaders.go: MsgHeader.PrlDecode reads MsgCertificate FIRST, then BlockHeader.
  wire/certificate.go: MsgCertificate = Version(4) | cert fields
    V1: Hash(32) | PublicData(164)          | ProofLen(4) | Proof
    V2: Hash(32) | PublicDataLen(4) | PData | ProofLen(4) | Proof

zk-pow/src/api/proof_utils.rs MiningConfiguration::from_bytes (52 B):
  [0:4] common_dim u32  [4:6] rank u16  [6:8] mma_type u16
  [8:14] rows_pattern   [14:20] cols_pattern
  [20:52] trailer = e u16 | top_k u16 | 28 zero bytes
PublicProofParams dense wire (164 B):
  mining_config(52) | hash_a(32) | hash_b(32) | hash_jackpot(32) | m(4) | n(4) | t_rows(4) | t_cols(4)
"""
import struct, glob, re

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def parse_pattern(b, o):
    """PeriodicPattern::to_bytes: data[2i]=factor-1, data[2i+1]=length-1, min_stride chained."""
    shape, min_stride = [], 1
    for i in range(3):
        factor = b[o + 2*i] + 1
        length = b[o + 2*i + 1] + 1
        stride = factor * min_stride
        shape.append((stride, length))
        min_stride = stride * length
    return shape

def pattern_span(shape):
    n = 1
    for _, length in shape:
        n *= length
    return n

def parse_public_data(pd):
    rows = parse_pattern(pd, 8)
    cols = parse_pattern(pd, 14)
    out = {
        'common_dim_k': u32(pd, 0),
        'rank_r':       u16(pd, 4),
        'mma_type':     u16(pd, 6),
        'rows_pattern': rows,
        'cols_pattern': cols,
        'tile_h':       pattern_span(rows),
        'tile_w':       pattern_span(cols),
        'tile_h_x_w':   pattern_span(rows) * pattern_span(cols),
        'moe_e':        u16(pd, 20),
        'moe_top_k':    u16(pd, 22),
        'trailer_rest_zero': all(x == 0 for x in pd[24:52]),
        'hash_a':       pd[52:84].hex(),
        'hash_b':       pd[84:116].hex(),
        'hash_jackpot': pd[116:148].hex(),
    }
    if len(pd) >= 164:
        out.update({'m': u32(pd, 148), 'n': u32(pd, 152),
                    't_rows': u32(pd, 156), 't_cols': u32(pd, 160)})
    return out

def parse_block(raw):
    o = 0
    ver = u32(raw, o); o += 4
    res = {'cert_version': ver}
    if ver == 0:
        res['note'] = 'null certificate'
        return res
    # V3 shares the V2 wire layout: only the noise-seed derivation changes.
    if ver not in (1, 2, 3):
        res['note'] = f'UNKNOWN cert version {ver}'
        return res
    res['cert_block_hash'] = raw[o:o+32].hex(); o += 32
    if ver == 1:
        pdl = 164
    else:
        pdl = u32(raw, o); o += 4
    pd = raw[o:o+pdl]; o += pdl
    res['public_data_len'] = pdl
    res['is_moe'] = pdl > 164
    res['proof_len'] = u32(raw, o)
    if pdl >= 164:
        res.update(parse_public_data(pd))
    return res

PENALTY_BASE_RANK = 128


def main():
    import argparse
    import json
    import sys

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--hex', dest='hexblock',
                    help="raw block (or raw certificate) hex, or '-' to read it "
                         'from stdin (blocks can exceed the argv size limit)')
    ap.add_argument('--json', action='store_true',
                    help='emit one JSON object (machine-readable, for reproduce-certs.sh)')
    args = ap.parse_args()

    if args.hexblock:
        hexblock = sys.stdin.read() if args.hexblock == '-' else args.hexblock
        r = parse_block(bytes.fromhex(hexblock.strip()))
        if args.json:
            json.dump(r, sys.stdout, default=str)
            print()
        else:
            for k, v in r.items():
                print(f"  {k:20} {v}")
        return

    for f in sorted(glob.glob('/opt/pearl_keshi/keshi/docs/fixtures/node/block-*.hex'),
                    key=lambda p: int(re.search(r'block-(\d+)', p).group(1))):
        h = int(re.search(r'block-(\d+)', f).group(1))
        raw = bytes.fromhex(open(f).read().strip())
        r = parse_block(raw)
        print(f"=== height {h}  ({len(raw)} bytes) ===")
        for k, v in r.items():
            vs = v[:32] + '…' if isinstance(v, str) and len(v) > 40 else v
            print(f"  {k:20} {vs}")
        if r.get('rank_r'):
            rk, k = r['rank_r'], r['common_dim_k']
            k_eff = k - (k % rk) if rk else 0
            print(f"  -> POST-FORK CHECK: rank {rk} {'PASSES' if rk >= PENALTY_BASE_RANK else 'REJECTED'} "
                  f"(needs >= {PENALTY_BASE_RANK}); bound multiplier {PENALTY_BASE_RANK}/{rk} = {PENALTY_BASE_RANK/rk:.4f}; "
                  f"k_eff={k_eff}; k>=16r? {k >= 16*rk}")
        print()


if __name__ == '__main__':
    main()
