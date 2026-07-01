#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/generator_cmd_iaedu.sh final_prompt.txt > raw_output.py
#
# This is intentionally a single-call bridge.
# Retry-empty is handled by the outer one_sut workflow, not here.

PROMPT_FILE="${1:?usage: generator_cmd_iaedu.sh PROMPT_FILE}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HELPER="$REPO_ROOT/common/iaedu_from_prompt.py"

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "[ERROR] prompt file not found: $PROMPT_FILE" >&2
  exit 2
fi

if [[ ! -f "$HELPER" ]]; then
  echo "[ERROR] IAEdu helper not found: $HELPER" >&2
  exit 2
fi

# Most mature GPT-4o workflows call the helper with the prompt file path.
# Keep this wrapper minimal so attempt counts remain truthful.
python3 "$HELPER" "$PROMPT_FILE"
