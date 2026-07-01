#!/usr/bin/env bash
set -u
set -o pipefail

PROMPT_FILE="${1:-}"

CLUSTER_DATA_ROOT="${CLUSTER_DATA_ROOT:-}"
CLUSTER_MODEL="${CLUSTER_MODEL:-${MODEL_LABEL:-}}"
SUT_NAME="${SUT_NAME:-}"
REP="${REP:-}"

if [ -z "$CLUSTER_DATA_ROOT" ]; then
  echo "ERROR CLUSTER_DATA_ROOT não definido" >&2
  exit 64
fi

if [ -z "$CLUSTER_MODEL" ]; then
  echo "ERROR CLUSTER_MODEL não definido" >&2
  exit 64
fi

if [ -z "$SUT_NAME" ]; then
  echo "ERROR SUT_NAME não definido" >&2
  exit 64
fi

if [ -z "$REP" ]; then
  echo "ERROR REP não definido" >&2
  exit 64
fi

REP_PAD="$(printf '%02d' "$REP")"

SOURCE_DIR=""

for candidate in \
  "$CLUSTER_DATA_ROOT/$CLUSTER_MODEL/$SUT_NAME/rep_$REP_PAD" \
  "$CLUSTER_DATA_ROOT/$CLUSTER_MODEL/$SUT_NAME/run_0001/1-$REP"
do
  if [ -d "$candidate" ]; then
    SOURCE_DIR="$candidate"
    break
  fi
done

if [ -z "$SOURCE_DIR" ]; then
  echo "ERROR source directory não encontrado" >&2
  echo "MODEL=$CLUSTER_MODEL" >&2
  echo "SUT=$SUT_NAME" >&2
  echo "REP=$REP" >&2
  exit 66
fi

STATUS_JSON="$SOURCE_DIR/status.json"
GENERATED="$SOURCE_DIR/generated_tests.py"
RAW_RESPONSE="$SOURCE_DIR/raw_response.txt"
VALIDATION_JSON="$SOURCE_DIR/validation.json"
PROMPT_SOURCE="$SOURCE_DIR/prompt.txt"
API_RESPONSE="$SOURCE_DIR/api_response.json"

CLUSTER_STATUS="$(
  python3 - "$STATUS_JSON" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

if not path.is_file():
    print("missing_status")
else:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        print(data.get("status", "unknown"))
    except Exception:
        print("invalid_status_json")
PY
)"

if [ "$CLUSTER_STATUS" = "timeout" ]; then
  echo "CLUSTER_SOURCE_TIMEOUT source=$SOURCE_DIR" >&2
  exit 124
fi

SOURCE_FILE=""

if [ -s "$GENERATED" ] && grep -q '[^[:space:]]' "$GENERATED"; then
  SOURCE_FILE="$GENERATED"
elif [ -s "$RAW_RESPONSE" ] && grep -q '[^[:space:]]' "$RAW_RESPONSE"; then
  SOURCE_FILE="$RAW_RESPONSE"
else
  echo "ERROR nenhum teste Python não vazio em $SOURCE_DIR" >&2
  exit 67
fi

if [ -n "$PROMPT_FILE" ]; then
  RUN_DIR="$(cd "$(dirname "$PROMPT_FILE")/.." 2>/dev/null && pwd || true)"

  if [ -n "$RUN_DIR" ]; then
    SNAPSHOT="$RUN_DIR/generation/cluster_input"
    mkdir -p "$SNAPSHOT"

    for f in \
      "$STATUS_JSON" \
      "$VALIDATION_JSON" \
      "$PROMPT_SOURCE" \
      "$API_RESPONSE"
    do
      if [ -f "$f" ]; then
        cp -a "$f" "$SNAPSHOT/$(basename "$f")"
      fi
    done

    if [ -f "$GENERATED" ]; then
      cp -a "$GENERATED" "$SNAPSHOT/generated_tests_original.py"
    fi

    python3 - \
      "$SNAPSHOT/provenance.json" \
      "$CLUSTER_MODEL" \
      "$SUT_NAME" \
      "$REP" \
      "$CLUSTER_STATUS" \
      "$SOURCE_FILE" \
      "$STATUS_JSON" <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

out, model, sut, rep, status, source, status_json = sys.argv[1:]

def describe(value):
    path = Path(value)
    if not path.is_file():
        return {
            "path": str(path),
            "exists": False,
            "bytes": 0,
            "sha256": None,
        }

    data = path.read_bytes()

    return {
        "path": str(path),
        "exists": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }

payload = {
    "schema_version": "quixbugs_python_cluster_local_eval_provenance_v1",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "model": model,
    "sut_name": sut,
    "repeat": int(rep),
    "cluster_status": status,
    "selected_source": describe(source),
    "cluster_status_json": describe(status_json),
    "methodological_notes": [
        "The original cluster-generated test was not modified.",
        "The local evaluator consumes a copied test.",
        "No LLM, API or Ollama request is made during local evaluation."
    ],
}

Path(out).write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
  fi
fi

echo \
  "CLUSTER_SOURCE model=$CLUSTER_MODEL sut=$SUT_NAME rep=$REP status=$CLUSTER_STATUS file=$SOURCE_FILE" \
  >&2

cat "$SOURCE_FILE"
