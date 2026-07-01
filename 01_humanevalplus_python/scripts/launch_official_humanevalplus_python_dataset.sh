#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/humanevalplus}"
OUT_BASE="${1:-$ROOT/out/_official_humanevalplus_dataset_tests}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
DATASET_JSONL="${DATASET_JSONL:-$HOME/datasets/humanevalplus_release/HumanEvalPlus.jsonl.gz}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-120}"
COVERAGE_TIMEOUT_S="${COVERAGE_TIMEOUT_S:-180}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-300}"
RUN_MUTATION="${RUN_MUTATION:-1}"

mkdir -p "$OUT_BASE"
OUT_BASE="$(readlink -f "$OUT_BASE")"

INDEX_TSV="$OUT_BASE/dataset_runs_index.tsv"
SUMMARY_TSV="$OUT_BASE/dataset_summary.tsv"
LOG_DIR="$OUT_BASE/logs"
mkdir -p "$LOG_DIR"

echo -e "sut_id\trun_dir\tstatus_json" > "$INDEX_TSV"

for SUT_DIR in $(find "$SUT_ROOT" -maxdepth 1 -mindepth 1 -type d -name 'HumanEval_*' | sort -V); do
  SUT_ID="$(basename "$SUT_DIR")"
  echo
  echo "============================================================"
  echo "SUT_ID=$SUT_ID"
  echo "SUT_DIR=$SUT_DIR"
  echo "============================================================"

  RUN_LOG="$LOG_DIR/${SUT_ID}.log"

  set +e
  SUT_ID="$SUT_ID" \
  SUT_DIR="$SUT_DIR" \
  DATASET_JSONL="$DATASET_JSONL" \
  OUT_BASE="$OUT_BASE" \
  PYTHON_BIN="$PYTHON_BIN" \
  PYTEST_TIMEOUT_S="$PYTEST_TIMEOUT_S" \
  COVERAGE_TIMEOUT_S="$COVERAGE_TIMEOUT_S" \
  MUTATION_TIMEOUT_S="$MUTATION_TIMEOUT_S" \
  RUN_MUTATION="$RUN_MUTATION" \
  "$ROOT/scripts/run_official_humanevalplus_python_one_sut.sh" \
    > "$RUN_LOG" 2>&1
  RC="$?"
  set -e

  RUN_DIR="$OUT_BASE/$SUT_ID/run_0001"
  STATUS_JSON="$RUN_DIR/metrics/status.json"

  echo "SCRIPT_RC=$RC"
  echo "RUN_DIR=$RUN_DIR"
  echo "STATUS_JSON=$STATUS_JSON"

  echo -e "${SUT_ID}\t${RUN_DIR}\t${STATUS_JSON}" >> "$INDEX_TSV"
done

"$PYTHON_BIN" - <<PY
from pathlib import Path
import json

out = Path(r"$OUT_BASE")
index = out / "dataset_runs_index.tsv"
summary = out / "dataset_summary.tsv"

rows = []
for line in index.read_text(encoding="utf-8").splitlines()[1:]:
    if not line.strip():
        continue
    sut_id, run_dir, status_json = line.split("\t")
    p = Path(status_json)
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        rows.append([
            sut_id,
            d.get("status"),
            d.get("ok"),
            d.get("pytest_exit_code"),
            d.get("coverage_exit_code"),
            d.get("mutation_exit_code"),
            d.get("line_pct"),
            d.get("branch_pct"),
            d.get("mutation_score_pct"),
        ])
    else:
        rows.append([sut_id, "missing_status", False, "", "", "", "", "", ""])

with summary.open("w", encoding="utf-8") as fp:
    fp.write("sut_id\tstatus\tok\tpytest_rc\tcoverage_rc\tmutation_rc\tline_pct\tbranch_pct\tmutation_score_pct\n")
    for row in rows:
        fp.write("\t".join("" if x is None else str(x) for x in row) + "\n")

print(f"Wrote: {summary}")
PY

echo
echo "DONE OFFICIAL HUMANEVAL+ DATASET ✅"
echo "OUT_BASE=$OUT_BASE"
echo "INDEX_TSV=$INDEX_TSV"
echo "SUMMARY_TSV=$SUMMARY_TSV"
