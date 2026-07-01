#!/usr/bin/env bash
set -u
set -o pipefail

RUNNER_DIR="${1:?runner dir}"
INPUT_FILE="${2:?input file}"
OUTPUT_FILE="${3:?output file}"
TIMEOUT_S="${4:-60}"
OUT_JSON="${5:?output json}"
LOG_PREFIX="${6:?log prefix}"

cd "$RUNNER_DIR" || {
  echo "ERROR: não foi possível entrar em $RUNNER_DIR" >&2
  return 90 2>/dev/null || exit 90
}

mkdir -p "$(dirname "$OUT_JSON")" "$(dirname "$LOG_PREFIX")"

cp -a "$INPUT_FILE" "$OUTPUT_FILE"

cat > conftest.py <<'PYCONF'
import builtins
import importlib
import os
from pathlib import Path

try:
    builtins.sut = importlib.import_module("sut")
except Exception:
    pass

def pytest_collection_modifyitems(config, items):
    if os.environ.get("QUIXBUGS_EFFECTIVE_FILTER") != "1":
        return

    allow_file = Path(__file__).with_name("effective_nodeids.txt")

    if not allow_file.is_file():
        return

    allowed = {
        line.strip()
        for line in allow_file.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }

    selected = []
    deselected = []

    for item in items:
        if item.nodeid in allowed:
            selected.append(item)
        else:
            deselected.append(item)

    items[:] = selected

    if deselected:
        config.hook.pytest_deselected(items=deselected)
PYCONF

COLLECTED="collected_nodeids.txt"
EFFECTIVE="effective_nodeids.txt"
RESULTS="nodeid_results.tsv"

: > "$COLLECTED"
: > "$EFFECTIVE"

printf 'nodeid\texit_code\tclassification\n' > "$RESULTS"

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH="$RUNNER_DIR" \
timeout --kill-after=3s "${TIMEOUT_S}s" \
python3 -m pytest \
  --collect-only \
  -q \
  "$OUTPUT_FILE" \
  > "${LOG_PREFIX}.collect.log" 2>&1

COLLECT_RC=$?

grep "^${OUTPUT_FILE}::" \
  "${LOG_PREFIX}.collect.log" \
  > "$COLLECTED" || true

COLLECTED_COUNT="$(
  wc -l < "$COLLECTED" | tr -d ' '
)"

PASS_COUNT=0
FAIL_COUNT=0
TIMEOUT_COUNT=0

while IFS= read -r NODEID; do
  [ -n "$NODEID" ] || continue

  SAFE_NAME="$(
    printf '%s' "$NODEID" \
      | sha256sum \
      | cut -d' ' -f1
  )"

  NODE_LOG="${LOG_PREFIX}.node_${SAFE_NAME}.log"

  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH="$RUNNER_DIR" \
  timeout --kill-after=3s "${TIMEOUT_S}s" \
  python3 -m pytest \
    -q \
    --disable-warnings \
    "$NODEID" \
    > "$NODE_LOG" 2>&1

  RC=$?

  if [ "$RC" = "0" ]; then
    CLASSIFICATION="pass"
    PASS_COUNT=$((PASS_COUNT + 1))
    printf '%s\n' "$NODEID" >> "$EFFECTIVE"
  elif [ "$RC" = "124" ] || [ "$RC" = "137" ]; then
    CLASSIFICATION="timeout"
    TIMEOUT_COUNT=$((TIMEOUT_COUNT + 1))
  else
    CLASSIFICATION="fail"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  printf '%s\t%s\t%s\n' \
    "$NODEID" \
    "$RC" \
    "$CLASSIFICATION" \
    >> "$RESULTS"

done < "$COLLECTED"

INITIAL_EFFECTIVE_COUNT="$(
  wc -l < "$EFFECTIVE" | tr -d ' '
)"

GREEDY_USED=0
FINAL_RC=5

run_effective_suite() {
  local log_file="$1"

  QUIXBUGS_EFFECTIVE_FILTER=1 \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH="$RUNNER_DIR" \
  timeout --kill-after=5s "${TIMEOUT_S}s" \
  python3 -m pytest \
    -q \
    --disable-warnings \
    "$OUTPUT_FILE" \
    > "$log_file" 2>&1
}

if [ "$INITIAL_EFFECTIVE_COUNT" -gt 0 ]; then
  run_effective_suite "${LOG_PREFIX}.combined_initial.log"
  FINAL_RC=$?
fi

if [ "$INITIAL_EFFECTIVE_COUNT" -gt 0 ] &&
   [ "$FINAL_RC" != "0" ]
then
  GREEDY_USED=1

  cp "$EFFECTIVE" effective_nodeids_initial.txt
  : > "$EFFECTIVE"
  : > effective_nodeids_candidate.txt

  while IFS= read -r NODEID; do
    [ -n "$NODEID" ] || continue

    cp "$EFFECTIVE" effective_nodeids_candidate.txt
    printf '%s\n' "$NODEID" \
      >> effective_nodeids_candidate.txt

    cp effective_nodeids_candidate.txt "$EFFECTIVE"

    SAFE_NAME="$(
      printf '%s' "$NODEID" \
        | sha256sum \
        | cut -d' ' -f1
    )"

    run_effective_suite \
      "${LOG_PREFIX}.greedy_${SAFE_NAME}.log"

    GREEDY_RC=$?

    if [ "$GREEDY_RC" != "0" ]; then
      grep -Fvx "$NODEID" "$EFFECTIVE" \
        > effective_nodeids.tmp || true

      mv effective_nodeids.tmp "$EFFECTIVE"
    fi
  done < effective_nodeids_initial.txt

  FINAL_COUNT="$(
    wc -l < "$EFFECTIVE" | tr -d ' '
  )"

  if [ "$FINAL_COUNT" -gt 0 ]; then
    run_effective_suite "${LOG_PREFIX}.combined_final.log"
    FINAL_RC=$?
  else
    FINAL_RC=5
  fi
fi

FINAL_EFFECTIVE_COUNT="$(
  wc -l < "$EFFECTIVE" | tr -d ' '
)"

python3 - \
  "$OUT_JSON" \
  "$COLLECT_RC" \
  "$COLLECTED_COUNT" \
  "$PASS_COUNT" \
  "$FAIL_COUNT" \
  "$TIMEOUT_COUNT" \
  "$INITIAL_EFFECTIVE_COUNT" \
  "$FINAL_EFFECTIVE_COUNT" \
  "$GREEDY_USED" \
  "$FINAL_RC" <<'PYJSON'
import json
import sys
from pathlib import Path

(
    out,
    collect_rc,
    collected,
    passed,
    failed,
    timed_out,
    initial_effective,
    final_effective,
    greedy_used,
    final_rc,
) = sys.argv[1:]

payload = {
    "schema_version": "quixbugs_python_nodeid_sanitization_v1",
    "collect_exit_code": int(collect_rc),
    "collected_nodeids": int(collected),
    "individual_pass_nodeids": int(passed),
    "individual_fail_nodeids": int(failed),
    "individual_timeout_nodeids": int(timed_out),
    "initial_effective_nodeids": int(initial_effective),
    "final_effective_nodeids": int(final_effective),
    "greedy_stabilization_used": bool(int(greedy_used)),
    "final_pytest_exit_code": int(final_rc),
}

Path(out).write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PYJSON

echo "collected_nodeids=$COLLECTED_COUNT"
echo "individual_pass_nodeids=$PASS_COUNT"
echo "individual_fail_nodeids=$FAIL_COUNT"
echo "individual_timeout_nodeids=$TIMEOUT_COUNT"
echo "initial_effective_nodeids=$INITIAL_EFFECTIVE_COUNT"
echo "final_effective_nodeids=$FINAL_EFFECTIVE_COUNT"
echo "greedy_stabilization_used=$GREEDY_USED"
echo "final_pytest_exit_code=$FINAL_RC"

if [ "$FINAL_EFFECTIVE_COUNT" -eq 0 ]; then
  exit 5
fi

if [ "$FINAL_RC" != "0" ]; then
  exit "$FINAL_RC"
fi

exit 0
