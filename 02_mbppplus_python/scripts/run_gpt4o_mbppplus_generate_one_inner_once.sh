#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BASE_PROMPT="${1:?Uso: run_gpt4o_mbppplus_generate_one_inner_once.sh BASE_PROMPT LANG FRAMEWORK SUT_FILE OUT_DIR}"
LANG="${2:?Uso: run_gpt4o_mbppplus_generate_one_inner_once.sh BASE_PROMPT LANG FRAMEWORK SUT_FILE OUT_DIR}"
FRAMEWORK="${3:?Uso: run_gpt4o_mbppplus_generate_one_inner_once.sh BASE_PROMPT LANG FRAMEWORK SUT_FILE OUT_DIR}"
SUT_FILE="${4:?Uso: run_gpt4o_mbppplus_generate_one_inner_once.sh BASE_PROMPT LANG FRAMEWORK SUT_FILE OUT_DIR}"
OUT_DIR="${5:?Uso: run_gpt4o_mbppplus_generate_one_inner_once.sh BASE_PROMPT LANG FRAMEWORK SUT_FILE OUT_DIR}"

GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-200}"
MODEL_NAME="${MODEL_NAME:-gpt-iaedu}"

BASE_PROMPT="$(readlink -f "$BASE_PROMPT")"
SUT_FILE="$(readlink -f "$SUT_FILE")"
mkdir -p "$OUT_DIR"
OUT_DIR="$(readlink -f "$OUT_DIR")"

[[ -f "$BASE_PROMPT" ]] || { echo "ERRO: BASE_PROMPT não existe: $BASE_PROMPT" >&2; exit 1; }
[[ -f "$SUT_FILE" ]] || { echo "ERRO: SUT_FILE não existe: $SUT_FILE" >&2; exit 1; }

PROMPT_FILE="$OUT_DIR/prompt_final_used.txt"
RAW_FILE="$OUT_DIR/output_gpt-iaedu_raw.txt"
TEST_FILE="$OUT_DIR/output_gpt-iaedu.txt"
ERR_FILE="$OUT_DIR/gpt-iaedu.stderr.log"
META_FILE="$OUT_DIR/generation_meta.tsv"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

pushd "$TMP_DIR" >/dev/null
bash "$ROOT/common/generate_final_prompt.sh" "$BASE_PROMPT" "$LANG" "$FRAMEWORK" "$SUT_FILE"
cp prompt1.txt "$PROMPT_FILE"
popd >/dev/null

echo -e "model\tlang\tframework\tsut_file\tprompt_file\traw_file\ttest_file\ttimeout_s" > "$META_FILE"
echo -e "$MODEL_NAME\t$LANG\t$FRAMEWORK\t$SUT_FILE\t$PROMPT_FILE\t$RAW_FILE\t$TEST_FILE\t$GEN_TIMEOUT_S" >> "$META_FILE"

echo "[INFO] Calling $MODEL_NAME via IAEdu with timeout=${GEN_TIMEOUT_S}s..."

set +e
timeout "$GEN_TIMEOUT_S" python3 "$ROOT/common/iaedu_from_prompt.py" "$PROMPT_FILE" > "$RAW_FILE" 2> "$ERR_FILE"
RC=$?
set -e

echo "$RC" > "$OUT_DIR/generation_exit_code.txt"

if [[ "$RC" -ne 0 ]]; then
  echo "[ERROR] $MODEL_NAME generation failed with rc=$RC" >&2
  echo "[ERROR] stderr: $ERR_FILE" >&2
  exit "$RC"
fi

if [[ ! -s "$RAW_FILE" ]]; then
  echo "[ERROR] $MODEL_NAME generated empty output" >&2
  exit 10
fi

python3 - <<PY
from pathlib import Path
p = Path("$RAW_FILE")
txt = p.read_text(encoding="utf-8", errors="ignore")
if not txt.strip():
    raise SystemExit(10)
PY

cp "$RAW_FILE" "$TEST_FILE"

echo "[OK] Generated:"
echo "  MODEL:  $MODEL_NAME"
echo "  PROMPT: $PROMPT_FILE"
echo "  RAW:    $RAW_FILE"
echo "  TEST:   $TEST_FILE"
echo "  META:   $META_FILE"
