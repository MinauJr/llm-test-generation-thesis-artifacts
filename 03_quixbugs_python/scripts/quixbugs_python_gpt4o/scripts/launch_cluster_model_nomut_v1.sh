#!/usr/bin/env bash
set -u
set -o pipefail

MODEL="${1:?usage: launch_cluster_model_nomut_v1.sh MODEL}"

PY_ROOT="${PY_ROOT:-$HOME/projetos/quixbugs_python_gpt4o}"
CLUSTER_ROOT="${CLUSTER_ROOT:-$HOME/projetos/quixbugs_python_cluster/out/quixbugs_python_zero_shot_cluster_v1}"
SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/quixbugs}"

: "${FULL_ROOT:?FULL_ROOT não definido}"

MODEL_ROOT="$FULL_ROOT/$MODEL"
SUTS_FILE="${SUTS_FILE:-$PY_ROOT/manifests/python_suts.txt}"

CLUSTER_ONE="$PY_ROOT/scripts/run_quixbugs_cluster_one_sut.sh"
GENERATOR="$PY_ROOT/scripts/generator_cmd_cluster_source.sh"

PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"

mkdir -p "$MODEL_ROOT/_logs"

echo "===== QUIXBUGS PYTHON CLUSTER MODEL NO-MUTATION V1 ====="
date
echo "MODEL=$MODEL"
echo "MODEL_ROOT=$MODEL_ROOT"
echo "CLUSTER_ROOT=$CLUSTER_ROOT"
echo "SUT_ROOT=$SUT_ROOT"
echo "PYTEST_TIMEOUT_S=$PYTEST_TIMEOUT_S"

started=0
skipped=0
launcher_failures=0

while IFS= read -r SUT; do
  [ -n "$SUT" ] || continue

  for REP in 1 2 3 4 5; do
    STATUS_JSON="$MODEL_ROOT/$SUT/run_0001/1-$REP/metrics/status.json"
    LOG="$MODEL_ROOT/_logs/${SUT}__rep_${REP}.log"

    if [ -f "$STATUS_JSON" ]; then
      skipped=$((skipped + 1))
      echo "[SKIP] model=$MODEL sut=$SUT rep=$REP status exists"
      continue
    fi

    started=$((started + 1))

    echo
    echo "===== RUN $started: $MODEL $SUT rep=$REP ====="

    set +e

    OUT_ROOT="$MODEL_ROOT" \
    SUT_ROOT="$SUT_ROOT" \
    MODEL_LABEL="$MODEL" \
    CLUSTER_MODEL="$MODEL" \
    CLUSTER_DATA_ROOT="$CLUSTER_ROOT" \
    GENERATOR_CMD="$GENERATOR" \
    REPEATS=5 \
    ONLY_REPEATS="$REP" \
    GEN_EMPTY_RETRY_MAX=1 \
    GEN_TIMEOUT_S=30 \
    RUN_MUTATION=0 \
    PYTEST_TIMEOUT_S="$PYTEST_TIMEOUT_S" \
    bash "$CLUSTER_ONE" "$SUT" \
      > "$LOG" 2>&1

    RC=$?

    set -e 2>/dev/null || true

    echo "$RC" > "${LOG}.exit_code"

    if [ "$RC" -ne 0 ]; then
      launcher_failures=$((launcher_failures + 1))
      echo "[LAUNCHER_FAILURE] rc=$RC model=$MODEL sut=$SUT rep=$REP"
    fi

    if [ -f "$STATUS_JSON" ]; then
      STATUS="$(
        python3 -c '
import json,sys
try:
    print(json.load(open(sys.argv[1])).get("status", "UNKNOWN"))
except Exception:
    print("INVALID_STATUS_JSON")
' "$STATUS_JSON"
      )"

      echo "[DONE] model=$MODEL sut=$SUT rep=$REP status=$STATUS"
    else
      echo "[MISSING_STATUS] model=$MODEL sut=$SUT rep=$REP"
    fi
  done
done < "$SUTS_FILE"

echo
echo "===== AGGREGATE MODEL ====="

python3 "$PY_ROOT/tools/aggregate_quixbugs_gpt4o_results.py" \
  --out-root "$MODEL_ROOT" \
  > "$MODEL_ROOT/_logs/aggregate.log" 2>&1 || true

echo
echo "===== MODEL COMPLETE ====="
date
echo "MODEL=$MODEL"
echo "started=$started"
echo "skipped=$skipped"
echo "launcher_failures=$launcher_failures"
echo "MODEL_ROOT=$MODEL_ROOT"
