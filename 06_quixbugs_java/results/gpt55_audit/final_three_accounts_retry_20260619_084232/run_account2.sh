#!/usr/bin/env bash

set +e
set +u
set +o pipefail 2>/dev/null || true
set +H 2>/dev/null || true

ROOT=/home/jpaiva/projetos/quixbugs_java_gpt55
SECRET=/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55/account2.env
MANIFEST=/home/jpaiva/projetos/quixbugs_java_gpt55/_audit/final_three_accounts_retry_20260619_084232/account2_suts.txt
OUT=/home/jpaiva/projetos/quixbugs_java_gpt55/out/_final_gpt55_quixbugs_java_account2_20260619_084232
LOG=/home/jpaiva/projetos/quixbugs_java_gpt55/_smoke/final_gpt55_quixbugs_java_account2_20260619_084232.log
ACCOUNT=account2
EXPECTED=65

cd "$ROOT" || exit 1

set -a
source "$ROOT/config.env"
set +a

unset IAEDU_ENDPOINT
unset IAEDU_CHANNEL_ID
unset IAEDU_API_KEY

export IAEDU_SECRETS_FILE="$SECRET"
export GENERATOR_CMD="$ROOT/scripts/generator_cmd_iaedu.sh"

{
  echo "============================================================"
  echo "QUIXBUGS JAVA GPT-5.5 — FINAL $ACCOUNT"
  echo "============================================================"
  echo "START_DATE=$(date)"
  echo "ACCOUNT=$ACCOUNT"
  echo "EXPECTED_STATUS_FILES=$EXPECTED"
  echo "OUT_ROOT=$OUT"
  echo

  rm -rf "$OUT"

  OUT_ROOT="$OUT"   SUT_LIST_FILE="$MANIFEST"   ONLY_SUTS=""   REPEATS=5   RUN_MUTATION=1   GEN_TIMEOUT_S=200   GEN_EMPTY_RETRY_MAX=15   GENERATION_RETRY_SLEEP_S=2   MVN_TEST_TIMEOUT_S=120   PIT_TIMEOUT_S=180   MODEL_LABEL="gpt-5.5"   GENERATOR_CMD="$GENERATOR_CMD"   bash "$ROOT/scripts/run_quixbugs_gpt55_dataset.sh"

  RC=$?

  echo
  echo "FINAL_RUN_RC=$RC"
  echo "END_DATE=$(date)"

  exit "$RC"

} 2>&1 | tee "$LOG"

RC=${PIPESTATUS[0]}

printf '%s\n' "$RC" > "$LOG.exit_code"

exit "$RC"
