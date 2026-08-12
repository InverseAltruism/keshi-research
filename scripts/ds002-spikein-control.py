#!/usr/bin/env python3
"""Post-boundary positive control for the weight-provenance scan (spike-in).

DS-002's negative control spans h41,237-52,280 only, so it has no power in
the post-boundary region where the headline reports (almost) no matches.
This script demonstrates detection power there by construction:

  1. take the first N candidate (non-control) records above the boundary
     from a COPY of the frozen extract, in (height, hash) order;
  2. overwrite each record's hashB with blake3(buffer bytes, key = that
     block's own on-chain-derived jobKey) for one deterministic buffer of
     the block's first candidate family;
  3. run the REAL Go hash stage (`keshictl scan-weights --resume`) over the
     doctored copy in a scratch directory, against the real weights root;
  4. assert every doctored pair reports match=true and nothing else does.

What this exercises: the production hash stage (manifest loading, keyed
BLAKE3, match comparison, result emission) on post-boundary job keys. What
it does not exercise: the extract stage and its derivation checks, which
are validated separately per block at extract time.

The frozen dataset is only ever read. All writes go to --out (scratch).

Usage:
  ds002-spikein-control.py --out /path/to/scratch/dir [--run]

Env:
  KESHI_DS002_DIR   frozen dataset dir (default: the committed DS-002 copy)
  KESHI_KESHICTL    keshictl binary for --run (default: repo bin/keshictl)
"""

import argparse
import gzip
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DS = HERE.parent / "docs" / "research" / "datasets" / "DS-002-weight-scan-v1"


def die(msg: str, code: int = 1) -> None:
    print(f"ds002-spikein-control: {msg}", file=sys.stderr)
    sys.exit(code)


def load_manifests(weights_root: Path) -> dict[str, list[dict]]:
    """candidate id ("Model/layer/tpN") -> manifest file entries, sorted."""
    fams: dict[str, list[dict]] = {}
    for mpath in sorted(weights_root.glob("*/manifest.json")):
        man = json.loads(mpath.read_text())
        for f in man["files"]:
            cid = f"{man['model']}/{f['layer']}/tp{f['tp']}"
            f = dict(f, _dir=str(mpath.parent))
            fams.setdefault(cid, []).append(f)
    for entries in fams.values():
        entries.sort(key=lambda f: (f["layer_index"], f["shard"]))
    return fams


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="scratch dataset dir (created; must not exist)")
    ap.add_argument("--weights", default="/opt/pearl_keshi/weights", help="weights root")
    ap.add_argument("--boundary", type=int, default=54972,
                    help="last pre-gap match height; spikes are taken above it")
    ap.add_argument("--n", type=int, default=3, help="records to doctor")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--run", action="store_true",
                    help="invoke the Go hash stage and verify (else print the command)")
    args = ap.parse_args()

    import blake3  # independent pip implementation, same as the repro script

    ds = Path(os.environ.get("KESHI_DS002_DIR", str(DEFAULT_DS)))
    extract = ds / "extract.jsonl.gz"
    if not extract.is_file():
        die(f"no extract at {extract}")
    out = Path(args.out)
    if out.exists():
        die(f"{out} exists; scratch dirs are one-shot, pick a new path")
    weights_root = Path(args.weights)
    fams = load_manifests(weights_root)
    if not fams:
        die(f"no manifests under {weights_root}")

    # Deterministic selection: first n doctorable + next n untouched, in the
    # extract's own (height, hash) order, above the boundary.
    doctored: list[dict] = []
    untouched: list[dict] = []
    picks: list[tuple[dict, dict]] = []  # (record, buffer entry)
    with gzip.open(extract, "rt") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("control") or rec["height"] <= args.boundary:
                continue
            cands = [c for c in rec.get("candidates", []) if c in fams]
            if not cands:
                continue
            if len(doctored) < args.n:
                entries = fams[cands[0]]
                buf_entry = entries[len(doctored) % len(entries)]
                picks.append((rec, buf_entry))
                doctored.append(rec)
            elif len(untouched) < args.n:
                untouched.append(rec)
            else:
                break
    if len(doctored) < args.n:
        die(f"only {len(doctored)} doctorable records above h{args.boundary}")

    expected = []  # (height, candidate id, layer_index, shard)
    for rec, ent in picks:
        buf = (Path(ent["_dir"]) / ent["file"]).read_bytes()
        if len(buf) != ent["bytes"]:
            die(f"{ent['file']}: {len(buf)} bytes, manifest says {ent['bytes']}")
        key = bytes.fromhex(rec["jobKey"])
        rec["hashB"] = blake3.blake3(buf, key=key).digest().hex()
        cid = f"{ent['_dir'].rsplit('/', 1)[-1]}/{ent['layer']}/tp{ent['tp']}"
        expected.append((rec["height"], cid, ent["layer_index"], ent["shard"]))
        print(f"spiked h{rec['height']}: hashB <- blake3({ent['file']}, key=jobKey) "
              f"[{cid} L{ent['layer_index']:03d} s{ent['shard']}]")

    out.mkdir(parents=True)
    with gzip.open(out / "extract.jsonl.gz", "wt") as f:
        for rec in doctored + untouched:
            f.write(json.dumps(rec) + "\n")
    print(f"doctored extract: {args.n} spiked + {len(untouched)} untouched "
          f"post-boundary records -> {out}")

    keshictl = os.environ.get("KESHI_KESHICTL", str(HERE.parent / "bin" / "keshictl"))
    cmd = [keshictl, "scan-weights", "--out", str(out), "--weights", str(weights_root),
           "--resume", "--workers", str(args.workers)]
    if not args.run:
        print("run the hash stage with:\n  " + " ".join(cmd))
        return 0

    print("running:", " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        die(f"hash stage exited {proc.returncode}")

    got = set()
    false_extras = []
    for part in (out / "results").glob("*.jsonl.gz"):
        with gzip.open(part, "rt") as f:
            for line in f:
                r = json.loads(line)
                if r["match"]:
                    key = (r["height"], r["candidate"], r["layerIndex"], r["shard"])
                    (got.add if key in set(expected) else false_extras.append)(key)
    missing = [e for e in expected if e not in got]
    print(f"expected spikes detected: {len(got)}/{len(expected)}; "
          f"false extras: {len(false_extras)}")
    for m in missing:
        print(f"  MISSING: {m}")
    for x in false_extras:
        print(f"  FALSE EXTRA: {x}")
    if missing or false_extras:
        die("spike-in control FAILED")
    print("spike-in control PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
