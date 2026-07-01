#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SUT_ROOT="${1:-$HOME/projetos/SUTs/humanevalplus}"
OUT_BASE="${2:-$ROOT/out/_gpt4o_humanevalplus_python_dataset}"
REPEATS="${REPEATS:-5}"
GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-200}"
RUN_MUTATION="${RUN_MUTATION:-1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

SUT_ROOT="$(readlink -f "$SUT_ROOT")"
mkdir -p "$OUT_BASE"
OUT_BASE="$(readlink -f "$OUT_BASE")"

echo "============================================================"
echo "GPT-4o HumanEval+ Python dataset workflow"
echo "SUT_ROOT=$SUT_ROOT"
echo "OUT_BASE=$OUT_BASE"
echo "REPEATS=$REPEATS"
echo "GEN_TIMEOUT_S=$GEN_TIMEOUT_S"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "PYTHON_BIN=$PYTHON_BIN"
echo "============================================================"

INDEX_TSV="$OUT_BASE/dataset_runs_index.tsv"
SUMMARY_TSV="$OUT_BASE/dataset_summary.tsv"
MASTER_LOG_DIR="$OUT_BASE/logs"
mkdir -p "$MASTER_LOG_DIR"

echo -e "sut_name\trepeat\trun_dir\tstatus_json" > "$INDEX_TSV"

mapfile -t SUTS < <(find "$SUT_ROOT" -maxdepth 1 -mindepth 1 -type d -name 'HumanEval_*' | sort -V)

echo "SUT_COUNT=${#SUTS[@]}"

for SUT_DIR in "${SUTS[@]}"; do
  SUT_NAME="$(basename "$SUT_DIR")"
  echo
  echo "############################################################"
  echo "SUT=$SUT_NAME"
  echo "############################################################"

  for ((REP=1; REP<=REPEATS; REP++)); do
    echo
    echo "---- $SUT_NAME / REP=$REP ----"

    LOG_FILE="$MASTER_LOG_DIR/${SUT_NAME}_rep$(printf "%04d" "$REP").log"

    set +e
    GEN_TIMEOUT_S="$GEN_TIMEOUT_S" RUN_MUTATION="$RUN_MUTATION" PYTHON_BIN="$PYTHON_BIN" \
      "$ROOT/scripts/run_gpt4o_humanevalplus_python_one_sut.sh" \
      "$SUT_DIR" \
      "$OUT_BASE" \
      "$REP" \
      > "$LOG_FILE" 2>&1
    RC=$?
    set -e

    RUN_DIR="$OUT_BASE/$SUT_NAME/run_$(printf "%04d" "$REP")"
    STATUS_JSON="$RUN_DIR/metrics/status.json"

    echo "SCRIPT_RC=$RC"
    echo "RUN_DIR=$RUN_DIR"
    echo "STATUS_JSON=$STATUS_JSON"

    echo -e "${SUT_NAME}\t${REP}\t${RUN_DIR}\t${STATUS_JSON}" >> "$INDEX_TSV"
  done
done

"$PYTHON_BIN" - <<PY
from pathlib import Path
import json

out_base = Path("$OUT_BASE")
index_file = out_base / "dataset_runs_index.tsv"
summary_file = out_base / "dataset_summary.tsv"

rows = []
for line in index_file.read_text(encoding="utf-8").splitlines()[1:]:
    if not line.strip():
        continue
    sut_name, rep, run_dir, status_json = line.split("\t")
    p = Path(status_json)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        rows.append([
            sut_name,
            rep,
            data.get("status"),
            data.get("generation_exit_code"),
            data.get("pytest_raw_exit_code"),
            data.get("pytest_final_exit_code"),
            data.get("coverage_exit_code"),
            data.get("mutmut_exit_code"),
            data.get("line_coverage_pct"),
            data.get("branch_coverage_pct"),
            data.get("mutation_score_pct"),
        ])
    else:
        rows.append([sut_name, rep, "missing_status", "", "", "", "", "", "", "", ""])

with summary_file.open("w", encoding="utf-8") as f:
    f.write("sut_name\trepeat\tstatus\tgen_rc\traw_rc\tfinal_rc\tcov_rc\tmut_rc\tline\tbranch\tmutation\n")
    for r in rows:
        f.write("\t".join("" if x is None else str(x) for x in r) + "\n")

print(f"Wrote: {summary_file}")
PY

echo
echo "DONE DATASET ✅"
echo "INDEX_TSV=$INDEX_TSV"
echo "SUMMARY_TSV=$SUMMARY_TSV"
