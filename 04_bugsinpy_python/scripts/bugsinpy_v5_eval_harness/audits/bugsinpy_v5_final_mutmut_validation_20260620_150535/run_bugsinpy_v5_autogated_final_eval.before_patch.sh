#!/usr/bin/env bash
set -Eeuo pipefail

source "/home/jpaiva/projetos/bugsinpy_v5_eval_harness/current_bugsinpy_v5_eval.env"

HARNESS="/home/jpaiva/projetos/bugsinpy_v5_eval_harness"
WRAPPER="$HARNESS/run_bugsinpy_v5_downstream_no_api.sh"

STAMP="$(date +%Y%m%d_%H%M%S)"

SESSION_ROOT="$HARNESS/final_eval_${STAMP}"
LOG_ROOT="$SESSION_ROOT/logs"
AUDIT_ROOT="$SESSION_ROOT/audit"

SMOKE_ROOT="$PROJECT/out/_smoke_bugsinpy_v5_package_target_${STAMP}"
SMOKE_SOURCE="$EVAL_ROOT/cluster-safe-qwen3-coder-30b-official-ctx32k/PySnooper_2f/run_0001/0001-5"
SMOKE_RUN="$SMOKE_ROOT/PySnooper_2f/run_0001/0001-5"
SMOKE_LOG="$LOG_ROOT/package_target_smoke.log"

PRE_STATUS_BACKUP="$AUDIT_ROOT/pre_final_status_json.tar.gz"
COMPLETION_MARKER="$SESSION_ROOT/FINAL_EVALUATION_COMPLETED.txt"

mkdir -p "$LOG_ROOT" "$AUDIT_ROOT"

MAIN_LOG="$SESSION_ROOT/main.log"

exec > >(tee -a "$MAIN_LOG") 2>&1

echo "======================================================================"
echo "BUGSINPY V5 AUTOGATED FINAL EVALUATION"
echo "======================================================================"
date
echo "PROJECT=$PROJECT"
echo "EVAL_ROOT=$EVAL_ROOT"
echo "HARNESS=$HARNESS"
echo "SESSION_ROOT=$SESSION_ROOT"
echo "SMOKE_ROOT=$SMOKE_ROOT"
echo

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTEST_ADDOPTS=
export PYTHONDONTWRITEBYTECODE=1

test -d "$EVAL_ROOT" || {
  echo "ERRO: EVAL_ROOT não existe"
  exit 1
}

test -d "$SMOKE_SOURCE" || {
  echo "ERRO: smoke source não existe: $SMOKE_SOURCE"
  exit 1
}

echo "===== INITIAL COUNTS ====="

STATUS_COUNT="$(
  find "$EVAL_ROOT" \
    -path '*/metrics/status.json' \
    -type f |
  wc -l
)"

MODEL_COUNT="$(
  find "$EVAL_ROOT" \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -name 'cluster-*' |
  wc -l
)"

echo "status_count=$STATUS_COUNT"
echo "model_count=$MODEL_COUNT"

test "$STATUS_COUNT" -eq 443
test "$MODEL_COUNT" -eq 7

echo
echo "===== BACKUP PRE-FINAL STATUS FILES ====="

(
  cd "$EVAL_ROOT"

  find . \
    -path '*/metrics/status.json' \
    -type f \
    -print0 |
  tar \
    --null \
    -czf "$PRE_STATUS_BACKUP" \
    --files-from=-
)

sha256sum "$PRE_STATUS_BACKUP" \
  > "$PRE_STATUS_BACKUP.sha256"

ls -lh "$PRE_STATUS_BACKUP" "$PRE_STATUS_BACKUP.sha256"

echo
echo "===== CREATE CLEAN PACKAGE-TARGET SMOKE ====="

rm -rf -- "$SMOKE_ROOT"

mkdir -p "$(dirname "$SMOKE_RUN")"
cp -a "$SMOKE_SOURCE" "$SMOKE_RUN"

python3 - "$SMOKE_SOURCE" "$SMOKE_RUN" <<'PY'
import json
import sys
from pathlib import Path

old_root = Path(sys.argv[1]).resolve()
new_root = Path(sys.argv[2]).resolve()

def replace_paths(value):
    if isinstance(value, str):
        return value.replace(
            str(old_root),
            str(new_root),
        )

    if isinstance(value, list):
        return [replace_paths(item) for item in value]

    if isinstance(value, dict):
        return {
            key: replace_paths(item)
            for key, item in value.items()
        }

    return value

for path in new_root.rglob("*.json"):
    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except Exception:
        continue

    path.write_text(
        json.dumps(
            replace_paths(data),
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
PY

echo
echo "===== RUN AUTOGATE SMOKE ====="

FINAL_OUT="$SMOKE_ROOT" \
PYTEST_TIMEOUT_S=90 \
MUTATION_TIMEOUT_S=300 \
bash "$WRAPPER" \
  2>&1 | tee "$SMOKE_LOG"

echo
echo "===== VALIDATE AUTOGATE SMOKE ====="

python3 - "$SMOKE_RUN/metrics/status.json" <<'PY'
import json
import sys
from pathlib import Path

status_path = Path(sys.argv[1])

data = json.loads(
    status_path.read_text(
        encoding="utf-8",
        errors="replace",
    )
)

counts = data.get("mutmut_counts") or {}

checked = sum(
    int(counts.get(key) or 0)
    for key in (
        "killed",
        "survived",
        "timeout",
        "suspicious",
    )
)

checks = {
    "status_ok": data.get("status") == "ok",
    "runnable_tests": int(
        data.get("runnable_test_count") or 0
    ) > 0,
    "coverage_available": bool(
        data.get("coverage_available")
    ),
    "mutation_available": bool(
        data.get("mutation_available")
    ),
    "checked_mutants": checked > 0,
    "mutation_project_cleaned": bool(
        data.get("mutation_project_cleaned")
    ),
}

for key, value in checks.items():
    print(f"{key}={value}")

print(f"status={data.get('status')}")
print(f"runnable_test_count={data.get('runnable_test_count')}")
print(f"line_pct={data.get('line_pct')}")
print(f"branch_pct={data.get('branch_pct')}")
print(f"mutation_score_pct={data.get('mutation_score_pct')}")
print(f"mutation_target_relpath={data.get('mutation_target_relpath')}")
print(f"checked_mutants={checked}")
print(f"mutmut_counts={counts}")

failed = [
    key
    for key, value in checks.items()
    if not value
]

if failed:
    print(
        "AUTOGATE_STATUS=FAILED:"
        + ",".join(failed)
    )
    raise SystemExit(20)

print("AUTOGATE_STATUS=PASSED")
PY

echo
echo "===== PRESERVE SMALL SMOKE EVIDENCE ====="

SMOKE_EVIDENCE="$AUDIT_ROOT/package_target_smoke_evidence"
mkdir -p "$SMOKE_EVIDENCE"

cp -a \
  "$SMOKE_RUN/metrics/status.json" \
  "$SMOKE_EVIDENCE/"

for file in \
  "$SMOKE_RUN/metrics/mutation_isolation.json" \
  "$SMOKE_RUN/metrics/mutmut_counts.json" \
  "$SMOKE_RUN/metrics/mutation_results.txt" \
  "$SMOKE_RUN/logs/mutmut.stdout.log" \
  "$SMOKE_RUN/logs/mutmut.stderr.log" \
  "$SMOKE_RUN/logs/mutmut_results.stdout.log" \
  "$SMOKE_RUN/logs/mutmut_results.stderr.log" \
  "$SMOKE_LOG"
do
  [ -f "$file" ] && cp -a "$file" "$SMOKE_EVIDENCE/" || true
done

tar -czf \
  "$SMOKE_EVIDENCE.tar.gz" \
  -C "$(dirname "$SMOKE_EVIDENCE")" \
  "$(basename "$SMOKE_EVIDENCE")"

sha256sum "$SMOKE_EVIDENCE.tar.gz" \
  > "$SMOKE_EVIDENCE.tar.gz.sha256"

echo
echo "===== DELETE OBSOLETE SMOKE ====="

du -sh "$SMOKE_ROOT" || true
rm -rf -- "$SMOKE_ROOT"

test ! -e "$SMOKE_ROOT"

echo "REMOVED $SMOKE_ROOT"

echo
echo "======================================================================"
echo "AUTOGATE PASSED — STARTING FULL 443-CASE EVALUATION"
echo "======================================================================"
date

for MODEL_DIR in "$EVAL_ROOT"/cluster-*; do
  [ -d "$MODEL_DIR" ] || continue

  MODEL_NAME="$(basename "$MODEL_DIR")"
  MODEL_LOG="$LOG_ROOT/${MODEL_NAME}.log"
  DONE_MARKER="$LOG_ROOT/${MODEL_NAME}.done"

  echo
  echo "======================================================================"
  echo "MODEL=$MODEL_NAME"
  echo "MODEL_DIR=$MODEL_DIR"
  echo "MODEL_LOG=$MODEL_LOG"
  echo "======================================================================"
  date

  EXPECTED="$(
    find "$MODEL_DIR" \
      -path '*/metrics/status.json' \
      -type f |
    wc -l
  )"

  echo "expected_status_files=$EXPECTED"

  FINAL_OUT="$MODEL_DIR" \
  PYTEST_TIMEOUT_S=90 \
  MUTATION_TIMEOUT_S=300 \
  bash "$WRAPPER" \
    2>&1 | tee "$MODEL_LOG"

  echo
  echo "===== DEFENSIVE MUTATION-PROJECT CLEANUP ====="

  find "$MODEL_DIR" \
    -type d \
    -path '*/work/mutation_project' \
    -prune \
    -print \
    -exec rm -rf -- {} +

  LEFTOVER_MUTATION_PROJECTS="$(
    find "$MODEL_DIR" \
      -type d \
      -path '*/work/mutation_project' |
    wc -l
  )"

  ACTUAL="$(
    find "$MODEL_DIR" \
      -path '*/metrics/status.json' \
      -type f |
    wc -l
  )"

  SUMMARY_COUNT="$(
    find "$MODEL_DIR" \
      -maxdepth 1 \
      -type f \
      -name 'dataset_summary.tsv' |
    wc -l
  )"

  echo "actual_status_files=$ACTUAL"
  echo "dataset_summary_count=$SUMMARY_COUNT"
  echo "leftover_mutation_projects=$LEFTOVER_MUTATION_PROJECTS"

  test "$ACTUAL" -eq "$EXPECTED"
  test "$SUMMARY_COUNT" -eq 1
  test "$LEFTOVER_MUTATION_PROJECTS" -eq 0

  {
    echo "model=$MODEL_NAME"
    echo "completed_at=$(date --iso-8601=seconds)"
    echo "status_files=$ACTUAL"
    echo "dataset_summary=$MODEL_DIR/dataset_summary.tsv"
  } > "$DONE_MARKER"

  echo
  echo "===== DISK AFTER MODEL ====="
  df -h "$EVAL_ROOT"

  FREE_KB="$(
    df -Pk "$EVAL_ROOT" |
    awk 'NR==2 {print $4}'
  )"

  if [ "$FREE_KB" -lt 15728640 ]; then
    echo "ERRO: menos de 15 GiB livres; avaliação interrompida com segurança."
    exit 30
  fi

  echo
  echo "MODEL_COMPLETED=$MODEL_NAME"
  date
done

echo
echo "===== FINAL FULL-EVALUATION CHECK ====="

DONE_COUNT="$(
  find "$LOG_ROOT" \
    -maxdepth 1 \
    -type f \
    -name '*.done' |
  wc -l
)"

STATUS_COUNT_AFTER="$(
  find "$EVAL_ROOT" \
    -path '*/metrics/status.json' \
    -type f |
  wc -l
)"

LEFTOVER_AFTER="$(
  find "$EVAL_ROOT" \
    -type d \
    -path '*/work/mutation_project' |
  wc -l
)"

echo "completed_models=$DONE_COUNT"
echo "status_files=$STATUS_COUNT_AFTER"
echo "leftover_mutation_projects=$LEFTOVER_AFTER"

test "$DONE_COUNT" -eq 7
test "$STATUS_COUNT_AFTER" -eq 443
test "$LEFTOVER_AFTER" -eq 0

{
  echo "BUGSINPY V5 FINAL EVALUATION COMPLETED"
  echo "completed_at=$(date --iso-8601=seconds)"
  echo "models=7"
  echo "prepared_cluster_ok_runs=443"
  echo "total_requested_runs=560"
  echo "eval_root=$EVAL_ROOT"
  echo "session_root=$SESSION_ROOT"
} > "$COMPLETION_MARKER"

echo
echo "======================================================================"
echo "BUGSINPY V5 FULL EVALUATION COMPLETED"
echo "======================================================================"
cat "$COMPLETION_MARKER"

df -h "$EVAL_ROOT"
date
