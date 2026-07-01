#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true
umask 077

ROOT='/home/jpaiva/projetos/bugsinpy_gpt55'
ACCOUNT='account2'
SECRET='/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55/account2.env'
MANIFEST='/home/jpaiva/projetos/bugsinpy_gpt55/manifests/real_smokes/20260620_150438/account2.tsv'
OUT_BASE='/home/jpaiva/projetos/bugsinpy_gpt55/out/_REAL_SMOKE_GPT55_BUGSINPY_3ACCOUNTS_20260620_150438/account2'
RC_FILE='/home/jpaiva/projetos/bugsinpy_gpt55/audit/stage6b_real_three_account_smokes_20260620_150438/run_real_smoke_account2.rc'

mkdir -p "$OUT_BASE"

export IAEDU_SECRETS_FILE="$SECRET"
export TARGET_MAP="$MANIFEST"
export OUT_BASE="$OUT_BASE"

export REPEATS=1
export RUN_ID=1

# Obrigatório: geração e avaliação reais.
export DRY_RUN=0
export RUN_MUTATION=1

export GEN_TIMEOUT_S=200
export GEN_EMPTY_RETRY_MAX=3
export GENERATION_RETRY_SLEEP_S=2

export PYTEST_TIMEOUT_S=60
export MUTATION_TIMEOUT_S=180

echo "============================================================"
echo "BUGSINPY GPT-5.5 — REAL ACCOUNT SMOKE"
echo "============================================================"
echo "account=$ACCOUNT"
echo "secrets_file=$SECRET"
echo "manifest=$MANIFEST"
echo "out_base=$OUT_BASE"
echo "DRY_RUN=$DRY_RUN"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "GEN_TIMEOUT_S=$GEN_TIMEOUT_S"
echo "GEN_EMPTY_RETRY_MAX=$GEN_EMPTY_RETRY_MAX"
echo "PYTEST_TIMEOUT_S=$PYTEST_TIMEOUT_S"
echo "MUTATION_TIMEOUT_S=$MUTATION_TIMEOUT_S"
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
