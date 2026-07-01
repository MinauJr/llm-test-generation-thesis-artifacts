#!/usr/bin/env bash
set -u
set -o pipefail

REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ROOT="${ROOT:-$REPO}"
SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/BugsInPy_OK}"
TARGET_MAP="${TARGET_MAP:-$REPO/configs/bugsinpy_gpt4o_target_map.tsv}"
PROMPT_TEMPLATE="${PROMPT_TEMPLATE:-$REPO/prompts/python_bugsinpy_gpt4o_zero_shot_v1.txt}"
OUT_BASE="${OUT_BASE:-$REPO/out/_dev_bugsinpy_gpt4o_one_sut}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MODEL_NAME="${MODEL_NAME:-gpt-4o-iaedu}"

SUT_ID="${SUT_ID:-${1:-}}"
REP="${REP:-1}"
RUN_ID="${RUN_ID:-1}"

REPEATS="${REPEATS:-5}"
GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-200}"
GEN_EMPTY_RETRY_MAX="${GEN_EMPTY_RETRY_MAX:-15}"
GENERATION_RETRY_SLEEP_S="${GENERATION_RETRY_SLEEP_S:-2}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}"
RUN_MUTATION="${RUN_MUTATION:-1}"

DRY_RUN="${DRY_RUN:-1}"

if [ -z "$SUT_ID" ]; then
  echo "ERRO: define SUT_ID ou passa como primeiro argumento."
  echo "Exemplo: SUT_ID=cookiecutter_1f DRY_RUN=1 $0"
  exit 2
fi

if [ ! -f "$TARGET_MAP" ]; then
  echo "ERRO: target map nao existe: $TARGET_MAP"
  exit 3
fi

if [ ! -d "$SUT_ROOT/$SUT_ID" ]; then
  echo "ERRO: SUT dir nao existe: $SUT_ROOT/$SUT_ID"
  exit 4
fi

RESOLVED="$("$PYTHON_BIN" - "$TARGET_MAP" "$SUT_ID" <<'PY'
import csv
import sys
from pathlib import Path

target_map = Path(sys.argv[1])
wanted = sys.argv[2]

with target_map.open(encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for idx, row in enumerate(reader, start=1):
        sut_id = (row.get("sut_id") or "").strip().replace("\r", "")
        target = (row.get("target_module") or "").strip().replace("\r", "")
        if sut_id == wanted:
            print(f"{idx}\t{target}")
            raise SystemExit(0)

raise SystemExit(10)
PY
)"
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "ERRO: SUT_ID nao encontrado no target map: $SUT_ID"
  exit 5
fi

SUT_INDEX="$(printf "%s" "$RESOLVED" | cut -f1 | tr -d '\r')"
TARGET_MODULE="$(printf "%s" "$RESOLVED" | cut -f2 | tr -d '\r')"
COV_TARGET="${COV_TARGET:-${TARGET_MODULE%%.*}}"

RUN_DIR="$OUT_BASE/$SUT_ID/run_$(printf "%04d" "$RUN_ID")/$(printf "%04d" "$SUT_INDEX")-$REP"
RAW_DIR="$RUN_DIR/raw"
LOG_DIR="$RUN_DIR/logs"
METRICS_DIR="$RUN_DIR/metrics"
WORK_DIR="$RUN_DIR/work"
WORK_SUT_DIR="$WORK_DIR/sut"
TESTS_DIR="$WORK_DIR/tests"

mkdir -p "$RAW_DIR" "$LOG_DIR" "$METRICS_DIR" "$WORK_DIR" "$TESTS_DIR"

write_status_json() {
  local final_status="${1:-unknown}"
  local prep_rc="${2:-}"
  local ctx_rc="${3:-}"
  local prompt_rc="${4:-}"
  local gen_rc="${5:-}"
  local gen_attempts="${6:-}"
  local gen_empty_attempts="${7:-}"
  local gen_final_state="${8:-}"
  local gen_output_nonempty="${9:-false}"

  "$PYTHON_BIN" - "$METRICS_DIR/status.json" <<PY
import json
from pathlib import Path

def as_int(v):
    try:
        if v is None or v == "":
            return None
        return int(str(v))
    except Exception:
        return None

status = {
    "dataset": "BugsInPy",
    "language": "python",
    "model": "$MODEL_NAME",
    "sut_id": "$SUT_ID",
    "sut_index": as_int("$SUT_INDEX"),
    "sut_dir": "$SUT_ROOT/$SUT_ID",
    "work_sut_dir": "$WORK_SUT_DIR",
    "target_module": "$TARGET_MODULE",
    "cov_target": "$COV_TARGET",
    "run_id": as_int("$RUN_ID"),
    "rep": as_int("$REP"),
    "status": "$final_status",
    "dry_run": "$DRY_RUN",

    "prep_sut_exit_code": as_int("$prep_rc"),
    "context_exit_code": as_int("$ctx_rc"),
    "render_prompt_exit_code": as_int("$prompt_rc"),

    "generation_exit_code": as_int("$gen_rc"),
    "generation_attempts": as_int("$gen_attempts"),
    "generation_empty_attempts": as_int("$gen_empty_attempts"),
    "generation_final_state": "$gen_final_state",
    "generation_output_nonempty": "$gen_output_nonempty",
    "generation_timeout_s": as_int("$GEN_TIMEOUT_S"),
    "generation_empty_retry_max": as_int("$GEN_EMPTY_RETRY_MAX"),
    "generation_retry_sleep_s": as_int("$GENERATION_RETRY_SLEEP_S"),

    "pytest_timeout_s": as_int("$PYTEST_TIMEOUT_S"),
    "mutation_timeout_s": as_int("$MUTATION_TIMEOUT_S"),
    "run_mutation": "$RUN_MUTATION",

    "pytest_raw_exit_code": None,
    "pytest_final_exit_code": None,
    "coverage_exit_code": None,
    "mutmut_exit_code": None,

    "line_pct": None,
    "branch_pct": None,
    "mutation_score_pct": None,

    "prompt_file": "$RAW_DIR/prompt.txt",
    "model_raw_output_file": "$RAW_DIR/model_raw_output.py.txt",
    "generated_test_file": "$TESTS_DIR/test_gpt_iaedu.py",
}
Path("$METRICS_DIR/status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
PY
}

echo "===== BUGSINPY ${MODEL_NAME} ONE_SUT =====" | tee "$LOG_DIR/runner.log"
echo "REPO=$REPO" | tee -a "$LOG_DIR/runner.log"
echo "ROOT=$ROOT" | tee -a "$LOG_DIR/runner.log"
echo "SUT_ID=$SUT_ID" | tee -a "$LOG_DIR/runner.log"
echo "SUT_INDEX=$SUT_INDEX" | tee -a "$LOG_DIR/runner.log"
echo "SUT_DIR=$SUT_ROOT/$SUT_ID" | tee -a "$LOG_DIR/runner.log"
echo "WORK_SUT_DIR=$WORK_SUT_DIR" | tee -a "$LOG_DIR/runner.log"
echo "TARGET_MODULE=$TARGET_MODULE" | tee -a "$LOG_DIR/runner.log"
echo "COV_TARGET=$COV_TARGET" | tee -a "$LOG_DIR/runner.log"
echo "OUT_BASE=$OUT_BASE" | tee -a "$LOG_DIR/runner.log"
echo "RUN_DIR=$RUN_DIR" | tee -a "$LOG_DIR/runner.log"
echo "MODEL_NAME=$MODEL_NAME" | tee -a "$LOG_DIR/runner.log"
echo "DRY_RUN=$DRY_RUN" | tee -a "$LOG_DIR/runner.log"
echo "REPEATS=$REPEATS" | tee -a "$LOG_DIR/runner.log"
echo "GEN_TIMEOUT_S=$GEN_TIMEOUT_S" | tee -a "$LOG_DIR/runner.log"
echo "GEN_EMPTY_RETRY_MAX=$GEN_EMPTY_RETRY_MAX" | tee -a "$LOG_DIR/runner.log"
echo "GENERATION_RETRY_SLEEP_S=$GENERATION_RETRY_SLEEP_S" | tee -a "$LOG_DIR/runner.log"
echo "PYTEST_TIMEOUT_S=$PYTEST_TIMEOUT_S" | tee -a "$LOG_DIR/runner.log"
echo "MUTATION_TIMEOUT_S=$MUTATION_TIMEOUT_S" | tee -a "$LOG_DIR/runner.log"
echo "RUN_MUTATION=$RUN_MUTATION" | tee -a "$LOG_DIR/runner.log"

echo
echo "[0/5] Preparing isolated SUT workdir..."
"$PYTHON_BIN" "$REPO/tools/prepare_bugsinpy_work_sut.py" \
  --sut-id "$SUT_ID" \
  --target-module "$TARGET_MODULE" \
  --source-dir "$SUT_ROOT/$SUT_ID" \
  --work-dir "$WORK_SUT_DIR" \
  --out-metadata "$RAW_DIR/work_sut_prepare.json" \
  > "$LOG_DIR/prepare_sut.stdout.log" \
  2> "$LOG_DIR/prepare_sut.stderr.log"
PREP_RC=$?
echo "$PREP_RC" > "$METRICS_DIR/prep_sut_exit_code.txt"

if [ "$PREP_RC" -ne 0 ]; then
  echo "WARNING: SUT staging failed with rc=$PREP_RC" | tee -a "$LOG_DIR/runner.log"
  write_status_json "context_prepare_fail" "$PREP_RC" "" "" "" "" "" "" "false"
  echo "DONE status=context_prepare_fail"
  echo "RUN_DIR=$RUN_DIR"
  exit 0
fi


echo "[0B/5] Applying runtime compatibility shims..."
python3 "$REPO/tools/apply_bugsinpy_runtime_shims.py" \
  --run-dir "$RUN_DIR" \
  --work-sut-dir "$WORK_SUT_DIR" \
  --target-module "$TARGET_MODULE" \
  > "$LOG_DIR/runtime_shims.stdout.log" \
  2> "$LOG_DIR/runtime_shims.stderr.log" || true

echo "[1/5] Extracting target context..."
"$PYTHON_BIN" "$REPO/tools/extract_bugsinpy_context.py" \
  --sut-id "$SUT_ID" \
  --sut-dir "$WORK_SUT_DIR" \
  --target-module "$TARGET_MODULE" \
  --out-dir "$RAW_DIR" \
  > "$LOG_DIR/context.stdout.log" \
  2> "$LOG_DIR/context.stderr.log"
CTX_RC=$?
echo "$CTX_RC" > "$METRICS_DIR/context_exit_code.txt"

# Some package-level targets can produce usable context artifacts even when
# the extractor returns a non-zero import-oriented code. In that case, keep
# the original code for auditability, but allow the workflow to continue.
if [ "$CTX_RC" -ne 0 ] && [ -s "$RAW_DIR/target_context.txt" ] && [ -s "$RAW_DIR/module_info.json" ]; then
  echo "WARN: context extractor returned rc=$CTX_RC but target_context.txt and module_info.json exist; continuing with fallback context."
  echo "$CTX_RC" > "$METRICS_DIR/context_exit_code_original.txt"
  CTX_RC=0
  echo "$CTX_RC" > "$METRICS_DIR/context_exit_code.txt"
fi

if [ "$CTX_RC" -ne 0 ]; then
  write_status_json "context_import_fail" "$PREP_RC" "$CTX_RC" "" "" "" "" "" "false"
  echo "DONE status=context_import_fail"
  echo "RUN_DIR=$RUN_DIR"
  exit 0
fi

echo "[2/5] Rendering final prompt..."
"$PYTHON_BIN" "$REPO/tools/render_bugsinpy_prompt.py" \
  --template "$PROMPT_TEMPLATE" \
  --context "$RAW_DIR/target_context.txt" \
  --sut-id "$SUT_ID" \
  --target-module "$TARGET_MODULE" \
  --out "$RAW_DIR/prompt.txt" \
  > "$LOG_DIR/render_prompt.stdout.log" \
  2> "$LOG_DIR/render_prompt.stderr.log"
PROMPT_RC=$?
echo "$PROMPT_RC" > "$METRICS_DIR/render_prompt_exit_code.txt"

if [ "$PROMPT_RC" -ne 0 ]; then
  write_status_json "prompt_render_fail" "$PREP_RC" "$CTX_RC" "$PROMPT_RC" "" "" "" "" "false"
  echo "DONE status=prompt_render_fail"
  echo "RUN_DIR=$RUN_DIR"
  exit 0
fi

if [ "$DRY_RUN" = "1" ]; then
  echo "[3/5] DRY_RUN=1: skipping ${MODEL_NAME} generation."
  write_status_json "context_ready" "$PREP_RC" "$CTX_RC" "$PROMPT_RC" "" "" "" "" "false"
  echo
  echo "DONE status=context_ready"
  echo "RUN_DIR=$RUN_DIR"
  echo "status_json=$METRICS_DIR/status.json"
  echo "prompt=$RAW_DIR/prompt.txt"
  exit 0
fi

echo "[3/5] Calling ${MODEL_NAME} via IAEdu with retry only on empty output..."

ATTEMPTS_DIR="$RAW_DIR/_attempts"
mkdir -p "$ATTEMPTS_DIR"
TRACE_FILE="$RAW_DIR/generation_retry_trace.tsv"
printf "attempt\trc\traw_state\tattempt_dir\n" > "$TRACE_FILE"

GEN_FINAL_RC=0
GEN_ATTEMPTS=0
GEN_EMPTY_ATTEMPTS=0
GEN_FINAL_STATE="not_started"
GEN_OUTPUT_NONEMPTY="false"
FINAL_ATTEMPT_DIR=""

for ATTEMPT in $(seq 1 "$GEN_EMPTY_RETRY_MAX"); do
  GEN_ATTEMPTS="$ATTEMPT"
  ATTEMPT_DIR="$ATTEMPTS_DIR/attempt_$(printf "%02d" "$ATTEMPT")"
  FINAL_ATTEMPT_DIR="$ATTEMPT_DIR"
  rm -rf "$ATTEMPT_DIR"
  mkdir -p "$ATTEMPT_DIR"

  ATTEMPT_RAW="$ATTEMPT_DIR/model_raw_output.py.txt"
  ATTEMPT_ERR="$ATTEMPT_DIR/gpt4o.stderr.log"
  ATTEMPT_META="$ATTEMPT_DIR/generation_meta.tsv"

  {
    echo -e "model\tlang\tframework\tsut_id\ttarget_module\tprompt_file\traw_file\ttimeout_s\tattempt"
    echo -e "gpt-iaedu\tpython\tpytest\t$SUT_ID\t$TARGET_MODULE\t$RAW_DIR/prompt.txt\t$ATTEMPT_RAW\t$GEN_TIMEOUT_S\t$ATTEMPT"
  } > "$ATTEMPT_META"

  echo "  attempt $ATTEMPT/$GEN_EMPTY_RETRY_MAX..."

  set +e
  IAEDU_SECRETS_FILE="${IAEDU_SECRETS_FILE:?}" \
  timeout "$GEN_TIMEOUT_S" \
    "$ROOT/scripts/generator_cmd_iaedu.sh" \
    "$RAW_DIR/prompt.txt" \
    > "$ATTEMPT_RAW" \
    2> "$ATTEMPT_ERR"
  GEN_FINAL_RC=$?
  set -u

  echo "$GEN_FINAL_RC" > "$ATTEMPT_DIR/generation_exit_code.txt"

  if "$PYTHON_BIN" - "$ATTEMPT_RAW" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
raise SystemExit(0 if p.exists() and p.read_text(encoding="utf-8", errors="ignore").strip() else 1)
PY
  then
    GEN_FINAL_STATE="nonempty_success"
    GEN_OUTPUT_NONEMPTY="true"

    cp "$ATTEMPT_RAW" "$RAW_DIR/model_raw_output.py.txt"
    cp "$ATTEMPT_ERR" "$LOG_DIR/gpt4o.stderr.log"
    cp "$ATTEMPT_META" "$RAW_DIR/generation_meta.tsv"
    cp "$ATTEMPT_DIR/generation_exit_code.txt" "$METRICS_DIR/generation_exit_code.txt"
    cp "$ATTEMPT_RAW" "$TESTS_DIR/test_gpt_iaedu.py"

    printf "%s\t%s\tnonempty\t%s\n" "$ATTEMPT" "$GEN_FINAL_RC" "$ATTEMPT_DIR" >> "$TRACE_FILE"
    break
  else
    GEN_EMPTY_ATTEMPTS=$((GEN_EMPTY_ATTEMPTS + 1))
    printf "%s\t%s\tempty\t%s\n" "$ATTEMPT" "$GEN_FINAL_RC" "$ATTEMPT_DIR" >> "$TRACE_FILE"

    if [ "$ATTEMPT" -lt "$GEN_EMPTY_RETRY_MAX" ]; then
      sleep "$GENERATION_RETRY_SLEEP_S"
    fi
  fi
done

echo "$GEN_ATTEMPTS" > "$RAW_DIR/generation_attempts.txt"
echo "$GEN_EMPTY_ATTEMPTS" > "$RAW_DIR/generation_empty_attempts.txt"
echo "$GEN_ATTEMPTS" > "$RAW_DIR/generation_final_attempt.txt"
echo "$GEN_FINAL_STATE" > "$RAW_DIR/generation_final_state.txt"

if [ "$GEN_OUTPUT_NONEMPTY" != "true" ]; then
  : > "$RAW_DIR/model_raw_output.py.txt"
  : > "$TESTS_DIR/test_gpt_iaedu.py"
  echo "$GEN_FINAL_RC" > "$METRICS_DIR/generation_exit_code.txt"
  GEN_FINAL_STATE="no_output_exhausted"
  echo "$GEN_FINAL_STATE" > "$RAW_DIR/generation_final_state.txt"

  write_status_json "generation_no_output" "$PREP_RC" "$CTX_RC" "$PROMPT_RC" "$GEN_FINAL_RC" "$GEN_ATTEMPTS" "$GEN_EMPTY_ATTEMPTS" "$GEN_FINAL_STATE" "$GEN_OUTPUT_NONEMPTY"

  echo
  echo "DONE status=generation_no_output"
  echo "RUN_DIR=$RUN_DIR"
  echo "attempts=$GEN_ATTEMPTS empty_attempts=$GEN_EMPTY_ATTEMPTS"
  echo "trace=$TRACE_FILE"
  exit 0
fi

write_status_json "generation_ready" "$PREP_RC" "$CTX_RC" "$PROMPT_RC" "$GEN_FINAL_RC" "$GEN_ATTEMPTS" "$GEN_EMPTY_ATTEMPTS" "$GEN_FINAL_STATE" "$GEN_OUTPUT_NONEMPTY"

echo
echo "DONE status=generation_ready"
echo "RUN_DIR=$RUN_DIR"
echo "status_json=$METRICS_DIR/status.json"
echo "prompt=$RAW_DIR/prompt.txt"
echo "model_raw_output=$RAW_DIR/model_raw_output.py.txt"
echo "generated_test_file=$TESTS_DIR/test_gpt_iaedu.py"
echo "attempts=$GEN_ATTEMPTS empty_attempts=$GEN_EMPTY_ATTEMPTS"
echo "trace=$TRACE_FILE"

echo
echo "[4/5] Base generation stage completed."
echo "[5/5] Downstream pytest/coverage/mutation are handled by the full wrapper when used."
exit 0
