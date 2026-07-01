#!/usr/bin/env bash
set -u
set -o pipefail

REPO="${REPO:-$HOME/projetos/llm_test_generation_gpt4o/bugsinpy_gpt4o}"
SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/BugsInPy_OK}"
TARGET_MAP="${TARGET_MAP:-$REPO/configs/bugsinpy_gpt4o_target_map.tsv}"
OUT_BASE="${OUT_BASE:-$REPO/out/_dev_bugsinpy_gpt4o_dataset_full}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

FULL_ONE_SUT="${FULL_ONE_SUT:-$REPO/scripts/run_bugsinpy_gpt4o_one_sut_full.sh}"
MODEL_NAME="${MODEL_NAME:-gpt-4o-iaedu}"
AGGREGATOR="$REPO/tools/aggregate_bugsinpy_gpt4o_status.py"

REPEATS="${REPEATS:-5}"
RUN_ID="${RUN_ID:-1}"
ONLY_SUTS="${ONLY_SUTS:-}"

DRY_RUN="${DRY_RUN:-1}"
RUN_MUTATION="${RUN_MUTATION:-1}"

GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-200}"
GEN_EMPTY_RETRY_MAX="${GEN_EMPTY_RETRY_MAX:-15}"
GENERATION_RETRY_SLEEP_S="${GENERATION_RETRY_SLEEP_S:-2}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}"

if [ ! -f "$TARGET_MAP" ]; then
  echo "ERRO: target map nao existe: $TARGET_MAP"
  exit 2
fi

if [ ! -x "$FULL_ONE_SUT" ]; then
  echo "ERRO: full one_sut nao existe ou nao e executavel: $FULL_ONE_SUT"
  exit 3
fi

mkdir -p "$OUT_BASE"

TRACE="$OUT_BASE/launcher_trace.tsv"
printf "timestamp\tsut_id\ttarget_module\trep\trc\n" > "$TRACE"

echo "===== BUGSINPY ${MODEL_NAME} DATASET FULL LAUNCHER ====="
echo "REPO=$REPO"
echo "SUT_ROOT=$SUT_ROOT"
echo "TARGET_MAP=$TARGET_MAP"
echo "OUT_BASE=$OUT_BASE"
echo "FULL_ONE_SUT=$FULL_ONE_SUT"
echo "MODEL_NAME=$MODEL_NAME"
echo "REPEATS=$REPEATS"
echo "RUN_ID=$RUN_ID"
echo "ONLY_SUTS=$ONLY_SUTS"
echo "DRY_RUN=$DRY_RUN"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "GEN_TIMEOUT_S=$GEN_TIMEOUT_S"
echo "GEN_EMPTY_RETRY_MAX=$GEN_EMPTY_RETRY_MAX"
echo "GENERATION_RETRY_SLEEP_S=$GENERATION_RETRY_SLEEP_S"
echo "PYTEST_TIMEOUT_S=$PYTEST_TIMEOUT_S"
echo "MUTATION_TIMEOUT_S=$MUTATION_TIMEOUT_S"
echo

contains_sut() {
  local wanted="$1"

  if [ -z "$ONLY_SUTS" ]; then
    return 0
  fi

  for s in $ONLY_SUTS; do
    if [ "$s" = "$wanted" ]; then
      return 0
    fi
  done

  return 1
}

TOTAL_REQUESTED_REPS=0
FAILED_COMMANDS=0

while IFS=$'\t' read -r sut_id target_module rest; do
  sut_id="${sut_id//$'\r'/}"
  target_module="${target_module//$'\r'/}"

  if [ -z "$sut_id" ] || [ "$sut_id" = "sut_id" ]; then
    continue
  fi

  if ! contains_sut "$sut_id"; then
    continue
  fi

  echo "===== SUT $sut_id -> $target_module ====="

  for rep in $(seq 1 "$REPEATS"); do
    TOTAL_REQUESTED_REPS=$((TOTAL_REQUESTED_REPS + 1))

    echo "--- REP $rep/$REPEATS: $sut_id ---"

    set +e
    REPO="$REPO" \
    SUT_ROOT="$SUT_ROOT" \
    TARGET_MAP="$TARGET_MAP" \
    OUT_BASE="$OUT_BASE" \
    PYTHON_BIN="$PYTHON_BIN" \
    MODEL_NAME="$MODEL_NAME" \
    SUT_ID="$sut_id" \
    REP="$rep" \
    RUN_ID="$RUN_ID" \
    DRY_RUN="$DRY_RUN" \
    RUN_MUTATION="$RUN_MUTATION" \
    GEN_TIMEOUT_S="$GEN_TIMEOUT_S" \
    GEN_EMPTY_RETRY_MAX="$GEN_EMPTY_RETRY_MAX" \
    GENERATION_RETRY_SLEEP_S="$GENERATION_RETRY_SLEEP_S" \
    PYTEST_TIMEOUT_S="$PYTEST_TIMEOUT_S" \
    MUTATION_TIMEOUT_S="$MUTATION_TIMEOUT_S" \
      "$FULL_ONE_SUT"
    RC=$?
    set -u

    printf "%s\t%s\t%s\t%s\t%s\n" "$(date -Is)" "$sut_id" "$target_module" "$rep" "$RC" >> "$TRACE"

    if [ "$RC" -ne 0 ]; then
      FAILED_COMMANDS=$((FAILED_COMMANDS + 1))
      echo "WARN: command failed: sut=$sut_id rep=$rep rc=$RC"
    else
      echo "OK: sut=$sut_id rep=$rep"
    fi
  done

  echo
done < "$TARGET_MAP"

echo "===== AGGREGATING ====="

if [ -f "$AGGREGATOR" ]; then
  set +e
  "$PYTHON_BIN" "$AGGREGATOR" --out-base "$OUT_BASE"
  AGG_RC=$?
  set -u
  echo "AGGREGATOR_RC=$AGG_RC"
else
  echo "WARN: aggregator nao encontrado: $AGGREGATOR"
fi

echo
echo "===== DONE DATASET FULL LAUNCHER ====="
echo "TOTAL_REQUESTED_REPS=$TOTAL_REQUESTED_REPS"
echo "FAILED_COMMANDS=$FAILED_COMMANDS"
echo "OUT_BASE=$OUT_BASE"
echo "TRACE=$TRACE"

exit 0
