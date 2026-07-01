#!/usr/bin/env bash
set -u
set -o pipefail

PY_ROOT="${PY_ROOT:-$HOME/projetos/quixbugs_python_gpt4o}"
CLUSTER_ROOT="${CLUSTER_ROOT:-$HOME/projetos/quixbugs_python_cluster/out/quixbugs_python_zero_shot_cluster_v1}"
SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/quixbugs}"
MODELS_FILE="${MODELS_FILE:-$PY_ROOT/manifests/cluster_models.txt}"

: "${FULL_ROOT:?FULL_ROOT não definido}"

MAX_PARALLEL_MODELS="${MAX_PARALLEL_MODELS:-1}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"

MASTER_LOG_ROOT="$FULL_ROOT/_master_logs"
SUMMARY_ROOT="$FULL_ROOT/_summaries"

mkdir -p "$MASTER_LOG_ROOT" "$SUMMARY_ROOT"

echo "===== FULL QUIXBUGS PYTHON CLUSTER NO-MUTATION V1 ====="
date
echo "FULL_ROOT=$FULL_ROOT"
echo "MAX_PARALLEL_MODELS=$MAX_PARALLEL_MODELS"
echo "MODELS_FILE=$MODELS_FILE"

summarise() {
  python3 "$PY_ROOT/scripts/summarise_cluster_nomut_v1.py" \
    --full-root "$FULL_ROOT" \
    --cluster-root "$CLUSTER_ROOT" \
    --sut-root "$SUT_ROOT" \
    --models-file "$MODELS_FILE" \
    > "$MASTER_LOG_ROOT/latest_summary.stdout.log" \
    2> "$MASTER_LOG_ROOT/latest_summary.stderr.log" \
    || true
}

trap summarise EXIT

run_model() {
  local model="$1"
  local model_log="$MASTER_LOG_ROOT/${model}.log"
  local rc_file="$MASTER_LOG_ROOT/${model}.exit_code"
  local done_file="$MASTER_LOG_ROOT/${model}.done"

  {
    echo "===== MODEL START ====="
    date
    echo "MODEL=$model"
  } > "$model_log"

  set +e

  PY_ROOT="$PY_ROOT" \
  CLUSTER_ROOT="$CLUSTER_ROOT" \
  SUT_ROOT="$SUT_ROOT" \
  FULL_ROOT="$FULL_ROOT" \
  PYTEST_TIMEOUT_S="$PYTEST_TIMEOUT_S" \
  bash "$PY_ROOT/scripts/launch_cluster_model_nomut_v1.sh" "$model" \
    >> "$model_log" 2>&1

  local rc=$?

  set -e 2>/dev/null || true

  echo "$rc" > "$rc_file"

  {
    echo
    echo "===== MODEL END ====="
    date
    echo "MODEL=$model"
    echo "EXIT_CODE=$rc"
  } >> "$model_log"

  touch "$done_file"
  summarise
}

export -f run_model
export -f summarise

running_jobs() {
  jobs -rp | wc -l | tr -d ' '
}

while IFS= read -r model; do
  [ -n "$model" ] || continue

  while [ "$(running_jobs)" -ge "$MAX_PARALLEL_MODELS" ]; do
    wait -n || true
  done

  echo "[MASTER] launching model=$model"
  run_model "$model" &
done < "$MODELS_FILE"

wait || true

summarise

date > "$MASTER_LOG_ROOT/COMPLETE"

echo
echo "===== FULL PYTHON NO-MUTATION V1 COMPLETE ====="
date
echo "FULL_ROOT=$FULL_ROOT"

cat "$SUMMARY_ROOT/latest_summary.txt" 2>/dev/null || true
