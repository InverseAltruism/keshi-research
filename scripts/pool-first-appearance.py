#!/usr/bin/env python3
"""First attributed block per pool label, by full sweep of the blocks API.

Emits one line per pool label: earliest height, its date, and the total
attributed count seen, plus the sweep's tip so the number is reproducible
at a stated point in time. Used by OBS-005 §5.1 (extinction-curve
correlates: first appearance of each labeled pool relative to the
boundary). Read-only; needs only KESHI_API.

Env:
  KESHI_API   Keshi API base (default http://127.0.0.1:8081/v1)
"""

import json
import os
import sys
import urllib.request

API = os.environ.get("KESHI_API", "http://127.0.0.1:8081/v1")


def get(path: str):
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.load(r)


def main() -> int:
    first: dict[str, tuple[int, str]] = {}
    counts: dict[str, int] = {}
    tip = None
    before = None
    pages = 0
    while True:
        q = f"/blocks?limit=200" + (f"&before={before}" if before is not None else "")
        data = get(q)
        rows = data.get("blocks") or []
        if not rows:
            break
        if tip is None:
            tip = rows[0]["height"]
        for b in rows:
            pool = (b.get("pool") or {}).get("name")
            if not pool:
                continue
            counts[pool] = counts.get(pool, 0) + 1
            h = b["height"]
            if pool not in first or h < first[pool][0]:
                first[pool] = (h, b.get("time", "")[:10])
        before = rows[-1]["height"]
        pages += 1
        if before == 0:
            break
    print(f"sweep tip {tip}, {pages} pages")
    for pool, (h, day) in sorted(first.items(), key=lambda kv: kv[1][0]):
        print(f"  {pool:16s} first attributed block h{h:<7d} {day}   "
              f"({counts[pool]} attributed blocks total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
