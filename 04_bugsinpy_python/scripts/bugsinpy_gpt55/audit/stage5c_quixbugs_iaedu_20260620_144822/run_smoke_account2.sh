#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true
umask 077

ROOT='/home/jpaiva/projetos/bugsinpy_gpt55'
ACCOUNT='account2'
SECRET='/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55/account2.env'
MANIFEST='/home/jpaiva/projetos/bugsinpy_gpt55/manifests/smokes/20260620_144822/account2.tsv'
OUT_BASE='/home/jpaiva/projetos/bugsinpy_gpt55/out/_SMOKE_GPT55_BUGSINPY_3ACCOUNTS_20260620_144822/account2'
RC_FILE='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage5c_quixbugs_iaedu_20260620_144822/run_smoke_account2.rc'

mkdir -p "$OUT_BASE"

export IAEDU_SECRETS_FILE="$SECRET"
export TARGET_MAP="$MANIFEST"
export OUT_BASE="$OUT_BASE"

export REPEATS=1
export RUN_ID=1
export RUN_MUTATION=1

export GEN_TIMEOUT_S=200
export GEN_EMPTY_RETRY_MAX=3
export GENERATION_RETRY_SLEEP_S=2

export PYTEST_TIMEOUT_S=60
export MUTATION_TIMEOUT_S=180

echo "============================================================"
echo "BUGSINPY GPT-5.5 REAL SMOKE — QUIXBUGS IAEdu CONFIG"
echo "============================================================"
echo "account=$ACCOUNT"
echo "secrets_file=$SECRET"
echo "manifest=$MANIFEST"
echo "out_base=$OUT_BASE"
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
