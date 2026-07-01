#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true
umask 077

ROOT='/home/jpaiva/projetos/bugsinpy_gpt55'
MUTATION_TOOL='/home/jpaiva/projetos/bugsinpy_gpt55/tools/run_bugsinpy_mutation_manual_fallback_10z.py'
STAGE12_AUDIT='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage12_reprocess_pysnooper2f_mutation_20260623_080444'
RUN_DIRS_TSV='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage12_reprocess_pysnooper2f_mutation_20260623_080444/run_dirs_to_reprocess.tsv'
RESULTS_TSV='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage12_reprocess_pysnooper2f_mutation_20260623_080444/stage12_reprocess_results.tsv'
RC_FILE='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage12_reprocess_pysnooper2f_mutation_20260623_080444/stage12_reprocess.rc'

printf 'account\tplanned_run_id\tsut_id\ttarget_module\tplanned_rep\trc\tstatus_before\tstatus_after\tline_pct\tbranch_pct\tmutation_score_pct\tmutation_available\trun_dir\tstatus_json\n' \
  > "$RESULTS_TSV"

while IFS=$'\t' read -r ACCOUNT RUN_ID SUT_ID TARGET_MODULE REP RUN_DIR STATUS_JSON
do
  if [[ "$ACCOUNT" = "account" ]]; then
    continue
  fi

  [[ -n "$RUN_DIR" ]] || continue

  echo
  echo "============================================================"
  echo "REPROCESS MUTATION"
  echo "============================================================"
  echo "account=$ACCOUNT"
  echo "run_id=$RUN_ID"
  echo "sut_id=$SUT_ID"
  echo "target_module=$TARGET_MODULE"
  echo "rep=$REP"
  echo "run_dir=$RUN_DIR"
  echo "started_at=$(date --iso-8601=seconds)"

  STATUS_BEFORE="$(
    python3 - "$STATUS_JSON" <<'PY_STATUS_BEFORE'
import json
import pathlib
import sys
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print(d.get("status", ""))
PY_STATUS_BEFORE
  )"

  echo "status_before=$STATUS_BEFORE"

  cp -a "$STATUS_JSON" "$STATUS_JSON.before_stage12_$(date +%Y%m%d_%H%M%S).bak"

  set +e

  python3 "$MUTATION_TOOL" \
    --run-dir "$RUN_DIR" \
    --per-mutant-timeout-s 20

  RC=$?

  set -e

  EVAL="$(
    python3 - "$STATUS_JSON" <<'PY_STATUS_AFTER'
import json
import pathlib
import sys

p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))

def v(key):
    raw = d.get(key)
    return "" if raw is None else str(raw)

print("\t".join([
    v("status"),
    v("line_pct"),
    v("branch_pct"),
    v("mutation_score_pct"),
    v("mutation_available"),
]))
PY_STATUS_AFTER
  )"

  IFS=$'\t' read -r STATUS_AFTER LINE_PCT BRANCH_PCT MUTATION_SCORE MUTATION_AVAILABLE <<< "$EVAL"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$ACCOUNT" "$RUN_ID" "$SUT_ID" "$TARGET_MODULE" "$REP" "$RC" \
    "$STATUS_BEFORE" "$STATUS_AFTER" "$LINE_PCT" "$BRANCH_PCT" "$MUTATION_SCORE" "$MUTATION_AVAILABLE" "$RUN_DIR" "$STATUS_JSON" \
    >> "$RESULTS_TSV"

  echo "rc=$RC"
  echo "status_after=$STATUS_AFTER"
  echo "line_pct=$LINE_PCT"
  echo "branch_pct=$BRANCH_PCT"
  echo "mutation_score_pct=$MUTATION_SCORE"
  echo "mutation_available=$MUTATION_AVAILABLE"
  echo "finished_at=$(date --iso-8601=seconds)"
done < "$RUN_DIRS_TSV"

echo "0" > "$RC_FILE"

echo
echo "============================================================"
echo "STAGE12 DONE"
echo "============================================================"
echo "RESULTS_TSV=$RESULTS_TSV"
echo "RC_FILE=$RC_FILE"
