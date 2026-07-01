#!/usr/bin/env bash
set -u
set -o pipefail

REPO="${REPO:-$HOME/projetos/llm_test_generation_gpt4o/bugsinpy_gpt4o}"
TARGET_MAP="${TARGET_MAP:-$REPO/configs/bugsinpy_gpt4o_target_map.tsv}"
SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/BugsInPy_OK}"
OUT_BASE="${OUT_BASE:-$REPO/out/_dev_bugsinpy_gpt4o_dataset_dryrun}"

REPEATS="${REPEATS:-5}"
RUN_ID="${RUN_ID:-1}"
ONLY_SUTS="${ONLY_SUTS:-}"
DRY_RUN="${DRY_RUN:-1}"

GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-200}"
GEN_EMPTY_RETRY_MAX="${GEN_EMPTY_RETRY_MAX:-15}"
GENERATION_RETRY_SLEEP_S="${GENERATION_RETRY_SLEEP_S:-2}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}"
RUN_MUTATION="${RUN_MUTATION:-1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$OUT_BASE" "$OUT_BASE/_logs"

TRACE="$OUT_BASE/launcher_trace.tsv"
{
  echo -e "timestamp\tsut_id\ttarget_module\trep\trc"
} > "$TRACE"

contains_sut() {
  local wanted="$1"
  if [ -z "$ONLY_SUTS" ]; then
    return 0
  fi
  for x in $ONLY_SUTS; do
    if [ "$x" = "$wanted" ]; then
      return 0
    fi
  done
  return 1
}

echo "===== BUGSINPY GPT-4o DATASET LAUNCHER ====="
echo "REPO=$REPO"
echo "TARGET_MAP=$TARGET_MAP"
echo "SUT_ROOT=$SUT_ROOT"
echo "OUT_BASE=$OUT_BASE"
echo "REPEATS=$REPEATS"
echo "RUN_ID=$RUN_ID"
echo "ONLY_SUTS=$ONLY_SUTS"
echo "DRY_RUN=$DRY_RUN"
echo "GEN_TIMEOUT_S=$GEN_TIMEOUT_S"
echo "GEN_EMPTY_RETRY_MAX=$GEN_EMPTY_RETRY_MAX"
echo "GENERATION_RETRY_SLEEP_S=$GENERATION_RETRY_SLEEP_S"
echo "PYTEST_TIMEOUT_S=$PYTEST_TIMEOUT_S"
echo "MUTATION_TIMEOUT_S=$MUTATION_TIMEOUT_S"
echo "RUN_MUTATION=$RUN_MUTATION"
echo

if [ ! -f "$TARGET_MAP" ]; then
  echo "ERRO: target map nao encontrado: $TARGET_MAP"
  exit 2
fi

TOTAL=0
FAILED=0

while IFS=$'\t' read -r sut_id target_module rest; do
  sut_id="${sut_id//$'\r'/}"
  target_module="${target_module//$'\r'/}"
  rest="${rest//$'\r'/}"

  if [ "$sut_id" = "sut_id" ]; then
    continue
  fi
  if [ -z "$sut_id" ]; then
    continue
  fi
  if ! contains_sut "$sut_id"; then
    continue
  fi

  echo "===== SUT $sut_id -> $target_module ====="

  for rep in $(seq 1 "$REPEATS"); do
    TOTAL=$((TOTAL + 1))
    echo "--- REP $rep/$REPEATS: $sut_id ---"

    SUT_ID="$sut_id" \
    REP="$rep" \
    RUN_ID="$RUN_ID" \
    OUT_BASE="$OUT_BASE" \
    DRY_RUN="$DRY_RUN" \
    GEN_TIMEOUT_S="$GEN_TIMEOUT_S" \
    GEN_EMPTY_RETRY_MAX="$GEN_EMPTY_RETRY_MAX" \
    GENERATION_RETRY_SLEEP_S="$GENERATION_RETRY_SLEEP_S" \
    PYTEST_TIMEOUT_S="$PYTEST_TIMEOUT_S" \
    MUTATION_TIMEOUT_S="$MUTATION_TIMEOUT_S" \
    RUN_MUTATION="$RUN_MUTATION" \
    PYTHON_BIN="$PYTHON_BIN" \
      "$REPO/scripts/run_bugsinpy_gpt4o_one_sut.sh" \
      > "$OUT_BASE/_logs/${sut_id}_rep${rep}.stdout.log" \
      2> "$OUT_BASE/_logs/${sut_id}_rep${rep}.stderr.log"

    RC=$?
    if [ "$RC" -ne 0 ]; then
      FAILED=$((FAILED + 1))
      echo "WARN: $sut_id rep=$rep rc=$RC"
      tail -n 25 "$OUT_BASE/_logs/${sut_id}_rep${rep}.stderr.log" || true
      tail -n 25 "$OUT_BASE/_logs/${sut_id}_rep${rep}.stdout.log" || true
    else
      echo "OK: $sut_id rep=$rep"
    fi

    printf "%s\t%s\t%s\t%s\t%s\n" "$(date -Is)" "$sut_id" "$target_module" "$rep" "$RC" >> "$TRACE"
  done
done < "$TARGET_MAP"

echo
echo "===== AGGREGATING ====="
"$PYTHON_BIN" "$REPO/tools/aggregate_bugsinpy_gpt4o_status.py" --out-base "$OUT_BASE" \
  > "$OUT_BASE/_logs/aggregate.stdout.log" \
  2> "$OUT_BASE/_logs/aggregate.stderr.log"
AGG_RC=$?
cat "$OUT_BASE/_logs/aggregate.stdout.log" || true
if [ "$AGG_RC" -ne 0 ]; then
  echo "WARN: aggregate rc=$AGG_RC"
  cat "$OUT_BASE/_logs/aggregate.stderr.log" || true
fi

echo
echo "===== DONE DATASET LAUNCHER ====="
echo "TOTAL_REQUESTED_REPS=$TOTAL"
echo "FAILED_COMMANDS=$FAILED"
echo "OUT_BASE=$OUT_BASE"
echo "TRACE=$TRACE"

if [ "$FAILED" -ne 0 ]; then
  exit 20
fi
exit 0
