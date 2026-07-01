#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$HOME/projetos/llm_test_generation_gpt4o"
SUT_ROOT="$HOME/projetos/SUTs/humanevalplus"
CLUSTER_ROOT="$HOME/cluster_debug/humaneval_v4_merged/humanevalplus_zero_shot_cluster_v4"
OUT_PARENT="$REPO_ROOT/out/_cluster_humanevalplus_v4_eval_all"
MODELS_FILE="$CLUSTER_ROOT/_as_run_models.txt"
MASTER_LOG="$OUT_PARENT/_logs/launcher_master.log"

RUN_MUTATION="${RUN_MUTATION:-1}"

mkdir -p "$OUT_PARENT/_logs"

if [[ ! -f "$MODELS_FILE" ]]; then
  echo "[ERROR] Missing models file: $MODELS_FILE" >&2
  exit 1
fi

sanitize_model() {
  echo "$1" | sed 's/[^A-Za-z0-9._-]/_/g'
}

echo "============================================================" | tee "$MASTER_LOG"
echo "HumanEval+ cluster evaluation launcher" | tee -a "$MASTER_LOG"
echo "REPO_ROOT=$REPO_ROOT" | tee -a "$MASTER_LOG"
echo "SUT_ROOT=$SUT_ROOT" | tee -a "$MASTER_LOG"
echo "CLUSTER_ROOT=$CLUSTER_ROOT" | tee -a "$MASTER_LOG"
echo "OUT_PARENT=$OUT_PARENT" | tee -a "$MASTER_LOG"
echo "MODELS_FILE=$MODELS_FILE" | tee -a "$MASTER_LOG"
echo "RUN_MUTATION=$RUN_MUTATION" | tee -a "$MASTER_LOG"
echo "START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"
echo "============================================================" | tee -a "$MASTER_LOG"

while IFS= read -r model || [[ -n "$model" ]]; do
  [[ -z "$model" ]] && continue

  slug="$(sanitize_model "$model")"
  model_out="$OUT_PARENT/$slug"
  model_log="$OUT_PARENT/_logs/${slug}.log"

  echo | tee -a "$MASTER_LOG"
  echo "############################################################" | tee -a "$MASTER_LOG"
  echo "[MODEL] $model" | tee -a "$MASTER_LOG"
  echo "SLUG=$slug" | tee -a "$MASTER_LOG"
  echo "MODEL_OUT=$model_out" | tee -a "$MASTER_LOG"
  echo "MODEL_LOG=$model_log" | tee -a "$MASTER_LOG"
  echo "############################################################" | tee -a "$MASTER_LOG"

  set +e
  RUN_MUTATION="$RUN_MUTATION" \
  ONLY_MODELS="$model" \
  "$REPO_ROOT/scripts/eval_cluster_humanevalplus_python_dataset.sh" \
    "$SUT_ROOT" \
    "$CLUSTER_ROOT" \
    "$model_out" \
    > "$model_log" 2>&1
  rc=$?
  set -e

  echo "[MODEL_DONE] $model rc=$rc end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"
done < "$MODELS_FILE"

echo | tee -a "$MASTER_LOG"
echo "============================================================" | tee -a "$MASTER_LOG"
echo "END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"
echo "MASTER_LOG=$MASTER_LOG" | tee -a "$MASTER_LOG"
echo "============================================================" | tee -a "$MASTER_LOG"
