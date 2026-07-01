#!/usr/bin/env bash
set -euo pipefail

cd ~/projetos/llm_test_generation_gpt4o || exit 1

AUDIT="$(find "$HOME/cluster_debug" -maxdepth 1 -type d -name 'mbppplus_lowperf_r2_ingest_*' | sort | tail -1)"
source "$AUDIT/selected_roots.env"

SUT_ROOT="$HOME/projetos/SUTs/mbppPlus"
OUT_ROOT="$HOME/projetos/llm_test_generation_gpt4o/out/_final_eval_cluster_mbppplus_lowperf_r2_metrics"
LOG="$OUT_ROOT/final_eval_driver.log"

mkdir -p "$OUT_ROOT"

{
  echo "===== MBPP+ LOWPERF R2 LOCAL METRICS EVAL ====="
  date
  echo "AUDIT=$AUDIT"
  echo "SUT_ROOT=$SUT_ROOT"
  echo "OUT_ROOT=$OUT_ROOT"
  echo "CODELLAMA_GEN_ROOT=$CODELLAMA_GEN_ROOT"
  echo "CODESTRAL_GEN_ROOT=$CODESTRAL_GEN_ROOT"

  run_model() {
    local MODEL="$1"
    local GEN_ROOT="$2"

    echo
    echo "============================================================"
    echo "MODEL=$MODEL"
    echo "GEN_ROOT=$GEN_ROOT"
    echo "START=$(date)"
    echo "============================================================"

    if [[ ! -d "$GEN_ROOT" ]]; then
      echo "[ERROR] GEN_ROOT não existe: $GEN_ROOT"
      exit 1
    fi

    python3 scripts/eval_cluster_mbppplus_python_generated.py \
      --generated-root "$GEN_ROOT" \
      --sut-root "$SUT_ROOT" \
      --out-root "$OUT_ROOT" \
      --model-name "$MODEL" \
      --run-mutation 1 \
      --pytest-timeout-s 60 \
      --mutation-timeout-s 120 \
      --force

    echo "END_MODEL=$MODEL $(date)"
  }

  run_model "cluster-max-codellama-7b-instruct-ctx16k" "$CODELLAMA_GEN_ROOT"
  run_model "cluster-safe-codestral-22b-ctx16k" "$CODESTRAL_GEN_ROOT"

  echo
  echo "===== POSTPROCESS MUTMUT METRICS FROM LOGS ====="
  python3 scripts/fix_mbppplus_mutmut_metrics_from_logs.py \
    --out-root "$OUT_ROOT"

  echo
  echo "===== SUMMARY BY MODEL ====="
  python3 scripts/summarize_mbppplus_cluster_eval_by_model.py \
    --out-root "$OUT_ROOT"

  echo
  echo "===== FINAL SUMMARY BY MODEL ====="
  cat "$OUT_ROOT/dataset_summary_by_model.txt"

  echo
  echo "===== DONE ====="
  date
} 2>&1 | tee -a "$LOG"
