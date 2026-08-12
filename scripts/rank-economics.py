#!/usr/bin/env python3
"""Rank-escalation economics: the measurement behind Open question 4.

Read-only over the frozen datasets. Produces the numbers that decide whether
the 128 -> 256 -> 1024 rank escalation bought a mining advantage (economic) or
bought nothing on reward-per-MAC (neutral). It does NOT assert a mechanism; it
prints the source-derived reward-per-MAC(r) factors and the measured trajectory
side by side.

Three things are computed:

  1. Reward-per-MAC(r), symbolic. The accept bound per jackpot attempt is
     target * h * w * dot_product_length pre-fork
     (zk-pow/src/v1/api/sanity_checks.rs:86-102 and
      zk-pow/src/api/sanity_checks.rs:190-192,229-231), and the real work of one
     attempt is h * w * dot_product_length int8 MACs
     (compute_jackpot loop over the full contraction,
      zk-pow/src/circuit/chip/jackpot/helper.rs:21-33). So P(win)/attempt and
     MACs/attempt carry the SAME h*w*dpl factor and it cancels: expected MACs to
     find a block is 2^256 / target, independent of r, k, h, w. Post-fork the
     bound gains a 128/rank multiplier
     (penalized_adjustment_factor, sanity_checks.rs:194-196), so reward-per-MAC
     becomes proportional to 128/r: neutral at 128, 8x worse at 1024.

  2. The k-gating test the economic reading depends on. Economic claim: a higher
     rank is REQUIRED to declare a higher k, because k <= 4r^2
     (sanity_checks.rs:35). This script computes, per block, the MINIMUM legal
     rank for that block's k under k <= 4r^2 AND the global cap k <= 2^16
     (sanity_checks.rs:33), and reports how often the declared rank exceeds it.
     Decisive constant: 4 * 128^2 == 2^16, so rank 128 already unlocks the
     largest legal k and no k ever requires rank > 128.

  3. The per-pool boundary-hugging split post-fork: share at the exact legal
     minimum (rank 128 and k = 16*rank = 2048) versus rank 128 at high k.

Env / args:
  KESHI_DS001_DIR   DS-001 classification dataset dir (default: committed copy)
  KESHI_DS003_DIR   DS-003 network-state dataset dir  (default: committed copy)

Exit 0 always; this is a measurement, not a check.
"""

import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASETS = HERE.parent / "docs" / "research" / "datasets"
DS001 = Path(os.environ.get("KESHI_DS001_DIR", str(DATASETS / "DS-001-classification-v1")))
DS003 = Path(os.environ.get("KESHI_DS003_DIR", str(DATASETS / "DS-003-network-state-v1")))

# Consensus constants, from source (cited in the module docstring).
PENALTY_BASE_RANK = 128
K_GLOBAL_CAP = 1 << 16          # k <= 2^16
RANK_PENALTY_FORK = 96251       # node/chaincfg/params.go:353
MOE_FORK = 71935
DENSE_ONLY_FORK = 91630
LEGAL_RANKS = [32, 64, 128, 256, 512, 1024]


K_GLOBAL_CAP = 1 << 16  # k <= 2^16 (sanity_checks.rs)


def min_legal_rank_for_k(k: int) -> int:
    """Smallest legal rank r with k <= 4r^2 and k within the global cap.

    Returns the lowest power-of-two rank in [32,1024] that admits this k. The
    global cap k <= 2^16 is reached at r = 128 (4*128^2 == 2^16), so any k a
    block can legally carry is admissible at rank 128. A k above the global
    cap is not legally admissible at any rank; return None so corrupt data
    cannot silently deflate the over-ranked count.
    """
    if k > K_GLOBAL_CAP:
        return None
    for r in LEGAL_RANKS:
        if k <= 4 * r * r:
            return r
    return LEGAL_RANKS[-1]


def reward_per_mac_factor(rank: int, post_fork: bool) -> float:
    """Reward-per-real-MAC relative to the base rank, from the bound arithmetic.

    Pre-fork the bound per attempt equals the real work per attempt, so the
    ratio is 1 for every rank. Post-fork the bound carries a 128/rank multiplier
    while the real work is unchanged, so the ratio is 128/rank.
    """
    if not post_fork:
        return 1.0
    return PENALTY_BASE_RANK / rank


def load_ds003_bins():
    with open(DS003 / "bins.json") as f:
        return json.load(f)


def iter_ds001_blocks():
    with gzip.open(DS001 / "blocks.jsonl.gz", "rt") as f:
        for line in f:
            yield json.loads(line)


def era(height: int) -> str:
    if height < 52000:
        return "0-51999 (early)"
    if height < MOE_FORK:
        return "52000-71934 (pre-MoE)"
    if height < DENSE_ONLY_FORK:
        return "71935-91629 (MoE window)"
    if height < RANK_PENALTY_FORK:
        return "91630-96250 (dense-only)"
    return "96251+ (post rank-penalty)"


ERAS = [
    "0-51999 (early)",
    "52000-71934 (pre-MoE)",
    "71935-91629 (MoE window)",
    "91630-96250 (dense-only)",
    "96251+ (post rank-penalty)",
]


def section(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def report_reward_per_mac():
    section("1. Reward-per-real-MAC(r), from the bound arithmetic")
    print("Decisive constant: 4 * 128^2 =", 4 * 128 * 128,
          "== 2^16 =", K_GLOBAL_CAP, "->", 4 * 128 * 128 == K_GLOBAL_CAP)
    print()
    print(f"{'rank':>6} | {'pre-fork':>10} | {'post-fork':>10}")
    print("-" * 32)
    for r in LEGAL_RANKS:
        pre = reward_per_mac_factor(r, post_fork=False)
        post = reward_per_mac_factor(r, post_fork=True)
        print(f"{r:>6} | {pre:>10.4f} | {post:>10.4f}")
    print()
    print("Pre-fork: reward per real MAC is 1.0 for every rank (work-normalized).")
    print("Post-fork: reward per real MAC = 128/rank; rank 1024 is 8x worse.")


def report_k_gating():
    section("2. k-gating test: is a higher rank REQUIRED to declare higher k?")
    over_ranked = Counter()          # era -> blocks whose rank > min legal for k
    total_highrank = Counter()       # era -> blocks with rank > 128
    anomalous_k = Counter()          # era -> blocks with k above the global cap
    k_by_minrank = defaultdict(Counter)
    for b in iter_ds001_blocks():
        r = b["rank"]
        k = b["k"]
        if r <= 0 or k <= 0:
            continue
        e = era(b["height"])
        need = min_legal_rank_for_k(k)
        if need is None:
            anomalous_k[e] += 1  # k above the global cap; not legally admissible
            continue
        k_by_minrank[need][k] += 1
        if r > PENALTY_BASE_RANK:
            total_highrank[e] += 1
            if r > need:
                over_ranked[e] += 1
    print("Minimum legal rank each observed k actually requires (k <= 4r^2 with")
    print("the global k <= 2^16 cap). Anything at min-rank 128 needs no rank > 128:")
    for need in sorted(k_by_minrank):
        ks = ", ".join(f"k={k}:{c}" for k, c in sorted(k_by_minrank[need].items()))
        print(f"  needs rank >= {need:>4}: {ks}")
    print()
    print("Of blocks declaring rank > 128, how many carry a k that rank 128")
    print("(or lower) already admits, i.e. the rank is not required by k:")
    for e in ERAS:
        n = total_highrank.get(e, 0)
        if n == 0:
            continue
        ov = over_ranked.get(e, 0)
        print(f"  {e:<28} {ov:>6} / {n:<6} ({100.0 * ov / n:5.1f}% over-ranked)")


def report_trajectory():
    section("3. Rank and k trajectory over height (DS-003, 500-block bins)")
    bins = load_ds003_bins()
    print("Per-era rank histogram (whole bins only; fork edges straddle a bin):")
    for e in ERAS:
        # map era string to bounds
        bounds = {
            "0-51999 (early)": (0, 51999),
            "52000-71934 (pre-MoE)": (52000, 71934),
            "71935-91629 (MoE window)": (71935, 91629),
            "91630-96250 (dense-only)": (91630, 96250),
            "96251+ (post rank-penalty)": (96251, 10 ** 9),
        }[e]
        lo, hi = bounds
        rt = Counter()
        tot = 0
        for b in bins:
            if b["from"] >= lo and b["to"] <= hi:
                tot += b["blocks"]
                for entry in b["rankHistogram"]:
                    rt[entry["value"]] += entry["count"]
        dist = " ".join(f"r{r}={rt.get(r, 0)}" for r in LEGAL_RANKS)
        print(f"  {e:<28} n={tot:<6} {dist}")


def report_pool_split():
    section("4. Post-fork per-pool boundary-hugging (DS-001, height >= 96251)")
    at_min = Counter()
    highk = Counter()
    total = Counter()
    for b in iter_ds001_blocks():
        if b["height"] < RANK_PENALTY_FORK:
            continue
        r, k, p = b["rank"], b["k"], b["pool"]
        if r != PENALTY_BASE_RANK:
            continue
        total[p] += 1
        if k == 16 * r:              # exact legal minimum k = 2048
            at_min[p] += 1
        elif k > 16 * r:
            highk[p] += 1
    print("Among rank-128 blocks: share at the exact legal minimum k=2048 vs")
    print("rank-128 with k above the minimum (both legal, cost-different):")
    print(f"{'pool':<16} {'n(r=128)':>9} {'k=2048':>8} {'k>2048':>8}")
    for p in sorted(total, key=lambda x: -total[x]):
        n = total[p]
        print(f"{p:<16} {n:>9} {at_min.get(p, 0):>8} {highk.get(p, 0):>8}")
    print()
    print("(DS-001 tip is 96,405; only 155 post-fork blocks here. OBS-001's")
    print(" +1,000-block census at tip 97,530 is the larger post-fork window.)")


def main():
    for d in (DS001, DS003):
        if not d.exists():
            print(f"missing dataset dir: {d}", file=sys.stderr)
            return 2
    report_reward_per_mac()
    report_k_gating()
    report_trajectory()
    report_pool_split()
    return 0


if __name__ == "__main__":
    sys.exit(main())
