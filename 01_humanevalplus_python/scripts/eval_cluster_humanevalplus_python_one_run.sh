#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT

SUT_DIR="${1:?Uso: eval_cluster_humanevalplus_python_one_run.sh SUT_DIR CLUSTER_REP_DIR OUT_BASE}"
CLUSTER_REP_DIR="${2:?Uso: eval_cluster_humanevalplus_python_one_run.sh SUT_DIR CLUSTER_REP_DIR OUT_BASE}"
OUT_BASE="${3:?Uso: eval_cluster_humanevalplus_python_one_run.sh SUT_DIR CLUSTER_REP_DIR OUT_BASE}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_MUTATION="${RUN_MUTATION:-1}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}"

SUT_DIR="$(readlink -f "$SUT_DIR")"
CLUSTER_REP_DIR="$(readlink -f "$CLUSTER_REP_DIR")"
OUT_BASE="$(readlink -f "$OUT_BASE")"

CLUSTER_STATUS_JSON="$CLUSTER_REP_DIR/status.json"
CLUSTER_TEST_FILE="$CLUSTER_REP_DIR/generated_tests.py"

if [[ ! -f "$CLUSTER_STATUS_JSON" ]]; then
  echo "[ERROR] Missing cluster status.json: $CLUSTER_STATUS_JSON" >&2
  exit 1
fi

if [[ ! -f "$CLUSTER_TEST_FILE" ]]; then
  echo "[ERROR] Missing cluster generated_tests.py: $CLUSTER_TEST_FILE" >&2
  exit 1
fi

IFS=$'\t' read -r MODEL SUT_NAME REP SOURCE_STATUS < <(
python3 - "$CLUSTER_STATUS_JSON" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print("\t".join([
    str(d.get("model", "")),
    str(d.get("sut_id", "")),
    str(d.get("repeat", "")),
    str(d.get("status", "")),
]))
PY
)

if [[ "$SOURCE_STATUS" != "ok" ]]; then
  echo "[ERROR] Cluster repetition is not status=ok: $SOURCE_STATUS" >&2
  exit 1
fi

RUN_ID="run_$(printf "%04d" "$REP")"
RUN_DIR="$OUT_BASE/$SUT_NAME/$RUN_ID"

SRC_DIR="$RUN_DIR/source_cluster"
RUNNER="$RUN_DIR/runner"
LOG_DIR="$RUN_DIR/logs"
METRICS_DIR="$RUN_DIR/metrics"

mkdir -p "$SRC_DIR" "$RUNNER" "$LOG_DIR" "$METRICS_DIR"

STATUS_JSON="$METRICS_DIR/status.json"
SUT_FILE="$SUT_DIR/sut.py"
MODULE_NAME="sut"

write_status () {
  local status="$1"
  local note="$2"
  local test_compile_rc="${3:-}"
  local pytest_raw_rc="${4:-}"
  local pytest_final_rc="${5:-}"
  local coverage_rc="${6:-}"
  local mutmut_rc="${7:-}"
  local line_cov="${8:-0}"
  local branch_cov="${9:-0}"
  local mutation_score="${10:-0}"

  python3 - <<PY
import json
from pathlib import Path

def as_int(x):
    try:
        return int(str(x))
    except Exception:
        return None

def as_float(x):
    try:
        return float(str(x))
    except Exception:
        return None

data = {
    "dataset": "humanevalplus_cluster_llm",
    "language": "python",
    "model": "$MODEL",
    "sut_name": "$SUT_NAME",
    "sut_dir": "$SUT_DIR",
    "sut_file": "$SUT_FILE",
    "module_name": "$MODULE_NAME",
    "run_id": "$RUN_ID",
    "repeat": int("$REP"),
    "status": "$status",
    "note": "$note",
    "source_cluster_status": "$SOURCE_STATUS",
    "source_cluster_rep_dir": "$CLUSTER_REP_DIR",
    "source_cluster_status_json": "$CLUSTER_STATUS_JSON",
    "source_cluster_generated_file": "$CLUSTER_TEST_FILE",
    "generated_test_compile_exit_code": as_int("$test_compile_rc"),
    "pytest_raw_exit_code": as_int("$pytest_raw_rc"),
    "pytest_final_exit_code": as_int("$pytest_final_rc"),
    "coverage_exit_code": as_int("$coverage_rc"),
    "mutmut_exit_code": as_int("$mutmut_rc"),
    "line_coverage_pct": as_float("$line_cov"),
    "branch_coverage_pct": as_float("$branch_cov"),
    "mutation_score_pct": as_float("$mutation_score"),
    "run_mutation": "$RUN_MUTATION",
    "run_dir": "$RUN_DIR",
    "runner_dir": "$RUNNER"
}
Path("$STATUS_JSON").write_text(json.dumps(data, indent=2) + "\n")
PY
}

metric_zero_files () {
  echo "0" > "$METRICS_DIR/line_coverage_pct.txt"
  echo "0" > "$METRICS_DIR/branch_coverage_pct.txt"
  echo "0" > "$METRICS_DIR/mutation_score_pct.txt"
}

echo "============================================================"
echo "Cluster HumanEval+ Python evaluation of one run"
echo "MODEL=$MODEL"
echo "SUT_DIR=$SUT_DIR"
echo "SUT_NAME=$SUT_NAME"
echo "CLUSTER_REP_DIR=$CLUSTER_REP_DIR"
echo "OUT_BASE=$OUT_BASE"
echo "RUN_DIR=$RUN_DIR"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "PYTHON_BIN=$PYTHON_BIN"
echo "============================================================"

metric_zero_files

if [[ ! -f "$SUT_FILE" ]]; then
  write_status "sut_missing" "sut.py not found" "" "" "" "" "" 0 0 0
  echo "[ERROR] Missing SUT file: $SUT_FILE" >&2
  exit 0
fi

echo "[1/8] Preparing isolated runner..."
rm -rf "$RUNNER"
mkdir -p "$RUNNER/tests"

cp -a "$SUT_DIR/." "$RUNNER/"
rm -rf "$RUNNER/__pycache__" "$RUNNER/.pytest_cache" "$RUNNER/htmlcov" "$RUNNER/.coverage"

cp -a "$CLUSTER_STATUS_JSON" "$SRC_DIR/"
cp -a "$CLUSTER_TEST_FILE" "$SRC_DIR/generated_tests.py"

if [[ ! -f "$RUNNER/sut.py" ]]; then
  write_status "runner_sut_missing" "runner/sut.py not found after copy" "" "" "" "" "" 0 0 0
  echo "[ERROR] runner/sut.py missing" >&2
  exit 0
fi

echo "[2/8] Copying generated pytest file..."
python3 - "$CLUSTER_TEST_FILE" "$RUNNER" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
runner = Path(sys.argv[2])

dst_raw = runner / "tests" / "test_cluster_llm.raw.txt"
dst = runner / "tests" / "test_cluster_llm.py"

txt = src.read_text(encoding="utf-8", errors="ignore").strip()
dst_raw.write_text(txt + "\n", encoding="utf-8")

clean_lines = []
for line in txt.splitlines():
    stripped = line.strip()
    if stripped.startswith("```"):
        continue
    clean_lines.append(line)

txt = "\n".join(clean_lines).strip()

if "import sut" not in txt and "from sut import" not in txt:
    txt = "import sut\n\n" + txt

dst.write_text(txt + "\n", encoding="utf-8")
print(dst)
PY
echo "[3/8] Checking SUT import/compile..."
cd "$RUNNER" || exit 1

set +e
"$PYTHON_BIN" -m py_compile sut.py > "$LOG_DIR/py_compile_sut.stdout.log" 2> "$LOG_DIR/py_compile_sut.stderr.log"
PYCOMPILE_SUT_RC=$?
"$PYTHON_BIN" - <<'PY' > "$LOG_DIR/import_sut.stdout.log" 2> "$LOG_DIR/import_sut.stderr.log"
import sut
print("OK import sut")
PY
IMPORT_RC=$?
set -e

echo "$PYCOMPILE_SUT_RC" > "$METRICS_DIR/py_compile_sut_exit_code.txt"
echo "$IMPORT_RC" > "$METRICS_DIR/import_exit_code.txt"

if [[ "$PYCOMPILE_SUT_RC" -ne 0 ]] || [[ "$IMPORT_RC" -ne 0 ]]; then
  write_status "sut_import_fail" "SUT failed py_compile or import" "" "" "" "" "" 0 0 0
  echo "[WARN] SUT import/compile failed. Strict-zero metrics for this repetition."
  exit 0
fi

echo "[4/8] Checking generated test compilation..."
set +e
"$PYTHON_BIN" -m py_compile tests/test_cluster_llm.py > "$LOG_DIR/py_compile_test.stdout.log" 2> "$LOG_DIR/py_compile_test.stderr.log"
TEST_COMPILE_RC=$?
set -e

echo "$TEST_COMPILE_RC" > "$METRICS_DIR/generated_test_compile_exit_code.txt"

if [[ "$TEST_COMPILE_RC" -ne 0 ]]; then
  write_status "generated_test_compile_fail" "Generated pytest file is not valid Python" "$TEST_COMPILE_RC" "" "" "" "" 0 0 0
  echo "[WARN] Generated test file does not compile. Strict-zero metrics for this repetition."
  exit 0
fi

echo "[5/8] Running raw pytest..."
set +e
timeout "$PYTEST_TIMEOUT_S" env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$PYTHON_BIN" -m pytest -vv --tb=short tests/test_cluster_llm.py \
  > "$LOG_DIR/pytest_raw.stdout.log" \
  2> "$LOG_DIR/pytest_raw.stderr.log"
PYTEST_RAW_RC=$?
set -e

echo "$PYTEST_RAW_RC" > "$METRICS_DIR/pytest_raw_exit_code.txt"

if [ "$PYTEST_RAW_RC" -eq 5 ]; then
  echo "[WARN] Raw pytest collected no tests. Strict-zero metrics for this repetition."
  : > "$METRICS_DIR/skipped_tests.txt"
  write_status "pytest_no_tests_raw" "Pytest collected no tests from generated suite" "$TEST_COMPILE_RC" "$PYTEST_RAW_RC" "" "" "" "0" "0" "0"
  echo "DONE ✅"
  echo "RUN_DIR=$RUN_DIR"
  echo "STATUS=$STATUS_JSON"
  exit 0
fi

cp tests/test_cluster_llm.py tests/test_cluster_llm_sanitized.py
echo "" > "$METRICS_DIR/skipped_tests.txt"

if [[ "$PYTEST_RAW_RC" -ne 0 ]]; then
  echo "[INFO] Raw pytest failed. Attempting sanitisation..."

  python3 - <<PY
from pathlib import Path
import re

test_file = Path("tests/test_cluster_llm_sanitized.py")
stdout = Path("$LOG_DIR/pytest_raw.stdout.log").read_text(errors="ignore")
stderr = Path("$LOG_DIR/pytest_raw.stderr.log").read_text(errors="ignore")
txt = test_file.read_text(errors="ignore")

combined = stdout + "\n" + stderr
failed = set()

patterns = [
    r"FAILED\s+[^:\s]+::([A-Za-z_][A-Za-z0-9_]*)(?:\[.*?\])?",
    r"tests/test_cluster_llm\.py::([A-Za-z_][A-Za-z0-9_]*)(?:\[.*?\])?\s+FAILED",
    r"_{2,}\s*([A-Za-z_][A-Za-z0-9_]*)\s*_{2,}",
]

for pat in patterns:
    for m in re.finditer(pat, combined):
        name = m.group(1).split("[", 1)[0]
        failed.add(name)

if failed:
    if "import pytest" not in txt:
        txt = "import pytest\n" + txt
    for name in sorted(failed):
        pattern = rf"(?m)^(def\s+{re.escape(name)}\s*\()"
        replacement = '@pytest.mark.skip(reason="Generated test failed during raw validation")\n' + r"\1"
        txt = re.sub(pattern, replacement, txt, count=1)

test_file.write_text(txt)
Path("$METRICS_DIR/skipped_tests.txt").write_text("\n".join(sorted(failed)) + ("\n" if failed else ""))
PY
fi

SKIPPED_COUNT="$(sed '/^$/d' "$METRICS_DIR/skipped_tests.txt" | wc -l)"
echo "$SKIPPED_COUNT" > "$METRICS_DIR/skipped_count.txt"

echo "[6/8] Running final pytest..."
set +e
"$PYTHON_BIN" -m py_compile tests/test_cluster_llm_sanitized.py > "$LOG_DIR/py_compile_sanitized.stdout.log" 2> "$LOG_DIR/py_compile_sanitized.stderr.log"
SAN_COMPILE_RC=$?
timeout "$PYTEST_TIMEOUT_S" env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$PYTHON_BIN" -m pytest -q tests/test_cluster_llm_sanitized.py \
  > "$LOG_DIR/pytest_final.stdout.log" \
  2> "$LOG_DIR/pytest_final.stderr.log"
PYTEST_FINAL_RC=$?
set -e

echo "$SAN_COMPILE_RC" > "$METRICS_DIR/sanitized_test_compile_exit_code.txt"
echo "$PYTEST_FINAL_RC" > "$METRICS_DIR/pytest_final_exit_code.txt"

if [ "$PYTEST_FINAL_RC" -eq 5 ]; then
  echo "[WARN] Final pytest collected no tests after sanitisation. Strict-zero metrics for this repetition."
  : > "$METRICS_DIR/skipped_tests.txt"
  write_status "pytest_no_tests_final" "Pytest collected no tests after sanitisation" "$TEST_COMPILE_RC" "$PYTEST_RAW_RC" "$PYTEST_FINAL_RC" "" "" "0" "0" "0"
  echo "DONE ✅"
  echo "RUN_DIR=$RUN_DIR"
  echo "STATUS=$STATUS_JSON"
  exit 0
fi

if [[ "$SAN_COMPILE_RC" -ne 0 ]] || [[ "$PYTEST_FINAL_RC" -ne 0 ]]; then
  write_status "pytest_final_fail" "Final pytest failed after sanitisation" "$TEST_COMPILE_RC" "$PYTEST_RAW_RC" "$PYTEST_FINAL_RC" "" "" 0 0 0
  echo "[WARN] Final pytest failed. Strict-zero metrics for this repetition."
  exit 0
fi

echo "[6.5/8] Promoting sanitized suite as canonical downstream suite..."
cp tests/test_cluster_llm_sanitized.py tests/test_cluster_llm.py

echo "[7/8] Measuring coverage with pytest-cov..."
set +e
timeout "$PYTEST_TIMEOUT_S" env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$PYTHON_BIN" -m pytest -p pytest_cov -q tests/test_cluster_llm_sanitized.py \
  --cov=sut \
  --cov-branch \
  --cov-report=xml:"$METRICS_DIR/coverage.xml" \
  --cov-report=term \
  > "$LOG_DIR/coverage.stdout.log" \
  2> "$LOG_DIR/coverage.stderr.log"
COV_RC=$?
set -e

echo "$COV_RC" > "$METRICS_DIR/coverage_exit_code.txt"

LINE_COV="0"
BRANCH_COV="0"

if [[ "$COV_RC" -eq 0 ]] && [[ -f "$METRICS_DIR/coverage.xml" ]]; then
  read LINE_COV BRANCH_COV < <(python3 - <<PY
import xml.etree.ElementTree as ET
root = ET.parse("$METRICS_DIR/coverage.xml").getroot()
line = float(root.attrib.get("line-rate", "0")) * 100
branch = float(root.attrib.get("branch-rate", "0")) * 100
print(f"{line:.2f} {branch:.2f}")
PY
)
fi

echo "$LINE_COV" > "$METRICS_DIR/line_coverage_pct.txt"
echo "$BRANCH_COV" > "$METRICS_DIR/branch_coverage_pct.txt"

MUT_RC=""
MUT_SCORE="0"

echo "[8/8] Running mutation testing with mutmut if enabled..."
if [[ "$RUN_MUTATION" == "1" ]]; then
  cat > setup.cfg <<CFG
[mutmut]
paths_to_mutate=sut.py
tests_dir=tests
runner=env PYTHONPATH=$ROOT/_py_overrides\${PYTHONPATH:+:\$PYTHONPATH} PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_cluster_llm_sanitized.py
CFG

  set +e
  timeout "$MUTATION_TIMEOUT_S" env PYTHONPATH="$ROOT/_py_overrides${PYTHONPATH:+:$PYTHONPATH}" PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$PYTHON_BIN" -m mutmut run \
    > "$LOG_DIR/mutmut.stdout.log" \
    2> "$LOG_DIR/mutmut.stderr.log"
  MUT_RC=$?
  set -e

  echo "$MUT_RC" > "$METRICS_DIR/mutmut_exit_code.txt"

  set +e
  timeout "$MUTATION_TIMEOUT_S" env PYTHONPATH="$ROOT/_py_overrides${PYTHONPATH:+:$PYTHONPATH}" PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$PYTHON_BIN" -m mutmut results \
    > "$METRICS_DIR/mutmut_results.txt" \
    2> "$LOG_DIR/mutmut_results.stderr.log"
  RESULTS_RC=$?
  set -e

  echo "$RESULTS_RC" > "$METRICS_DIR/mutmut_results_exit_code.txt"

  MUT_SCORE="$(python3 - <<PY
from pathlib import Path
import json
import re

stdout_p = Path("$LOG_DIR/mutmut.stdout.log")
results_p = Path("$METRICS_DIR/mutmut_results.txt")

stdout_txt = stdout_p.read_text(encoding="utf-8", errors="ignore") if stdout_p.exists() else ""
results_txt = results_p.read_text(encoding="utf-8", errors="ignore") if results_p.exists() else ""

stdout_txt = stdout_txt.replace("\r", "\n")
stdout_txt = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", stdout_txt)

counts = {
    "killed": 0,
    "not_checked": 0,
    "timeout": 0,
    "suspicious": 0,
    "survived": 0,
    "skipped": 0,
}

matches = []
for line in stdout_txt.splitlines():
    m = re.search(r"^\D*(\d+)/(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D*$", line)
    if m:
        matches.append(tuple(int(m.group(i)) for i in range(1, 9)))

if matches:
    done, total_progress, killed, not_checked, timeout, suspicious, survived, skipped = matches[-1]
    counts["killed"] = killed
    counts["not_checked"] = not_checked
    counts["timeout"] = timeout
    counts["suspicious"] = suspicious
    counts["survived"] = survived
    counts["skipped"] = skipped
    total = max(total_progress, sum(counts.values()))
else:
    for line in results_txt.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.search(r"\bnot checked\b", s, flags=re.I):
            counts["not_checked"] += 1
        elif re.search(r"\btimeout\b", s, flags=re.I):
            counts["timeout"] += 1
        elif re.search(r"\bsuspicious\b", s, flags=re.I):
            counts["suspicious"] += 1
        elif re.search(r"\bsurvived\b", s, flags=re.I):
            counts["survived"] += 1
        elif re.search(r"\bskipped\b", s, flags=re.I):
            counts["skipped"] += 1
        elif re.search(r"\bkilled\b", s, flags=re.I):
            counts["killed"] += 1
    total = sum(counts.values())

score = (100.0 * counts["killed"] / total) if total else 0.0

Path("$METRICS_DIR/mutmut_counts.json").write_text(
    json.dumps({"counts": counts, "total": total, "score_pct": round(score, 2)}, indent=2) + "\n",
    encoding="utf-8"
)

print(f"{score:.2f}")
PY
  )"
else
  echo "0" > "$METRICS_DIR/mutmut_exit_code.txt"
fi

echo "$MUT_SCORE" > "$METRICS_DIR/mutation_score_pct.txt"

write_status "ok" "Cluster run evaluated locally with final pytest, coverage and mutation completed" "$TEST_COMPILE_RC" "$PYTEST_RAW_RC" "$PYTEST_FINAL_RC" "$COV_RC" "$MUT_RC" "$LINE_COV" "$BRANCH_COV" "$MUT_SCORE"

echo "DONE ✅"
echo "RUN_DIR=$RUN_DIR"
echo "STATUS=$STATUS_JSON"
