#!/usr/bin/env bash
set -euo pipefail

source "$HOME/.config/iaedu/model_endpoints.env"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export MODEL_NAME="gpt-5.5-iaedu"
export IAEDU_ENDPOINT="$IAEDU_GPT55_ENDPOINT"
export IAEDU_API_KEY="$IAEDU_GPT55_API_KEY"
export IAEDU_CHANNEL_ID="$IAEDU_GPT55_CHANNEL_ID"
export IAEDU_THREAD_PREFIX="gpt55_mbppplus_"

exec "$ROOT/scripts/run_gpt4o_mbppplus_python_one_sut.sh" "$@"
