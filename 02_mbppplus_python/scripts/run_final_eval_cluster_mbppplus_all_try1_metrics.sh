#!/usr/bin/env bash

set -euo pipefail

cd ~/projetos/llm_test_generation_gpt4o || exit 1

AUDIT="/home/jpaiva/cluster_debug/mbppplus_all_try1_ingest_20260516_122926"
SUT_ROOT="$HOME/projetos/SUTs/mbppPlus"
OUT_ROOT="$HOME/projetos/llm_test_generation_gpt4o/out/_final_eval_cluster_mbppplus_all_try1_metrics"

mkdir -p "$OUT_ROOT"

LOG="$OUT_ROOT/final_eval_driver.log"

{
  echo "===== MBPP+ ALL TRY1 LOCAL METRICS FULL EVAL ====="
  date
  echo "AUDIT=$AUDIT"
  echo "SUT_ROOT=$SUT_ROOT"
  echo "OUT_ROOT=$OUT_ROOT"

  run_model() {
    local PART="$1"
    local MODEL="$2"
    local GEN_ROOT="$AUDIT/raw_unzipped/$PART/mbppplus_job/results/mbppplus_zero_shot_cluster_v1/$MODEL"

    echo
    echo "============================================================"
    echo "MODEL=$MODEL"
    echo "PART=$PART"
    echo "GEN_ROOT=$GEN_ROOT"
    echo "START=$(date)"
    echo "============================================================"

    if [[ ! -d "$GEN_ROOT" ]]; then
      echo "[ERROR] GEN_ROOT não existe: $GEN_ROOT"
      return 1
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

  run_model "mbpp_part1" "cluster-max-codellama-7b-instruct-ctx16k"
  run_model "mbpp_part1" "cluster-safe-codestral-22b-ctx16k"
  run_model "mbpp_part1" "cluster-safe-qwen2.5-coder-14b-ctx32k"
  run_model "mbpp_part1" "cluster-safe-qwen3-coder-30b-official-ctx32k"

  run_model "mbpp_part2" "cluster-safe-deepseek-coder-v2-16b-ctx16k"
  run_model "mbpp_part2" "cluster-safe-deepseek-v2-16b-ctx32k"
  run_model "mbpp_part2" "cluster-safe-qwen3.5-9b-ctx32k"

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
