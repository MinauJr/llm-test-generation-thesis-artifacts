#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SUT_ROOT="${1:?Uso: eval_cluster_humanevalplus_python_dataset.sh SUT_ROOT CLUSTER_ROOT OUT_BASE}"
CLUSTER_ROOT="${2:?Uso: eval_cluster_humanevalplus_python_dataset.sh SUT_ROOT CLUSTER_ROOT OUT_BASE}"
OUT_BASE="${3:?Uso: eval_cluster_humanevalplus_python_dataset.sh SUT_ROOT CLUSTER_ROOT OUT_BASE}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_MUTATION="${RUN_MUTATION:-1}"
ONLY_MODELS="${ONLY_MODELS:-}"
MAX_OK_RUNS="${MAX_OK_RUNS:-0}"

SUT_ROOT="$(readlink -f "$SUT_ROOT")"
CLUSTER_ROOT="$(readlink -f "$CLUSTER_ROOT")"
mkdir -p "$OUT_BASE"
OUT_BASE="$(readlink -f "$OUT_BASE")"

echo "============================================================"
echo "Cluster HumanEval+ Python dataset evaluation"
echo "SUT_ROOT=$SUT_ROOT"
echo "CLUSTER_ROOT=$CLUSTER_ROOT"
echo "OUT_BASE=$OUT_BASE"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "ONLY_MODELS=$ONLY_MODELS"
echo "MAX_OK_RUNS=$MAX_OK_RUNS"
echo "PYTHON_BIN=$PYTHON_BIN"
echo "============================================================"

INDEX_TSV="$OUT_BASE/eval_runs_index.tsv"
OK_SUMMARY_TSV="$OUT_BASE/eval_ok_summary.tsv"
MODEL_SUMMARY_TSV="$OUT_BASE/model_summary_penalized.tsv"
DATASET_SUMMARY_TSV="$OUT_BASE/dataset_summary_penalized.tsv"
SELECTED_OK_TSV="$OUT_BASE/_selected_ok_runs.tsv"
SOURCE_NONOK_TSV="$OUT_BASE/_source_nonok_runs.tsv"
LOG_DIR="$OUT_BASE/logs"
mkdir -p "$LOG_DIR"

echo -e "model\tmodel_slug\tsut_name\trepeat\tcluster_rep_dir\tcluster_status_json\teval_run_dir\teval_status_json" > "$INDEX_TSV"

ONLY_MODELS="$ONLY_MODELS" MAX_OK_RUNS="$MAX_OK_RUNS" "$PYTHON_BIN" - <<PY
import json
import os
import re
from pathlib import Path

cluster_root = Path("$CLUSTER_ROOT")
out_ok = Path("$SELECTED_OK_TSV")
out_nonok = Path("$SOURCE_NONOK_TSV")

only_models = [x.strip() for x in os.environ.get("ONLY_MODELS","").split(",") if x.strip()]
max_ok_runs = int(os.environ.get("MAX_OK_RUNS","0") or "0")

def slugify(s):
    return re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')

rows_ok = []
rows_nonok = []

for p in sorted(cluster_root.rglob("status.json")):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    model = d.get("model","")
    sut_id = d.get("sut_id","")
    repeat = int(d.get("repeat",0))
    status = d.get("status","")
    rep_dir = str(p.parent)

    if only_models and model not in only_models:
        continue

    row = [model, slugify(model), sut_id, str(repeat), status, rep_dir, str(p)]
    if status == "ok":
        rows_ok.append(row)
    else:
        rows_nonok.append(row)

rows_ok.sort(key=lambda r: (r[0], r[2], int(r[3])))
rows_nonok.sort(key=lambda r: (r[0], r[2], int(r[3])))

if max_ok_runs > 0:
    rows_ok = rows_ok[:max_ok_runs]

with out_ok.open("w", encoding="utf-8") as f:
    f.write("model\tmodel_slug\tsut_name\trepeat\tstatus\tcluster_rep_dir\tcluster_status_json\n")
    for r in rows_ok:
        f.write("\t".join(r) + "\n")

with out_nonok.open("w", encoding="utf-8") as f:
    f.write("model\tmodel_slug\tsut_name\trepeat\tstatus\tcluster_rep_dir\tcluster_status_json\n")
    for r in rows_nonok:
        f.write("\t".join(r) + "\n")

print("SELECTED_OK", len(rows_ok))
print("SOURCE_NONOK", len(rows_nonok))
PY

echo
echo "===== SELECTED OK RUNS ====="
wc -l "$SELECTED_OK_TSV"
echo "===== SOURCE NON-OK RUNS ====="
wc -l "$SOURCE_NONOK_TSV"

tail -n +2 "$SELECTED_OK_TSV" | while IFS=$'\t' read -r MODEL MODEL_SLUG SUT_NAME REP STATUS CLUSTER_REP_DIR CLUSTER_STATUS_JSON; do
  echo
  echo "---- MODEL=$MODEL / SUT=$SUT_NAME / REP=$REP ----"

  SUT_DIR="$SUT_ROOT/$SUT_NAME"
  MODEL_OUT="$OUT_BASE/$MODEL_SLUG"

  LOG_FILE="$LOG_DIR/${MODEL_SLUG}__${SUT_NAME}__rep$(printf "%04d" "$REP").log"

  set +e
  RUN_MUTATION="$RUN_MUTATION" PYTHON_BIN="$PYTHON_BIN" \
    "$ROOT/scripts/eval_cluster_humanevalplus_python_one_run.sh" \
    "$SUT_DIR" \
    "$CLUSTER_REP_DIR" \
    "$MODEL_OUT" \
    > "$LOG_FILE" 2>&1
  RC=$?
  set -e

  EVAL_RUN_DIR="$MODEL_OUT/$SUT_NAME/run_$(printf "%04d" "$REP")"
  EVAL_STATUS_JSON="$EVAL_RUN_DIR/metrics/status.json"

  echo "SCRIPT_RC=$RC"
  echo "EVAL_RUN_DIR=$EVAL_RUN_DIR"
  echo "EVAL_STATUS_JSON=$EVAL_STATUS_JSON"

  echo -e "${MODEL}\t${MODEL_SLUG}\t${SUT_NAME}\t${REP}\t${CLUSTER_REP_DIR}\t${CLUSTER_STATUS_JSON}\t${EVAL_RUN_DIR}\t${EVAL_STATUS_JSON}" >> "$INDEX_TSV"
done

"$PYTHON_BIN" - <<PY
from pathlib import Path
import json
from collections import defaultdict

out_base = Path("$OUT_BASE")
index_file = out_base / "eval_runs_index.tsv"
ok_summary_file = out_base / "eval_ok_summary.tsv"
model_summary_file = out_base / "model_summary_penalized.tsv"
dataset_summary_file = out_base / "dataset_summary_penalized.tsv"
selected_ok_file = out_base / "_selected_ok_runs.tsv"
source_nonok_file = out_base / "_source_nonok_runs.tsv"

selected_ok = []
for line in selected_ok_file.read_text(encoding="utf-8").splitlines()[1:]:
    if not line.strip():
        continue
    selected_ok.append(line.split("\t"))

source_nonok = []
for line in source_nonok_file.read_text(encoding="utf-8").splitlines()[1:]:
    if not line.strip():
        continue
    source_nonok.append(line.split("\t"))

eval_rows = []
eval_map = {}

for line in index_file.read_text(encoding="utf-8").splitlines()[1:]:
    if not line.strip():
        continue
    model, model_slug, sut_name, rep, cluster_rep_dir, cluster_status_json, eval_run_dir, eval_status_json = line.split("\t")
    p = Path(eval_status_json)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        eval_status = data.get("status", "missing_status")
        line_cov = float(data.get("line_coverage_pct") or 0)
        branch_cov = float(data.get("branch_coverage_pct") or 0)
        mutation = float(data.get("mutation_score_pct") or 0)
        skipped = 0
        skipped_file = Path(eval_run_dir) / "metrics" / "skipped_count.txt"
        if skipped_file.exists():
            try:
                skipped = int(skipped_file.read_text(encoding="utf-8").strip() or "0")
            except Exception:
                skipped = 0
    else:
        eval_status = "missing_status"
        line_cov = 0.0
        branch_cov = 0.0
        mutation = 0.0
        skipped = 0

    key = (model, sut_name, rep)
    eval_map[key] = {
        "eval_status": eval_status,
        "line": line_cov,
        "branch": branch_cov,
        "mutation": mutation,
        "skipped": skipped,
    }
    eval_rows.append([model, sut_name, rep, eval_status, line_cov, branch_cov, mutation, skipped, eval_run_dir])

with ok_summary_file.open("w", encoding="utf-8") as f:
    f.write("model\tsut_name\trepeat\teval_status\tline_coverage_pct\tbranch_coverage_pct\tmutation_score_pct\tskipped_count\teval_run_dir\n")
    for r in eval_rows:
        f.write("\t".join(str(x) for x in r) + "\n")

by_model = defaultdict(lambda: {
    "source_ok_total": 0,
    "source_ok_evaluated": 0,
    "source_nonok_total": 0,
    "sum_line": 0.0,
    "sum_branch": 0.0,
    "sum_mutation": 0.0,
})

for model, model_slug, sut_name, rep, status, cluster_rep_dir, cluster_status_json in selected_ok:
    by_model[model]["source_ok_total"] += 1
    by_model[model]["source_ok_evaluated"] += 1
    m = eval_map.get((model, sut_name, rep), None)
    if m is None:
        continue
    if m["eval_status"] == "ok":
        by_model[model]["sum_line"] += m["line"]
        by_model[model]["sum_branch"] += m["branch"]
        by_model[model]["sum_mutation"] += m["mutation"]

for model, model_slug, sut_name, rep, status, cluster_rep_dir, cluster_status_json in source_nonok:
    by_model[model]["source_nonok_total"] += 1

with model_summary_file.open("w", encoding="utf-8") as f:
    f.write("model\tsource_ok_total\tsource_ok_evaluated\tsource_nonok_total\ttotal_runs_counted\tmean_line_pct_penalized\tmean_branch_pct_penalized\tmean_mutation_pct_penalized\tpartial_ok_selection\n")
    for model in sorted(by_model):
        d = by_model[model]
        total = d["source_ok_evaluated"] + d["source_nonok_total"]
        mean_line = (d["sum_line"] / total) if total else 0.0
        mean_branch = (d["sum_branch"] / total) if total else 0.0
        mean_mutation = (d["sum_mutation"] / total) if total else 0.0
        partial = "true" if d["source_ok_total"] != d["source_ok_evaluated"] else "false"
        f.write(f"{model}\t{d['source_ok_total']}\t{d['source_ok_evaluated']}\t{d['source_nonok_total']}\t{total}\t{mean_line:.2f}\t{mean_branch:.2f}\t{mean_mutation:.2f}\t{partial}\n")

total_ok = sum(v["source_ok_total"] for v in by_model.values())
total_ok_eval = sum(v["source_ok_evaluated"] for v in by_model.values())
total_nonok = sum(v["source_nonok_total"] for v in by_model.values())
total_counted = total_ok_eval + total_nonok
sum_line = sum(v["sum_line"] for v in by_model.values())
sum_branch = sum(v["sum_branch"] for v in by_model.values())
sum_mutation = sum(v["sum_mutation"] for v in by_model.values())

dataset_line = (sum_line / total_counted) if total_counted else 0.0
dataset_branch = (sum_branch / total_counted) if total_counted else 0.0
dataset_mutation = (sum_mutation / total_counted) if total_counted else 0.0
dataset_partial = "true" if total_ok != total_ok_eval else "false"

with dataset_summary_file.open("w", encoding="utf-8") as f:
    f.write("source_ok_total\tsource_ok_evaluated\tsource_nonok_total\ttotal_runs_counted\tmean_line_pct_penalized\tmean_branch_pct_penalized\tmean_mutation_pct_penalized\tpartial_ok_selection\n")
    f.write(f"{total_ok}\t{total_ok_eval}\t{total_nonok}\t{total_counted}\t{dataset_line:.2f}\t{dataset_branch:.2f}\t{dataset_mutation:.2f}\t{dataset_partial}\n")

print(f"Wrote: {ok_summary_file}")
print(f"Wrote: {model_summary_file}")
print(f"Wrote: {dataset_summary_file}")
PY

echo
echo "DONE DATASET EVAL ✅"
echo "INDEX_TSV=$INDEX_TSV"
echo "OK_SUMMARY_TSV=$OK_SUMMARY_TSV"
echo "MODEL_SUMMARY_TSV=$MODEL_SUMMARY_TSV"
echo "DATASET_SUMMARY_TSV=$DATASET_SUMMARY_TSV"
