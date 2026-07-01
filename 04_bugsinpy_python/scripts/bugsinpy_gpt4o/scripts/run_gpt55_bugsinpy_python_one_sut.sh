#!/usr/bin/env bash
set -euo pipefail

source "$HOME/.config/iaedu/model_endpoints.env"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pick_first_nonempty() {
  for name in "$@"; do
    eval "val=\${$name:-}"
    if [[ -n "${val:-}" ]]; then
      printf '%s' "$val"
      return 0
    fi
  done
  return 1
}

export MODEL_NAME="gpt-5.5-iaedu"

export IAEDU_ENDPOINT="$(pick_first_nonempty \
  IAEDU_GPT55_ENDPOINT \
  GPT55_ENDPOINT \
  IAEDU_GPT5_ENDPOINT \
  GPT5_ENDPOINT \
  || true)"

export IAEDU_API_KEY="$(pick_first_nonempty \
  IAEDU_GPT55_API_KEY \
  GPT55_API_KEY \
  IAEDU_GPT5_API_KEY \
  GPT5_API_KEY \
  || true)"

export IAEDU_CHANNEL_ID="$(pick_first_nonempty \
  IAEDU_GPT55_CHANNEL_ID \
  GPT55_CHANNEL_ID \
  IAEDU_GPT5_CHANNEL_ID \
  GPT5_CHANNEL_ID \
  || true)"

export IAEDU_THREAD_PREFIX="gpt55_bugsinpy_"

for v in IAEDU_ENDPOINT IAEDU_API_KEY IAEDU_CHANNEL_ID; do
  if [[ -z "${!v:-}" ]]; then
    echo "[ERROR] Missing required GPT-5.5 BugsInPy variable: $v" >&2
    echo "[ERROR] Check ~/.config/iaedu/model_endpoints.env" >&2
    exit 1
  fi
done

exec "$REPO/scripts/run_bugsinpy_gpt4o_one_sut_full.sh" "$@"
