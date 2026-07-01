#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true
umask 077

ROOT='/home/jpaiva/projetos/bugsinpy_gpt55'
ACCOUNT='account3'
SECRET='/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55/account3.env'
ACCOUNT_PLAN='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage7_final_launch_20260622_142827/_resume_plan_20260622_151629/resume_generation_account3.tsv'
ACCOUNT_OUT='/home/jpaiva/projetos/bugsinpy_gpt55/out/_RESUME_GPT55_BUGSINPY_MISSING12_20260623_073437/account3'
RESULT_TSV='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage10b_resume_missing12_20260623_073437/run_resume_account3.result.tsv'
RC_FILE='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage10b_resume_missing12_20260623_073437/run_resume_account3.rc'

mkdir -p "$ACCOUNT_OUT"

printf 'account\tplanned_run_id\tsut_id\ttarget_module\tplanned_rep\tresume_reason\told_status\tstatus\tgeneration_output_nonempty\tgeneration_attempts\tgeneration_empty_attempts\tline_pct\tbranch_pct\tmutation_score_pct\tstatus_json\n' \
  > "$RESULT_TSV"

while IFS=$'\t' read -r PLANNED_RUN_ID SUT_ID TARGET_MODULE PLANNED_REP RESUME_REASON OLD_STATUS
do
  if [[ "$PLANNED_RUN_ID" = "planned_run_id" ]]; then
    continue
  fi

  [[ -n "$PLANNED_RUN_ID" ]] || continue

  SLOT_MANIFEST="$ACCOUNT_OUT/_manifests/resume_run_$(printf '%04d' "$PLANNED_RUN_ID")_${SUT_ID}.tsv"

  mkdir -p "$(dirname "$SLOT_MANIFEST")"

  printf 'sut_id\ttarget_module\n%s\t%s\n' \
    "$SUT_ID"     "$TARGET_MODULE"     > "$SLOT_MANIFEST"

  echo
  echo "============================================================"
  echo "RESUME SLOT"
  echo "============================================================"
  echo "account=$ACCOUNT"
  echo "planned_run_id=$PLANNED_RUN_ID"
  echo "sut_id=$SUT_ID"
  echo "target_module=$TARGET_MODULE"
  echo "planned_rep=$PLANNED_REP"
  echo "resume_reason=$RESUME_REASON"
  echo "old_status=$OLD_STATUS"
  echo "started_at=$(date --iso-8601=seconds)"

  export IAEDU_SECRETS_FILE="$SECRET"
  export TARGET_MAP="$SLOT_MANIFEST"
  export OUT_BASE="$ACCOUNT_OUT"

  export REPEATS=1
  export RUN_ID="$PLANNED_RUN_ID"

  export DRY_RUN=0
  export RUN_MUTATION=1

  export GEN_TIMEOUT_S=200
  export GEN_EMPTY_RETRY_MAX=3
  export GENERATION_RETRY_SLEEP_S=2

  export PYTEST_TIMEOUT_S=60
  export MUTATION_TIMEOUT_S=180

  set +e

  bash "$ROOT/scripts/run_gpt55_bugsinpy_python_dataset.sh"

  DATASET_RC=$?
  set -e

  STATUS_FILE="$(
    find "$ACCOUNT_OUT/$SUT_ID/run_$(printf '%04d' "$PLANNED_RUN_ID")" \
      -type f \
      -path '*/metrics/status.json' \
      -print \
      2>/dev/null \
      | sort \
      | head -n 1
  )"

  if [[ -z "$STATUS_FILE" || ! -f "$STATUS_FILE" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$ACCOUNT" "$PLANNED_RUN_ID" "$SUT_ID" "$TARGET_MODULE" "$PLANNED_REP" "$RESUME_REASON" "$OLD_STATUS" \
      "missing_status_json" "" "" "" "" "" "" ""       >> "$RESULT_TSV"

    echo "STOP_REASON=missing_status_json"
    echo "90" > "$RC_FILE"
    exit 90
  fi

  EVAL="$(
    python3 - "$STATUS_FILE" <<'PY_STATUS'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))

def value(key):
    raw = data.get(key)
    return "" if raw is None else str(raw)

fields = [
    value("status"),
    value("generation_output_nonempty"),
    value("generation_attempts"),
    value("generation_empty_attempts"),
    value("line_pct"),
    value("branch_pct"),
    value("mutation_score_pct"),
]
print("\t".join(fields))
PY_STATUS
  )"

  IFS=$'\t' read -r STATUS GEN_NONEMPTY GEN_ATTEMPTS GEN_EMPTY LINE_PCT BRANCH_PCT MUTATION_PCT <<< "$EVAL"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$ACCOUNT" "$PLANNED_RUN_ID" "$SUT_ID" "$TARGET_MODULE" "$PLANNED_REP" "$RESUME_REASON" "$OLD_STATUS"     "$STATUS" "$GEN_NONEMPTY" "$GEN_ATTEMPTS" "$GEN_EMPTY" "$LINE_PCT" "$BRANCH_PCT" "$MUTATION_PCT" "$STATUS_FILE"     >> "$RESULT_TSV"

  echo "slot_status=$STATUS"
  echo "generation_output_nonempty=$GEN_NONEMPTY"
  echo "generation_attempts=$GEN_ATTEMPTS"
  echo "generation_empty_attempts=$GEN_EMPTY"
  echo "line_pct=$LINE_PCT"
  echo "branch_pct=$BRANCH_PCT"
  echo "mutation_score_pct=$MUTATION_PCT"
  echo "dataset_rc=$DATASET_RC"
  echo "finished_at=$(date --iso-8601=seconds)"

  case "$STATUS" in
    generation_no_output|generation_no_output_account_blocked|generation_api_quota_exhausted|generation_api_auth_error|generation_api_rate_limited|generation_api_error|timeout)
      echo "STOP_REASON=$STATUS"
      echo "86" > "$RC_FILE"
      exit 86
      ;;
  esac

  if [[ "$GEN_NONEMPTY" = "false" || "$GEN_NONEMPTY" = "False" || "$GEN_NONEMPTY" = "0" ]]; then
    echo "STOP_REASON=generation_output_empty"
    echo "86" > "$RC_FILE"
    exit 86
  fi

done < "$ACCOUNT_PLAN"

echo "0" > "$RC_FILE"

echo
echo "============================================================"
echo "ACCOUNT RESUME WORKER DONE"
echo "============================================================"
echo "account=$ACCOUNT"
echo "rc=0"
exit 0
