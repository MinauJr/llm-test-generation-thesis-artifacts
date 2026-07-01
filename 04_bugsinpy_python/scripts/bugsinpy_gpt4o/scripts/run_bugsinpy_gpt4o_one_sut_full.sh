export MUTANT_UNDER_TEST="${MUTANT_UNDER_TEST:-}"
#!/usr/bin/env bash
set -u
set -o pipefail

REPO="${REPO:-$HOME/projetos/llm_test_generation_gpt4o/bugsinpy_gpt4o}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MODEL_NAME="${MODEL_NAME:-gpt-4o-iaedu}"

DRY_RUN="${DRY_RUN:-1}"
RUN_MUTATION="${RUN_MUTATION:-1}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}"

ONE_SUT="$REPO/scripts/run_bugsinpy_gpt4o_one_sut.sh"
RAW_VALIDATOR="$REPO/tools/validate_bugsinpy_generated_pytest.py"
SANITIZER="$REPO/tools/sanitize_and_validate_bugsinpy_pytest.py"
COVERAGE_TOOL="$REPO/tools/run_bugsinpy_coverage.py"
MUTATION_TOOL="$REPO/tools/run_bugsinpy_mutation_flat.py"

if [ ! -x "$ONE_SUT" ]; then
  echo "ERRO: one_sut base nao existe ou nao e executavel: $ONE_SUT"
  exit 2
fi

for f in "$RAW_VALIDATOR" "$SANITIZER" "$COVERAGE_TOOL" "$MUTATION_TOOL"; do
  if [ ! -f "$f" ]; then
    echo "ERRO: ferramenta em falta: $f"
    exit 3
  fi
done

echo "===== BUGSINPY ${MODEL_NAME} ONE_SUT FULL PIPELINE ====="
echo "REPO=$REPO"
echo "ONE_SUT=$ONE_SUT"
echo "MODEL_NAME=$MODEL_NAME"
echo "RAW_VALIDATOR=$RAW_VALIDATOR"
echo "SANITIZER=$SANITIZER"
echo "COVERAGE_TOOL=$COVERAGE_TOOL"
echo "MUTATION_TOOL=$MUTATION_TOOL"
echo "DRY_RUN=$DRY_RUN"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "PYTEST_TIMEOUT_S=$PYTEST_TIMEOUT_S"
echo "MUTATION_TIMEOUT_S=$MUTATION_TIMEOUT_S"

set +e
"$ONE_SUT" "$@"
BASE_RC=$?
set -u

echo
echo "BASE_RC=$BASE_RC"

OUT_BASE="${OUT_BASE:-$REPO/out/_dev_bugsinpy_gpt4o_one_sut}"
SUT_ID_EFFECTIVE="${SUT_ID:-${1:-}}"

if [ -z "$SUT_ID_EFFECTIVE" ]; then
  echo "WARN: SUT_ID nao definido; nao consigo resolver status para pipeline."
  exit "$BASE_RC"
fi

STATUS_FILE="$(find "$OUT_BASE/$SUT_ID_EFFECTIVE" -path '*/metrics/status.json' -type f 2>/dev/null | sort | tail -n 1 || true)"

if [ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ]; then
  echo "ERRO: status.json nao encontrado em OUT_BASE=$OUT_BASE SUT_ID=$SUT_ID_EFFECTIVE"
  exit 4
fi

RUN_DIR="$(dirname "$(dirname "$STATUS_FILE")")"

echo "STATUS_FILE=$STATUS_FILE"
echo "RUN_DIR=$RUN_DIR"

CURRENT_STATUS="$("$PYTHON_BIN" - "$STATUS_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print(d.get("status", ""))
PY
)"

echo "CURRENT_STATUS=$CURRENT_STATUS"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN=1: full pipeline stops after context/prompt generation."
  exit "$BASE_RC"
fi

if [ "$BASE_RC" -ne 0 ]; then
  echo "WARN: base one_sut returned non-zero rc=$BASE_RC; not continuing."
  exit "$BASE_RC"
fi

if [ "$CURRENT_STATUS" != "generation_ready" ]; then
  echo "WARN: expected generation_ready before validation, got: $CURRENT_STATUS"
  echo "Pipeline stops here."
  exit 0
fi

echo

LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

echo "===== STEP A0 — normalize generated pytest file ====="
python3 "$REPO/tools/normalize_bugsinpy_generated_test.py" \
  --run-dir "$RUN_DIR" \
  > "$LOG_DIR/normalize_generated_test.stdout.log" \
  2> "$LOG_DIR/normalize_generated_test.stderr.log" || true

echo "===== STEP A — raw pytest validator ====="
set +e
"$PYTHON_BIN" "$RAW_VALIDATOR" \
  --run-dir "$RUN_DIR" \
  --pytest-timeout-s "$PYTEST_TIMEOUT_S"
RAW_VALIDATOR_RC=$?
set -u
echo "RAW_VALIDATOR_RC=$RAW_VALIDATOR_RC"

CURRENT_STATUS="$("$PYTHON_BIN" - "$STATUS_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print(d.get("status", ""))
PY
)"
echo "STATUS_AFTER_RAW=$CURRENT_STATUS"

if [ "$CURRENT_STATUS" = "pytest_raw_fail" ]; then
  echo
  echo "===== STEP B — sanitization + final pytest ====="
  set +e
  "$PYTHON_BIN" "$SANITIZER" \
    --run-dir "$RUN_DIR" \
    --pytest-timeout-s "$PYTEST_TIMEOUT_S"
  SANITIZER_RC=$?
  set -u
  echo "SANITIZER_RC=$SANITIZER_RC"

  CURRENT_STATUS="$("$PYTHON_BIN" - "$STATUS_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print(d.get("status", ""))
PY
)"
  echo "STATUS_AFTER_SANITIZATION=$CURRENT_STATUS"
else
  echo "Sanitization skipped because raw status is: $CURRENT_STATUS"
fi

if [ "$CURRENT_STATUS" != "pytest_raw_pass" ] && [ "$CURRENT_STATUS" != "pytest_final_pass" ]; then
  echo "Pipeline stops before coverage because pytest did not reach a pass state."
  echo "FINAL_STATUS=$CURRENT_STATUS"
  exit 0
fi

echo
echo "===== STEP C — coverage ====="
set +e
"$PYTHON_BIN" "$COVERAGE_TOOL" \
  --run-dir "$RUN_DIR" \
  --pytest-timeout-s "$PYTEST_TIMEOUT_S"
COVERAGE_RC=$?
set -u
echo "COVERAGE_RC=$COVERAGE_RC"

CURRENT_STATUS="$("$PYTHON_BIN" - "$STATUS_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print(d.get("status", ""))
PY
)"
echo "STATUS_AFTER_COVERAGE=$CURRENT_STATUS"

COVERAGE_AVAILABLE="$("$PYTHON_BIN" - "$STATUS_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print("1" if d.get("coverage_available") else "0")
PY
)"

if [ "$COVERAGE_AVAILABLE" != "1" ]; then
  echo "Pipeline stops before mutation because coverage_available is not true."
  echo "FINAL_STATUS=$CURRENT_STATUS"
  exit 0
fi

if [ "$RUN_MUTATION" != "1" ]; then
  echo "RUN_MUTATION=$RUN_MUTATION: mutation skipped."
  echo "FINAL_STATUS=$CURRENT_STATUS"
  exit 0
fi

echo
echo "===== STEP D — mutation flat ====="
MUTATION_RC=0

if [[ "${RUN_MUTATION:-1}" == "1" ]]; then
  set +e
  python3 "$MUTATION_TOOL" \
    --run-dir "$RUN_DIR" \
    --mutation-timeout-s "$MUTATION_TIMEOUT_S" \
    2>&1 | tee "$LOG_DIR/mutmut.full_wrapper.log"
  MUTATION_RC=${PIPESTATUS[0]}
  set -e
else
  echo "SKIP mutation because RUN_MUTATION=${RUN_MUTATION:-}"
fi

echo "MUTATION_RC=$MUTATION_RC"

FINAL_STATUS="$(python3 -c 'import json,sys; from pathlib import Path; p=Path(sys.argv[1]); print((json.loads(p.read_text(encoding="utf-8")).get("status") or "unknown") if p.exists() else "missing_status")' "$STATUS_FILE" 2>/dev/null || echo unknown)"

echo "===== FULL PIPELINE DONE ====="
echo "FINAL_STATUS=$FINAL_STATUS"
echo "STATUS_FILE=$STATUS_FILE"
echo "RUN_DIR=$RUN_DIR"

"$PYTHON_BIN" - "$STATUS_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))

for k in [
    "sut_id",
    "target_module",
    "status",
    "generation_attempts",
    "generation_empty_attempts",
    "pytest_raw_exit_code",
    "pytest_final_exit_code",
    "coverage_available",
    "line_pct",
    "branch_pct",
    "mutation_available",
    "mutation_score_pct",
    "mutmut_counts",
]:
    print(f"{k}={d.get(k)}")
PY

exit 0
