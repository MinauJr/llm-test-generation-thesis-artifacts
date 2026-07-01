#!/usr/bin/env bash
set -uo pipefail
set +H 2>/dev/null || true

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export CLUSTER_ROOT="${CLUSTER_ROOT:-$ROOT_DIR/out/_cluster_raw_defects4j_java_import_latest/merged/defects4j_java_zero_shot_cluster_v1}"
export OUT_ROOT="${OUT_ROOT:-$ROOT_DIR/out/_cluster_defects4j_java_openweight_eval_all_v1}"

export SUTS_ROOT="${SUTS_ROOT:-$HOME/projetos/SUTs/defects4j}"
export TARGET_MAP_TSV="${TARGET_MAP_TSV:-$ROOT_DIR/configs/defects4j_target_map_seed.tsv}"

export RUN_MUTATION="${RUN_MUTATION:-1}"
export PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
export MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}"
export TEST_COMPILE_TIMEOUT_S="${TEST_COMPILE_TIMEOUT_S:-$PYTEST_TIMEOUT_S}"
export RAW_TIMEOUT_S="${RAW_TIMEOUT_S:-$PYTEST_TIMEOUT_S}"
export FINAL_TIMEOUT_S="${FINAL_TIMEOUT_S:-$PYTEST_TIMEOUT_S}"
export PIT_TIMEOUT_S="${PIT_TIMEOUT_S:-$MUTATION_TIMEOUT_S}"

export SKIP_IF_DONE="${SKIP_IF_DONE:-1}"
export MAX_RUNS="${MAX_RUNS:-0}"
export ONLY_MODELS="${ONLY_MODELS:-}"
export ONLY_SUTS="${ONLY_SUTS:-}"

mkdir -p "$OUT_ROOT"

{
  echo "===== LAUNCH DEFECTS4J JAVA CLUSTER LOCAL EVAL ALL MODELS ====="
  date
  echo "ROOT_DIR=$ROOT_DIR"
  echo "CLUSTER_ROOT=$CLUSTER_ROOT"
  echo "OUT_ROOT=$OUT_ROOT"
  echo "RUN_MUTATION=$RUN_MUTATION"
  echo "ONLY_MODELS=$ONLY_MODELS"
  echo "ONLY_SUTS=$ONLY_SUTS"
  echo "MAX_RUNS=$MAX_RUNS"
  echo "SKIP_IF_DONE=$SKIP_IF_DONE"
  echo
} | tee "$OUT_ROOT/final_eval_driver.log"

bash "$ROOT_DIR/scripts/eval_cluster_defects4j_java_dataset.sh" 2>&1 | tee -a "$OUT_ROOT/final_eval_driver.log"

python3 "$ROOT_DIR/scripts/finalize_cluster_defects4j_java_eval_summary.py" "$OUT_ROOT" 2>&1 | tee -a "$OUT_ROOT/final_eval_driver.log"

echo "===== LAUNCH DONE =====" | tee -a "$OUT_ROOT/final_eval_driver.log"
date | tee -a "$OUT_ROOT/final_eval_driver.log"
