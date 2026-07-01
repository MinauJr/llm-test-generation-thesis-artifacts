#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true
umask 077

ROOT='/home/jpaiva/projetos/bugsinpy_gpt55'
ACCOUNT='account3'
SECRET='/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55/account3.env'

CANDIDATES='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage6d_smoke_ladder_20260620_151033/frozen_smoke_candidates.tsv'
MANIFEST_ROOT='/home/jpaiva/projetos/bugsinpy_gpt55/manifests/smoke_ladder/20260620_151033/account3'
ACCOUNT_OUT='/home/jpaiva/projetos/bugsinpy_gpt55/out/_REAL_SMOKE_LADDER_GPT55_BUGSINPY_20260620_151033/account3'

RESULT='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage6d_smoke_ladder_20260620_151033/run_smoke_ladder_account3.result.tsv'
RC_FILE='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage6d_smoke_ladder_20260620_151033/run_smoke_ladder_account3.rc'

mkdir -p "$MANIFEST_ROOT" "$ACCOUNT_OUT"

printf 'account\tcandidate_index\tsut_id\ttarget_module\tclassification\tstatus\tstatus_json\tout_base\n'     > "$RESULT"

CANDIDATE_INDEX=0

while IFS=$'\t' read -r     RANK     SUT_ID     TARGET_MODULE     HISTORICAL_COMPLETE_RUNS     LATEST_COMPLETE_AT     LATEST_STATUS     LATEST_LINE     LATEST_BRANCH     LATEST_MUTATION     LATEST_STATUS_JSON
do
    CANDIDATE_INDEX=$((CANDIDATE_INDEX + 1))

    MANIFEST="$MANIFEST_ROOT/candidate_${CANDIDATE_INDEX}.tsv"
    OUT_BASE="$ACCOUNT_OUT/candidate_${CANDIDATE_INDEX}_${SUT_ID}"

    printf 'sut_id\ttarget_module\n%s\t%s\n'         "$SUT_ID"         "$TARGET_MODULE"         > "$MANIFEST"

    mkdir -p "$OUT_BASE"

    echo
    echo "============================================================"
    echo "SMOKE LADDER CANDIDATE"
    echo "============================================================"
    echo "account=$ACCOUNT"
    echo "candidate_index=$CANDIDATE_INDEX"
    echo "sut_id=$SUT_ID"
    echo "target_module=$TARGET_MODULE"
    echo "historical_complete_runs=$HISTORICAL_COMPLETE_RUNS"
    echo "out_base=$OUT_BASE"
    echo "started_at=$(date --iso-8601=seconds)"

    export IAEDU_SECRETS_FILE="$SECRET"
    export TARGET_MAP="$MANIFEST"
    export OUT_BASE="$OUT_BASE"

    export REPEATS=1
    export RUN_ID="$CANDIDATE_INDEX"

    export DRY_RUN=0
    export RUN_MUTATION=1

    export GEN_TIMEOUT_S=200
    export GEN_EMPTY_RETRY_MAX=2
    export GENERATION_RETRY_SLEEP_S=2

    export PYTEST_TIMEOUT_S=60
    export MUTATION_TIMEOUT_S=180

    set +e

    bash "$ROOT/scripts/run_gpt55_bugsinpy_python_dataset.sh"

    DATASET_RC=$?
    set -e

    STATUS_FILE="$(
        find "$OUT_BASE"             -type f             -path '*/metrics/status.json'             -print             2>/dev/null             | sort             | head -n 1
    )"

    if [[ -z "$STATUS_FILE" || ! -f "$STATUS_FILE" ]]; then
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n'             "$ACCOUNT"             "$CANDIDATE_INDEX"             "$SUT_ID"             "$TARGET_MODULE"             "harness_or_environment_failure"             "missing_status_json"             ""             "$OUT_BASE"             >> "$RESULT"

        echo "90" > "$RC_FILE"
        exit 90
    fi

    EVALUATION="$(
        python3 - "$STATUS_FILE" <<'PY_STATUS'
from pathlib import Path
import json
import math
import sys

path = Path(sys.argv[1])

data = json.loads(
    path.read_text(
        encoding="utf-8",
        errors="replace",
    )
)

status = str(
    data.get("status")
    or ""
)

def as_number(value):
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        number = float(value)

        if math.isfinite(number):
            return number

    if isinstance(value, str):
        try:
            number = float(value)

            if math.isfinite(number):
                return number
        except ValueError:
            pass

    return None

def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def as_true(value):
    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
    }

generation_nonempty = as_true(
    data.get("generation_output_nonempty")
)

pytest_raw = as_int(
    data.get("pytest_raw_exit_code")
)

pytest_final = as_int(
    data.get("pytest_final_exit_code")
)

pytest_passed = (
    pytest_raw == 0
    or pytest_final == 0
)

line_pct = as_number(
    data.get("line_pct")
)

branch_pct = as_number(
    data.get("branch_pct")
)

mutation_pct = as_number(
    data.get("mutation_score_pct")
)

complete = (
    generation_nonempty
    and pytest_passed
    and line_pct is not None
    and branch_pct is not None
    and mutation_pct is not None
)

generation_unavailable = (
    not generation_nonempty
    or status.startswith("generation_no_output")
    or status.startswith("generation_api")
    or status in {
        "generation_failed",
        "timeout",
    }
)

if complete:
    classification = "valid_complete_smoke"
elif generation_unavailable:
    classification = "generation_account_unavailable"
else:
    classification = "generated_suite_invalid"

print(
    "\t".join(
        [
            classification,
            status,
            str(line_pct if line_pct is not None else ""),
            str(branch_pct if branch_pct is not None else ""),
            str(mutation_pct if mutation_pct is not None else ""),
        ]
    )
)
PY_STATUS
    )"

    IFS=$'\t' read -r         CLASSIFICATION         FINAL_STATUS         LINE_PCT         BRANCH_PCT         MUTATION_PCT         <<< "$EVALUATION"

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n'         "$ACCOUNT"         "$CANDIDATE_INDEX"         "$SUT_ID"         "$TARGET_MODULE"         "$CLASSIFICATION"         "$FINAL_STATUS"         "$STATUS_FILE"         "$OUT_BASE"         >> "$RESULT"

    echo "classification=$CLASSIFICATION"
    echo "status=$FINAL_STATUS"
    echo "line_pct=$LINE_PCT"
    echo "branch_pct=$BRANCH_PCT"
    echo "mutation_pct=$MUTATION_PCT"
    echo "dataset_rc=$DATASET_RC"
    echo "finished_at=$(date --iso-8601=seconds)"

    case "$CLASSIFICATION" in
        valid_complete_smoke)
            cat > "$ACCOUNT_OUT/ACCOUNT_SMOKE_SUCCESS.env" <<SUCCESS
ACCOUNT='$ACCOUNT'
SUT_ID='$SUT_ID'
TARGET_MODULE='$TARGET_MODULE'
STATUS_FILE='$STATUS_FILE'
LINE_PCT='$LINE_PCT'
BRANCH_PCT='$BRANCH_PCT'
MUTATION_PCT='$MUTATION_PCT'
SUCCESS

            echo "0" > "$RC_FILE"
            exit 0
            ;;

        generation_account_unavailable)
            cat > "$ACCOUNT_OUT/ACCOUNT_GENERATION_UNAVAILABLE.env" <<UNAVAILABLE
ACCOUNT='$ACCOUNT'
SUT_ID='$SUT_ID'
TARGET_MODULE='$TARGET_MODULE'
STATUS_FILE='$STATUS_FILE'
FINAL_STATUS='$FINAL_STATUS'
UNAVAILABLE

            echo "86" > "$RC_FILE"
            exit 86
            ;;

        generated_suite_invalid)
            echo                 "Generated suite is invalid; preserving it and trying the next frozen candidate."
            ;;
    esac

done < <(
    tail -n +2 "$CANDIDATES"
)

echo "2" > "$RC_FILE"
exit 2
