#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true
umask 077

ROOT='/home/jpaiva/projetos/bugsinpy_gpt55'
ACCOUNT_DIR='/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55'
MANIFEST='/home/jpaiva/projetos/bugsinpy_gpt55/manifests/final_prelaunch_account1_20260622_142512.tsv'
OUT_BASE='/home/jpaiva/projetos/bugsinpy_gpt55/out/_FINAL_PRELAUNCH_SMOKE_ACCOUNT1_20260622_142512'
RC_FILE='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage6h_account1_final_smoke_20260622_142512/run_account1_black2_smoke.rc'

mkdir -p "$OUT_BASE"

export IAEDU_SECRETS_FILE="$ACCOUNT_DIR/account1.env"
export TARGET_MAP="$MANIFEST"
export OUT_BASE="$OUT_BASE"

export REPEATS=1
export RUN_ID=1

export DRY_RUN=0
export RUN_MUTATION=1

export GEN_TIMEOUT_S=200
export GEN_EMPTY_RETRY_MAX=2
export GENERATION_RETRY_SLEEP_S=2

export PYTEST_TIMEOUT_S=60
export MUTATION_TIMEOUT_S=180

echo "============================================================"
echo "ACCOUNT1 FINAL PRE-LAUNCH SMOKE"
echo "============================================================"
echo "sut=black_2f"
echo "target=blib2to3.pgen2.token"
echo "out_base=$OUT_BASE"
echo "DRY_RUN=$DRY_RUN"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "started_at=$(date --iso-8601=seconds)"
echo

set +e

bash "$ROOT/scripts/run_gpt55_bugsinpy_python_dataset.sh"

RC=$?
set -e

echo "$RC" > "$RC_FILE"

echo
echo "finished_at=$(date --iso-8601=seconds)"
echo "runner_rc=$RC"

exit "$RC"
