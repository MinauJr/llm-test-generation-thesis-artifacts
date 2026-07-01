#!/usr/bin/env bash

set +e
set +u
set +o pipefail 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

FINAL_OUT="${FINAL_OUT:-$REPO/out/_final_bugsinpy_gpt4o_full_5rep}"
PER_MUTANT_TIMEOUT_S="${PER_MUTANT_TIMEOUT_S:-20}"

echo "===== BUGSINPY MANUAL FALLBACK 10X — restantes, SEM API ====="
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
  if [[ "$STATUS" == "manual_fallback_baseline_fail" ]]; then
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
p = Path(sys.argv[1])
try:
    d = json.loads(p.read_text(encoding="utf-8"))
    print(d.get("sut_id"))
except Exception:
    print("UNKNOWN")
PY
)"

  echo
  echo "======================================================================"
  echo "[$N/${#TARGETS[@]}] SUT=$SUT"
  echo "RUN_DIR=$RUN_DIR"
  echo "======================================================================"

  python3 tools/run_bugsinpy_mutation_manual_fallback_10x.py \
    --run-dir "$RUN_DIR" \
    --per-mutant-timeout-s "$PER_MUTANT_TIMEOUT_S" \
    --force \
    2>&1 | tee "$RUN_DIR/logs/manual_fallback_10x.log"
done

echo
echo "===== REAGREGAR RESULTADOS APÓS 10X ====="

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

def mean_penalised(key):
    vals = []
    for d in rows:
        v = d.get(key)
        vals.append(float(v) if v is not None else 0.0)
    return sum(vals) / len(vals) if vals else 0.0

mutation_available_runs = sum(1 for d in rows if d.get("mutation_available") is True)
manual_used_runs = sum(
    1 for d in rows
    if (d.get("mutmut_counts") or {}).get("parse_source", "").startswith("manual_fallback")
)

allowed = {"ok", "mutation_results_empty"}
bad = [d for d in rows if d.get("status") not in allowed]

summary = {
    "total_status_files": len(rows),
    "total_suts": len({d.get("sut_id") for d in rows}),
    "status_counts_json": json.dumps(dict(status_counts), sort_keys=True),
    "mutation_available_runs": mutation_available_runs,
    "manual_fallback_used_runs": manual_used_runs,
    "line_pct_penalized_mean": f"{mean_penalised('line_pct'):.6f}",
    "branch_pct_penalized_mean": f"{mean_penalised('branch_pct'):.6f}",
    "mutation_score_pct_penalized_mean": f"{mean_penalised('mutation_score_pct'):.6f}",
    "bad_infra_count": len(bad),
}

print("TOTAL_STATUS_FILES=", summary["total_status_files"])
print("TOTAL_SUTS=", summary["total_suts"])
print("STATUS_COUNTS=", summary["status_counts_json"])
print("MUTATION_AVAILABLE_RUNS=", mutation_available_runs)
print("MANUAL_FALLBACK_USED_RUNS=", manual_used_runs)
print("LINE_PCT_PENALIZED_MEAN=", summary["line_pct_penalized_mean"])
print("BRANCH_PCT_PENALIZED_MEAN=", summary["branch_pct_penalized_mean"])
print("MUTATION_SCORE_PCT_PENALIZED_MEAN=", summary["mutation_score_pct_penalized_mean"])
print("BAD_INFRA_COUNT=", len(bad))

out = root / "dataset_summary_manual_fallback_10x.tsv"
with out.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(summary.keys()), delimiter="\t")
    w.writeheader()
    w.writerow(summary)

index = root / "dataset_runs_index_manual_fallback_10x.tsv"
fields = [
    "sut_id", "target_module", "status", "line_pct", "branch_pct",
    "mutation_available", "mutation_score_pct", "mutation_target_relpath",
    "mutmut_counts", "_status_path",
]
with index.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
    w.writeheader()
    for d in rows:
        dd = dict(d)
        dd["mutmut_counts"] = json.dumps(dd.get("mutmut_counts"), sort_keys=True)
        w.writerow(dd)

if bad:
    print()
    print("BAD_INFRA:")
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
    print()
    print("⚠️ AINDA HÁ ESTADOS A ANALISAR.")
else:
    print()
    print("✅ FINAL COM MUTATION FALLBACK 10X ACEITÁVEL: sem estados reais de infraestrutura.")

print()
print("DATASET_SUMMARY_10X_TSV=", out)
print("DATASET_RUNS_INDEX_10X_TSV=", index)
PY

echo
echo "===== DONE BUGSINPY MANUAL FALLBACK 10X ====="
date
