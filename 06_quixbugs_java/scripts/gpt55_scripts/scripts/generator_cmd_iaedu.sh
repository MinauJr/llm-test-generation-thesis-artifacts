#!/usr/bin/env bash

set -Eeuo pipefail
set +H 2>/dev/null || true

ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
  pwd
)"

PROMPT_FILE="${1:?Usage: generator_cmd_iaedu.sh PROMPT_FILE}"
SECRET_FILE="${IAEDU_SECRETS_FILE:-}"

if [[ -z "$SECRET_FILE" ]]; then
  echo "ERRO: IAEDU_SECRETS_FILE não está definido." >&2
  exit 2
fi

if [[ ! -f "$SECRET_FILE" ]]; then
  echo "ERRO: secrets file não encontrado: $SECRET_FILE" >&2
  exit 2
fi

unset IAEDU_ENDPOINT
unset IAEDU_CHANNEL_ID
unset IAEDU_API_KEY

set -a
source "$SECRET_FILE"
set +a

: "${IAEDU_ENDPOINT:?IAEDU_ENDPOINT não definido}"
: "${IAEDU_CHANNEL_ID:?IAEDU_CHANNEL_ID não definido}"
: "${IAEDU_API_KEY:?IAEDU_API_KEY não definida}"

exec python3 \
  "$ROOT/common/iaedu_from_prompt.py" \
  "$PROMPT_FILE"
