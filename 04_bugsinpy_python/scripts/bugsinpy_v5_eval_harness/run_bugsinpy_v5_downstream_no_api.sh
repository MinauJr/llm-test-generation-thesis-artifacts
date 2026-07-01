#!/usr/bin/env bash
set -Eeuo pipefail

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTEST_ADDOPTS=
export PYTHONDONTWRITEBYTECODE=1

CORE="/home/jpaiva/projetos/bugsinpy_v5_eval_harness/run_bugsinpy_v5_downstream_core.sh"

echo "===== BUGSINPY V5 ISOLATED DOWNSTREAM ====="
date
echo "FINAL_OUT=${FINAL_OUT:-}"
echo "PYTEST_TIMEOUT_S=${PYTEST_TIMEOUT_S:-90}"
echo "MUTATION_TIMEOUT_S=${MUTATION_TIMEOUT_S:-300}"
echo "PYTEST_DISABLE_PLUGIN_AUTOLOAD=$PYTEST_DISABLE_PLUGIN_AUTOLOAD"

exec bash "$CORE"
