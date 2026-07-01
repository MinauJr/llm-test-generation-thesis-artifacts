#!/usr/bin/env bash
set -u
set -o pipefail

REPO="${REPO:-$HOME/projetos/llm_test_generation_gpt4o/bugsinpy_gpt4o}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}"
DRY_RUN="${DRY_RUN:-1}"

ONE_SUT="$REPO/scripts/run_bugsinpy_gpt4o_one_sut.sh"
VALIDATOR="$REPO/tools/validate_bugsinpy_generated_pytest.py"

if [ ! -x "$ONE_SUT" ]; then
  echo "ERRO: one_sut base nao existe ou nao e executavel: $ONE_SUT"
  exit 2
fi

if [ ! -f "$VALIDATOR" ]; then
  echo "ERRO: validator nao existe: $VALIDATOR"
  exit 3
fi

echo "===== BUGSINPY GPT-4o ONE_SUT WITH RAW PYTEST ====="
echo "ONE_SUT=$ONE_SUT"
echo "VALIDATOR=$VALIDATOR"
echo "DRY_RUN=$DRY_RUN"

set +e
"$ONE_SUT" "$@"
BASE_RC=$?
set -u

echo "BASE_RC=$BASE_RC"

# O one_sut base ja escreve RUN_DIR no runner.log; aqui resolvemos o run dir a partir do status mais recente
# para evitar duplicar logica de indices.
OUT_BASE="${OUT_BASE:-$REPO/out/_dev_bugsinpy_gpt4o_one_sut}"
SUT_ID_EFFECTIVE="${SUT_ID:-${1:-}}"

if [ -z "$SUT_ID_EFFECTIVE" ]; then
  echo "WARN: SUT_ID nao definido; nao consigo resolver status para validacao."
  exit "$BASE_RC"
fi

STATUS_FILE="$(find "$OUT_BASE/$SUT_ID_EFFECTIVE" -path '*/metrics/status.json' -type f 2>/dev/null | sort | tail -n 1)"
if [ -z "$STATUS_FILE" ]; then
  echo "WARN: status.json nao encontrado em $OUT_BASE/$SUT_ID_EFFECTIVE"
  exit "$BASE_RC"
fi

RUN_DIR="$(dirname "$(dirname "$STATUS_FILE")")"

echo "STATUS_FILE=$STATUS_FILE"
echo "RUN_DIR=$RUN_DIR"

CURRENT_STATUS="$("$PYTHON_BIN" - "$STATUS_FILE" <<'PY2'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print(d.get("status", "unknown"))
PY2
)"

echo "CURRENT_STATUS=$CURRENT_STATUS"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN=1: raw pytest validation skipped."
  exit "$BASE_RC"
fi

if [ "$CURRENT_STATUS" != "generation_ready" ]; then
  echo "Generation not ready; raw pytest validation skipped."
  exit "$BASE_RC"
fi

echo "===== RUNNING RAW PYTEST VALIDATOR ====="
set +e
"$PYTHON_BIN" "$VALIDATOR" \
  --run-dir "$RUN_DIR" \
  --python-bin "$PYTHON_BIN" \
  --pytest-timeout-s "$PYTEST_TIMEOUT_S" \
  > "$RUN_DIR/logs/validate_generated_pytest.stdout.log" \
  2> "$RUN_DIR/logs/validate_generated_pytest.stderr.log"
VALIDATE_RC=$?
set -u

echo "$VALIDATE_RC" > "$RUN_DIR/metrics/validate_generated_pytest_exit_code.txt"
cat "$RUN_DIR/logs/validate_generated_pytest.stdout.log" || true

FINAL_STATUS="$("$PYTHON_BIN" - "$STATUS_FILE" <<'PY3'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print(d.get("status", "unknown"))
PY3
)"

echo "FINAL_STATUS=$FINAL_STATUS"
echo "STATUS_FILE=$STATUS_FILE"
echo "RUN_DIR=$RUN_DIR"

exit "$BASE_RC"
