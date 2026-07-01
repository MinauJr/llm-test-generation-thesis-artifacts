#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source ~/.config/iaedu/model_endpoints.env

export MODEL_NAME=gpt55
export IAEDU_ENDPOINT="${IAEDU_GPT55_ENDPOINT:?missing IAEDU_GPT55_ENDPOINT}"
export IAEDU_API_KEY="${IAEDU_GPT55_API_KEY:?missing IAEDU_GPT55_API_KEY}"
export IAEDU_CHANNEL_ID="${IAEDU_GPT55_CHANNEL_ID:?missing IAEDU_GPT55_CHANNEL_ID}"
export IAEDU_THREAD_PREFIX="defects4j-gpt55-"

exec "$ROOT_DIR/scripts/run_defects4j_gpt4o_one_sut.sh"
