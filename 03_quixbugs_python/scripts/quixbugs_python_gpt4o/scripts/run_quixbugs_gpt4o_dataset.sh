#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$REPO_ROOT/config.env" ]]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/config.env"
fi

SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/quixbugs}"
OUT_ROOT="${OUT_ROOT:-$REPO_ROOT/out/_dev_dataset}"
ONLY_SUTS="${ONLY_SUTS:-}"
SUT_LIST_FILE="${SUT_LIST_FILE:-}"
REPEATS="${REPEATS:-5}"
RUN_MUTATION="${RUN_MUTATION:-1}"

mkdir -p "$OUT_ROOT" "$OUT_ROOT/_logs"

echo "===== QUIXBUGS GPT-4O DATASET LAUNCHER ====="
echo "REPO_ROOT=$REPO_ROOT"
echo "SUT_ROOT=$SUT_ROOT"
echo "OUT_ROOT=$OUT_ROOT"
echo "ONLY_SUTS=$ONLY_SUTS"
echo "SUT_LIST_FILE=$SUT_LIST_FILE"
echo "REPEATS=$REPEATS"
echo "GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-200}"
echo "GEN_EMPTY_RETRY_MAX=${GEN_EMPTY_RETRY_MAX:-15}"
echo "GENERATION_RETRY_SLEEP_S=${GENERATION_RETRY_SLEEP_S:-2}"
echo "PYTEST_TIMEOUT_S=${PYTEST_TIMEOUT_S:-60}"
echo "MUTATION_TIMEOUT_S=${MUTATION_TIMEOUT_S:-180}"
echo "RUN_MUTATION=$RUN_MUTATION"
echo

SELECTED="$OUT_ROOT/selected_suts.txt"
: > "$SELECTED"

if [[ -n "$SUT_LIST_FILE" ]]; then
  if [[ ! -f "$SUT_LIST_FILE" ]]; then
    echo "[ERROR] SUT_LIST_FILE not found: $SUT_LIST_FILE" >&2
    exit 2
  fi
  grep -v '^[[:space:]]*$' "$SUT_LIST_FILE" | sed 's/[[:space:]]*$//' > "$SELECTED"
elif [[ -n "$ONLY_SUTS" ]]; then
  printf "%s\n" "$ONLY_SUTS" \
    | tr ',;' '  ' \
    | tr ' ' '\n' \
    | sed '/^[[:space:]]*$/d' \
    > "$SELECTED"
else
  python3 "$REPO_ROOT/tools/list_quixbugs_python_suts.py" "$SUT_ROOT" > "$SELECTED"
fi

echo "===== SELECTED SUTS ====="
cat "$SELECTED"
echo "SELECTED_COUNT=$(wc -l < "$SELECTED")"
echo

cat > "$OUT_ROOT/effective_config.env" <<CFG
REPEATS=$REPEATS
GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-200}
GEN_EMPTY_RETRY_MAX=${GEN_EMPTY_RETRY_MAX:-15}
GENERATION_RETRY_SLEEP_S=${GENERATION_RETRY_SLEEP_S:-2}
PYTEST_TIMEOUT_S=${PYTEST_TIMEOUT_S:-60}
MUTATION_TIMEOUT_S=${MUTATION_TIMEOUT_S:-180}
RUN_MUTATION=$RUN_MUTATION
SUT_ROOT=$SUT_ROOT
OUT_ROOT=$OUT_ROOT
ONLY_SUTS=$ONLY_SUTS
SUT_LIST_FILE=$SUT_LIST_FILE
CFG

failures=0
started=0

while IFS= read -r sut; do
  [[ -z "$sut" ]] && continue
  started=$((started + 1))

  if [[ ! -d "$SUT_ROOT/$sut" ]]; then
    echo "[ERROR] selected SUT does not exist: $SUT_ROOT/$sut" | tee "$OUT_ROOT/_logs/${sut}.missing.log"
    failures=$((failures + 1))
    continue
  fi

  echo
  echo "===== DATASET SUT $started: $sut ====="

  LOG="$OUT_ROOT/_logs/${sut}.one_sut.log"

  OUT_ROOT="$OUT_ROOT" \
  SUT_ROOT="$SUT_ROOT" \
  REPEATS="$REPEATS" \
  RUN_MUTATION="$RUN_MUTATION" \
  bash "$REPO_ROOT/scripts/run_quixbugs_gpt4o_one_sut.sh" "$sut" 2>&1 | tee "$LOG"

  rc=${PIPESTATUS[0]}
  echo "$rc" > "$OUT_ROOT/_logs/${sut}.one_sut.exit_code"

  if [[ "$rc" -ne 0 ]]; then
    echo "[ERROR] one_sut exited non-zero for $sut rc=$rc"
    failures=$((failures + 1))
  fi
done < "$SELECTED"

echo
echo "===== AGGREGATING DATASET ====="
python3 "$REPO_ROOT/tools/aggregate_quixbugs_gpt4o_results.py" --out-root "$OUT_ROOT" \
  2>&1 | tee "$OUT_ROOT/_logs/aggregate.log"
agg_rc=${PIPESTATUS[0]}

echo
echo "===== DATASET LAUNCHER DONE ====="
echo "started_suts=$started"
echo "launcher_failures=$failures"
echo "aggregate_rc=$agg_rc"
echo "out_root=$OUT_ROOT"

if [[ "$agg_rc" -ne 0 ]]; then
  exit "$agg_rc"
fi

exit 0
