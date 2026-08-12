#!/usr/bin/env python3
"""Live certificate census across the rank-penalty fork boundary (96,251).

Pulls raw blocks from our own Blockbook (loopback), parses certificate public
data per the layout validated in keshi/scripts/parse-certificate.py, attributes
pools via coinbase payout address, and summarizes pre- vs post-fork.
"""
import json, struct, sys, urllib.request
from collections import Counter, defaultdict

BB = "http://127.0.0.1:9131"
FORK = 96251

POOLS = {
    "prl1p50ltku2jjcwdxh4nzjrw98nwdswdn25qdkr2fdtw8hsq3qu9cdhscchnnm": "PearlHash",
    "prl1puv0gqv4x0wd0ylwz086y3sqrg4a6umza9r08aecehjrmdqq7mctsmqaqsh": "Kryptex",
    "prl1pl7ch5q7f225sumuutpw9u466auzellprh432z4vd9pfzvnfqmysq2f3xjw": "PearlFortune",
    "prl1pksfzrn8g760gmcqy65a4tl30eyv25eksl5sf8y332kes6fwx9pjszgymmz": "HeroMiners",
    "prl1pspr7jpw2a6ed0mw0h03zmu7huxnfjh46j3lzgsrez0ysvh7mcq4q4ztsxp": "LuckyPool",
    "prl1pn7pk3x955mp788u70qslde858x5xqu80z7lklpeuz2ln724ennvqgz3e57": "PearlNet",
}

def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def parse_pattern(b, o):
    shape, min_stride = [], 1
    for i in range(3):
        factor = b[o + 2*i] + 1
        length = b[o + 2*i + 1] + 1
        stride = factor * min_stride
        shape.append((stride, length))
        min_stride = stride * length
    return shape

def span(shape):
    n = 1
    for _, l in shape: n *= l
    return n

def parse_cert(raw):
    o = 0
    ver = u32(raw, o); o += 4
    # V3 shares the V2 wire layout: only the noise-seed derivation changes.
    if ver not in (1, 2, 3): return {"cert_version": ver, "err": "unknown version"}
    o += 32  # cert block hash
    if ver == 1: pdl = 164
    else: pdl = u32(raw, o); o += 4
    pd = raw[o:o+pdl]
    r = {"cert_version": ver, "pdl": pdl, "is_moe": pdl > 164}
    if pdl >= 164:
        rows, cols = parse_pattern(pd, 8), parse_pattern(pd, 14)
        r.update(k=u32(pd, 0), rank=u16(pd, 4), mma=u16(pd, 6),
                 h=span(rows), w=span(cols),
                 rows=rows, cols=cols,
                 moe_e=u16(pd, 20), moe_top_k=u16(pd, 22),
                 reserved_zero=all(x == 0 for x in pd[24:52]),
                 m=u32(pd, 148), n=u32(pd, 152))
    return r

def official_fingerprint(r):
    # unmodified official stack: rank in {64,128}, h*w == 128, m >= 1024
    return r.get("rank") in (64, 128) and r.get("h", 0) * r.get("w", 0) == 128 and r.get("m", 0) >= 1024

def main(lo, hi):
    out = []
    for h in range(lo, hi + 1):
        try:
            bh = get(f"{BB}/api/v2/block-index/{h}")["blockHash"]
            raw = bytes.fromhex(get(f"{BB}/api/v2/rawblock/{bh}")["hex"])
            blk = get(f"{BB}/api/v2/block/{bh}")
            cb = blk["txs"][0]
            addr = (cb["vout"][0].get("addresses") or ["?"])[0]
            pool = POOLS.get(addr, "unattributed:" + addr[:14])
            r = parse_cert(raw)
            r.update(height=h, pool=pool)
            out.append(r)
        except Exception as e:
            print(f"height {h}: ERROR {e}", file=sys.stderr)
    json.dump(out, open(sys.argv[3], "w"), default=str)

    pre  = [r for r in out if r["height"] <  FORK]
    post = [r for r in out if r["height"] >= FORK]
    def dist(rows, key):
        return dict(Counter(r.get(key) for r in rows))
    print(f"blocks parsed: {len(out)} (pre-fork {len(pre)}, post-fork {len(post)})")
    for name, rows in (("PRE ", pre), ("POST", post)):
        print(f"\n== {name} rank dist:", dist(rows, "rank"))
        print(f"== {name} k dist:   ", dist(rows, "k"))
        print(f"== {name} tile h*w: ", dict(Counter(r.get('h',0)*r.get('w',0) for r in rows)))
        print(f"== {name} m dist:   ", dist(rows, "m"))
        print(f"== {name} n dist:   ", dist(rows, "n"))
        print(f"== {name} pools:    ", dist(rows, "pool"))
        print(f"== {name} official-fingerprint blocks: {sum(1 for r in rows if official_fingerprint(r))}/{len(rows)}")
        print(f"== {name} moe_e nonzero: {sum(1 for r in rows if r.get('moe_e'))}")
        print(f"== {name} reserved-nonzero: {sum(1 for r in rows if r.get('reserved_zero') is False)}")
    # violations of the new rule, post-fork
    bad = [r for r in post if r.get("rank", 0) < 128]
    print(f"\npost-fork rank<128 (would be invalid): {len(bad)}")
    # per-pool rank crosstab post-fork
    x = defaultdict(Counter)
    for r in post: x[r["pool"]][r.get("rank")] += 1
    print("\nPOST per-pool rank crosstab:")
    for p, c in sorted(x.items()):
        print(f"  {p:24} {dict(c)}")
    x = defaultdict(Counter)
    for r in pre: x[r["pool"]][r.get("rank")] += 1
    print("\nPRE per-pool rank crosstab:")
    for p, c in sorted(x.items()):
        print(f"  {p:24} {dict(c)}")

if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
