#!/usr/bin/env bash
set -euo pipefail

source "$HOME/.config/iaedu/model_endpoints.env"

export MODEL_NAME="claude-opus-4.7-iaedu"
export IAEDU_ENDPOINT="$IAEDU_CLAUDE47_ENDPOINT"
export IAEDU_API_KEY="$IAEDU_CLAUDE47_API_KEY"
export IAEDU_CHANNEL_ID="$IAEDU_CLAUDE47_CHANNEL_ID"
export IAEDU_THREAD_PREFIX="claude47_humanevalplus_"

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/run_gpt4o_humanevalplus_python_one_sut.sh" "$@"
