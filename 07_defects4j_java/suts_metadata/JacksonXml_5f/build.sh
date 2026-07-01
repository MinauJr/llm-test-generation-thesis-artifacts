#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/datasets/defect4j/defects4j/framework/bin:$PATH"
defects4j compile
echo "OK: compiled"
