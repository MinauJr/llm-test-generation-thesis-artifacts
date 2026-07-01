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
export FULL_ONE_SUT="$REPO/scripts/run_gpt55_bugsinpy_python_one_sut.sh"

if [[ -z "${OUT_BASE:-}" ]]; then
    echo "[ERRO] OUT_BASE deve ser definido explicitamente." >&2
    exit 75
fi

exec "$REPO/scripts/run_bugsinpy_gpt4o_dataset_full.sh" "$@"
