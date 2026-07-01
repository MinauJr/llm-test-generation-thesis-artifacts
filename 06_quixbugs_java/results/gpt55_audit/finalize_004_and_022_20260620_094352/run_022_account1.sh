#!/usr/bin/env bash

set +e
set +u
set +o pipefail 2>/dev/null || true
set +H 2>/dev/null || true

ROOT=/home/jpaiva/projetos/quixbugs_java_gpt55
SECRET=/home/jpaiva/projetos/_iaedu_accounts_clean/current/gpt55/account1.env
MANIFEST=/home/jpaiva/projetos/quixbugs_java_gpt55/_audit/finalize_004_and_022_20260620_094352/022_manifest.txt
ACCOUNT=account1
STAMP=20260620_094352
LOG=/home/jpaiva/projetos/quixbugs_java_gpt55/_smoke/final_022_account1_20260620_094352.log
POINTER=/home/jpaiva/projetos/quixbugs_java_gpt55/_audit/finalize_004_and_022_20260620_094352/valid_022_account1.txt

cd "$ROOT" || exit 1

set -a
source "$ROOT/config.env"
set +a

unset IAEDU_ENDPOINT
unset IAEDU_CHANNEL_ID
unset IAEDU_API_KEY

export IAEDU_SECRETS_FILE="$SECRET"
export GENERATOR_CMD="$ROOT/scripts/generator_cmd_iaedu.sh"

: > "$POINTER"

{
  echo "============================================================"
  echo "GERAR REPETIÇÃO VÁLIDA DO 022 — $ACCOUNT"
  echo "============================================================"
  echo "START_DATE=$(date)"

  for TRY in 1 2 3
  do
    OUT="$ROOT/out/_final_022_${ACCOUNT}_try${TRY}_${STAMP}"

    echo
    echo "===== TRY $TRY ====="
    echo "OUT=$OUT"

    OUT_ROOT="$OUT"     SUT_LIST_FILE="$MANIFEST"     ONLY_SUTS=""     REPEATS=1     RUN_MUTATION=1     GEN_TIMEOUT_S=200     GEN_EMPTY_RETRY_MAX=15     GENERATION_RETRY_SLEEP_S=2     MVN_TEST_TIMEOUT_S=120     PIT_TIMEOUT_S=180     MODEL_LABEL="gpt-5.5"     GENERATOR_CMD="$GENERATOR_CMD"     bash "$ROOT/scripts/run_quixbugs_gpt55_dataset.sh"

    STATUS_FILE="$(
      find "$OUT"         -path '*/metrics/status.json'         -type f         -print         -quit         2>/dev/null
    )"

    VALID="$(
      python3 - "$STATUS_FILE" <<'PY'
from pathlib import Path
import json
import sys

if len(sys.argv) < 2:
    print(0)
    raise SystemExit

path = Path(sys.argv[1])

if not path.is_file():
    print(0)
    raise SystemExit

data = json.loads(
    path.read_text(
        encoding="utf-8",
        errors="replace",
    )
)

run_dir = path.parent.parent

valid = (
    data.get("sut_name")
    == "022_java_minimum_spanning_tree"
    and data.get("status") == "ok"
    and data.get("mvn_test_exit_code") == 0
    and data.get("pit_exit_code") == 0
    and data.get("line_coverage_pct") is not None
    and data.get("branch_coverage_pct") is not None
    and data.get("instruction_coverage_pct") is not None
    and data.get("mutation_score_pct") is not None
    and (
        run_dir
        / "metrics"
        / "java_metrics.json"
    ).is_file()
)

print(1 if valid else 0)
PY
    )"

    echo "VALID=$VALID"

    if [[ "$VALID" = "1" ]]; then
      printf '%s\n' "$OUT" > "$POINTER"
      echo "VALID_OUT=$OUT"
      echo "END_DATE=$(date)"
      exit 0
    fi
  done

  echo "ERRO: não foi obtida uma repetição válida em três tentativas."
  echo "END_DATE=$(date)"
  exit 20

} > "$LOG" 2>&1

RC=$?

printf '%s\n' "$RC" > "$LOG.exit_code"

exit "$RC"
