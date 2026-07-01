#!/usr/bin/env bash

set +e
set +u
set +o pipefail 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

FINAL_OUT="${FINAL_OUT:-$REPO/out/_final_bugsinpy_gpt4o_full_5rep}"
PER_MUTANT_TIMEOUT_S="${PER_MUTANT_TIMEOUT_S:-20}"

echo "===== BUGSINPY MANUAL MUTATION FALLBACK — SEM API ====="
echo "REPO=$REPO"
echo "FINAL_OUT=$FINAL_OUT"
echo "PER_MUTANT_TIMEOUT_S=$PER_MUTANT_TIMEOUT_S"

mapfile -t STATUS_FILES < <(find "$FINAL_OUT" -path "*/metrics/status.json" | sort)

echo "FOUND_STATUS_FILES=${#STATUS_FILES[@]}"

N=0
RERUN=0
SKIP=0

for STATUS_FILE in "${STATUS_FILES[@]}"; do
  N=$((N+1))
  RUN_DIR="$(dirname "$(dirname "$STATUS_FILE")")"

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
  echo "[$N/${#STATUS_FILES[@]}] RUN_DIR=$RUN_DIR"
  echo "SUT=$SUT"
  echo "STATUS=$STATUS"
  echo "======================================================================"

  case "$STATUS" in
    mutation_no_checked_mutants)
      RERUN=$((RERUN+1))
      mkdir -p "$RUN_DIR/logs"
      python3 tools/run_bugsinpy_mutation_manual_fallback.py \
        --run-dir "$RUN_DIR" \
        --per-mutant-timeout-s "$PER_MUTANT_TIMEOUT_S" \
        | tee "$RUN_DIR/logs/manual_mutation_fallback_10u.log"
      ;;
    *)
      SKIP=$((SKIP+1))
      echo "SKIP manual fallback for status=$STATUS"
      ;;
  esac
done

echo
echo "===== REAGREGAR RESULTADOS APÓS MANUAL FALLBACK ====="

python3 - <<'PY'
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

root = Path("out/_final_bugsinpy_gpt4o_full_5rep")
rows = []

for p in sorted(root.glob("*/run_0001/*/metrics/status.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    d["_status_path"] = str(p)
    rows.append(d)

def fnum(v):
    try:
        if v is None:
            return 0.0
        return float(v)
    except Exception:
        return 0.0

status_counts = Counter(d.get("status") for d in rows)
sut_count = len({d.get("sut_id") for d in rows})
total = len(rows)

line_mean = sum(fnum(d.get("line_pct")) for d in rows) / total if total else 0.0
branch_mean = sum(fnum(d.get("branch_pct")) for d in rows) / total if total else 0.0
mutation_mean = sum(fnum(d.get("mutation_score_pct")) for d in rows) / total if total else 0.0

manual_used = sum(1 for d in rows if d.get("manual_mutation_fallback_used"))
mutation_available = sum(1 for d in rows if d.get("mutation_available") is True)

print("TOTAL_STATUS_FILES=", total)
print("TOTAL_SUTS=", sut_count)
print("STATUS_COUNTS=", json.dumps(dict(status_counts), sort_keys=True))
print("MUTATION_AVAILABLE_RUNS=", mutation_available)
print("MANUAL_FALLBACK_USED_RUNS=", manual_used)
print(f"LINE_PCT_PENALIZED_MEAN={line_mean:.4f}")
print(f"BRANCH_PCT_PENALIZED_MEAN={branch_mean:.4f}")
print(f"MUTATION_SCORE_PCT_PENALIZED_MEAN={mutation_mean:.4f}")

bad = []
allowed = {"ok", "mutation_results_empty"}
for d in rows:
    if d.get("status") not in allowed:
        bad.append(d)

print()
print("BAD_INFRA_COUNT=", len(bad))
for d in bad[:80]:
    print(
        d.get("sut_id"),
        d.get("target_module"),
        d.get("status"),
        "line=", d.get("line_pct"),
        "branch=", d.get("branch_pct"),
        "mut=", d.get("mutation_score_pct"),
        d.get("_status_path"),
    )

summary_path = root / "dataset_summary_manual_fallback.tsv"
index_path = root / "dataset_runs_index_manual_fallback.tsv"

with summary_path.open("w", encoding="utf-8", newline="") as f:
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
        total,
        sut_count,
        json.dumps(dict(status_counts), sort_keys=True),
        mutation_available,
        manual_used,
        f"{line_mean:.6f}",
        f"{branch_mean:.6f}",
        f"{mutation_mean:.6f}",
        len(bad),
    ])

with index_path.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "sut_id",
        "target_module",
        "status",
        "line_pct",
        "branch_pct",
        "mutation_score_pct",
        "mutation_available",
        "manual_mutation_fallback_used",
        "manual_mutation_fallback_total",
        "manual_mutation_fallback_killed",
        "manual_mutation_fallback_survived",
        "manual_mutation_fallback_timeout",
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
            "manual_mutation_fallback_used": d.get("manual_mutation_fallback_used"),
            "manual_mutation_fallback_total": d.get("manual_mutation_fallback_total"),
            "manual_mutation_fallback_killed": d.get("manual_mutation_fallback_killed"),
            "manual_mutation_fallback_survived": d.get("manual_mutation_fallback_survived"),
            "manual_mutation_fallback_timeout": d.get("manual_mutation_fallback_timeout"),
            "status_path": d.get("_status_path"),
        })

print()
print("DATASET_SUMMARY_MANUAL_FALLBACK_TSV=", summary_path)
print("DATASET_RUNS_INDEX_MANUAL_FALLBACK_TSV=", index_path)

if len(bad) == 0:
    print()
    print("✅ FINAL COM MUTATION FALLBACK ACEITÁVEL.")
else:
    print()
    print("⚠️ AINDA HÁ ESTADOS A ANALISAR.")
PY

echo
echo "===== DONE BUGSINPY MANUAL MUTATION FALLBACK ====="
date
