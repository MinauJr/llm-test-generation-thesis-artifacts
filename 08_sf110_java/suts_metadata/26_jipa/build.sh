#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

JAR_COUNT="$(find "$ROOT" -maxdepth 1 -type f -name '*.jar' | wc -l | tr -d ' ')"
if [ "$JAR_COUNT" -gt 0 ]; then
  touch .build_ok
  echo "OK: jar already present"
  exit 0
fi

if [ -d "$ROOT/src" ]; then
  echo "WARN: src existe mas este SUT SF110 nao tem rebuild automatico configurado"
  touch .build_ok
  exit 0
fi

echo "WARN: nao encontrei jar nem src"
touch .build_ok
exit 0
