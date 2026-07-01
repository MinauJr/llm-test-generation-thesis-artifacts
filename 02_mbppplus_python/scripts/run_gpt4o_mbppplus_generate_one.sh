#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INNER="$ROOT/scripts/run_gpt4o_mbppplus_generate_one_inner_once.sh"

PROMPT_TEMPLATE="${1:?missing prompt template}"
LANGUAGE="${2:?missing language}"
FRAMEWORK="${3:?missing framework}"
SUT_FILE="${4:?missing SUT file}"
OUT_DIR="${5:?missing output dir}"

GEN_EMPTY_RETRY_MAX="${GEN_EMPTY_RETRY_MAX:-15}"

mkdir -p "$OUT_DIR"
ATTEMPTS_DIR="$OUT_DIR/_attempts"
mkdir -p "$ATTEMPTS_DIR"

TRACE_FILE="$OUT_DIR/generation_retry_trace.tsv"
printf "attempt\trc\traw_state\tattempt_dir\n" > "$TRACE_FILE"

is_nonempty_payload() {
  local f="$1"
  python3 - "$f" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
if not p.exists():
    raise SystemExit(1)

txt = p.read_text(encoding="utf-8", errors="ignore")
raise SystemExit(0 if txt.strip() else 1)
PY
}

promote_attempt() {
  local src="$1"
  local dst="$2"

  for f in \
    prompt_final_used.txt \
    output_gpt-iaedu_raw.txt \
    output_gpt-iaedu.txt \
    gpt-iaedu.stderr.log \
    generation_exit_code.txt \
    generation_meta.tsv
  do
    if [[ -f "$src/$f" ]]; then
      cp -f "$src/$f" "$dst/$f"
    fi
  done
}

EMPTY_COUNT=0
LAST_ATTEMPT_DIR=""

for ATT in $(seq 1 "$GEN_EMPTY_RETRY_MAX"); do
  ATT_DIR="$ATTEMPTS_DIR/attempt_$(printf "%02d" "$ATT")"
  mkdir -p "$ATT_DIR"
  LAST_ATTEMPT_DIR="$ATT_DIR"

  set +e
  "$INNER" "$PROMPT_TEMPLATE" "$LANGUAGE" "$FRAMEWORK" "$SUT_FILE" "$ATT_DIR"
  RC=$?
  set -e

  if [[ "$RC" -ne 0 ]]; then
    if [[ "$RC" -eq 10 ]]; then
      EMPTY_COUNT=$((EMPTY_COUNT + 1))
      printf "%s\t%s\t%s\t%s\n" "$ATT" "$RC" "empty" "$ATT_DIR" >> "$TRACE_FILE"
      continue
    fi

    promote_attempt "$ATT_DIR" "$OUT_DIR"
    printf "%s\t%s\t%s\t%s\n" "$ATT" "$RC" "error_rc_$RC" "$ATT_DIR" >> "$TRACE_FILE"
    echo "$ATT" > "$OUT_DIR/generation_attempts.txt"
    echo "$EMPTY_COUNT" > "$OUT_DIR/generation_empty_attempts.txt"
    echo "$ATT" > "$OUT_DIR/generation_final_attempt.txt"
    echo "error_rc_$RC" > "$OUT_DIR/generation_final_state.txt"
    exit "$RC"
  fi

  if is_nonempty_payload "$ATT_DIR/output_gpt-iaedu.txt"; then
    promote_attempt "$ATT_DIR" "$OUT_DIR"
    printf "%s\t%s\t%s\t%s\n" "$ATT" "$RC" "nonempty_success" "$ATT_DIR" >> "$TRACE_FILE"
    echo "$ATT" > "$OUT_DIR/generation_attempts.txt"
    echo "$EMPTY_COUNT" > "$OUT_DIR/generation_empty_attempts.txt"
    echo "$ATT" > "$OUT_DIR/generation_final_attempt.txt"
    echo "nonempty_success" > "$OUT_DIR/generation_final_state.txt"
    exit 0
  fi

  EMPTY_COUNT=$((EMPTY_COUNT + 1))
  printf "%s\t%s\t%s\t%s\n" "$ATT" "$RC" "empty" "$ATT_DIR" >> "$TRACE_FILE"
done

if [[ -n "$LAST_ATTEMPT_DIR" ]]; then
  promote_attempt "$LAST_ATTEMPT_DIR" "$OUT_DIR"
fi

: > "$OUT_DIR/output_gpt-iaedu.txt"
echo "$GEN_EMPTY_RETRY_MAX" > "$OUT_DIR/generation_attempts.txt"
echo "$EMPTY_COUNT" > "$OUT_DIR/generation_empty_attempts.txt"
echo "$GEN_EMPTY_RETRY_MAX" > "$OUT_DIR/generation_final_attempt.txt"
echo "no_output_exhausted" > "$OUT_DIR/generation_final_state.txt"
printf "%s\t%s\t%s\t%s\n" "$GEN_EMPTY_RETRY_MAX" "10" "empty_exhausted" "$LAST_ATTEMPT_DIR" >> "$TRACE_FILE"

exit 0
