#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAIN_GPT_ROOT="$(cd "$REPO_ROOT/.." && pwd)"

if [[ -f "$REPO_ROOT/config.env" ]]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/config.env"
fi

SUT_NAME="${1:-${SUT_NAME:-}}"
if [[ -z "$SUT_NAME" ]]; then
  echo "[ERROR] usage: run_quixbugs_gpt4o_one_sut.sh SUT_NAME" >&2
  exit 2
fi

SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/quixbugs}"
SUT_DIR="$SUT_ROOT/$SUT_NAME"
MODULE_NAME="${MODULE_NAME:-sut}"
DATASET_LABEL="${DATASET_LABEL:-quixbugs_python}"
MODEL_LABEL="${MODEL_LABEL:-gpt-4o}"

REPEATS="${REPEATS:-5}"
GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-200}"
GEN_EMPTY_RETRY_MAX="${GEN_EMPTY_RETRY_MAX:-15}"
GENERATION_RETRY_SLEEP_S="${GENERATION_RETRY_SLEEP_S:-2}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}"
RUN_MUTATION="${RUN_MUTATION:-1}"

OUT_ROOT="${OUT_ROOT:-$REPO_ROOT/out/_dev_one_sut}"
RUN_ID="${RUN_ID:-run_0001}"
GENERATOR_CMD="${GENERATOR_CMD:-$REPO_ROOT/scripts/generator_cmd_iaedu.sh}"
PROMPT_TEMPLATE="${PROMPT_TEMPLATE:-$REPO_ROOT/prompts/python_quixbugs_zero_shot_v1_retryempty.txt}"

if [[ ! -d "$SUT_DIR" ]]; then
  echo "[ERROR] missing SUT_DIR: $SUT_DIR" >&2
  exit 2
fi

if [[ ! -f "$SUT_DIR/sut.py" ]]; then
  echo "[ERROR] missing sut.py in $SUT_DIR" >&2
  exit 2
fi

if [[ ! -x "$GENERATOR_CMD" ]]; then
  echo "[ERROR] generator command not executable: $GENERATOR_CMD" >&2
  exit 2
fi

SUT_OUT="$OUT_ROOT/$SUT_NAME/$RUN_ID"
mkdir -p "$SUT_OUT"

echo "===== QUIXBUGS GPT-4O ONE_SUT ====="
echo "SUT_NAME=$SUT_NAME"
echo "SUT_DIR=$SUT_DIR"
echo "OUT_ROOT=$OUT_ROOT"
echo "SUT_OUT=$SUT_OUT"
echo "REPEATS=$REPEATS"
echo "GEN_TIMEOUT_S=$GEN_TIMEOUT_S"
echo "GEN_EMPTY_RETRY_MAX=$GEN_EMPTY_RETRY_MAX"
echo "PYTEST_TIMEOUT_S=$PYTEST_TIMEOUT_S"
echo "MUTATION_TIMEOUT_S=$MUTATION_TIMEOUT_S"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "GENERATOR_CMD=$GENERATOR_CMD"
echo

write_status() {
  local out="$1"; shift
  python3 "$REPO_ROOT/tools/write_status.py" --out "$out" "$@"
}

is_nonempty_file() {
  local f="$1"
  [[ -s "$f" ]] && grep -q '[^[:space:]]' "$f"
}

for rep in $(seq 1 "$REPEATS"); do
  REP_ID="1-$rep"
  REP_DIR="$SUT_OUT/$REP_ID"
  GEN_DIR="$REP_DIR/generation"
  RUNNER_DIR="$REP_DIR/runner"
  LOG_DIR="$REP_DIR/logs"
  METRICS_DIR="$REP_DIR/metrics"

  mkdir -p "$GEN_DIR/attempts" "$RUNNER_DIR" "$LOG_DIR" "$METRICS_DIR"

  STATUS_JSON="$METRICS_DIR/status.json"

  # Effective-test counters are filled after the canonical suite is promoted.
  # Defaults keep status writing safe for earlier failure paths.
  top_level_test_functions=""
  skipped_test_functions=""
  effective_test_functions=""

  echo "===== $SUT_NAME rep=$REP_ID ====="

  PROMPT_FILE="$GEN_DIR/final_prompt.txt"
  RAW_FINAL="$GEN_DIR/raw_output.py"
  TRACE="$GEN_DIR/generation_retry_trace.tsv"
  META_JSON="$GEN_DIR/generation_meta.json"

  python3 "$REPO_ROOT/tools/render_quixbugs_prompt.py" \
    --sut-dir "$SUT_DIR" \
    --template "$PROMPT_TEMPLATE" \
    --out "$PROMPT_FILE" > "$LOG_DIR/render_prompt.log" 2>&1

  echo -e "attempt\texit_code\tbytes\tnonempty\tstate" > "$TRACE"

  generation_state="generation_no_output"
  generation_exit_code=0
  generation_attempts=0
  generation_empty_attempts=0
  generation_final_attempt=0

  rm -f "$RAW_FINAL"

  for attempt in $(seq 1 "$GEN_EMPTY_RETRY_MAX"); do
    generation_attempts="$attempt"
    attempt_raw="$GEN_DIR/attempts/attempt_${attempt}.raw.py"
    attempt_stderr="$GEN_DIR/attempts/attempt_${attempt}.stderr.log"

    timeout "$GEN_TIMEOUT_S" "$GENERATOR_CMD" "$PROMPT_FILE" > "$attempt_raw" 2> "$attempt_stderr"
    rc=$?
    bytes=$(wc -c < "$attempt_raw" | tr -d ' ')

    if [[ "$rc" -ne 0 ]]; then
      generation_exit_code="$rc"
      generation_state="generation_failed"
      echo -e "$attempt\t$rc\t$bytes\t0\tnonzero_exit" >> "$TRACE"
      break
    fi

    if is_nonempty_file "$attempt_raw"; then
      generation_exit_code=0
      generation_state="nonempty_success"
      generation_final_attempt="$attempt"
      cp "$attempt_raw" "$RAW_FINAL"
      echo -e "$attempt\t$rc\t$bytes\t1\tnonempty_success" >> "$TRACE"
      break
    fi

    generation_empty_attempts=$((generation_empty_attempts + 1))
    echo -e "$attempt\t$rc\t$bytes\t0\tempty" >> "$TRACE"
    sleep "$GENERATION_RETRY_SLEEP_S"
  done

  python3 - "$META_JSON" <<PY
import json
from pathlib import Path
data = {
  "dataset": "$DATASET_LABEL",
  "model": "$MODEL_LABEL",
  "sut_name": "$SUT_NAME",
  "repeat": $rep,
  "rep_id": "$REP_ID",
  "generation_state": "$generation_state",
  "generation_exit_code": $generation_exit_code,
  "generation_attempts": $generation_attempts,
  "generation_empty_attempts": $generation_empty_attempts,
  "generation_final_attempt": $generation_final_attempt,
  "gen_timeout_s": $GEN_TIMEOUT_S,
  "gen_empty_retry_max": $GEN_EMPTY_RETRY_MAX,
  "generation_retry_sleep_s": $GENERATION_RETRY_SLEEP_S,
}
Path("$META_JSON").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

  if [[ "$generation_state" != "nonempty_success" ]]; then
    write_status "$STATUS_JSON" \
      --set dataset="$DATASET_LABEL" \
      --set language="python" \
      --set model="$MODEL_LABEL" \
      --set sut_name="$SUT_NAME" \
      --set module_name="$MODULE_NAME" \
      --set run_id="$RUN_ID" \
      --set repeat="$rep" \
      --set rep_id="$REP_ID" \
      --set status="$generation_state" \
      --set note="generation did not produce a usable non-empty output" \
      --set generation_exit_code="$generation_exit_code" \
      --set generation_attempts="$generation_attempts" \
      --set generation_empty_attempts="$generation_empty_attempts" \
      --set generation_final_attempt="$generation_final_attempt" \
      --set line_coverage_pct="" \
      --set branch_coverage_pct="" \
      --set mutation_score_pct="" \
      --set run_mutation="$RUN_MUTATION" \
      --set run_dir="$REP_DIR"
    echo "[REP $REP_ID] status=$generation_state"
    continue
  fi

  cp "$SUT_DIR/sut.py" "$RUNNER_DIR/sut.py"
  cp "$RAW_FINAL" "$RUNNER_DIR/test_generated_raw.py"

  (
    cd "$RUNNER_DIR" || exit 1

    python3 -m py_compile sut.py > "$LOG_DIR/py_compile_sut.log" 2>&1
    sut_compile_rc=$?
    echo "$sut_compile_rc" > "$METRICS_DIR/sut_compile_exit_code.txt"
    if [[ "$sut_compile_rc" -ne 0 ]]; then
      exit 30
    fi

    python3 -m py_compile test_generated_raw.py > "$LOG_DIR/py_compile_generated.log" 2>&1
    gen_compile_rc=$?
    echo "$gen_compile_rc" > "$METRICS_DIR/generated_test_compile_exit_code.txt"
    if [[ "$gen_compile_rc" -ne 0 ]]; then
      exit 31
    fi
  )
  compile_stage_rc=$?

  if [[ "$compile_stage_rc" -eq 30 ]]; then
    write_status "$STATUS_JSON" \
      --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
      --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
      --set repeat="$rep" --set rep_id="$REP_ID" --set status="sut_compile_fail" \
      --set note="sut.py failed py_compile" \
      --set generation_exit_code="$generation_exit_code" \
      --set generation_attempts="$generation_attempts" \
      --set generation_empty_attempts="$generation_empty_attempts" \
      --set generation_final_attempt="$generation_final_attempt" \
      --set line_coverage_pct="" --set branch_coverage_pct="" --set mutation_score_pct="" \
      --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
    echo "[REP $REP_ID] status=sut_compile_fail"
    continue
  elif [[ "$compile_stage_rc" -eq 31 ]]; then
    write_status "$STATUS_JSON" \
      --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
      --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
      --set repeat="$rep" --set rep_id="$REP_ID" --set status="generated_test_compile_fail" \
      --set note="generated test failed py_compile" \
      --set generation_exit_code="$generation_exit_code" \
      --set generation_attempts="$generation_attempts" \
      --set generation_empty_attempts="$generation_empty_attempts" \
      --set generation_final_attempt="$generation_final_attempt" \
      --set line_coverage_pct="" --set branch_coverage_pct="" --set mutation_score_pct="" \
      --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
    echo "[REP $REP_ID] status=generated_test_compile_fail"
    continue
  elif [[ "$compile_stage_rc" -ne 0 ]]; then
    write_status "$STATUS_JSON" \
      --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
      --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
      --set repeat="$rep" --set rep_id="$REP_ID" --set status="compile_stage_fail" \
      --set note="unexpected compile stage failure" \
      --set generation_exit_code="$generation_exit_code" \
      --set generation_attempts="$generation_attempts" \
      --set generation_empty_attempts="$generation_empty_attempts" \
      --set generation_final_attempt="$generation_final_attempt" \
      --set line_coverage_pct="" --set branch_coverage_pct="" --set mutation_score_pct="" \
      --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
    echo "[REP $REP_ID] status=compile_stage_fail"
    continue
  fi

  (
    cd "$RUNNER_DIR" || exit 1
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 timeout "$PYTEST_TIMEOUT_S" \
      python3 -m pytest -q test_generated_raw.py --tb=short \
      > "$LOG_DIR/pytest_raw.log" 2>&1
    echo "$?" > "$METRICS_DIR/pytest_raw_exit_code.txt"
  )
  pytest_raw_exit_code="$(cat "$METRICS_DIR/pytest_raw_exit_code.txt")"

  if [[ "$pytest_raw_exit_code" -eq 0 ]]; then
    cp "$RUNNER_DIR/test_generated_raw.py" "$RUNNER_DIR/test_generated.py"
    sanitized_used=0
    pytest_final_exit_code=0
    echo "0" > "$METRICS_DIR/pytest_final_exit_code.txt"
  elif [[ "$pytest_raw_exit_code" -eq 5 ]]; then
    write_status "$STATUS_JSON" \
      --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
      --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
      --set repeat="$rep" --set rep_id="$REP_ID" --set status="pytest_no_tests_raw" \
      --set note="raw pytest collected no tests" \
      --set generation_exit_code="$generation_exit_code" \
      --set generation_attempts="$generation_attempts" \
      --set generation_empty_attempts="$generation_empty_attempts" \
      --set generation_final_attempt="$generation_final_attempt" \
      --set pytest_raw_exit_code="$pytest_raw_exit_code" \
      --set line_coverage_pct="" --set branch_coverage_pct="" --set mutation_score_pct="" \
      --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
    echo "[REP $REP_ID] status=pytest_no_tests_raw"
    continue
  else
    sanitized_used=1
    python3 "$REPO_ROOT/tools/sanitize_pytest_suite.py" \
      --runner-dir "$RUNNER_DIR" \
      --input test_generated_raw.py \
      --output test_generated_sanitized.py \
      --timeout "$PYTEST_TIMEOUT_S" \
      --log "$LOG_DIR/sanitizer_individual_tests.log" \
      > "$LOG_DIR/sanitizer.log" 2>&1
    sanitizer_rc=$?

    if [[ "$sanitizer_rc" -ne 0 ]]; then
      write_status "$STATUS_JSON" \
        --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
        --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
        --set repeat="$rep" --set rep_id="$REP_ID" --set status="sanitization_fail" \
        --set note="sanitizer could not create a usable suite" \
        --set generation_exit_code="$generation_exit_code" \
        --set generation_attempts="$generation_attempts" \
        --set generation_empty_attempts="$generation_empty_attempts" \
        --set generation_final_attempt="$generation_final_attempt" \
        --set pytest_raw_exit_code="$pytest_raw_exit_code" \
        --set line_coverage_pct="" --set branch_coverage_pct="" --set mutation_score_pct="" \
        --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
      echo "[REP $REP_ID] status=sanitization_fail"
      continue
    fi

    (
      cd "$RUNNER_DIR" || exit 1
      PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 timeout "$PYTEST_TIMEOUT_S" \
        python3 -m pytest -q test_generated_sanitized.py --tb=short \
        > "$LOG_DIR/pytest_final.log" 2>&1
      echo "$?" > "$METRICS_DIR/pytest_final_exit_code.txt"
    )
    pytest_final_exit_code="$(cat "$METRICS_DIR/pytest_final_exit_code.txt")"

    if [[ "$pytest_final_exit_code" -ne 0 ]]; then
      write_status "$STATUS_JSON" \
        --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
        --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
        --set repeat="$rep" --set rep_id="$REP_ID" --set status="pytest_final_fail" \
        --set note="final pytest failed after sanitisation" \
        --set generation_exit_code="$generation_exit_code" \
        --set generation_attempts="$generation_attempts" \
        --set generation_empty_attempts="$generation_empty_attempts" \
        --set generation_final_attempt="$generation_final_attempt" \
        --set pytest_raw_exit_code="$pytest_raw_exit_code" \
        --set pytest_final_exit_code="$pytest_final_exit_code" \
        --set line_coverage_pct="" --set branch_coverage_pct="" --set mutation_score_pct="" \
        --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
      echo "[REP $REP_ID] status=pytest_final_fail"
      continue
    fi

    cp "$RUNNER_DIR/test_generated_sanitized.py" "$RUNNER_DIR/test_generated.py"
  fi

  python3 "$REPO_ROOT/tools/analyze_pytest_effective_tests.py" \
    --test-file "$RUNNER_DIR/test_generated.py" \
    --out-json "$METRICS_DIR/effective_tests.json" \
    > "$LOG_DIR/analyze_effective_tests.log" 2>&1

  effective_test_functions="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("effective_test_functions", 0))' "$METRICS_DIR/effective_tests.json")"
  top_level_test_functions="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("top_level_test_functions", 0))' "$METRICS_DIR/effective_tests.json")"
  skipped_test_functions="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("top_level_skipped_test_functions", 0))' "$METRICS_DIR/effective_tests.json")"

  if [[ "$top_level_test_functions" -gt 0 && "$effective_test_functions" -eq 0 ]]; then
    write_status "$STATUS_JSON" \
      --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
      --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
      --set repeat="$rep" --set rep_id="$REP_ID" --set status="no_effective_tests_after_sanitization" \
      --set note="all generated top-level tests were skipped after sanitization" \
      --set generation_exit_code="$generation_exit_code" \
      --set generation_attempts="$generation_attempts" \
      --set generation_empty_attempts="$generation_empty_attempts" \
      --set generation_final_attempt="$generation_final_attempt" \
      --set pytest_raw_exit_code="$pytest_raw_exit_code" \
      --set pytest_final_exit_code="$pytest_final_exit_code" \
      --set sanitized_used="$sanitized_used" \
      --set top_level_test_functions="$top_level_test_functions" \
      --set skipped_test_functions="$skipped_test_functions" \
      --set effective_test_functions="$effective_test_functions" \
      --set line_coverage_pct="" --set branch_coverage_pct="" --set mutation_score_pct="" \
      --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
    echo "[REP $REP_ID] status=no_effective_tests_after_sanitization"
    continue
  fi

  (
    cd "$RUNNER_DIR" || exit 1
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 timeout "$PYTEST_TIMEOUT_S" \
      python3 -m pytest -q test_generated.py \
        -p pytest_cov \
        --cov=sut \
        --cov-branch \
        --cov-report=term-missing \
        --cov-report=xml:coverage.xml \
      > "$LOG_DIR/coverage.log" 2>&1
    echo "$?" > "$METRICS_DIR/coverage_exit_code.txt"
  )
  coverage_exit_code="$(cat "$METRICS_DIR/coverage_exit_code.txt")"

  if [[ "$coverage_exit_code" -ne 0 || ! -f "$RUNNER_DIR/coverage.xml" ]]; then
    write_status "$STATUS_JSON" \
      --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
      --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
      --set repeat="$rep" --set rep_id="$REP_ID" --set status="coverage_fail" \
      --set note="coverage did not produce usable coverage.xml" \
      --set generation_exit_code="$generation_exit_code" \
      --set generation_attempts="$generation_attempts" \
      --set generation_empty_attempts="$generation_empty_attempts" \
      --set generation_final_attempt="$generation_final_attempt" \
      --set pytest_raw_exit_code="$pytest_raw_exit_code" \
      --set pytest_final_exit_code="$pytest_final_exit_code" \
      --set coverage_exit_code="$coverage_exit_code" \
      --set sanitized_used="$sanitized_used" \
      --set top_level_test_functions="$top_level_test_functions" \
      --set skipped_test_functions="$skipped_test_functions" \
      --set effective_test_functions="$effective_test_functions" \
      --set line_coverage_pct="" --set branch_coverage_pct="" --set mutation_score_pct="" \
      --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
    echo "[REP $REP_ID] status=coverage_fail"
    continue
  fi

  python3 "$REPO_ROOT/tools/parse_coverage_xml.py" \
    --xml "$RUNNER_DIR/coverage.xml" \
    --out-json "$METRICS_DIR/coverage_metrics.json" \
    > "$LOG_DIR/parse_coverage.log" 2>&1

  line_cov="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("line_coverage_pct") or "")' "$METRICS_DIR/coverage_metrics.json")"
  branch_cov="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("branch_coverage_pct") or "")' "$METRICS_DIR/coverage_metrics.json")"

  mutation_exit_code=""
  mutation_score=""
  mutation_status_note="mutation disabled"

  if [[ "$RUN_MUTATION" == "1" ]]; then
    # Important: mutmut may discover test_*.py files from tests_dir=.
    # Keep only the canonical promoted suite executable in the runner.
    # Raw/sanitized intermediate suites are preserved outside pytest discovery.
    NONCANONICAL_DIR="$REP_DIR/noncanonical_generated_tests"
    mkdir -p "$NONCANONICAL_DIR"

    for extra_test in test_generated_raw.py test_generated_sanitized.py; do
      if [[ -f "$RUNNER_DIR/$extra_test" ]]; then
        cp "$RUNNER_DIR/$extra_test" "$NONCANONICAL_DIR/$extra_test"
        mv "$RUNNER_DIR/$extra_test" "$RUNNER_DIR/${extra_test}.audit.txt"
      fi
    done

    cat > "$RUNNER_DIR/setup.cfg" <<CFG
[mutmut]
paths_to_mutate=sut.py
tests_dir=.
runner=python -m pytest -q test_generated.py
CFG

    (
      cd "$RUNNER_DIR" || exit 1
      PYTHONPATH="$MAIN_GPT_ROOT/_py_overrides:${PYTHONPATH:-}" \
      PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
      timeout "$MUTATION_TIMEOUT_S" python3 -m mutmut run \
        > "$LOG_DIR/mutmut.stdout.log" 2> "$LOG_DIR/mutmut.stderr.log"
      echo "$?" > "$METRICS_DIR/mutmut_exit_code.txt"
    )
    mutation_exit_code="$(cat "$METRICS_DIR/mutmut_exit_code.txt")"

    python3 "$REPO_ROOT/tools/parse_mutmut_stdout.py" \
      --stdout "$LOG_DIR/mutmut.stdout.log" \
      --stats-json "$RUNNER_DIR/mutants/mutmut-stats.json" \
      --out-json "$METRICS_DIR/mutmut_counts.json" \
      > "$LOG_DIR/parse_mutmut.log" 2>&1

    mutation_score="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1])).get("mutation_score_pct"); print("" if v is None else v)' "$METRICS_DIR/mutmut_counts.json")"

    if [[ "$mutation_exit_code" -ne 0 ]]; then
      write_status "$STATUS_JSON" \
        --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
        --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
        --set repeat="$rep" --set rep_id="$REP_ID" --set status="mutation_fail" \
        --set note="mutmut exited non-zero or timed out" \
        --set generation_exit_code="$generation_exit_code" \
        --set generation_attempts="$generation_attempts" \
        --set generation_empty_attempts="$generation_empty_attempts" \
        --set generation_final_attempt="$generation_final_attempt" \
        --set pytest_raw_exit_code="$pytest_raw_exit_code" \
        --set pytest_final_exit_code="$pytest_final_exit_code" \
        --set coverage_exit_code="$coverage_exit_code" \
        --set mutmut_exit_code="$mutation_exit_code" \
        --set sanitized_used="$sanitized_used" \
        --set top_level_test_functions="$top_level_test_functions" \
        --set skipped_test_functions="$skipped_test_functions" \
        --set effective_test_functions="$effective_test_functions" \
        --set line_coverage_pct="$line_cov" \
        --set branch_coverage_pct="$branch_cov" \
        --set mutation_score_pct="$mutation_score" \
        --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
      echo "[REP $REP_ID] status=mutation_fail"
      continue
    fi

    if [[ -z "$mutation_score" ]]; then
      write_status "$STATUS_JSON" \
        --set dataset="$DATASET_LABEL" --set language="python" --set model="$MODEL_LABEL" \
        --set sut_name="$SUT_NAME" --set module_name="$MODULE_NAME" --set run_id="$RUN_ID" \
        --set repeat="$rep" --set rep_id="$REP_ID" --set status="mutation_parse_fail" \
        --set note="mutmut completed but mutation score could not be parsed" \
        --set generation_exit_code="$generation_exit_code" \
        --set generation_attempts="$generation_attempts" \
        --set generation_empty_attempts="$generation_empty_attempts" \
        --set generation_final_attempt="$generation_final_attempt" \
        --set pytest_raw_exit_code="$pytest_raw_exit_code" \
        --set pytest_final_exit_code="$pytest_final_exit_code" \
        --set coverage_exit_code="$coverage_exit_code" \
        --set mutmut_exit_code="$mutation_exit_code" \
        --set sanitized_used="$sanitized_used" \
        --set top_level_test_functions="$top_level_test_functions" \
        --set skipped_test_functions="$skipped_test_functions" \
        --set effective_test_functions="$effective_test_functions" \
        --set line_coverage_pct="$line_cov" \
        --set branch_coverage_pct="$branch_cov" \
        --set mutation_score_pct="" \
        --set run_mutation="$RUN_MUTATION" --set run_dir="$REP_DIR"
      echo "[REP $REP_ID] status=mutation_parse_fail"
      continue
    fi

    mutation_status_note="ok"
  fi

  write_status "$STATUS_JSON" \
    --set dataset="$DATASET_LABEL" \
    --set language="python" \
    --set model="$MODEL_LABEL" \
    --set sut_name="$SUT_NAME" \
    --set module_name="$MODULE_NAME" \
    --set run_id="$RUN_ID" \
    --set repeat="$rep" \
    --set rep_id="$REP_ID" \
    --set status="ok" \
    --set note="$mutation_status_note" \
    --set generation_exit_code="$generation_exit_code" \
    --set generation_attempts="$generation_attempts" \
    --set generation_empty_attempts="$generation_empty_attempts" \
    --set generation_final_attempt="$generation_final_attempt" \
    --set pytest_raw_exit_code="$pytest_raw_exit_code" \
    --set pytest_final_exit_code="$pytest_final_exit_code" \
    --set coverage_exit_code="$coverage_exit_code" \
    --set mutmut_exit_code="$mutation_exit_code" \
    --set sanitized_used="$sanitized_used" \
    --set top_level_test_functions="$top_level_test_functions" \
    --set skipped_test_functions="$skipped_test_functions" \
    --set effective_test_functions="$effective_test_functions" \
    --set line_coverage_pct="$line_cov" \
    --set branch_coverage_pct="$branch_cov" \
    --set mutation_score_pct="$mutation_score" \
    --set run_mutation="$RUN_MUTATION" \
    --set run_dir="$REP_DIR"

  echo "[REP $REP_ID] status=ok line=$line_cov branch=$branch_cov mutation=${mutation_score:-NA}"
done

echo
echo "===== ONE_SUT DONE: $SUT_NAME ====="
find "$SUT_OUT" -path '*/metrics/status.json' | sort
