#!/usr/bin/env bash
# Reproduce every OBS-005 table from the committed DS-002 dataset alone.
# No database, no host assumptions. The core tables need only the dataset;
# the calendar and operator-structure sections additionally need either a
# live Keshi API or a pre-emitted address artifact.
#
# Usage:
#   scripts/ds002-reproduce.sh [DATASET_DIR]
#
# Env:
#   KESHI_DS002_DIR   dataset dir (default: arg 1, else the committed copy)
#   KESHI_API         Keshi API base for the optional enrichment sections
#   KESHI_ADDR_ARTIFACT  path to an emitted operator-structure artifact,
#                     used instead of the API when set
#
# A third party needs only the dataset for the headline numbers; the two
# API-dependent sections are skipped with a notice when neither the API nor
# an artifact is available.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export KESHI_DS002_DIR="${KESHI_DS002_DIR:-${1:-$here/../docs/research/datasets/DS-002-weight-scan-v1}}"

command -v python3 >/dev/null || { echo "error: python3 is required" >&2; exit 1; }
py() { python3 "$@"; }

echo "############################################################"
echo "# DS-002 reproduction"
echo "# dataset: $KESHI_DS002_DIR"
echo "############################################################"

echo; echo "===== 1. Headline aggregation (dataset only) ====="
py "$here/ds002-aggregate.py"

echo; echo "===== 2. Stratified rates, decline, boundary checks (dataset only) ====="
combine=()
for d in "$KESHI_DS002_DIR/../DS-002b-o-tp48-v1" "$KESHI_DS002_DIR/../DS-002b-gemma-v1"; do
  [ -f "$d/extract.jsonl.gz" ] && combine+=(--combine "$d")
done
py "$here/ds002-strata.py" "${combine[@]}"

echo; echo "===== 2b. Layer mixture / TV statistic (dataset only) ====="
py "$here/ds002-mixture-tv.py"

echo; echo "===== 3. Tensor coverage / tile reuse (dataset only) ====="
py "$here/ds002-tensor-coverage.py"

# ---- API/artifact-dependent enrichment ----
api="${KESHI_API:-}"
have_enrichment=0
if [ -n "${KESHI_ADDR_ARTIFACT:-}" ] && [ -f "${KESHI_ADDR_ARTIFACT:-}" ]; then
  have_enrichment=1
elif [ -n "$api" ] && py - <<PY 2>/dev/null
import os, urllib.request
urllib.request.urlopen(os.environ["KESHI_API"].rstrip("/") + "/status", timeout=5)
PY
then
  have_enrichment=1
fi

if [ "$have_enrichment" = "1" ]; then
  echo; echo "===== 4. Deep checks: m-distribution, MSC list, calendar ====="
  py "$here/ds002-deep-checks.py" || echo "(deep-checks needs the API for its calendar section)"
  echo; echo "===== 5. Operator structure (addresses, HHI, by-day) ====="
  if [ -n "${KESHI_ADDR_ARTIFACT:-}" ]; then
    py "$here/ds002-operator-structure.py" --from-artifact "$KESHI_ADDR_ARTIFACT"
  else
    py "$here/ds002-operator-structure.py"
  fi
else
  echo
  echo "===== 4-5. SKIPPED (no live API and no address artifact) ====="
  echo "The headline tables above reproduce from the dataset alone."
  echo "For the calendar and operator-structure sections, set KESHI_API to a"
  echo "Keshi API base, or KESHI_ADDR_ARTIFACT to an emitted address artifact"
  echo "(produce one on a host with the API via:"
  echo "   ds002-operator-structure.py --emit addr-artifact.json )."
fi

echo; echo "DS-002 reproduction complete."
