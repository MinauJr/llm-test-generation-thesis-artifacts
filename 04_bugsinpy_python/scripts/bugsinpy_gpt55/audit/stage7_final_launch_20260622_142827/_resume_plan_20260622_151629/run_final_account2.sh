#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true
umask 077

ROOT='/home/jpaiva/projetos/bugsinpy_gpt55'
ACCOUNT='account2'
SECRET='/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55/account2.env'
ACCOUNT_MANIFEST='/home/jpaiva/projetos/bugsinpy_gpt55/manifests/final_gpt55_20260622_142827/account2.tsv'
ACCOUNT_OUT='/home/jpaiva/projetos/bugsinpy_gpt55/out/_FINAL_GPT55_BUGSINPY_16SUTS_5REPS_3ACCOUNTS_20260622_142827/account2'
RESULT_TSV='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage7_final_launch_20260622_142827/run_final_account2.result.tsv'
RC_FILE='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage7_final_launch_20260622_142827/run_final_account2.rc'

mkdir -p "$ACCOUNT_OUT"

printf 'account\tslot\tsut_id\ttarget_module\trun_id\trep\tstatus\tgeneration_output_nonempty\tline_pct\tbranch_pct\tmutation_score_pct\tstatus_json\n' \
  > "$RESULT_TSV"

SLOT=0
STOP_REASON=""

while IFS=$'\t' read -r SUT_ID TARGET_MODULE
do
  if [[ "$SUT_ID" = "sut_id" ]]; then
    continue
  fi

  for REP in 1 2 3 4 5
  do
    SLOT=$((SLOT + 1))
    RUN_ID="$SLOT"

    SLOT_MANIFEST="$ACCOUNT_OUT/_manifests/slot_$(printf '%03d' "$SLOT")_${SUT_ID}.tsv"
    mkdir -p "$(dirname "$SLOT_MANIFEST")"

    printf 'sut_id\ttarget_module\n%s\t%s\n' \
      "$SUT_ID" \
      "$TARGET_MODULE" \
      > "$SLOT_MANIFEST"

    echo
    echo "============================================================"
    echo "FINAL SLOT"
    echo "============================================================"
    echo "account=$ACCOUNT"
    echo "slot=$SLOT"
    echo "sut_id=$SUT_ID"
    echo "target_module=$TARGET_MODULE"
    echo "rep=$REP"
    echo "run_id=$RUN_ID"
    echo "started_at=$(date --iso-8601=seconds)"

    export IAEDU_SECRETS_FILE="$SECRET"
    export TARGET_MAP="$SLOT_MANIFEST"
    export OUT_BASE="$ACCOUNT_OUT"

    export REPEATS=1
    export RUN_ID="$RUN_ID"

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
      find "$ACCOUNT_OUT/$SUT_ID/run_$(printf '%04d' "$RUN_ID")" \
        -type f \
        -path '*/metrics/status.json' \
        -print \
        2>/dev/null \
        | sort \
        | head -n 1
    )"

    if [[ -z "$STATUS_FILE" || ! -f "$STATUS_FILE" ]]; then
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$ACCOUNT" "$SLOT" "$SUT_ID" "$TARGET_MODULE" "$RUN_ID" "$REP" \
        "missing_status_json" "" "" "" "" "" \
        >> "$RESULT_TSV"

      STOP_REASON="missing_status_json"
      echo "STOP_REASON=$STOP_REASON"
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
    value("line_pct"),
    value("branch_pct"),
    value("mutation_score_pct"),
]
print("\t".join(fields))
PY_STATUS
    )"

    IFS=$'\t' read -r STATUS GEN_NONEMPTY LINE_PCT BRANCH_PCT MUTATION_PCT <<< "$EVAL"

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$ACCOUNT" "$SLOT" "$SUT_ID" "$TARGET_MODULE" "$RUN_ID" "$REP" \
      "$STATUS" "$GEN_NONEMPTY" "$LINE_PCT" "$BRANCH_PCT" "$MUTATION_PCT" "$STATUS_FILE" \
      >> "$RESULT_TSV"

    echo "slot_status=$STATUS"
    echo "generation_output_nonempty=$GEN_NONEMPTY"
    echo "line_pct=$LINE_PCT"
    echo "branch_pct=$BRANCH_PCT"
    echo "mutation_score_pct=$MUTATION_PCT"
    echo "dataset_rc=$DATASET_RC"
    echo "finished_at=$(date --iso-8601=seconds)"

    case "$STATUS" in
      generation_no_output|generation_no_output_account_blocked|generation_api_quota_exhausted|generation_api_auth_error|generation_api_rate_limited|generation_api_error|timeout)
        STOP_REASON="$STATUS"
        echo "STOP_REASON=$STOP_REASON"
        echo "86" > "$RC_FILE"
        exit 86
        ;;
    esac

    if [[ "$GEN_NONEMPTY" = "false" || "$GEN_NONEMPTY" = "False" || "$GEN_NONEMPTY" = "0" ]]; then
      STOP_REASON="generation_output_empty"
      echo "STOP_REASON=$STOP_REASON"
      echo "86" > "$RC_FILE"
      exit 86
    fi
  done
done < "$ACCOUNT_MANIFEST"

echo "0" > "$RC_FILE"

echo
echo "============================================================"
echo "ACCOUNT FINAL WORKER DONE"
echo "============================================================"
echo "account=$ACCOUNT"
echo "slots_completed=$SLOT"
echo "rc=0"
exit 0
