#!/usr/bin/env bash
set -u
set -o pipefail

REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OUT_BASE="${OUT_BASE:-${1:-}}"

PER_MUTANT_TIMEOUT_S="${PER_MUTANT_TIMEOUT_S:-20}"
MAX_MUTANTS="${MAX_MUTANTS:-0}"
DO_AGGREGATE="${DO_AGGREGATE:-1}"

FALLBACK_TOOL="$REPO/tools/run_bugsinpy_mutation_manual_fallback_10z.py"
AGGREGATOR="$REPO/tools/aggregate_bugsinpy_gpt4o_status.py"

if [[ -z "$OUT_BASE" ]]; then
  echo "ERRO: define OUT_BASE ou passa OUT_BASE como primeiro argumento."
  exit 2
fi

if [[ ! -d "$OUT_BASE" ]]; then
  echo "ERRO: OUT_BASE não existe: $OUT_BASE"
  exit 3
fi

if [[ ! -f "$FALLBACK_TOOL" ]]; then
  echo "ERRO: fallback tool não existe: $FALLBACK_TOOL"
  exit 4
fi

LOG="$OUT_BASE/manual_fallback_10z_outbase.log"
CAND="$OUT_BASE/manual_fallback_10z_candidates.tsv"

echo "===== BUGSINPY MANUAL FALLBACK 10Z OUT_BASE =====" | tee "$LOG"
echo "REPO=$REPO" | tee -a "$LOG"
echo "OUT_BASE=$OUT_BASE" | tee -a "$LOG"
echo "PER_MUTANT_TIMEOUT_S=$PER_MUTANT_TIMEOUT_S" | tee -a "$LOG"
echo "MAX_MUTANTS=$MAX_MUTANTS" | tee -a "$LOG"
echo "DO_AGGREGATE=$DO_AGGREGATE" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"

"$PYTHON_BIN" - "$OUT_BASE" "$CAND" <<'PY'
import json
import sys
from pathlib import Path

out_base = Path(sys.argv[1])
cand = Path(sys.argv[2])

target_statuses = {
    "mutation_no_checked_mutants",
    "manual_fallback_10y_baseline_fail",
    "manual_fallback_10z_baseline_fail",
}

rows = []
all_status = []

for p in sorted(out_base.glob("*/run_*/**/metrics/status.json")):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue

    status = d.get("status")
    mutation_available = bool(d.get("mutation_available"))
    all_status.append((status, str(p)))

    if status in target_statuses and not mutation_available:
        run_dir = p.parent.parent
        rows.append((str(run_dir), status, d.get("sut_id"), d.get("target_module")))

cand.parent.mkdir(parents=True, exist_ok=True)
with cand.open("w", encoding="utf-8") as f:
    f.write("run_dir\tstatus\tsut_id\ttarget_module\n")
    for row in rows:
        f.write("\t".join("" if x is None else str(x) for x in row) + "\n")

print(f"total_status_files={len(all_status)}")
print(f"fallback_candidates={len(rows)}")
PY

echo | tee -a "$LOG"
echo "===== CANDIDATES =====" | tee -a "$LOG"
cat "$CAND" | tee -a "$LOG"

TOTAL=0
OK=0
FAIL=0

tail -n +2 "$CAND" | while IFS=$'\t' read -r RUN_DIR STATUS SUT_ID TARGET_MODULE; do
  [[ -z "$RUN_DIR" ]] && continue

  TOTAL=$((TOTAL + 1))

  echo | tee -a "$LOG"
  echo "===== FALLBACK RUN_DIR =====" | tee -a "$LOG"
  echo "RUN_DIR=$RUN_DIR" | tee -a "$LOG"
  echo "status_before=$STATUS sut_id=$SUT_ID target_module=$TARGET_MODULE" | tee -a "$LOG"

  set +e
  if [[ "$MAX_MUTANTS" != "0" ]]; then
    "$PYTHON_BIN" "$FALLBACK_TOOL" \
      --run-dir "$RUN_DIR" \
      --per-mutant-timeout-s "$PER_MUTANT_TIMEOUT_S" \
      --max-mutants "$MAX_MUTANTS" \
      > "$RUN_DIR/logs/manual_fallback_10z.stdout.log" \
      2> "$RUN_DIR/logs/manual_fallback_10z.stderr.log"
  else
    "$PYTHON_BIN" "$FALLBACK_TOOL" \
      --run-dir "$RUN_DIR" \
      --per-mutant-timeout-s "$PER_MUTANT_TIMEOUT_S" \
      > "$RUN_DIR/logs/manual_fallback_10z.stdout.log" \
      2> "$RUN_DIR/logs/manual_fallback_10z.stderr.log"
  fi
  RC=$?
  set -u

  echo "fallback_rc=$RC" | tee -a "$LOG"
  tail -n 40 "$RUN_DIR/logs/manual_fallback_10z.stdout.log" 2>/dev/null | tee -a "$LOG"

  if [[ "$RC" = "0" ]]; then
    OK=$((OK + 1))
  else
    FAIL=$((FAIL + 1))
  fi
done

echo | tee -a "$LOG"
echo "===== POST-FALLBACK STATUS COUNTS =====" | tee -a "$LOG"
"$PYTHON_BIN" - "$OUT_BASE" <<'PY' | tee -a "$LOG"
import json
from pathlib import Path
from collections import Counter
import sys

out = Path(sys.argv[1])
rows = []
bad_json = 0

for p in sorted(out.glob("*/run_*/**/metrics/status.json")):
    try:
        rows.append(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        bad_json += 1

print("status_files=", len(rows))
print("json_bad=", bad_json)
print("sut_count=", len({d.get("sut_id") for d in rows}))
print("status_counts=", dict(Counter(d.get("status") for d in rows)))
print("mutation_available_runs=", sum(1 for d in rows if d.get("mutation_available")))

def mean(key):
    vals = []
    for d in rows:
        v = d.get(key)
        vals.append(float(v) if v is not None else 0.0)
    return sum(vals) / len(vals) if vals else 0.0

print("line_mean_penalized=", mean("line_pct"))
print("branch_mean_penalized=", mean("branch_pct"))
print("mutation_mean_penalized=", mean("mutation_score_pct"))
PY

if [[ "$DO_AGGREGATE" = "1" && -f "$AGGREGATOR" ]]; then
  echo | tee -a "$LOG"
  echo "===== AGGREGATING AFTER FALLBACK =====" | tee -a "$LOG"
  set +e
  "$PYTHON_BIN" "$AGGREGATOR" --out-base "$OUT_BASE" 2>&1 | tee -a "$LOG"
  AGG_RC=${PIPESTATUS[0]}
  set -u
  echo "AGGREGATOR_RC=$AGG_RC" | tee -a "$LOG"
fi

echo | tee -a "$LOG"
echo "===== DONE BUGSINPY MANUAL FALLBACK 10Z OUT_BASE =====" | tee -a "$LOG"
echo "OUT_BASE=$OUT_BASE" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"

exit 0
