#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source ~/.config/iaedu/model_endpoints.env

export MODEL_NAME=claude47
export IAEDU_ENDPOINT="${IAEDU_CLAUDE_ENDPOINT:?missing IAEDU_CLAUDE_ENDPOINT}"
export IAEDU_API_KEY="${IAEDU_CLAUDE_API_KEY:?missing IAEDU_CLAUDE_API_KEY}"
export IAEDU_CHANNEL_ID="${IAEDU_CLAUDE_CHANNEL_ID:?missing IAEDU_CLAUDE_CHANNEL_ID}"
export IAEDU_THREAD_PREFIX="defects4j-claude47-"

exec "$ROOT_DIR/scripts/run_defects4j_gpt4o_one_sut.sh"
