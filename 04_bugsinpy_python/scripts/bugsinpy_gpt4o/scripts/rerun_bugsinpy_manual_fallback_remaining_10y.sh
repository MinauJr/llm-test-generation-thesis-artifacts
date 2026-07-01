#!/usr/bin/env bash

set +e
set +u
set +o pipefail 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

FINAL_OUT="${FINAL_OUT:-$REPO/out/_final_bugsinpy_gpt4o_full_5rep}"
PER_MUTANT_TIMEOUT_S="${PER_MUTANT_TIMEOUT_S:-20}"

echo "===== BUGSINPY MANUAL FALLBACK 10Y — clean test dir, SEM API ====="
echo "REPO=$REPO"
echo "FINAL_OUT=$FINAL_OUT"
echo "PER_MUTANT_TIMEOUT_S=$PER_MUTANT_TIMEOUT_S"

mapfile -t STATUS_FILES < <(find "$FINAL_OUT" -path "*/metrics/status.json" | sort)

TARGETS=()

for STATUS_FILE in "${STATUS_FILES[@]}"; do
  STATUS="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    d = json.loads(p.read_text(encoding="utf-8"))
    print(d.get("status"))
except Exception:
    print("UNKNOWN")
PY
)"
  if [[ "$STATUS" == "manual_fallback_baseline_fail" || "$STATUS" == "manual_fallback_10y_baseline_fail" ]]; then
    TARGETS+=("$STATUS_FILE")
  fi
done

echo "FOUND_BASELINE_FAIL=${#TARGETS[@]}"

N=0
for STATUS_FILE in "${TARGETS[@]}"; do
  N=$((N+1))
  RUN_DIR="$(dirname "$(dirname "$STATUS_FILE")")"

  SUT="$(python3 - "$STATUS_FILE" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(d.get("sut_id"))
PY
)"

  echo
  echo "======================================================================"
  echo "[$N/${#TARGETS[@]}] SUT=$SUT"
  echo "RUN_DIR=$RUN_DIR"
  echo "======================================================================"

  python3 tools/run_bugsinpy_mutation_manual_fallback_10y.py \
    --run-dir "$RUN_DIR" \
    --per-mutant-timeout-s "$PER_MUTANT_TIMEOUT_S"

  echo "run_rc=$?"
done

echo
echo "===== REAGREGAR RESULTADOS APÓS 10Y ====="

python3 - <<'PY'
import csv
import json
from pathlib import Path
from collections import Counter

root = Path("out/_final_bugsinpy_gpt4o_full_5rep")
rows = []

for p in sorted(root.glob("*/run_0001/*/metrics/status.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    d["_status_path"] = str(p)
    rows.append(d)

status_counts = Counter(d.get("status") for d in rows)
accepted = {"ok", "mutation_results_empty"}
bad = [d for d in rows if d.get("status") not in accepted]

def mean_penalized(key):
    vals = []
    for d in rows:
        v = d.get(key)
        vals.append(float(v) if v is not None else 0.0)
    return sum(vals) / len(vals) if vals else 0.0

line_mean = mean_penalized("line_pct")
branch_mean = mean_penalized("branch_pct")
mut_mean = mean_penalized("mutation_score_pct")

mutation_available_runs = sum(1 for d in rows if d.get("mutation_available") is True)
manual_used = sum(1 for d in rows if d.get("manual_fallback_used") or d.get("manual_fallback_10y_used"))

print("TOTAL_STATUS_FILES=", len(rows))
print("TOTAL_SUTS=", len({d.get("sut_id") for d in rows}))
print("STATUS_COUNTS=", json.dumps(dict(status_counts), sort_keys=True))
print("MUTATION_AVAILABLE_RUNS=", mutation_available_runs)
print("MANUAL_FALLBACK_USED_RUNS=", manual_used)
print(f"LINE_PCT_PENALIZED_MEAN={line_mean:.4f}")
print(f"BRANCH_PCT_PENALIZED_MEAN={branch_mean:.4f}")
print(f"MUTATION_SCORE_PCT_PENALIZED_MEAN={mut_mean:.4f}")
print("BAD_INFRA_COUNT=", len(bad))

if bad:
    print()
    for d in bad:
        print(
            d.get("sut_id"),
            d.get("target_module"),
            d.get("status"),
            "line=", d.get("line_pct"),
            "branch=", d.get("branch_pct"),
            "mut=", d.get("mutation_score_pct"),
            d.get("_status_path"),
        )

summary = root / "dataset_summary_manual_fallback_10y.tsv"
with summary.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow([
        "total_status_files",
        "total_suts",
        "status_counts_json",
        "mutation_available_runs",
        "manual_fallback_used_runs",
        "line_pct_penalized_mean",
        "branch_pct_penalized_mean",
        "mutation_score_pct_penalized_mean",
        "bad_infra_count",
    ])
    w.writerow([
        len(rows),
        len({d.get("sut_id") for d in rows}),
        json.dumps(dict(status_counts), sort_keys=True),
        mutation_available_runs,
        manual_used,
        f"{line_mean:.6f}",
        f"{branch_mean:.6f}",
        f"{mut_mean:.6f}",
        len(bad),
    ])

index = root / "dataset_runs_index_manual_fallback_10y.tsv"
with index.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "sut_id",
        "target_module",
        "status",
        "line_pct",
        "branch_pct",
        "mutation_score_pct",
        "mutation_available",
        "manual_fallback_used",
        "manual_fallback_10y_used",
        "status_path",
    ]
    w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
    w.writeheader()
    for d in rows:
        w.writerow({
            "sut_id": d.get("sut_id"),
            "target_module": d.get("target_module"),
            "status": d.get("status"),
            "line_pct": d.get("line_pct"),
            "branch_pct": d.get("branch_pct"),
            "mutation_score_pct": d.get("mutation_score_pct"),
            "mutation_available": d.get("mutation_available"),
            "manual_fallback_used": d.get("manual_fallback_used"),
            "manual_fallback_10y_used": d.get("manual_fallback_10y_used"),
            "status_path": d.get("_status_path"),
        })

print()
print("DATASET_SUMMARY_MANUAL_FALLBACK_10Y_TSV=", summary)
print("DATASET_RUNS_INDEX_MANUAL_FALLBACK_10Y_TSV=", index)

if not bad:
    print()
    print("✅ FINAL COM MUTATION FALLBACK 10Y ACEITÁVEL: 16 SUTs × 5 reps, sem estados reais de infraestrutura.")
else:
    print()
    print("⚠️ AINDA HÁ ESTADOS A ANALISAR.")
PY

echo
echo "===== DONE BUGSINPY MANUAL FALLBACK 10Y ====="
date
