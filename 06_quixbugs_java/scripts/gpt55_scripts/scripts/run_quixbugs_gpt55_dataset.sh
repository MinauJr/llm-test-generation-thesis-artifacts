#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/quixbugs}"
OUT_ROOT="${OUT_ROOT:-$REPO_ROOT/out/_dev_quixbugs_java_gpt55_dataset}"
ONLY_SUTS="${ONLY_SUTS:-}"
SUT_LIST_FILE="${SUT_LIST_FILE:-}"

REPEATS="${REPEATS:-5}"
GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-200}"
GEN_EMPTY_RETRY_MAX="${GEN_EMPTY_RETRY_MAX:-15}"
GENERATION_RETRY_SLEEP_S="${GENERATION_RETRY_SLEEP_S:-2}"
MVN_TEST_TIMEOUT_S="${MVN_TEST_TIMEOUT_S:-120}"
PIT_TIMEOUT_S="${PIT_TIMEOUT_S:-180}"
RUN_MUTATION="${RUN_MUTATION:-1}"
GENERATOR_CMD="${GENERATOR_CMD:-$REPO_ROOT/scripts/generator_cmd_iaedu.sh}"

mkdir -p "$OUT_ROOT/_logs"

echo "===== QUIXBUGS JAVA GPT-5.5 DATASET LAUNCHER ====="
echo "REPO_ROOT=$REPO_ROOT"
echo "SUT_ROOT=$SUT_ROOT"
echo "OUT_ROOT=$OUT_ROOT"
echo "ONLY_SUTS=$ONLY_SUTS"
echo "SUT_LIST_FILE=$SUT_LIST_FILE"
echo "REPEATS=$REPEATS"
echo "GEN_TIMEOUT_S=$GEN_TIMEOUT_S"
echo "GEN_EMPTY_RETRY_MAX=$GEN_EMPTY_RETRY_MAX"
echo "GENERATION_RETRY_SLEEP_S=$GENERATION_RETRY_SLEEP_S"
echo "MVN_TEST_TIMEOUT_S=$MVN_TEST_TIMEOUT_S"
echo "PIT_TIMEOUT_S=$PIT_TIMEOUT_S"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "GENERATOR_CMD=$GENERATOR_CMD"
echo

selected="$OUT_ROOT/selected_suts.txt"
: > "$selected"

if [ -n "$SUT_LIST_FILE" ]; then
  sed '/^\s*$/d' "$SUT_LIST_FILE" > "$selected"
elif [ -n "$ONLY_SUTS" ]; then
  for s in $ONLY_SUTS; do
    echo "$s" >> "$selected"
  done
else
  find "$SUT_ROOT" -maxdepth 1 -mindepth 1 -type d -name '*_java_*' -printf '%f\n' | sort > "$selected"
fi

echo "===== SELECTED SUTS ====="
cat "$selected"
echo "SELECTED_COUNT=$(wc -l < "$selected")"
echo

# selected_suts.txt is already written directly under OUT_ROOT.
cat > "$OUT_ROOT/effective_config.env" <<EOF
REPO_ROOT=$REPO_ROOT
SUT_ROOT=$SUT_ROOT
OUT_ROOT=$OUT_ROOT
REPEATS=$REPEATS
GEN_TIMEOUT_S=$GEN_TIMEOUT_S
GEN_EMPTY_RETRY_MAX=$GEN_EMPTY_RETRY_MAX
GENERATION_RETRY_SLEEP_S=$GENERATION_RETRY_SLEEP_S
MVN_TEST_TIMEOUT_S=$MVN_TEST_TIMEOUT_S
PIT_TIMEOUT_S=$PIT_TIMEOUT_S
RUN_MUTATION=$RUN_MUTATION
GENERATOR_CMD=$GENERATOR_CMD
EOF

started=0
launcher_failures=0

while IFS= read -r sut; do
  [ -n "$sut" ] || continue
  started=$((started + 1))

  echo
  echo "===== DATASET SUT $started: $sut ====="

  set +e
  OUT_ROOT="$OUT_ROOT" \
  SUT_ROOT="$SUT_ROOT" \
  REPEATS="$REPEATS" \
  GEN_TIMEOUT_S="$GEN_TIMEOUT_S" \
  GEN_EMPTY_RETRY_MAX="$GEN_EMPTY_RETRY_MAX" \
  GENERATION_RETRY_SLEEP_S="$GENERATION_RETRY_SLEEP_S" \
  MVN_TEST_TIMEOUT_S="$MVN_TEST_TIMEOUT_S" \
  PIT_TIMEOUT_S="$PIT_TIMEOUT_S" \
  RUN_MUTATION="$RUN_MUTATION" \
  GENERATOR_CMD="$GENERATOR_CMD" \
  bash "$REPO_ROOT/scripts/run_quixbugs_gpt55_one_sut.sh" "$sut"
  rc=$?
  set -e

  if [ "$rc" -ne 0 ]; then
    launcher_failures=$((launcher_failures + 1))
    echo "WARNING launcher failure for $sut rc=$rc" | tee -a "$OUT_ROOT/_logs/launcher_failures.log"
  fi
done < "$selected"

echo
echo "===== AGGREGATING DATASET ====="
set +e
python3 "$REPO_ROOT/tools/aggregate_quixbugs_java_gpt55_results.py" --out-root "$OUT_ROOT" \
  2>&1 | tee "$OUT_ROOT/_logs/aggregate.log"
aggregate_rc=${PIPESTATUS[0]}
set -e

echo
echo "===== DATASET LAUNCHER DONE ====="
echo "started_suts=$started"
echo "launcher_failures=$launcher_failures"
echo "aggregate_rc=$aggregate_rc"
echo "out_root=$OUT_ROOT"

exit "$aggregate_rc"
