#!/usr/bin/env bash

set +e
set +u
set +o pipefail 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

FINAL_OUT="${FINAL_OUT:-$REPO/out/_final_bugsinpy_gpt4o_full_5rep_rerun2}"
PER_MUTANT_TIMEOUT_S="${PER_MUTANT_TIMEOUT_S:-20}"

echo "===== BUGSINPY RERUN2 MANUAL FALLBACK 10Z — SEM API ====="
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
  case "$STATUS" in
    mutation_no_checked_mutants|manual_fallback_10y_baseline_fail|manual_fallback_10z_baseline_fail)
      TARGETS+=("$STATUS_FILE")
      ;;
  esac
done

echo "FOUND_STATUS_FILES=${#STATUS_FILES[@]}"
echo "TARGETS_TO_RERUN=${#TARGETS[@]}"

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

  STATUS_BEFORE="$(python3 - "$STATUS_FILE" <<'PY'
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

  echo
  echo "======================================================================"
  echo "[$N/${#TARGETS[@]}] SUT=$SUT"
  echo "RUN_DIR=$RUN_DIR"
  echo "STATUS_BEFORE=$STATUS_BEFORE"
  echo "======================================================================"

  python3 tools/run_bugsinpy_mutation_manual_fallback_10z.py \
    --run-dir "$RUN_DIR" \
    --per-mutant-timeout-s "$PER_MUTANT_TIMEOUT_S"

  echo "fallback_rc=$?"
done

echo
echo "===== REAGREGAR RERUN2 APÓS MANUAL FALLBACK 10Z ====="

python3 - <<'PY'
import csv
import json
from pathlib import Path
from collections import Counter

root = Path("out/_final_bugsinpy_gpt4o_full_5rep_rerun2")

rows = []
bad_json = []

for p in sorted(root.glob("*/run_0001/*/metrics/status.json")):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        d["_status_json"] = str(p)
        d["_run_dir"] = str(p.parents[1])
        rows.append(d)
    except Exception as e:
        bad_json.append((str(p), repr(e)))

status_counts = Counter(d.get("status") for d in rows)

def fnum(v):
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except Exception:
        return 0.0

line_mean = sum(fnum(d.get("line_pct")) for d in rows) / len(rows) if rows else 0.0
branch_mean = sum(fnum(d.get("branch_pct")) for d in rows) / len(rows) if rows else 0.0
mut_mean = sum(fnum(d.get("mutation_score_pct")) for d in rows) / len(rows) if rows else 0.0

allowed = {"ok", "mutation_results_empty"}
bad_infra = [d for d in rows if d.get("status") not in allowed]

mutation_available_runs = sum(1 for d in rows if d.get("mutation_available") is True)

manual_fallback_used_runs = 0
for d in rows:
    counts = d.get("mutmut_counts") or {}
    parse_source = str(counts.get("parse_source") or "")
    if "manual_fallback" in parse_source:
        manual_fallback_used_runs += 1

summary_path = root / "dataset_summary_manual_fallback_10z_rerun2.tsv"
index_path = root / "dataset_runs_index_manual_fallback_10z_rerun2.tsv"

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
        "json_bad_count",
    ])
    w.writerow([
        len(rows),
        len({d.get("sut_id") for d in rows}),
        json.dumps(dict(status_counts), sort_keys=True),
        mutation_available_runs,
        manual_fallback_used_runs,
        f"{line_mean:.6f}",
        f"{branch_mean:.6f}",
        f"{mut_mean:.6f}",
        len(bad_infra),
        len(bad_json),
    ])

with index_path.open("w", encoding="utf-8", newline="") as f:
    fieldnames = [
        "sut_id",
        "target_module",
        "status",
        "line_pct",
        "branch_pct",
        "mutation_score_pct",
        "mutation_available",
        "generation_attempts",
        "generation_empty_attempts",
        "manual_fallback_10z_baseline_mode",
        "status_json",
        "run_dir",
    ]
    w = csv.DictWriter(f, delimiter="\t", fieldnames=fieldnames)
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
            "generation_attempts": d.get("generation_attempts"),
            "generation_empty_attempts": d.get("generation_empty_attempts"),
            "manual_fallback_10z_baseline_mode": d.get("manual_fallback_10z_baseline_mode"),
            "status_json": d.get("_status_json"),
            "run_dir": d.get("_run_dir"),
        })

print("TOTAL_STATUS_FILES=", len(rows))
print("TOTAL_SUTS=", len({d.get("sut_id") for d in rows}))
print("STATUS_COUNTS=", json.dumps(dict(status_counts), sort_keys=True))
print("MUTATION_AVAILABLE_RUNS=", mutation_available_runs)
print("MANUAL_FALLBACK_USED_RUNS=", manual_fallback_used_runs)
print(f"LINE_PCT_PENALIZED_MEAN={line_mean:.4f}")
print(f"BRANCH_PCT_PENALIZED_MEAN={branch_mean:.4f}")
print(f"MUTATION_SCORE_PCT_PENALIZED_MEAN={mut_mean:.4f}")
print("BAD_INFRA_COUNT=", len(bad_infra))
print("JSON_BAD_COUNT=", len(bad_json))

if bad_infra:
    print()
    print("===== BAD INFRA STATES =====")
    for d in bad_infra[:80]:
        print(
            d.get("sut_id"),
            d.get("target_module"),
            d.get("status"),
            "line=", d.get("line_pct"),
            "branch=", d.get("branch_pct"),
            "mut=", d.get("mutation_score_pct"),
            d.get("_status_json"),
        )
    print()
    print("⚠️ AINDA HÁ ESTADOS A ANALISAR.")
else:
    print()
    print("✅ FINAL RERUN2 COM MUTATION FALLBACK 10Z ACEITÁVEL: 16 SUTs × 5 reps, sem estados reais de infraestrutura.")

print()
print("DATASET_SUMMARY_MANUAL_FALLBACK_10Z_RERUN2_TSV=", summary_path)
print("DATASET_RUNS_INDEX_MANUAL_FALLBACK_10Z_RERUN2_TSV=", index_path)
PY

echo
echo "===== DONE BUGSINPY RERUN2 MANUAL FALLBACK 10Z ====="
date
