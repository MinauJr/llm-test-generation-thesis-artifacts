#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${SUT_ID:?missing SUT_ID}"
: "${SUT_DIR:?missing SUT_DIR}"

DATASET_JSONL="${DATASET_JSONL:-$HOME/datasets/humanevalplus_release/HumanEvalPlus.jsonl.gz}"
OUT_BASE="${OUT_BASE:-$ROOT/out/_official_humanevalplus_dataset_tests}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-120}"
COVERAGE_TIMEOUT_S="${COVERAGE_TIMEOUT_S:-180}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-300}"
RUN_MUTATION="${RUN_MUTATION:-1}"

TASK_NUM="${SUT_ID#HumanEval_}"
TASK_ID_DATASET="HumanEval/$TASK_NUM"

OUT_DIR="$OUT_BASE/$SUT_ID/run_0001"
RUNNER_DIR="$OUT_DIR/runner"
TESTS_DIR="$RUNNER_DIR/tests"
LOG_DIR="$OUT_DIR/logs"
METRICS_DIR="$OUT_DIR/metrics"
RAW_DIR="$OUT_DIR/raw"

mkdir -p "$RUNNER_DIR" "$TESTS_DIR" "$LOG_DIR" "$METRICS_DIR" "$RAW_DIR"

find_sut_source() {
  if [[ -f "$SUT_DIR/sut.py" ]]; then
    printf '%s\n' "$SUT_DIR/sut.py"
    return 0
  fi
  if [[ -f "$SUT_DIR/solution.py" ]]; then
    printf '%s\n' "$SUT_DIR/solution.py"
    return 0
  fi
  find "$SUT_DIR" -maxdepth 2 -type f -name '*.py' \
    ! -name 'test_*.py' ! -name '*_test.py' ! -path '*/tests/*' | sort | head -n 1
}

write_status_json() {
  local status="$1"
  local ok_bool="$2"
  local pytest_rc="${3:-null}"
  local coverage_rc="${4:-null}"
  local mutation_rc="${5:-null}"
  local line_pct="${6:-null}"
  local branch_pct="${7:-null}"
  local mutation_score_pct="${8:-null}"

  cat > "$METRICS_DIR/status.json" <<JSON
{
  "sut_id": "$SUT_ID",
  "sut_dir": "$SUT_DIR",
  "task_id": "$TASK_ID_DATASET",
  "status": "$status",
  "ok": $ok_bool,
  "pytest_exit_code": $pytest_rc,
  "coverage_exit_code": $coverage_rc,
  "mutation_exit_code": $mutation_rc,
  "line_pct": $line_pct,
  "branch_pct": $branch_pct,
  "mutation_score_pct": $mutation_score_pct
}
JSON
}

json_num_or_null() {
  local v="${1:-}"
  if [[ -z "$v" || "$v" == "null" ]]; then
    printf 'null'
  else
    printf '%s' "$v"
  fi
}

SUT_SOURCE="$(find_sut_source)"
if [[ -z "${SUT_SOURCE:-}" || ! -f "$SUT_SOURCE" ]]; then
  write_status_json "invalid_sut_source" "false"
  exit 0
fi

cp "$SUT_SOURCE" "$RUNNER_DIR/sut.py"

"$PYTHON_BIN" "$ROOT/tools/materialize_humanevalplus_official_tests.py" \
  --dataset "$DATASET_JSONL" \
  --task-id "$SUT_ID" \
  --sut-file "$RUNNER_DIR/sut.py" \
  --output "$TESTS_DIR/test_official_dataset.py" \
  --meta-output "$RAW_DIR/official_tests_meta.json" \
  > "$RAW_DIR/materialize.stdout.json" 2> "$LOG_DIR/materialize.stderr.log" || {
    write_status_json "materialize_fail" "false"
    exit 0
  }

pushd "$RUNNER_DIR" >/dev/null

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

set +e
timeout "${PYTEST_TIMEOUT_S}s" "$PYTHON_BIN" -m pytest -q tests/test_official_dataset.py \
  > "$LOG_DIR/pytest.stdout.log" 2> "$LOG_DIR/pytest.stderr.log"
PYTEST_RC="$?"
set -e

if [[ "$PYTEST_RC" != "0" ]]; then
  popd >/dev/null
  write_status_json "pytest_fail" "false" "$(json_num_or_null "$PYTEST_RC")"
  exit 0
fi

set +e
timeout "${COVERAGE_TIMEOUT_S}s" "$PYTHON_BIN" -m pytest -p pytest_cov -q \
  --cov=sut \
  --cov-branch \
  --cov-report=term \
  --cov-report=xml:"$METRICS_DIR/coverage.xml" \
  tests/test_official_dataset.py \
  > "$LOG_DIR/coverage.stdout.log" 2> "$LOG_DIR/coverage.stderr.log"
COV_RC="$?"
set -e

LINE_PCT=""
BRANCH_PCT=""
if [[ "$COV_RC" == "0" && -f "$METRICS_DIR/coverage.xml" ]]; then
  read -r LINE_PCT BRANCH_PCT < <("$PYTHON_BIN" - <<PY
import xml.etree.ElementTree as ET
root = ET.parse(r"$METRICS_DIR/coverage.xml").getroot()
line_rate = float(root.attrib.get("line-rate", 0.0)) * 100.0
branch_rate = float(root.attrib.get("branch-rate", 0.0)) * 100.0
print(f"{line_rate:.4f} {branch_rate:.4f}")
PY
)
fi

if [[ "$COV_RC" != "0" || -z "${LINE_PCT:-}" || -z "${BRANCH_PCT:-}" ]]; then
  popd >/dev/null
  write_status_json "coverage_fail" "false" \
    "$(json_num_or_null "$PYTEST_RC")" \
    "$(json_num_or_null "$COV_RC")"
  exit 0
fi

MUT_SCORE=""
MUT_RC="null"

if [[ "${RUN_MUTATION}" == "1" ]]; then
  cat > setup.cfg <<CFG
[mutmut]
paths_to_mutate=sut.py
tests_dir=tests
runner=env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_official_dataset.py
backup=False
CFG

  set +e
  timeout "${MUTATION_TIMEOUT_S}s" "$PYTHON_BIN" -m mutmut run \
    > "$LOG_DIR/mutmut.stdout.log" 2> "$LOG_DIR/mutmut.stderr.log"
  MUT_RC="$?"
  set -e

  set +e
  "$PYTHON_BIN" -m mutmut results > "$LOG_DIR/mutmut.results.log" 2>&1
  set -e

  TOTAL_MUTANTS="$("$PYTHON_BIN" - <<PY
import json
from pathlib import Path
p = Path("mutants/sut.py.meta")
if not p.exists():
    print("")
else:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        print(len(d))
    except Exception:
        print("")
PY
)"

  SURVIVED_MUTANTS="$("$PYTHON_BIN" - <<PY
import re
from pathlib import Path
p = Path(r"$LOG_DIR/mutmut.results.log")
txt = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
m = re.search(r"Survived\s*\((\d+)\)", txt)
print(m.group(1) if m else "0")
PY
)"

  if [[ -n "${TOTAL_MUTANTS:-}" && "$TOTAL_MUTANTS" != "0" ]]; then
    MUT_SCORE="$("$PYTHON_BIN" - <<PY
total = int("${TOTAL_MUTANTS}")
survived = int("${SURVIVED_MUTANTS:-0}")
killed = max(total - survived, 0)
print(f"{(100.0 * killed / total):.4f}")
PY
)"
  fi

  if [[ -z "${MUT_SCORE:-}" ]]; then
    popd >/dev/null
    write_status_json "mutation_fail" "false" \
      "$(json_num_or_null "$PYTEST_RC")" \
      "$(json_num_or_null "$COV_RC")" \
      "$(json_num_or_null "$MUT_RC")" \
      "$(json_num_or_null "$LINE_PCT")" \
      "$(json_num_or_null "$BRANCH_PCT")"
    exit 0
  fi
fi

popd >/dev/null

write_status_json "ok" "true" \
  "$(json_num_or_null "$PYTEST_RC")" \
  "$(json_num_or_null "$COV_RC")" \
  "$(json_num_or_null "$MUT_RC")" \
  "$(json_num_or_null "$LINE_PCT")" \
  "$(json_num_or_null "$BRANCH_PCT")" \
  "$(json_num_or_null "$MUT_SCORE")"

echo "DONE $SUT_ID status=ok"
