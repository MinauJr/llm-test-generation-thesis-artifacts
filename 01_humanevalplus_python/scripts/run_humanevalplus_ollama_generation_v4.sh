#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s nullglob

RUN_TAG="${RUN_TAG:-humanevalplus_zero_shot_cluster_v4}"
DATASET_ROOT="${DATASET_ROOT:-$HOME/projetos/SUTs/humanevalplus}"
PROMPT_TEMPLATE="${PROMPT_TEMPLATE:-$HOME/projetos/llm_test_generation_gpt4o/prompts/python_humanevalplus_zero_shot_v2.txt}"
OUT_ROOT="${OUT_ROOT:-$HOME/projetos/llm_cluster_generations/$RUN_TAG}"

REPEATS="${REPEATS:-5}"
TIMEOUT_S="${TIMEOUT_S:-200}"
KILL_AFTER_S="${KILL_AFTER_S:-10}"

OLLAMA_BIN="${OLLAMA_BIN:-ollama}"
OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://127.0.0.1:11434}"

SKIP_IF_DONE="${SKIP_IF_DONE:-1}"
EXPECTED_SUT_COUNT="${EXPECTED_SUT_COUNT:-164}"

ONLY_MODELS="${ONLY_MODELS:-}"
ONLY_SUTS="${ONLY_SUTS:-}"
MAX_SUTS="${MAX_SUTS:-0}"
PRECHECK_ONLY="${PRECHECK_ONLY:-0}"

EMPTY_RETRY_MAX="${EMPTY_RETRY_MAX:-15}"
GENERATION_RETRY_SLEEP_S="${GENERATION_RETRY_SLEEP_S:-2}"

DEFAULT_MODELS=(
  "cluster-max-codellama-7b-instruct-ctx16k"
  "cluster-safe-qwen3-14b-heretic-ctx32k"
  "cluster-safe-qwen3.5-9b-ctx32k"
  "cluster-safe-deepseek-coder-v2-16b-ctx16k"
  "cluster-safe-deepseek-v2-lite-ctx32k"
  "cluster-safe-qwen2.5-coder-14b-ctx32k"
  "cluster-safe-codestral-22b-ctx16k"
  "cluster-safe-qwen3-coder-30b-official-ctx8k"
)

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[ERROR] Missing command: $1" >&2
    exit 1
  }
}

csv_to_array() {
  local csv="$1"
  local -n out_ref="$2"
  out_ref=()
  [[ -z "$csv" ]] && return 0
  IFS=',' read -r -a out_ref <<< "$csv"
}

contains_in_array() {
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

json_get() {
  local json_file="$1"
  local key="$2"
  python3 - "$json_file" "$key" <<'PY'
import json, sys
from pathlib import Path

p = Path(sys.argv[1])
key = sys.argv[2]

if not p.exists():
    print("")
    raise SystemExit(0)

try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)

value = data.get(key, "")
if value is None:
    print("")
elif isinstance(value, bool):
    print("true" if value else "false")
else:
    print(value)
PY
}

build_prompt() {
  local template_file="$1"
  local sut_file="$2"
  local out_file="$3"

  python3 - "$template_file" "$sut_file" "$out_file" <<'PY'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
sut_path = Path(sys.argv[2])
out_path = Path(sys.argv[3])

template = template_path.read_text(encoding="utf-8")
sut_code = sut_path.read_text(encoding="utf-8")

final_prompt = template.replace("{UNDER_TEST_SNIPPET}", sut_code)
out_path.write_text(final_prompt, encoding="utf-8")
PY
}

make_payload_json() {
  local model="$1"
  local prompt_file="$2"
  local payload_file="$3"

  python3 - "$model" "$prompt_file" "$payload_file" <<'PY'
import json, sys
from pathlib import Path

model = sys.argv[1]
prompt_file = Path(sys.argv[2])
payload_file = Path(sys.argv[3])

prompt = prompt_file.read_text(encoding="utf-8")

payload = {
    "model": model,
    "prompt": prompt,
    "stream": False
}

payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
PY
}

write_placeholder_api_json() {
  local api_json_file="$1"
  local reason="$2"
  local exit_code="$3"
  local timed_out="$4"
  local attempt="$5"

  python3 - "$api_json_file" "$reason" "$exit_code" "$timed_out" "$attempt" <<'PY'
import json, sys
from pathlib import Path

api_json_file = Path(sys.argv[1])
reason = sys.argv[2]
exit_code = int(sys.argv[3])
timed_out = sys.argv[4].lower() == "true"
attempt = int(sys.argv[5])

payload = {
    "response": "",
    "done": False,
    "done_reason": "",
    "error": reason,
    "placeholder": True,
    "exit_code": exit_code,
    "timed_out": timed_out,
    "attempt": attempt
}

api_json_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
PY
}

extract_and_validate() {
  local api_json_file="$1"
  local raw_file="$2"
  local generated_file="$3"
  local validation_file="$4"

  python3 - "$api_json_file" "$raw_file" "$generated_file" "$validation_file" <<'PY'
import ast
import json
import re
import sys
import textwrap
from pathlib import Path

api_json_path = Path(sys.argv[1])
raw_path = Path(sys.argv[2])
gen_path = Path(sys.argv[3])
meta_path = Path(sys.argv[4])

ansi_re = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
fence_re = re.compile(r"```([^\n`]*)\n(.*?)```", flags=re.DOTALL)

CODE_LINE_PATTERNS = [
    re.compile(r'^\s*import\s+pytest\b'),
    re.compile(r'^\s*import\s+sut\b'),
    re.compile(r'^\s*from\s+sut\s+import\b'),
    re.compile(r'^\s*from\s+typing\s+import\b'),
    re.compile(r'^\s*import\s+\w+'),
    re.compile(r'^\s*from\s+\w+\s+import\b'),
    re.compile(r'^\s*@pytest\.'),
    re.compile(r'^\s*def\s+test_'),
    re.compile(r'^\s*class\s+Test'),
]

INTRO_PREFIXES = (
    "here is",
    "here's",
    "this is",
    "below is",
    "sure,",
    "sure!",
    "certainly",
    "i will",
    "i'll",
    "the following",
)

meta = {
    "api_json_ok": False,
    "api_error": "",
    "api_done": None,
    "api_done_reason": "",
    "raw_nonempty": False,
    "generated_nonempty": False,
    "ansi_escape_sequences_removed": 0,
    "control_chars_removed": 0,
    "fence_extracted": False,
    "fence_language": "",
    "syntax_ok": False,
    "syntax_error_type": "",
    "syntax_error_message": "",
    "syntax_error_lineno": "",
    "top_level_test_count": 0,
    "test_class_method_count": 0,
    "total_test_count": 0,
    "structure_ok": False,
    "candidate_count": 0,
    "chosen_strategy": "",
    "trimmed_suffix_lines": 0,
}

def is_code_like(line: str) -> bool:
    s = line.rstrip("\n")
    if not s.strip():
        return False
    return any(p.search(s) for p in CODE_LINE_PATTERNS)

def clean_text(s: str):
    ansi_matches = ansi_re.findall(s)
    s = ansi_re.sub("", s)

    out = []
    removed_controls = 0
    for ch in s:
        o = ord(ch)
        if o in (9, 10, 13):
            out.append(ch)
        elif o < 32 or o == 127:
            removed_controls += 1
        else:
            out.append(ch)

    return "".join(out), len(ansi_matches), removed_controls

def normalize_candidate(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    while lines and lines[0].strip().startswith("```"):
        lines.pop(0)
    while lines and lines[-1].strip().startswith("```"):
        lines.pop()

    while lines and not is_code_like(lines[0]):
        lower = lines[0].strip().lower()
        if lower.startswith(INTRO_PREFIXES) or lower.endswith(":") or "pytest file" in lower or "test file" in lower:
            lines.pop(0)
        else:
            break

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    text = "\n".join(lines)
    text = textwrap.dedent(text).strip("\n")
    if text:
        text += "\n"
    return text

def score_candidate(text: str):
    syntax_ok = False
    structure_ok = False
    top_level = 0
    class_methods = 0
    total_tests = 0
    code_lines = 0

    lines = text.splitlines()
    code_lines = sum(1 for ln in lines if is_code_like(ln))

    try:
        tree = ast.parse(text)
        syntax_ok = True
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                top_level += 1
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test_"):
                        class_methods += 1
        total_tests = top_level + class_methods
        structure_ok = total_tests >= 1
    except Exception:
        pass

    return {
        "syntax_ok": syntax_ok,
        "structure_ok": structure_ok,
        "top_level": top_level,
        "class_methods": class_methods,
        "total_tests": total_tests,
        "code_lines": code_lines,
        "length": len(text),
    }

def try_trim_suffix(text: str):
    text = text.strip("\n")
    if not text:
        return text, 0

    lines = text.split("\n")
    best = text + "\n"
    best_trim = 0

    try:
        ast.parse(best)
        return best, 0
    except Exception:
        pass

    for k in range(len(lines) - 1, 0, -1):
        candidate = "\n".join(lines[:k]).strip("\n")
        if not candidate:
            continue
        candidate += "\n"
        try:
            ast.parse(candidate)
            return candidate, len(lines) - k
        except Exception:
            continue

    return best, 0

raw_text = ""
clean = ""

if api_json_path.exists():
    try:
        data = json.loads(api_json_path.read_text(encoding="utf-8"))
        meta["api_json_ok"] = True
        if isinstance(data, dict):
            meta["api_error"] = str(data.get("error") or "")
            if "done" in data:
                meta["api_done"] = bool(data.get("done"))
            meta["api_done_reason"] = str(data.get("done_reason") or "")
            raw_text = str(data.get("response") or "")
    except Exception as e:
        meta["api_error"] = f"bad_api_json: {e}"

raw_path.write_text(raw_text, encoding="utf-8")
meta["raw_nonempty"] = bool(raw_text)

clean, ansi_removed, control_removed = clean_text(raw_text)
meta["ansi_escape_sequences_removed"] = ansi_removed
meta["control_chars_removed"] = control_removed

candidates = []

if clean:
    candidates.append(("full_clean", clean))

    matches = list(fence_re.finditer(clean))
    for m in matches:
        lang = (m.group(1) or "").strip().lower()
        block = m.group(2)
        if lang == "python":
            candidates.append(("fence_python", block))
        else:
            candidates.append(("fence_any", block))

    lines = clean.splitlines()
    code_start_ix = []
    for i, line in enumerate(lines):
        if is_code_like(line):
            code_start_ix.append(i)

    seen_ix = set()
    for i in code_start_ix[:8]:
        if i not in seen_ix:
            seen_ix.add(i)
            candidates.append((f"from_code_start_{i}", "\n".join(lines[i:])))

normalized = []
for strategy, text in candidates:
    norm = normalize_candidate(text)
    if norm:
        normalized.append((strategy, norm))
        trimmed, trimmed_count = try_trim_suffix(norm)
        normalized.append((f"{strategy}_trimmed", trimmed))

dedup = []
seen = set()
for strategy, text in normalized:
    key = text
    if key not in seen:
        seen.add(key)
        dedup.append((strategy, text))

meta["candidate_count"] = len(dedup)

best_text = ""
best_info = None
best_strategy = ""
best_trimmed = 0

for strategy, text in dedup:
    info = score_candidate(text)
    key = (
        1 if info["syntax_ok"] else 0,
        1 if info["structure_ok"] else 0,
        info["total_tests"],
        info["code_lines"],
        info["length"],
    )
    if best_info is None:
        best_text = text
        best_info = info
        best_strategy = strategy
    else:
        best_key = (
            1 if best_info["syntax_ok"] else 0,
            1 if best_info["structure_ok"] else 0,
            best_info["total_tests"],
            best_info["code_lines"],
            best_info["length"],
        )
        if key > best_key:
            best_text = text
            best_info = info
            best_strategy = strategy

if not best_text:
    best_text = ""
    best_info = score_candidate(best_text)

if best_strategy.startswith("fence_python"):
    meta["fence_extracted"] = True
    meta["fence_language"] = "python"
elif best_strategy.startswith("fence_any"):
    meta["fence_extracted"] = True
    meta["fence_language"] = "other"

meta["chosen_strategy"] = best_strategy

gen_path.write_text(best_text, encoding="utf-8")
meta["generated_nonempty"] = bool(best_text)

if best_text:
    try:
        tree = ast.parse(best_text)
        meta["syntax_ok"] = True

        top_level = 0
        class_methods = 0
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                top_level += 1
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test_"):
                        class_methods += 1

        meta["top_level_test_count"] = top_level
        meta["test_class_method_count"] = class_methods
        meta["total_test_count"] = top_level + class_methods
        meta["structure_ok"] = (top_level + class_methods) >= 1
    except Exception as e:
        meta["syntax_ok"] = False
        meta["syntax_error_type"] = e.__class__.__name__
        meta["syntax_error_message"] = str(e)
        meta["syntax_error_lineno"] = getattr(e, "lineno", "") or ""

meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

write_status_json() {
  local status_file="$1"

  STATUS_FILE="$status_file" VALIDATION_FILE="$VALIDATION_FILE" python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

def sha256_of(path_str):
    p = Path(path_str)
    if not p.exists() or not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()

def size_of(path_str):
    p = Path(path_str)
    if not p.exists() or not p.is_file():
        return 0
    return p.stat().st_size

def read_json(path_str):
    p = Path(path_str)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def to_bool(v):
    return str(v).lower() == "true"

val = read_json(os.environ["VALIDATION_FILE"])

data = {
    "dataset": os.environ["DATASET_NAME"],
    "prompt_variant": os.environ["PROMPT_VARIANT"],
    "model": os.environ["MODEL_NAME"],
    "sut_id": os.environ["SUT_ID"],
    "repeat": int(os.environ["REPEAT_NO"]),
    "attempt_count": int(os.environ["ATTEMPT_COUNT"]),
    "empty_retry_max": int(os.environ["EMPTY_RETRY_MAX"]),
    "generation_retry_sleep_s": int(os.environ["GENERATION_RETRY_SLEEP_S"]),
    "timeout_s": int(os.environ["TIMEOUT_S"]),
    "kill_after_s": int(os.environ["KILL_AFTER_S"]),
    "ollama_bin": os.environ["OLLAMA_BIN"],
    "ollama_api_base": os.environ["OLLAMA_API_BASE"],
    "prompt_template": os.environ["PROMPT_TEMPLATE"],
    "sut_root": os.environ["SUT_ROOT"],
    "sut_file": os.environ["SUT_FILE"],
    "started_at_utc": os.environ["STARTED_AT_UTC"],
    "finished_at_utc": os.environ["FINISHED_AT_UTC"],
    "duration_s": float(os.environ["DURATION_S"]),
    "exit_code": int(os.environ["EXIT_CODE"]),
    "timed_out": to_bool(os.environ["TIMED_OUT"]),
    "status": os.environ["RUN_STATUS"],

    "request_payload_file": os.environ["PAYLOAD_FILE"],
    "response_api_file": os.environ["API_JSON_FILE"],
    "response_raw_file": os.environ["RAW_FILE"],
    "generated_file": os.environ["GENERATED_FILE"],
    "stderr_file": os.environ["STDERR_FILE"],
    "prompt_final_file": os.environ["PROMPT_FILE"],
    "validation_file": os.environ["VALIDATION_FILE"],

    "request_payload_bytes": size_of(os.environ["PAYLOAD_FILE"]),
    "response_api_bytes": size_of(os.environ["API_JSON_FILE"]),
    "response_raw_bytes": size_of(os.environ["RAW_FILE"]),
    "generated_bytes": size_of(os.environ["GENERATED_FILE"]),
    "stderr_bytes": size_of(os.environ["STDERR_FILE"]),
    "prompt_bytes": size_of(os.environ["PROMPT_FILE"]),

    "request_payload_sha256": sha256_of(os.environ["PAYLOAD_FILE"]),
    "response_api_sha256": sha256_of(os.environ["API_JSON_FILE"]),
    "response_raw_sha256": sha256_of(os.environ["RAW_FILE"]),
    "generated_sha256": sha256_of(os.environ["GENERATED_FILE"]),
    "prompt_sha256": sha256_of(os.environ["PROMPT_FILE"]),
}

for k in [
    "api_json_ok", "api_error", "api_done", "api_done_reason",
    "raw_nonempty", "generated_nonempty",
    "ansi_escape_sequences_removed", "control_chars_removed",
    "fence_extracted", "fence_language",
    "syntax_ok", "syntax_error_type", "syntax_error_message", "syntax_error_lineno",
    "top_level_test_count", "test_class_method_count", "total_test_count", "structure_ok",
    "candidate_count", "chosen_strategy", "trimmed_suffix_lines"
]:
    data[k] = val.get(k)

Path(os.environ["STATUS_FILE"]).write_text(
    json.dumps(data, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8"
)
PY
}

append_global_tsv() {
  local tsv_file="$1"
  local model="$2"
  local sut_id="$3"
  local rep="$4"
  local status="$5"
  local exit_code="$6"
  local timed_out="$7"
  local duration_s="$8"
  local rep_dir="$9"

  if [[ ! -f "$tsv_file" ]]; then
    printf "model\tsut_id\trepeat\tstatus\texit_code\ttimed_out\tduration_s\trep_dir\n" > "$tsv_file"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$model" "$sut_id" "$rep" "$status" "$exit_code" "$timed_out" "$duration_s" "$rep_dir" >> "$tsv_file"
}

require_cmd python3
require_cmd curl
require_cmd timeout
require_cmd "$OLLAMA_BIN"

curl -fsS "$OLLAMA_API_BASE/api/tags" >/dev/null

if [[ ! -d "$DATASET_ROOT" ]]; then
  echo "[ERROR] DATASET_ROOT not found: $DATASET_ROOT" >&2
  exit 1
fi

if [[ ! -f "$PROMPT_TEMPLATE" ]]; then
  echo "[ERROR] PROMPT_TEMPLATE not found: $PROMPT_TEMPLATE" >&2
  exit 1
fi

if [[ -n "$ONLY_MODELS" ]]; then
  csv_to_array "$ONLY_MODELS" MODELS
else
  MODELS=("${DEFAULT_MODELS[@]}")
fi

mapfile -t ALL_SUT_DIRS < <(find "$DATASET_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'HumanEval_*' | sort -V)

if [[ "${#ALL_SUT_DIRS[@]}" -eq 0 ]]; then
  echo "[ERROR] No HumanEval_* SUT directories found under: $DATASET_ROOT" >&2
  exit 1
fi

if [[ -n "$ONLY_SUTS" ]]; then
  csv_to_array "$ONLY_SUTS" ONLY_SUTS_ARR
  SUT_DIRS=()
  for sut_dir in "${ALL_SUT_DIRS[@]}"; do
    sut_id="$(basename "$sut_dir")"
    if contains_in_array "$sut_id" "${ONLY_SUTS_ARR[@]}"; then
      SUT_DIRS+=("$sut_dir")
    fi
  done
else
  SUT_DIRS=("${ALL_SUT_DIRS[@]}")
fi

if [[ "$MAX_SUTS" -gt 0 && "${#SUT_DIRS[@]}" -gt "$MAX_SUTS" ]]; then
  SUT_DIRS=("${SUT_DIRS[@]:0:$MAX_SUTS}")
fi

echo "[INFO] DATASET_ROOT=$DATASET_ROOT"
echo "[INFO] PROMPT_TEMPLATE=$PROMPT_TEMPLATE"
echo "[INFO] OUT_ROOT=$OUT_ROOT"
echo "[INFO] REPEATS=$REPEATS"
echo "[INFO] TIMEOUT_S=$TIMEOUT_S"
echo "[INFO] KILL_AFTER_S=$KILL_AFTER_S"
echo "[INFO] OLLAMA_API_BASE=$OLLAMA_API_BASE"
echo "[INFO] EMPTY_RETRY_MAX=$EMPTY_RETRY_MAX"
echo "[INFO] GENERATION_RETRY_SLEEP_S=$GENERATION_RETRY_SLEEP_S"
echo "[INFO] PRECHECK_ONLY=$PRECHECK_ONLY"
echo "[INFO] MODEL_COUNT=${#MODELS[@]}"
echo "[INFO] SUT_COUNT=${#SUT_DIRS[@]}"

if [[ "${#ALL_SUT_DIRS[@]}" -ne "$EXPECTED_SUT_COUNT" ]]; then
  echo "[WARN] Expected $EXPECTED_SUT_COUNT total SUTs but found ${#ALL_SUT_DIRS[@]}"
fi

for model in "${MODELS[@]}"; do
  if ! "$OLLAMA_BIN" show "$model" >/dev/null 2>&1; then
    echo "[ERROR] Model not found in Ollama: $model" >&2
    exit 1
  fi
done

if [[ "$PRECHECK_ONLY" == "1" ]]; then
  echo "[OK] Precheck passed."
  exit 0
fi

mkdir -p "$OUT_ROOT"

GLOBAL_TSV="$OUT_ROOT/dataset_runs.tsv"
MASTER_LOG="$OUT_ROOT/master.log"

{
  echo "============================================================"
  echo "RUN_TAG=$RUN_TAG"
  echo "START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "DATASET_ROOT=$DATASET_ROOT"
  echo "PROMPT_TEMPLATE=$PROMPT_TEMPLATE"
  echo "REPEATS=$REPEATS"
  echo "TIMEOUT_S=$TIMEOUT_S"
  echo "KILL_AFTER_S=$KILL_AFTER_S"
  echo "OLLAMA_BIN=$OLLAMA_BIN"
  echo "OLLAMA_API_BASE=$OLLAMA_API_BASE"
  echo "EMPTY_RETRY_MAX=$EMPTY_RETRY_MAX"
  echo "GENERATION_RETRY_SLEEP_S=$GENERATION_RETRY_SLEEP_S"
  echo "MODELS=${MODELS[*]}"
  echo "SUT_COUNT=${#SUT_DIRS[@]}"
  echo "============================================================"
} | tee -a "$MASTER_LOG"

for model in "${MODELS[@]}"; do
  echo | tee -a "$MASTER_LOG"
  echo "############################################################" | tee -a "$MASTER_LOG"
  echo "[MODEL] $model" | tee -a "$MASTER_LOG"
  echo "############################################################" | tee -a "$MASTER_LOG"

  MODEL_ROOT="$OUT_ROOT/$model"
  mkdir -p "$MODEL_ROOT"

  for sut_dir in "${SUT_DIRS[@]}"; do
    sut_id="$(basename "$sut_dir")"
    sut_file="$sut_dir/sut.py"

    echo | tee -a "$MASTER_LOG"
    echo "---- $model / $sut_id ----" | tee -a "$MASTER_LOG"

    for rep in $(seq 1 "$REPEATS"); do
      rep_tag="$(printf 'rep_%02d' "$rep")"
      rep_dir="$MODEL_ROOT/$sut_id/$rep_tag"
      mkdir -p "$rep_dir"

      prompt_file="$rep_dir/prompt_final.txt"
      payload_file="$rep_dir/request_payload.json"
      api_json_file="$rep_dir/response_api.json"
      raw_file="$rep_dir/response_raw.txt"
      generated_file="$rep_dir/generated_tests.py"
      stderr_file="$rep_dir/stderr.log"
      validation_file="$rep_dir/extract_validation.json"
      status_file="$rep_dir/status.json"
      attempts_tsv="$rep_dir/attempts.tsv"

      if [[ "$SKIP_IF_DONE" == "1" && -f "$status_file" ]]; then
        echo "[SKIP] $model / $sut_id / $rep_tag" | tee -a "$MASTER_LOG"
        continue
      fi

      rm -f "$prompt_file" "$payload_file" "$api_json_file" "$raw_file" "$generated_file" \
            "$stderr_file" "$validation_file" "$status_file" "$attempts_tsv"

      printf "attempt\tstatus\texit_code\ttimed_out\n" > "$attempts_tsv"

      START_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      start_epoch="$(python3 - <<'PY'
import time
print(f"{time.time():.6f}")
PY
)"

      if [[ ! -f "$sut_file" ]]; then
        : > "$payload_file"
        : > "$api_json_file"
        : > "$raw_file"
        : > "$generated_file"
        : > "$stderr_file"
        : > "$validation_file"
        : > "$prompt_file"

        END_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        end_epoch="$(python3 - <<'PY'
import time
print(f"{time.time():.6f}")
PY
)"
        duration_s="$(python3 - "$start_epoch" "$end_epoch" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
)"

        ATTEMPT_COUNT="0"
        RUN_STATUS="missing_sut_file"
        EXIT_CODE="9001"
        TIMED_OUT="false"
        VALIDATION_FILE="$validation_file" \
        DATASET_NAME="HumanEval+" \
        PROMPT_VARIANT="zero_shot_v2" \
        MODEL_NAME="$model" \
        SUT_ID="$sut_id" \
        REPEAT_NO="$rep" \
        EMPTY_RETRY_MAX="$EMPTY_RETRY_MAX" \
        GENERATION_RETRY_SLEEP_S="$GENERATION_RETRY_SLEEP_S" \
        TIMEOUT_S="$TIMEOUT_S" \
        KILL_AFTER_S="$KILL_AFTER_S" \
        OLLAMA_BIN="$OLLAMA_BIN" \
        OLLAMA_API_BASE="$OLLAMA_API_BASE" \
        PROMPT_TEMPLATE="$PROMPT_TEMPLATE" \
        SUT_ROOT="$sut_dir" \
        SUT_FILE="$sut_file" \
        STARTED_AT_UTC="$START_TS" \
        FINISHED_AT_UTC="$END_TS" \
        DURATION_S="$duration_s" \
        EXIT_CODE="$EXIT_CODE" \
        TIMED_OUT="$TIMED_OUT" \
        RUN_STATUS="$RUN_STATUS" \
        PAYLOAD_FILE="$payload_file" \
        API_JSON_FILE="$api_json_file" \
        RAW_FILE="$raw_file" \
        GENERATED_FILE="$generated_file" \
        STDERR_FILE="$stderr_file" \
        PROMPT_FILE="$prompt_file" \
        ATTEMPT_COUNT="$ATTEMPT_COUNT" \
        write_status_json "$status_file"

        append_global_tsv "$GLOBAL_TSV" "$model" "$sut_id" "$rep" "$RUN_STATUS" "$EXIT_CODE" "$TIMED_OUT" "$duration_s" "$rep_dir"
        continue
      fi

      build_prompt "$PROMPT_TEMPLATE" "$sut_file" "$prompt_file"
      make_payload_json "$model" "$prompt_file" "$payload_file"

      attempt=1
      max_attempts=$((1 + EMPTY_RETRY_MAX))

      final_status=""
      final_exit_code="0"
      final_timed_out="false"

      while (( attempt <= max_attempts )); do
        rm -f "$api_json_file" "$raw_file" "$generated_file" "$stderr_file" "$validation_file"
        : > "$stderr_file"

        set +e
        timeout -k "${KILL_AFTER_S}s" "${TIMEOUT_S}s" \
          curl -sS --fail \
            "$OLLAMA_API_BASE/api/generate" \
            -H 'Content-Type: application/json' \
            --data-binary @"$payload_file" \
            -o "$api_json_file" \
            2> "$stderr_file"
        exit_code=$?
        set -e

        timed_out="false"
        if [[ "$exit_code" -eq 124 ]]; then
          timed_out="true"
          write_placeholder_api_json "$api_json_file" "timeout" "$exit_code" "$timed_out" "$attempt"
        elif [[ "$exit_code" -ne 0 ]]; then
          write_placeholder_api_json "$api_json_file" "transport_failure" "$exit_code" "$timed_out" "$attempt"
        elif [[ ! -f "$api_json_file" || ! -s "$api_json_file" ]]; then
          write_placeholder_api_json "$api_json_file" "empty_api_response_file" "$exit_code" "$timed_out" "$attempt"
        fi

        extract_and_validate "$api_json_file" "$raw_file" "$generated_file" "$validation_file"

        api_json_ok="$(json_get "$validation_file" api_json_ok)"
        api_error="$(json_get "$validation_file" api_error)"
        generated_nonempty="$(json_get "$validation_file" generated_nonempty)"
        syntax_ok="$(json_get "$validation_file" syntax_ok)"
        structure_ok="$(json_get "$validation_file" structure_ok)"

        status="ok"
        if [[ "$exit_code" -eq 124 ]]; then
          status="timeout"
        elif [[ "$exit_code" -ne 0 ]]; then
          status="failed"
        elif [[ "$api_json_ok" != "true" ]]; then
          status="bad_api_json"
        elif [[ -n "$api_error" ]]; then
          status="api_error"
        elif [[ "$generated_nonempty" != "true" ]]; then
          status="empty_output"
        elif [[ "$syntax_ok" != "true" ]]; then
          status="invalid_python_syntax"
        elif [[ "$structure_ok" != "true" ]]; then
          status="invalid_test_structure"
        else
          status="ok"
        fi

        printf "%s\t%s\t%s\t%s\n" "$attempt" "$status" "$exit_code" "$timed_out" >> "$attempts_tsv"

        final_status="$status"
        final_exit_code="$exit_code"
        final_timed_out="$timed_out"

        if [[ "$status" == "empty_output" || "$status" == "bad_api_json" || "$status" == "api_error" ]]; then
          if (( attempt < max_attempts )); then
            sleep "$GENERATION_RETRY_SLEEP_S"
            ((attempt++))
            continue
          fi
        fi

        break
      done

      END_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      end_epoch="$(python3 - <<'PY'
import time
print(f"{time.time():.6f}")
PY
)"
      duration_s="$(python3 - "$start_epoch" "$end_epoch" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
)"

      VALIDATION_FILE="$validation_file" \
      DATASET_NAME="HumanEval+" \
      PROMPT_VARIANT="zero_shot_v2" \
      MODEL_NAME="$model" \
      SUT_ID="$sut_id" \
      REPEAT_NO="$rep" \
      EMPTY_RETRY_MAX="$EMPTY_RETRY_MAX" \
      GENERATION_RETRY_SLEEP_S="$GENERATION_RETRY_SLEEP_S" \
      TIMEOUT_S="$TIMEOUT_S" \
      KILL_AFTER_S="$KILL_AFTER_S" \
      OLLAMA_BIN="$OLLAMA_BIN" \
      OLLAMA_API_BASE="$OLLAMA_API_BASE" \
      PROMPT_TEMPLATE="$PROMPT_TEMPLATE" \
      SUT_ROOT="$sut_dir" \
      SUT_FILE="$sut_file" \
      STARTED_AT_UTC="$START_TS" \
      FINISHED_AT_UTC="$END_TS" \
      DURATION_S="$duration_s" \
      EXIT_CODE="$final_exit_code" \
      TIMED_OUT="$final_timed_out" \
      RUN_STATUS="$final_status" \
      PAYLOAD_FILE="$payload_file" \
      API_JSON_FILE="$api_json_file" \
      RAW_FILE="$raw_file" \
      GENERATED_FILE="$generated_file" \
      STDERR_FILE="$stderr_file" \
      PROMPT_FILE="$prompt_file" \
      ATTEMPT_COUNT="$attempt" \
      write_status_json "$status_file"

      append_global_tsv "$GLOBAL_TSV" "$model" "$sut_id" "$rep" "$final_status" "$final_exit_code" "$final_timed_out" "$duration_s" "$rep_dir"
      echo "[DONE] $model / $sut_id / $rep_tag -> status=$final_status exit=$final_exit_code attempts=$attempt dur=${duration_s}s" | tee -a "$MASTER_LOG"
    done
  done
done

echo "============================================================" | tee -a "$MASTER_LOG"
echo "END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"
echo "OUT_ROOT=$OUT_ROOT" | tee -a "$MASTER_LOG"
echo "GLOBAL_TSV=$GLOBAL_TSV" | tee -a "$MASTER_LOG"
echo "MASTER_LOG=$MASTER_LOG" | tee -a "$MASTER_LOG"
echo "============================================================" | tee -a "$MASTER_LOG"
