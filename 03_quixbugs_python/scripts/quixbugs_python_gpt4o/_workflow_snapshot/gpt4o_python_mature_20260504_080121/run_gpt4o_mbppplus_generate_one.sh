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
  find "$src" -mindepth 1 -maxdepth 1 -exec cp -a {} "$OUT_DIR/" \;
}

LAST_ATTEMPT_DIR=""
LAST_RC=0
EMPTY_ATTEMPTS=0

for ATTEMPT in $(seq 1 "$GEN_EMPTY_RETRY_MAX"); do
  LAST_ATTEMPT_DIR="$ATTEMPTS_DIR/attempt_$(printf '%02d' "$ATTEMPT")"
  rm -rf "$LAST_ATTEMPT_DIR"
  mkdir -p "$LAST_ATTEMPT_DIR"

  set +e
  "$INNER" "$PROMPT_TEMPLATE" "$LANGUAGE" "$FRAMEWORK" "$SUT_FILE" "$LAST_ATTEMPT_DIR"
  LAST_RC=$?
  set -e

  PAYLOAD_FILE="$LAST_ATTEMPT_DIR/output_gpt-iaedu.txt"

  if is_nonempty_payload "$PAYLOAD_FILE"; then
    promote_attempt "$LAST_ATTEMPT_DIR"
    echo "$ATTEMPT" > "$OUT_DIR/generation_attempts.txt"
    echo "$EMPTY_ATTEMPTS" > "$OUT_DIR/generation_empty_attempts.txt"
    echo "$ATTEMPT" > "$OUT_DIR/generation_final_attempt.txt"
    echo "nonempty_success" > "$OUT_DIR/generation_final_state.txt"
    printf "%s\t%s\tnonempty\t%s\n" "$ATTEMPT" "$LAST_RC" "$LAST_ATTEMPT_DIR" >> "$TRACE_FILE"
    exit "$LAST_RC"
  fi

  EMPTY_ATTEMPTS=$((EMPTY_ATTEMPTS + 1))
  printf "%s\t%s\tempty\t%s\n" "$ATTEMPT" "$LAST_RC" "$LAST_ATTEMPT_DIR" >> "$TRACE_FILE"
done

if [ -n "$LAST_ATTEMPT_DIR" ] && [ -d "$LAST_ATTEMPT_DIR" ]; then
  promote_attempt "$LAST_ATTEMPT_DIR"
fi

: > "$OUT_DIR/output_gpt-iaedu.txt"
echo "$GEN_EMPTY_RETRY_MAX" > "$OUT_DIR/generation_attempts.txt"
echo "$EMPTY_ATTEMPTS" > "$OUT_DIR/generation_empty_attempts.txt"
echo "$GEN_EMPTY_RETRY_MAX" > "$OUT_DIR/generation_final_attempt.txt"
echo "no_output_exhausted" > "$OUT_DIR/generation_final_state.txt"
printf "%s\t%s\tempty_exhausted\t%s\n" "$GEN_EMPTY_RETRY_MAX" "$LAST_RC" "$LAST_ATTEMPT_DIR" >> "$TRACE_FILE"

exit 0
