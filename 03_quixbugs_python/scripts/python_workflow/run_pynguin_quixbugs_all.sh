#!/usr/bin/env bash
set -u

cd "$(dirname "$0")" || exit 1

SUT_ROOT_BASE="$HOME/projetos/SUTs/quixbugs"
STAMP="${STAMP:-$(date +%Y%m%d_%H%M%S)}"
OUT_ROOT="${OUT_ROOT:-$HOME/projetos/nonAI/python_workflow/out/pynguin_quixbugs_strict0_${STAMP}}"
LOG_DIR="$OUT_ROOT/logs"
LOG="$LOG_DIR/master_${STAMP}.log"

mkdir -p "$LOG_DIR" "$HOME/projetos/nonAI/python_workflow/out/_logs"
ln -sfn "$LOG" "$HOME/projetos/nonAI/python_workflow/out/_logs/quixbugs_pynguin_latest.log"

echo "OUT_ROOT=$OUT_ROOT" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"

find "$SUT_ROOT_BASE" -maxdepth 1 -type d -name '*_python_*' | sort | while read -r SUT; do
  SUT_NAME="$(basename "$SUT")"
  echo "==> SUT: $SUT_NAME" | tee -a "$LOG"

  PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-15}" \
  MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-200}" \
  REPEATS="${REPEATS:-5}" \
  BUDGET_S="${BUDGET_S:-180}" \
  PYNGUIN_TIMEOUT_S="${PYNGUIN_TIMEOUT_S:-200}" \
  RUN_MUTATION="${RUN_MUTATION:-1}" \
  GLOBAL_RUN_IDS=1 \
  ./run_python_baseline3.sh "$SUT" "sut" "$OUT_ROOT/$SUT_NAME" >>"$LOG" 2>&1

  RC=$?
  echo "EXIT_CODE=$RC for $SUT_NAME" | tee -a "$LOG"
  echo "✅ DONE SUT: $SUT_NAME" | tee -a "$LOG"
done

echo "✅ DONE DATASET: $OUT_ROOT" | tee -a "$LOG"
