#!/usr/bin/env bash
set -euo pipefail

: "${REPEATS:=5}"
: "${GEN_TIMEOUT_S:=200}"
: "${GEN_EMPTY_RETRY_MAX:=15}"
: "${PYTEST_TIMEOUT_S:=60}"
: "${MUTATION_TIMEOUT_S:=180}"
: "${RUN_MUTATION:=1}"
: "${GENERATION_RETRY_SLEEP_S:=2}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${SUTS_ROOT:=$HOME/projetos/SUTs/defects4j}"
: "${TARGET_MAP_TSV:=$ROOT_DIR/configs/defects4j_target_map_seed.tsv}"
: "${ONLY_SUTS:=}"
: "${MODEL_NAME:?set MODEL_NAME}"
: "${ONE_SUT_SCRIPT:?set ONE_SUT_SCRIPT}"
: "${OUT_BASE:?set OUT_BASE}"

export REPEATS GEN_TIMEOUT_S GEN_EMPTY_RETRY_MAX PYTEST_TIMEOUT_S MUTATION_TIMEOUT_S RUN_MUTATION GENERATION_RETRY_SLEEP_S MODEL_NAME

mkdir -p "$OUT_BASE"
INDEX_TSV="$OUT_BASE/dataset_runs_index.tsv"
printf 'sut_id\trun_dir\ttarget_class\tmodel_name\n' > "$INDEX_TSV"

while IFS=$'\t' read -r sut_id seed_slot target_class origin notes; do
  [[ "$sut_id" == "sut_id" ]] && continue

  if [[ -n "$ONLY_SUTS" ]]; then
    case ",$ONLY_SUTS," in
      *,"$sut_id",*) ;;
      *) continue ;;
    esac
  fi

  for rep in $(seq 1 "$REPEATS"); do
    SUT_ID="$sut_id" \
    SUT_ROOT="$SUTS_ROOT/$sut_id" \
    TARGET_CLASS="$target_class" \
    SUT_INDEX="$seed_slot" \
    REP="$rep" \
    OUT_BASE="$OUT_BASE" \
    MODEL_NAME="$MODEL_NAME" \
    "$ONE_SUT_SCRIPT"
  done

  printf '%s\t%s\t%s\t%s\n' \
    "$sut_id" "$OUT_BASE/$sut_id/run_0001" "$target_class" "$MODEL_NAME" >> "$INDEX_TSV"
done < "$TARGET_MAP_TSV"

python3 "$ROOT_DIR/scripts/finalize_dataset_summary.py" "$OUT_BASE"
