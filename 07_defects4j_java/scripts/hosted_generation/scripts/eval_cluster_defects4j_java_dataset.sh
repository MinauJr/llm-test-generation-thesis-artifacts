#!/usr/bin/env bash
set -uo pipefail
set +H 2>/dev/null || true

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CLUSTER_ROOT="${CLUSTER_ROOT:-$ROOT_DIR/out/_cluster_raw_defects4j_java_import_latest/merged/defects4j_java_zero_shot_cluster_v1}"
OUT_ROOT="${OUT_ROOT:-$ROOT_DIR/out/_cluster_defects4j_java_openweight_eval_all_v1}"

SUTS_ROOT="${SUTS_ROOT:-$HOME/projetos/SUTs/defects4j}"
TARGET_MAP_TSV="${TARGET_MAP_TSV:-$ROOT_DIR/configs/defects4j_target_map_seed.tsv}"

ONLY_MODELS="${ONLY_MODELS:-}"
ONLY_SUTS="${ONLY_SUTS:-}"
MAX_RUNS="${MAX_RUNS:-0}"
SKIP_IF_DONE="${SKIP_IF_DONE:-1}"

RUN_MUTATION="${RUN_MUTATION:-1}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}"
TEST_COMPILE_TIMEOUT_S="${TEST_COMPILE_TIMEOUT_S:-$PYTEST_TIMEOUT_S}"
RAW_TIMEOUT_S="${RAW_TIMEOUT_S:-$PYTEST_TIMEOUT_S}"
FINAL_TIMEOUT_S="${FINAL_TIMEOUT_S:-$PYTEST_TIMEOUT_S}"
PIT_TIMEOUT_S="${PIT_TIMEOUT_S:-$MUTATION_TIMEOUT_S}"

DEFECTS4J_BIN="${DEFECTS4J_BIN:-$HOME/datasets/defect4j/defects4j/framework/bin/defects4j}"

mkdir -p "$OUT_ROOT" "$OUT_ROOT/_logs"

INDEX_TSV="$OUT_ROOT/dataset_runs_index.tsv"
META="$OUT_ROOT/eval_dataset_meta.txt"
MASTER_LOG="$OUT_ROOT/master_eval.log"

echo "===== DEFECTS4J JAVA CLUSTER LOCAL EVAL DATASET =====" | tee "$META"
date | tee -a "$META"
echo "ROOT_DIR=$ROOT_DIR" | tee -a "$META"
echo "CLUSTER_ROOT=$CLUSTER_ROOT" | tee -a "$META"
echo "OUT_ROOT=$OUT_ROOT" | tee -a "$META"
echo "SUTS_ROOT=$SUTS_ROOT" | tee -a "$META"
echo "TARGET_MAP_TSV=$TARGET_MAP_TSV" | tee -a "$META"
echo "ONLY_MODELS=$ONLY_MODELS" | tee -a "$META"
echo "ONLY_SUTS=$ONLY_SUTS" | tee -a "$META"
echo "MAX_RUNS=$MAX_RUNS" | tee -a "$META"
echo "SKIP_IF_DONE=$SKIP_IF_DONE" | tee -a "$META"
echo "RUN_MUTATION=$RUN_MUTATION" | tee -a "$META"
echo "PYTEST_TIMEOUT_S=$PYTEST_TIMEOUT_S" | tee -a "$META"
echo "MUTATION_TIMEOUT_S=$MUTATION_TIMEOUT_S" | tee -a "$META"
echo "DEFECTS4J_BIN=$DEFECTS4J_BIN" | tee -a "$META"

if [ ! -d "$CLUSTER_ROOT" ]; then
  echo "[ABORT] CLUSTER_ROOT não existe: $CLUSTER_ROOT" | tee -a "$MASTER_LOG"
  exit 2
fi

if [ ! -f "$TARGET_MAP_TSV" ]; then
  echo "[ABORT] TARGET_MAP_TSV não existe: $TARGET_MAP_TSV" | tee -a "$MASTER_LOG"
  exit 3
fi

csv_has() {
  local csv="$1"
  local needle="$2"
  [ -z "$csv" ] && return 0
  IFS=',' read -r -a arr <<< "$csv"
  for x in "${arr[@]}"; do
    [ "$x" = "$needle" ] && return 0
  done
  return 1
}

get_map_field() {
  local sut="$1"
  local field="$2"
  awk -F '\t' -v s="$sut" -v f="$field" '
    NR==1 {next}
    $1==s {
      if (f=="seed") print $2;
      else if (f=="target") print $3;
      exit
    }
  ' "$TARGET_MAP_TSV"
}

json_field() {
  local file="$1"
  local key="$2"
  python3 - "$file" "$key" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
key = sys.argv[2]
try:
    data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    print(data.get(key, ""))
except Exception:
    print("")
PY
}

local_status_field() {
  local file="$1"
  python3 - "$file" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.exists():
    print("missing_status_json")
    raise SystemExit(0)
try:
    data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    print(data.get("final_status") or data.get("status") or "unknown")
except Exception:
    print("bad_status_json")
PY
}

write_minimal_fail_status() {
  local status_json="$1"
  local model="$2"
  local sut_id="$3"
  local rep="$4"
  local source_rep_dir="$5"
  local note="$6"
  mkdir -p "$(dirname "$status_json")"
  python3 - "$status_json" "$model" "$sut_id" "$rep" "$source_rep_dir" "$note" <<'PY'
import json, sys
from pathlib import Path
status_json, model, sut_id, rep, source_rep_dir, note = sys.argv[1:]
data = {
    "model_name": model,
    "sut_id": sut_id,
    "rep": int(rep) if str(rep).isdigit() else rep,
    "source_cluster_run_dir": source_rep_dir,
    "final_status": "wrapper_fail",
    "wrapper_note": note,
    "line_pct_penalized": 0.0,
    "branch_pct_penalized": 0.0,
    "pit_score_pct_penalized": 0.0
}
Path(status_json).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

printf 'model\tsut_id\trepeat\tsource_generation_status\tlocal_status\teval_run_dir\tstatus_json\tsource_run_dir\n' > "$INDEX_TSV"

run_count=0

mapfile -t MODEL_DIRS < <(find "$CLUSTER_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'cluster-*' | sort)

for model_dir in "${MODEL_DIRS[@]}"; do
  model="$(basename "$model_dir")"
  csv_has "$ONLY_MODELS" "$model" || continue

  echo | tee -a "$MASTER_LOG"
  echo "===== MODEL $model =====" | tee -a "$MASTER_LOG"

  mapfile -t SUT_DIRS < <(find "$model_dir" -mindepth 1 -maxdepth 1 -type d | sort)

  for sut_dir in "${SUT_DIRS[@]}"; do
    sut_id="$(basename "$sut_dir")"
    csv_has "$ONLY_SUTS" "$sut_id" || continue

    seed_slot="$(get_map_field "$sut_id" seed)"
    target_class="$(get_map_field "$sut_id" target)"

    if [ -z "$seed_slot" ] || [ -z "$target_class" ]; then
      echo "[WARN] target map missing for SUT=$sut_id; skipping" | tee -a "$MASTER_LOG"
      continue
    fi

    mapfile -t REP_DIRS < <(find "$sut_dir" -mindepth 1 -maxdepth 1 -type d -name 'run_*' | sort -V)

    for rep_dir in "${REP_DIRS[@]}"; do
      rep_base="$(basename "$rep_dir")"
      rep_num="$(echo "$rep_base" | sed -E 's/^run_0*//')"
      [ -z "$rep_num" ] && rep_num="0"

      run_count=$((run_count + 1))

      if [ "$MAX_RUNS" -gt 0 ] && [ "$run_count" -gt "$MAX_RUNS" ]; then
        echo "[INFO] MAX_RUNS reached: $MAX_RUNS" | tee -a "$MASTER_LOG"
        break 3
      fi

      source_status_json="$rep_dir/status.json"
      source_test="$rep_dir/generated_tests.java"
      source_generation_status="$(json_field "$source_status_json" status)"

      out_model_root="$OUT_ROOT/$model"
      eval_run_dir="$out_model_root/$sut_id/run_0001/$seed_slot-$rep_num"
      status_json="$eval_run_dir/metrics/status.json"

      if [ "$SKIP_IF_DONE" = "1" ] && [ -f "$status_json" ]; then
        existing_status="$(local_status_field "$status_json")"
        echo "[SKIP] model=$model sut=$sut_id rep=$rep_num status=$existing_status" | tee -a "$MASTER_LOG"
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
          "$model" "$sut_id" "$rep_num" "$source_generation_status" "$existing_status" "$eval_run_dir" "$status_json" "$rep_dir" >> "$INDEX_TSV"
        continue
      fi

      echo "[RUN] model=$model sut=$sut_id rep=$rep_num source_status=$source_generation_status" | tee -a "$MASTER_LOG"

      if [ ! -s "$source_test" ]; then
        echo "[WARN] missing/empty generated_tests.java: $source_test" | tee -a "$MASTER_LOG"
        write_minimal_fail_status "$status_json" "$model" "$sut_id" "$rep_num" "$rep_dir" "missing_or_empty_generated_tests"
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
          "$model" "$sut_id" "$rep_num" "$source_generation_status" "missing_or_empty_generated_tests" "$eval_run_dir" "$status_json" "$rep_dir" >> "$INDEX_TSV"
        continue
      fi

      mkdir -p "$eval_run_dir" "$eval_run_dir/source_cluster"

      set +e
      MODEL_NAME="$model" \
      MOCK_GENERATION=1 \
      FORCE_RAW_TEST_FILE="$source_test" \
      SUT_ID="$sut_id" \
      SUT_ROOT="$SUTS_ROOT/$sut_id" \
      TARGET_CLASS="$target_class" \
      SUT_INDEX="$seed_slot" \
      REP="$rep_num" \
      OUT_BASE="$out_model_root" \
      RUN_MUTATION="$RUN_MUTATION" \
      PYTEST_TIMEOUT_S="$PYTEST_TIMEOUT_S" \
      MUTATION_TIMEOUT_S="$MUTATION_TIMEOUT_S" \
      TEST_COMPILE_TIMEOUT_S="$TEST_COMPILE_TIMEOUT_S" \
      RAW_TIMEOUT_S="$RAW_TIMEOUT_S" \
      FINAL_TIMEOUT_S="$FINAL_TIMEOUT_S" \
      PIT_TIMEOUT_S="$PIT_TIMEOUT_S" \
      DEFECTS4J_BIN="$DEFECTS4J_BIN" \
      "$ROOT_DIR/scripts/run_defects4j_gpt4o_one_sut.sh" \
        > "$eval_run_dir/wrapper.stdout.log" \
        2> "$eval_run_dir/wrapper.stderr.log"
      rc=$?
      set -e

      mkdir -p "$eval_run_dir/source_cluster"
      cp -a "$rep_dir/status.json" "$eval_run_dir/source_cluster/generation_status.json" 2>/dev/null || true
      cp -a "$rep_dir/prompt_final_used.txt" "$eval_run_dir/source_cluster/prompt_final_used.txt" 2>/dev/null || true
      cp -a "$rep_dir/response_raw.txt" "$eval_run_dir/source_cluster/response_raw.txt" 2>/dev/null || true
      cp -a "$rep_dir/generated_tests.java" "$eval_run_dir/source_cluster/generated_tests.java" 2>/dev/null || true
      cp -a "$rep_dir/generation_retry_trace.tsv" "$eval_run_dir/source_cluster/generation_retry_trace.tsv" 2>/dev/null || true

      if [ ! -f "$status_json" ]; then
        write_minimal_fail_status "$status_json" "$model" "$sut_id" "$rep_num" "$rep_dir" "one_sut_script_did_not_create_status_json_rc_$rc"
      fi

      local_status="$(local_status_field "$status_json")"

      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$model" "$sut_id" "$rep_num" "$source_generation_status" "$local_status" "$eval_run_dir" "$status_json" "$rep_dir" >> "$INDEX_TSV"

      echo "[DONE] model=$model sut=$sut_id rep=$rep_num rc=$rc local_status=$local_status" | tee -a "$MASTER_LOG"
    done
  done
done

echo | tee -a "$MASTER_LOG"
echo "===== DATASET EVAL LOOP DONE =====" | tee -a "$MASTER_LOG"
date | tee -a "$MASTER_LOG"

python3 "$ROOT_DIR/scripts/finalize_cluster_defects4j_java_eval_summary.py" "$OUT_ROOT" || true
