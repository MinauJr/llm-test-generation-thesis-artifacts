#!/usr/bin/env bash
set -euo pipefail

source "$HOME/.config/iaedu/model_endpoints.env"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

export MODEL_NAME="claude-opus-4.7-iaedu"

export IAEDU_ENDPOINT="$(pick_first_nonempty \
  IAEDU_CLAUDE47_ENDPOINT \
  CLAUDE47_ENDPOINT \
  IAEDU_CLAUDE_ENDPOINT \
  CLAUDE_ENDPOINT \
  ANTHROPIC_ENDPOINT \
  || true)"

export IAEDU_API_KEY="$(pick_first_nonempty \
  IAEDU_CLAUDE47_API_KEY \
  CLAUDE47_API_KEY \
  IAEDU_CLAUDE_API_KEY \
  CLAUDE_API_KEY \
  ANTHROPIC_API_KEY \
  || true)"

export IAEDU_CHANNEL_ID="$(pick_first_nonempty \
  IAEDU_CLAUDE47_CHANNEL_ID \
  CLAUDE47_CHANNEL_ID \
  IAEDU_CLAUDE_CHANNEL_ID \
  CLAUDE_CHANNEL_ID \
  ANTHROPIC_CHANNEL_ID \
  || true)"

export IAEDU_THREAD_PREFIX="claude47_mbppplus_"
export ONE_SUT_SCRIPT="$ROOT/scripts/run_claude47_mbppplus_python_one_sut.sh"

for v in IAEDU_ENDPOINT IAEDU_API_KEY IAEDU_CHANNEL_ID; do
  if [[ -z "${!v:-}" ]]; then
    echo "[ERROR] Missing required Claude launcher variable: $v" >&2
    echo "[ERROR] Check ~/.config/iaedu/model_endpoints.env and Claude variable names." >&2
    exit 1
  fi
done

exec "$ROOT/scripts/run_gpt4o_mbppplus_python_dataset.sh" "$@"
