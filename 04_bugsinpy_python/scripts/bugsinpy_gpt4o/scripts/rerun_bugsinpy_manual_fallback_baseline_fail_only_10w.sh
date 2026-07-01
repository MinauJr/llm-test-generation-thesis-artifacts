#!/usr/bin/env bash

set +e
set +u
set +o pipefail 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

FINAL_OUT="${FINAL_OUT:-$REPO/out/_final_bugsinpy_gpt4o_full_5rep}"
PER_MUTANT_TIMEOUT_S="${PER_MUTANT_TIMEOUT_S:-20}"

echo "===== BUGSINPY MANUAL FALLBACK 10W — baseline_fail only, SEM API ====="
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
  echo "[$N/${#TARGETS[@]}] RERUN MANUAL FALLBACK 10W"
  echo "SUT=$SUT"
  echo "RUN_DIR=$RUN_DIR"
  echo "======================================================================"

  python3 tools/run_bugsinpy_mutation_manual_fallback.py \
    --run-dir "$RUN_DIR" \
    --per-mutant-timeout-s "$PER_MUTANT_TIMEOUT_S" \
    --force \
    2>&1 | tee "$RUN_DIR/logs/manual_fallback_10w.log"

  echo "manual_fallback_10w_RC=${PIPESTATUS[0]}"
done

echo
echo "===== REAGREGAR RESULTADOS APÓS 10W ====="

python3 - <<'PY'
import json
from pathlib import Path
from collections import Counter

root = Path("out/_final_bugsinpy_gpt4o_full_5rep")
rows = []

for p in sorted(root.glob("*/run_0001/*/metrics/status.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    d["_path"] = str(p)
    rows.append(d)

allowed = {
    "ok",
    "mutation_results_empty",
    "mutation_no_checked_mutants",
}

bad = [d for d in rows if d.get("status") not in allowed]

def mean_penalised(key):
    vals = []
    for d in rows:
        v = d.get(key)
        vals.append(float(v) if v is not None else 0.0)
    return sum(vals) / len(vals) if vals else 0.0

status_counts = Counter(d.get("status") for d in rows)
manual_used = sum(1 for d in rows if d.get("mutation_manual_fallback_used"))
mutation_available = sum(1 for d in rows if d.get("mutation_available") is True)

print("TOTAL_STATUS_FILES=", len(rows))
print("TOTAL_SUTS=", len({d.get("sut_id") for d in rows}))
print("STATUS_COUNTS=", json.dumps(dict(status_counts), sort_keys=True))
print("MUTATION_AVAILABLE_RUNS=", mutation_available)
print("MANUAL_FALLBACK_USED_RUNS=", manual_used)
print(f"LINE_PCT_PENALIZED_MEAN={mean_penalised('line_pct'):.4f}")
print(f"BRANCH_PCT_PENALIZED_MEAN={mean_penalised('branch_pct'):.4f}")
print(f"MUTATION_SCORE_PCT_PENALIZED_MEAN={mean_penalised('mutation_score_pct'):.4f}")
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
        d.get("_path"),
    )

summary = root / "dataset_summary_manual_fallback_10w.tsv"
index = root / "dataset_runs_index_manual_fallback_10w.tsv"

with summary.open("w", encoding="utf-8") as f:
    f.write(
        "total_status_files\ttotal_suts\tstatus_counts_json\t"
        "mutation_available_runs\tmanual_fallback_used_runs\t"
        "line_pct_penalized_mean\tbranch_pct_penalized_mean\tmutation_score_pct_penalized_mean\tbad_infra_count\n"
    )
    f.write(
        f"{len(rows)}\t"
        f"{len({d.get('sut_id') for d in rows})}\t"
        f"{json.dumps(dict(status_counts), sort_keys=True)}\t"
        f"{mutation_available}\t"
        f"{manual_used}\t"
        f"{mean_penalised('line_pct'):.6f}\t"
        f"{mean_penalised('branch_pct'):.6f}\t"
        f"{mean_penalised('mutation_score_pct'):.6f}\t"
        f"{len(bad)}\n"
    )

cols = [
    "sut_id",
    "target_module",
    "status",
    "line_pct",
    "branch_pct",
    "mutation_available",
    "mutation_score_pct",
    "mutation_manual_fallback_used",
    "manual_fallback_baseline_mode",
    "manual_fallback_mutant_mode",
    "mutmut_counts",
    "_path",
]

with index.open("w", encoding="utf-8") as f:
    f.write("\t".join(cols) + "\n")
    for d in rows:
        vals = []
        for c in cols:
            v = d.get(c)
            if isinstance(v, (dict, list)):
                v = json.dumps(v, sort_keys=True)
            vals.append("" if v is None else str(v))
        f.write("\t".join(vals) + "\n")

print()
print("DATASET_SUMMARY_MANUAL_FALLBACK_10W_TSV=", summary)
print("DATASET_RUNS_INDEX_MANUAL_FALLBACK_10W_TSV=", index)

if not bad:
    print()
    print("✅ FINAL COM MUTATION FALLBACK 10W ACEITÁVEL: sem estados reais de infraestrutura.")
else:
    print()
    print("⚠️ AINDA HÁ ESTADOS A ANALISAR.")
PY

echo
echo "===== DONE BUGSINPY MANUAL FALLBACK 10W ====="
date
