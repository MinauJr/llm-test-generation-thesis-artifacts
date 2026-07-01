#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
source "$REPO/scripts/select_iaedu_account.sh"

export REPO
export ROOT="$REPO"
export MODEL_NAME="gpt-5.5-iaedu"
export IAEDU_THREAD_PREFIX="gpt55_bugsinpy_${IAEDU_ACCOUNT_LABEL}_"

exec "$REPO/scripts/run_bugsinpy_gpt4o_one_sut_full.sh" "$@"
