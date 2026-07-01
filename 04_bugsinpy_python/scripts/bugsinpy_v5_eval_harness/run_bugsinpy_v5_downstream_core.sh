#!/usr/bin/env bash
set -euo pipefail
set +H 2>/dev/null || true

REPO="/home/jpaiva/projetos/bugsinpy_gpt4o"
cd "$REPO" || exit 1

FINAL_OUT="${FINAL_OUT:-$REPO/out/_final_bugsinpy_gpt4o_full_5rep}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}"

SHIMS_TOOL="$REPO/tools/apply_bugsinpy_runtime_shims.py"
NORMALIZE_TOOL="$REPO/tools/normalize_bugsinpy_generated_test.py"
RAW_VALIDATOR="$REPO/tools/validate_bugsinpy_generated_pytest.py"
SANITIZER="$REPO/tools/sanitize_and_validate_bugsinpy_pytest.py"
COVERAGE_TOOL="$REPO/tools/run_bugsinpy_coverage.py"
MUTATION_TOOL="/home/jpaiva/projetos/bugsinpy_v5_eval_harness/tools/run_bugsinpy_mutation_flat_v5_packageaware_v2.py"
RUNNABLE_TOOL="/home/jpaiva/projetos/bugsinpy_v5_eval_harness/tools/mark_bugsinpy_runnable_suite_v5.py"
CLEANUP_TOOL="/home/jpaiva/projetos/bugsinpy_v5_eval_harness/tools/cleanup_bugsinpy_mutation_project_v5.py"

echo "===== BUGSINPY FINAL DOWNSTREAM RERUN — SEM API ====="
echo "REPO=$REPO"
echo "FINAL_OUT=$FINAL_OUT"
echo "PYTEST_TIMEOUT_S=$PYTEST_TIMEOUT_S"
echo "MUTATION_TIMEOUT_S=$MUTATION_TIMEOUT_S"

if [[ ! -d "$FINAL_OUT" ]]; then
  echo "ERRO: FINAL_OUT nao existe: $FINAL_OUT"
  exit 1
fi

get_status() {
  local run_dir="$1"
  python3 - "$run_dir" <<'PY'
import json, sys
from pathlib import Path

run_dir = Path(sys.argv[1])
p = run_dir / "metrics" / "status.json"
if not p.exists():
    print("")
else:
    try:
        print(json.loads(p.read_text(encoding="utf-8")).get("status") or "")
    except Exception:
        print("")
PY
}

print_run_core() {
  local run_dir="$1"
  python3 - "$run_dir" <<'PY'
import json, sys
from pathlib import Path

run_dir = Path(sys.argv[1])
p = run_dir / "metrics" / "status.json"

if not p.exists():
    print("status_json_missing")
    raise SystemExit(0)

d = json.loads(p.read_text(encoding="utf-8"))

for k in [
    "sut_id",
    "target_module",
    "status",
    "generation_attempts",
    "generation_empty_attempts",
    "generated_test_compile_exit_code",
    "sut_import_check_exit_code",
    "pytest_raw_exit_code",
    "pytest_final_exit_code",
    "coverage_exit_code",
    "coverage_available",
    "line_pct",
    "branch_pct",
    "mutation_available",
    "mutation_score_pct",
    "mutmut_exit_code",
    "mutmut_results_exit_code",
    "mutation_target_relpath",
    "mutmut_counts",
]:
    print(f"{k}={d.get(k)}")
PY
}

run_tool() {
  local label="$1"
  local log_file="$2"
  shift 2

  echo
  echo ">>> $label"
  set +e
  "$@" 2>&1 | tee "$log_file"
  local rc=${PIPESTATUS[0]}
  set -e
  echo "${label}_RC=$rc"
  return 0
}

mapfile -t STATUS_FILES < <(find "$FINAL_OUT" -path "*/metrics/status.json" | sort)

echo "FOUND_STATUS_FILES=${#STATUS_FILES[@]}"

i=0
for STATUS_FILE in "${STATUS_FILES[@]}"; do
  i=$((i + 1))
  RUN_DIR="$(dirname "$(dirname "$STATUS_FILE")")"
  LOG_DIR="$RUN_DIR/logs"
  mkdir -p "$LOG_DIR"

  echo
  echo "======================================================================"
  echo "[$i/${#STATUS_FILES[@]}] RERUN DOWNSTREAM SEM API"
  echo "RUN_DIR=$RUN_DIR"
  echo "======================================================================"

  run_tool "runtime_shims" "$LOG_DIR/rerun_noapi_runtime_shims.log" \
    python3 "$SHIMS_TOOL" \
      --run-dir "$RUN_DIR"

  run_tool "normalize_generated_test" "$LOG_DIR/rerun_noapi_normalize.log" \
    python3 "$NORMALIZE_TOOL" \
      --run-dir "$RUN_DIR"

  run_tool "raw_validator" "$LOG_DIR/rerun_noapi_raw_validator.log" \
    python3 "$RAW_VALIDATOR" \
      --run-dir "$RUN_DIR" \
      --pytest-timeout-s "$PYTEST_TIMEOUT_S"

  STATUS_AFTER_RAW="$(get_status "$RUN_DIR")"
  echo "STATUS_AFTER_RAW=$STATUS_AFTER_RAW"

  if [[ "$STATUS_AFTER_RAW" == "pytest_raw_fail" ]]; then
    run_tool "sanitizer" "$LOG_DIR/rerun_noapi_sanitizer.log" \
      python3 "$SANITIZER" \
        --run-dir "$RUN_DIR" \
        --pytest-timeout-s "$PYTEST_TIMEOUT_S"
  else
    echo "SKIP sanitizer because status=$STATUS_AFTER_RAW"
  fi

  STATUS_AFTER_TESTS="$(get_status "$RUN_DIR")"
  echo "STATUS_AFTER_TESTS=$STATUS_AFTER_TESTS"

  python3 "$RUNNABLE_TOOL" --run-dir "$RUN_DIR" 2>&1 | tee "$LOG_DIR/rerun_noapi_runnable_gate.log"

  STATUS_AFTER_TESTS="$(get_status "$RUN_DIR")"
  echo "STATUS_AFTER_RUNNABLE_GATE=$STATUS_AFTER_TESTS"

  case "$STATUS_AFTER_TESTS" in
    pytest_raw_pass|pytest_final_pass|coverage_pass|coverage_fail|ok|mutation_results_empty|mutation_no_checked_mutants)
      run_tool "coverage" "$LOG_DIR/rerun_noapi_coverage.log" \
        python3 "$COVERAGE_TOOL" \
          --run-dir "$RUN_DIR" \
          --pytest-timeout-s "$PYTEST_TIMEOUT_S"

      chmod -R u+rwX "$RUN_DIR/work/mutation_project" 2>/dev/null || true
      rm -rf "$RUN_DIR/work/mutation_project" 2>/dev/null || true

      run_tool "mutation_flat" "$LOG_DIR/rerun_noapi_mutation_flat.log" \
        python3 "$MUTATION_TOOL" \
          --run-dir "$RUN_DIR" \
          --mutation-timeout-s "$MUTATION_TIMEOUT_S"

      python3 "$CLEANUP_TOOL" --run-dir "$RUN_DIR" 2>&1 | tee "$LOG_DIR/rerun_noapi_mutation_cleanup.log"
      ;;
    *)
      echo "SKIP coverage/mutation because status=$STATUS_AFTER_TESTS"
      ;;
  esac

  echo
  echo "----- STATUS FINAL DO RUN -----"
  print_run_core "$RUN_DIR"
done


echo
echo "===== REAGREGAR RESULTADOS A PARTIR DOS STATUS.JSON ====="

python3 - "$FINAL_OUT" <<'PY'
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict
import sys

root = Path(sys.argv[1])

rows = []
for p in sorted(root.glob("*/run_0001/*/metrics/status.json")):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue

    d["_status_path"] = str(p)
    d["_run_dir"] = str(p.parents[1])
    rows.append(d)

def fnum(v):
    try:
        if v is None:
            return 0.0
        return float(v)
    except Exception:
        return 0.0

def mean_penalised(key):
    return sum(fnum(d.get(key)) for d in rows) / len(rows) if rows else 0.0

index_path = root / "dataset_runs_index.tsv"
summary_path = root / "dataset_summary.tsv"

index_fields = [
    "sut_id",
    "target_module",
    "status",
    "generation_attempts",
    "generation_empty_attempts",
    "generated_test_compile_exit_code",
    "sut_import_check_exit_code",
    "pytest_raw_exit_code",
    "pytest_final_exit_code",
    "coverage_exit_code",
    "coverage_available",
    "line_pct",
    "branch_pct",
    "mutation_available",
    "mutation_score_pct",
    "mutmut_exit_code",
    "mutmut_results_exit_code",
    "mutation_target_relpath",
    "run_dir",
    "status_path",
]

with index_path.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow(index_fields)
    for d in rows:
        w.writerow([
            d.get("sut_id"),
            d.get("target_module"),
            d.get("status"),
            d.get("generation_attempts"),
            d.get("generation_empty_attempts"),
            d.get("generated_test_compile_exit_code"),
            d.get("sut_import_check_exit_code"),
            d.get("pytest_raw_exit_code"),
            d.get("pytest_final_exit_code"),
            d.get("coverage_exit_code"),
            d.get("coverage_available"),
            d.get("line_pct"),
            d.get("branch_pct"),
            d.get("mutation_available"),
            d.get("mutation_score_pct"),
            d.get("mutmut_exit_code"),
            d.get("mutmut_results_exit_code"),
            d.get("mutation_target_relpath"),
            d.get("_run_dir"),
            d.get("_status_path"),
        ])

status_counts = Counter(d.get("status") for d in rows)
sut_count = len({d.get("sut_id") for d in rows})

summary_rows = [
    ("out_base", str(root)),
    ("total_status_files", len(rows)),
    ("total_suts", sut_count),
    ("status_counts_json", json.dumps(dict(status_counts), sort_keys=True)),
    ("line_pct_penalized_mean", f"{mean_penalised('line_pct'):.4f}"),
    ("branch_pct_penalized_mean", f"{mean_penalised('branch_pct'):.4f}"),
    ("mutation_score_pct_penalized_mean", f"{mean_penalised('mutation_score_pct'):.4f}"),
]

with summary_path.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow(["metric", "value"])
    w.writerows(summary_rows)

print(f"OUT_BASE={root}")
print(f"TOTAL_STATUS_FILES={len(rows)}")
print(f"TOTAL_SUTS={sut_count}")
print(f"STATUS_COUNTS={json.dumps(dict(status_counts), sort_keys=True)}")
print(f"LINE_PCT_PENALIZED_MEAN={mean_penalised('line_pct'):.4f}")
print(f"BRANCH_PCT_PENALIZED_MEAN={mean_penalised('branch_pct'):.4f}")
print(f"MUTATION_SCORE_PCT_PENALIZED_MEAN={mean_penalised('mutation_score_pct'):.4f}")
print(f"DATASET_SUMMARY_TSV={summary_path}")
print(f"DATASET_RUNS_INDEX_TSV={index_path}")
PY


echo
echo "===== CHECK FINAL ====="

python3 - "$FINAL_OUT" <<'PY'
import json
from pathlib import Path
from collections import Counter
import sys

root = Path(sys.argv[1])

allowed_terminal = {
    "ok",
    "mutation_results_empty",
    "mutation_no_checked_mutants",
}

rows = []
bad = []

for p in sorted(root.glob("*/run_0001/*/metrics/status.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    rows.append(d)
    if d.get("status") not in allowed_terminal:
        bad.append((p, d))

print("status_files=", len(rows))
print("sut_count=", len({d.get("sut_id") for d in rows}))
print("status_counts=", dict(Counter(d.get("status") for d in rows)))

print()
print("BAD_INFRA_COUNT=", len(bad))
for p, d in bad:
    print(
        d.get("sut_id"),
        d.get("target_module"),
        d.get("status"),
        "line=", d.get("line_pct"),
        "branch=", d.get("branch_pct"),
        "mut=", d.get("mutation_score_pct"),
        p,
    )

def mean_penalised(key):
    vals = []
    for d in rows:
        v = d.get(key)
        vals.append(float(v) if v is not None else 0.0)
    return sum(vals) / len(vals) if vals else 0.0

print()
print("line_mean_penalized=", mean_penalised("line_pct"))
print("branch_mean_penalized=", mean_penalised("branch_pct"))
print("mutation_mean_penalized=", mean_penalised("mutation_score_pct"))

print()
if len(rows) == 80 and len({d.get("sut_id") for d in rows}) == 16 and not bad:
    print("✅ FINAL ACEITÁVEL: 16 SUTs × 5 reps, sem estados reais de infraestrutura.")
else:
    print("❌ FINAL AINDA PRECISA DE ANÁLISE.")
PY

echo
echo "===== DONE RERUN DOWNSTREAM SEM API ====="
date
