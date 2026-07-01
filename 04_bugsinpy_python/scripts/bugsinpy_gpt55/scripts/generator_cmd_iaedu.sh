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
DEFAULT_SECRETS_FILE="$REPO_ROOT/secrets.env"
SECRETS_FILE="${IAEDU_SECRETS_FILE:-$DEFAULT_SECRETS_FILE}"

# Respeitar credenciais já exportadas pelo launcher.
# Quando não existirem, carregar o ficheiro explicitamente selecionado.
if [[ -z "${IAEDU_ENDPOINT:-}" \
   || -z "${IAEDU_CHANNEL_ID:-}" \
   || -z "${IAEDU_API_KEY:-}" ]]
then
  if [[ ! -f "$SECRETS_FILE" ]]; then
    echo "[ERROR] secrets file not found: $SECRETS_FILE" >&2
    exit 1
  fi

  set -a
  # shellcheck disable=SC1090
  source "$SECRETS_FILE"
  set +a
fi

: "${IAEDU_ENDPOINT:?IAEDU_ENDPOINT is not defined}"
: "${IAEDU_CHANNEL_ID:?IAEDU_CHANNEL_ID is not defined}"
: "${IAEDU_API_KEY:?IAEDU_API_KEY is not defined}"

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
