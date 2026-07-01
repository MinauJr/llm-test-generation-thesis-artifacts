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

export IAEDU_THREAD_PREFIX="claude47_bugsinpy_"
export FULL_ONE_SUT="$REPO/scripts/run_claude47_bugsinpy_python_one_sut.sh"
export OUT_BASE="${OUT_BASE:-$REPO/out/_final_claude47_bugsinpy_python_v1}"

for v in IAEDU_ENDPOINT IAEDU_API_KEY IAEDU_CHANNEL_ID; do
  if [[ -z "${!v:-}" ]]; then
    echo "[ERROR] Missing required Claude BugsInPy variable: $v" >&2
    echo "[ERROR] Check ~/.config/iaedu/model_endpoints.env" >&2
    exit 1
  fi
done

exec "$REPO/scripts/run_bugsinpy_gpt4o_dataset_full.sh" "$@"
