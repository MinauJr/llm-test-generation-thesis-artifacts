#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source ~/.config/iaedu/model_endpoints.env

export MODEL_NAME=gpt55
export IAEDU_ENDPOINT="${IAEDU_GPT55_ENDPOINT:?missing IAEDU_GPT55_ENDPOINT}"
export IAEDU_API_KEY="${IAEDU_GPT55_API_KEY:?missing IAEDU_GPT55_API_KEY}"
export IAEDU_CHANNEL_ID="${IAEDU_GPT55_CHANNEL_ID:?missing IAEDU_GPT55_CHANNEL_ID}"
export IAEDU_THREAD_PREFIX="defects4j-gpt55-"

: "${OUT_BASE:=$ROOT_DIR/out/_gpt55_defects4j_java}"
: "${ONE_SUT_SCRIPT:=$ROOT_DIR/scripts/run_gpt55_defects4j_java_one_sut.sh}"

REPEATS="${REPEATS:-5}" \
GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-200}" \
GEN_EMPTY_RETRY_MAX="${GEN_EMPTY_RETRY_MAX:-15}" \
GENERATION_RETRY_SLEEP_S="${GENERATION_RETRY_SLEEP_S:-2}" \
PYTEST_TIMEOUT_S="${PYTEST_TIMEOUT_S:-60}" \
MUTATION_TIMEOUT_S="${MUTATION_TIMEOUT_S:-180}" \
RUN_MUTATION="${RUN_MUTATION:-1}" \
OUT_BASE="$OUT_BASE" \
MODEL_NAME="$MODEL_NAME" \
ONE_SUT_SCRIPT="$ONE_SUT_SCRIPT" \
bash "$ROOT_DIR/scripts/run_defects4j_multimodel_dataset.sh"
