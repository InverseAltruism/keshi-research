#!/usr/bin/env python3
"""Watch pearl-research-labs/pearl releases for unreviewed consensus changes.

This is the automation of the PCCR maintenance rule (docs/registry/PCCR.md):

    "A new pearld release triggers a review of `chaincfg`, `wire`,
    `blockchain` and `zk-pow` diffs for candidate entries."

The register itself is the state: a release counts as REVIEWED iff the
"## Release review log" table in docs/registry/PCCR.md carries a row for it
whose Result column is not a REVIEW PENDING placeholder. There is no side
state file, so the alert persists until a human actually logs the review --
which is the desired behavior for an append-only evidence register. Tags at
or below BASELINE_TAG are covered by the seeded entries PCCR-0001..0006 plus
the existing log rows and are never flagged.

The tool only ever *appends review-log placeholder rows* (--write). It never
authors PCCR entries and never fills a Result column: humans do the review,
per the register's append-only discipline.

Data sources (network):
  - https://api.github.com/repos/pearl-research-labs/pearl/tags   (discovery;
    anonymous is fine at this cadence, GITHUB_TOKEN honored when set;
    fallback: `git ls-remote --tags` which is verified to work anonymously)
  - .../compare/{prev}...{tag}  (file list + patches; the GitHub compare API
    caps the file list at 300 -- a capped response is reported as truncated
    and conservatively treated as consensus-relevant)
  - .../commits/{sha}           (release date, when the Release object is
    missing -- pearl has tags without Release objects, e.g. v1.2.0)

Node releases and wallet releases share one release stream; node tags match
^v[0-9] (docs/pearl-notes.md section "pearld operational facts").

Consensus surface (per the PCCR rule): node/chaincfg/, node/wire/,
node/blockchain/, zk-pow/.

Exit codes:
  0  no unreviewed node releases
  1  error (network, PCCR parse, rate limit)
  2  at least one unreviewed release touches the consensus surface
  3  unreviewed release(s) exist, none touch the consensus surface
     (a review-log row is still owed: "no entry" must stay distinguishable
     from "not reviewed")

Usage:
  pearl-release-watch.py [--json] [--write] [--notify] [--self-test]

  --json    machine-readable report to stdout instead of markdown
  --write   append idempotent "REVIEW PENDING" rows to the review log
  --notify  POST findings to ntfy (KESHI_NTFY_URL + KESHI_NTFY_TOPIC env,
            the same contract as /etc/keshi/ntfy.env)
  --self-test  replay the known v1.3.0...v1.3.1 compare and assert it is
            classified consensus-relevant (2 files, node/chaincfg/params.go)

Cadence note: designed for a daily systemd timer (keshi-release-watch.timer
in keshi-infra); ~4 API requests per run sits far under the 60/hr anonymous
limit.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "pearl-research-labs/pearl"
API = f"https://api.github.com/repos/{REPO}"
BASELINE_TAG = "v1.3.1"  # everything <= this is covered by PCCR-0001..0006 + the seeded log
CONSENSUS_RE = re.compile(r"^(node/chaincfg/|node/wire/|node/blockchain/|zk-pow/)")
NODE_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
COMPARE_FILE_CAP = 300  # documented GitHub compare-API file-list cap

SCRIPT_DIR = Path(__file__).resolve().parent
PCCR_PATH = SCRIPT_DIR.parent / "docs" / "registry" / "PCCR.md"
REVIEW_LOG_HEADING = "## Release review log"
PENDING_MARKER = "REVIEW PENDING"


class WatchError(Exception):
    """Fatal condition; maps to exit code 1."""


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "keshi-release-watch"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise WatchError(f"GitHub API {e.code} for {url}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise WatchError(f"network error for {url}: {e.reason}") from e


def semver(tag: str) -> tuple[int, int, int]:
    m = NODE_TAG_RE.match(tag)
    if not m:
        raise WatchError(f"not a node tag: {tag}")
    return tuple(int(g) for g in m.groups())  # type: ignore[return-value]


def node_tags() -> list[dict]:
    """All node tags (name + commit sha), ascending semver order."""
    try:
        raw = fetch_json(f"{API}/tags?per_page=100")
        tags = [t for t in raw if NODE_TAG_RE.match(t["name"])]
        tags.sort(key=lambda t: semver(t["name"]))
        if tags:
            return tags
        raise WatchError("GitHub /tags returned no node tags")
    except WatchError as api_err:
        # Discovery fallback: anonymous ls-remote (verified working). No shas
        # for dates in this path, but discovery still functions.
        try:
            out = subprocess.run(
                ["git", "ls-remote", "--tags", f"https://github.com/{REPO}"],
                capture_output=True, text=True, timeout=60, check=True,
            ).stdout
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise WatchError(f"tag discovery failed twice: {api_err}; ls-remote: {e}") from e
        found = []
        for line in out.splitlines():
            sha, _, ref = line.partition("\t")
            name = ref.removeprefix("refs/tags/").removesuffix("^{}")
            if NODE_TAG_RE.match(name):
                found.append({"name": name, "commit": {"sha": sha}})
        dedup = {t["name"]: t for t in found}  # ^{} peeled entries win (last)
        tags = sorted(dedup.values(), key=lambda t: semver(t["name"]))
        if not tags:
            raise WatchError("ls-remote fallback returned no node tags")
        print(f"warning: GitHub API discovery failed ({api_err}); used ls-remote",
              file=sys.stderr)
        return tags


def reviewed_tags(pccr_text: str) -> dict[str, str]:
    """tag -> Result cell, from the Release review log table. Strict parse."""
    if REVIEW_LOG_HEADING not in pccr_text:
        raise WatchError(
            f"PCCR.md has no '{REVIEW_LOG_HEADING}' section -- the register "
            "format drifted; refusing to guess"
        )
    section = pccr_text.split(REVIEW_LOG_HEADING, 1)[1]
    rows: dict[str, str] = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("Release", "---"):
            continue
        m = re.match(r"(v\d+\.\d+\.\d+)", cells[0])
        if m:
            rows[m.group(1)] = cells[2]
    return rows


def release_date(tag: dict) -> str:
    sha = tag.get("commit", {}).get("sha")
    if not sha:
        return "unknown-date"
    try:
        c = fetch_json(f"{API}/commits/{sha}")
        return c["commit"]["committer"]["date"][:10]
    except WatchError:
        return "unknown-date"


def compare(prev: str, tag: str) -> dict:
    """Diff prev...tag; classify against the consensus surface."""
    data = fetch_json(f"{API}/compare/{prev}...{tag}")
    files = data.get("files", [])
    truncated = len(files) >= COMPARE_FILE_CAP
    relevant = []
    for f in files:
        if CONSENSUS_RE.match(f["filename"]):
            relevant.append({
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "patch": f.get("patch", "(no patch -- binary or too large)"),
                "evidence": f"{f['filename']} @ {tag}",
            })
    return {
        "prev": prev,
        "tag": tag,
        "total_files": len(files),
        "total_commits": data.get("total_commits", 0),
        "truncated": truncated,
        # A capped file list may hide consensus files: conservative.
        "consensus_relevant": bool(relevant) or truncated,
        "relevant_files": relevant,
    }


def analyze() -> list[dict]:
    tags = node_tags()
    pccr = PCCR_PATH.read_text(encoding="utf-8")
    logged = reviewed_tags(pccr)
    baseline = semver(BASELINE_TAG)

    findings = []
    for i, t in enumerate(tags):
        name = t["name"]
        if semver(name) <= baseline:
            continue
        result = logged.get(name)
        if result is not None and PENDING_MARKER not in result:
            continue  # reviewed by a human
        if i == 0:
            findings.append({"tag": name, "prev": None, "date": release_date(t),
                             "consensus_relevant": True, "total_files": None,
                             "truncated": False, "relevant_files": [],
                             "note": "no predecessor tag -- review manually"})
            continue
        cmp = compare(tags[i - 1]["name"], name)
        cmp["date"] = release_date(t)
        cmp["already_pending"] = result is not None
        findings.append(cmp)
    return findings


def render_markdown(findings: list[dict]) -> str:
    if not findings:
        return "No unreviewed pearl node releases. Register is current.\n"
    out = [f"# Unreviewed pearl releases ({len(findings)})", ""]
    for f in findings:
        head = f"## {f['tag']}  ({f.get('date', '?')})  vs {f.get('prev', '–')}"
        out.append(head)
        if f.get("note"):
            out.append(f"- NOTE: {f['note']}")
        if f.get("truncated"):
            out.append(f"- WARNING: file list capped at {COMPARE_FILE_CAP} by the "
                       "compare API; may be incomplete -- treated as consensus-relevant")
        out.append(f"- files changed: {f.get('total_files', '?')} · commits: "
                   f"{f.get('total_commits', '?')} · consensus-relevant: "
                   f"**{'YES' if f['consensus_relevant'] else 'no'}**")
        for rf in f["relevant_files"]:
            out.append("")
            out.append(f"### {rf['evidence']}  ({rf['status']}, "
                       f"+{rf['additions']} −{rf['deletions']})")
            out.append("```diff")
            out.append(rf["patch"])
            out.append("```")
        out.append("")
    out.append("Review per docs/registry/PCCR.md maintenance rules; log every "
               "release in the Release review log (this tool's --write appends "
               "a placeholder row; a human fills the Result).")
    return "\n".join(out) + "\n"


def write_pending_rows(findings: list[dict]) -> int:
    """Append one placeholder row per finding without any existing row."""
    text = PCCR_PATH.read_text(encoding="utf-8")
    logged = reviewed_tags(text)
    new_rows = []
    for f in findings:
        if f["tag"] in logged:
            continue  # idempotent: some row already exists (pending or done)
        n = len(f["relevant_files"])
        cls = (f"{n} consensus-relevant file(s)" if f["consensus_relevant"]
               else "no consensus-surface files")
        if f.get("truncated"):
            cls += "; file list truncated"
        new_rows.append(
            f"| {f['tag']} ({f.get('date', '?')}) | - | {PENDING_MARKER} "
            f"(auto: {cls} vs {f.get('prev', '–')}; run "
            f"scripts/pearl-release-watch.py for the diff) |"
        )
    if not new_rows:
        return 0
    lines = text.splitlines()
    # Insert after the last table row of the review-log section.
    start = next(i for i, l in enumerate(lines) if l.startswith(REVIEW_LOG_HEADING))
    last_row = max(i for i in range(start, len(lines)) if lines[i].lstrip().startswith("|"))
    lines[last_row + 1:last_row + 1] = new_rows
    PCCR_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(new_rows)


def notify(findings: list[dict]) -> None:
    url = os.environ.get("KESHI_NTFY_URL", "https://ntfy.sh").rstrip("/")
    topic = os.environ.get("KESHI_NTFY_TOPIC")
    if not topic:
        raise WatchError("--notify requires KESHI_NTFY_TOPIC in the environment")
    tags_s = ", ".join(f["tag"] for f in findings)
    relevant = [f for f in findings if f["consensus_relevant"]]
    title = ("Pearl release: consensus-relevant diff unreviewed"
             if relevant else "Pearl release awaiting review log entry")
    body = (f"Unreviewed pearld release(s): {tags_s}. "
            + (f"{sum(len(f['relevant_files']) for f in relevant)} consensus-surface "
               f"file(s) changed. " if relevant else "No consensus-surface files. ")
            + "Review + log per docs/registry/PCCR.md.")
    req = urllib.request.Request(
        f"{url}/{topic}", data=body.encode(),
        headers={"Title": title, "Priority": "high" if relevant else "default",
                 "Tags": "pearl,release-watch"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def self_test() -> int:
    """Replay the reviewed v1.3.0...v1.3.1 case (2 files; chaincfg relevant)."""
    cmp = compare("v1.3.0", "v1.3.1")
    ok = (
        cmp["total_files"] == 2
        and cmp["consensus_relevant"] is True
        and [f["filename"] for f in cmp["relevant_files"]] == ["node/chaincfg/params.go"]
        and "DenseOnlyForkHeight" in cmp["relevant_files"][0]["patch"]
    )
    # The state parser must also see the human review of exactly this release.
    logged = reviewed_tags(PCCR_PATH.read_text(encoding="utf-8"))
    ok = ok and "v1.3.1" in logged and PENDING_MARKER not in logged["v1.3.1"]
    print("self-test:", "PASS" if ok else f"FAIL ({json.dumps(cmp)[:400]})")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    try:
        if args.self_test:
            return self_test()
        findings = analyze()
        if args.json:
            print(json.dumps({"findings": findings}, indent=2))
        else:
            print(render_markdown(findings), end="")
        if args.write and findings:
            n = write_pending_rows(findings)
            print(f"\n--write: appended {n} placeholder row(s) to {PCCR_PATH}",
                  file=sys.stderr)
        if args.notify and findings:
            notify(findings)
        if not findings:
            return 0
        return 2 if any(f["consensus_relevant"] for f in findings) else 3
    except WatchError as e:
        print(f"pearl-release-watch: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
