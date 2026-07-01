#!/usr/bin/env bash
set -Eeuo pipefail
set +H 2>/dev/null || true

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

ZIP1="${ZIP1:-$HOME/d4j_part1.zip}"
ZIP2="${ZIP2:-$HOME/d4j_qwen35.zip}"

STAMP="$(date +%Y%m%d_%H%M%S)"
IMPORT_ROOT="$ROOT/out/_cluster_raw_defects4j_java_import_$STAMP"
UNPACK="$IMPORT_ROOT/unpacked"
MERGED="$IMPORT_ROOT/merged/defects4j_java_zero_shot_cluster_v1"
AUDIT="$IMPORT_ROOT/audit"

mkdir -p "$UNPACK" "$MERGED" "$AUDIT"

echo "===== IMPORT DEFECTS4J CLUSTER GENERATION ZIPS ====="
date
echo "ROOT=$ROOT"
echo "IMPORT_ROOT=$IMPORT_ROOT"
echo "MERGED=$MERGED"

echo
echo "===== PRECHECK ZIPS ====="
for z in "$ZIP1" "$ZIP2"; do
  if [ ! -f "$z" ]; then
    echo "[ABORT] missing zip: $z"
    exit 2
  fi
  ls -lh "$z"
  sha256sum "$z"
done | tee "$AUDIT/zips_sha256.txt"

echo
echo "===== UNZIP ====="
mkdir -p "$UNPACK/d4j_part1" "$UNPACK/d4j_qwen35"

unzip -q "$ZIP1" -d "$UNPACK/d4j_part1"
unzip -q "$ZIP2" -d "$UNPACK/d4j_qwen35"

echo
echo "===== FIND GENERATION ROOTS ====="
find "$UNPACK" -type d -name "defects4j_java_zero_shot_cluster_v1" | sort | tee "$AUDIT/found_generation_roots.txt"

ROOT_COUNT="$(wc -l < "$AUDIT/found_generation_roots.txt" | tr -d ' ')"
echo "FOUND_GENERATION_ROOTS=$ROOT_COUNT"

if [ "$ROOT_COUNT" -lt 1 ]; then
  echo "[ABORT] no defects4j_java_zero_shot_cluster_v1 roots found"
  exit 3
fi

echo
echo "===== MERGE MODEL DIRS ====="
while read -r genroot; do
  [ -d "$genroot" ] || continue
  echo "--- SOURCE_ROOT=$genroot"

  find "$genroot" -mindepth 1 -maxdepth 1 -type d -name "cluster-*" | sort | while read -r modeldir; do
    model="$(basename "$modeldir")"
    dest="$MERGED/$model"

    if [ -e "$dest" ]; then
      echo "[WARN] model already exists in merged root, merging carefully: $model"
    else
      mkdir -p "$dest"
    fi

    rsync -a "$modeldir/" "$dest/"
    echo "MERGED_MODEL=$model"
  done

  if [ -f "$genroot/dataset_generation_index.tsv" ]; then
    base="$(echo "$genroot" | sed 's#[/ ]#_#g')"
    cp "$genroot/dataset_generation_index.tsv" "$AUDIT/dataset_generation_index_from_${base}.tsv"
  fi

  if [ -f "$genroot/master_generation.log" ]; then
    base="$(echo "$genroot" | sed 's#[/ ]#_#g')"
    cp "$genroot/master_generation.log" "$AUDIT/master_generation_from_${base}.log"
  fi
done < "$AUDIT/found_generation_roots.txt"

echo
echo "===== BUILD INVENTORY ====="
python3 - <<PY
from pathlib import Path
import json
from collections import Counter, defaultdict

merged = Path("$MERGED")
audit = Path("$AUDIT")
rows = []
status_counts = Counter()
model_counts = Counter()
sut_counts = Counter()
model_sut_runs = defaultdict(int)

for status_path in sorted(merged.glob("cluster-*/*/run_*/status.json")):
    run_dir = status_path.parent
    sut_id = run_dir.parent.name
    model_dir = run_dir.parent.parent.name
    run_id = run_dir.name

    try:
        data = json.loads(status_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        data = {"status": "bad_status_json", "json_error": str(e)}

    generated = run_dir / "generated_tests.java"
    response = run_dir / "response_raw.txt"
    prompt = run_dir / "prompt_final_used.txt"
    trace = run_dir / "generation_retry_trace.tsv"

    status = str(data.get("status", "missing_status"))
    model = str(data.get("model", model_dir))
    repeat = str(data.get("repeat", run_id.replace("run_", "")))
    target_class = str(data.get("target_class", ""))

    row = {
        "model": model,
        "model_dir": model_dir,
        "sut_id": sut_id,
        "run_id": run_id,
        "repeat": repeat,
        "target_class": target_class,
        "generation_status": status,
        "exit_code": str(data.get("exit_code", "")),
        "timed_out": str(data.get("timed_out", "")),
        "empty_output": str(data.get("empty_output", "")),
        "timeout_s": str(data.get("timeout_s", "")),
        "duration_s": str(data.get("duration_s", "")),
        "generated_exists": str(generated.exists()),
        "generated_size": str(generated.stat().st_size if generated.exists() else 0),
        "response_exists": str(response.exists()),
        "response_size": str(response.stat().st_size if response.exists() else 0),
        "prompt_exists": str(prompt.exists()),
        "trace_exists": str(trace.exists()),
        "run_dir": str(run_dir),
    }
    rows.append(row)

    status_counts[status] += 1
    model_counts[model_dir] += 1
    sut_counts[sut_id] += 1
    model_sut_runs[(model_dir, sut_id)] += 1

headers = [
    "model", "model_dir", "sut_id", "run_id", "repeat", "target_class",
    "generation_status", "exit_code", "timed_out", "empty_output",
    "timeout_s", "duration_s",
    "generated_exists", "generated_size",
    "response_exists", "response_size",
    "prompt_exists", "trace_exists",
    "run_dir",
]

inv = audit / "raw_generation_inventory.tsv"
with inv.open("w", encoding="utf-8") as f:
    f.write("\\t".join(headers) + "\\n")
    for r in rows:
        f.write("\\t".join(r[h].replace("\\t", " ").replace("\\n", " ") for h in headers) + "\\n")

summary = audit / "raw_generation_summary.txt"
with summary.open("w", encoding="utf-8") as f:
    f.write(f"MERGED={merged}\\n")
    f.write(f"TOTAL_STATUS_JSON={len(rows)}\\n")
    f.write(f"MODELS={len(model_counts)}\\n")
    f.write(f"SUTS={len(sut_counts)}\\n")
    f.write("\\nSTATUS_COUNTS\\n")
    for k, v in sorted(status_counts.items()):
        f.write(f"{k}\\t{v}\\n")
    f.write("\\nMODEL_COUNTS\\n")
    for k, v in sorted(model_counts.items()):
        f.write(f"{k}\\t{v}\\n")
    f.write("\\nSUT_COUNTS\\n")
    for k, v in sorted(sut_counts.items()):
        f.write(f"{k}\\t{v}\\n")
    f.write("\\nMODEL_SUT_RUNS_NOT_5\\n")
    bad = 0
    for (m, s), v in sorted(model_sut_runs.items()):
        if v != 5:
            bad += 1
            f.write(f"{m}\\t{s}\\t{v}\\n")
    if bad == 0:
        f.write("ALL_MODEL_SUT_PAIRS_HAVE_5_RUNS\\n")

print(summary.read_text(encoding="utf-8"))
print(f"INVENTORY={inv}")
PY

ln -sfn "$IMPORT_ROOT" "$ROOT/out/_cluster_raw_defects4j_java_import_latest"

echo
echo "===== FILE COUNTS ====="
echo "STATUS_JSON=$(find "$MERGED" -name status.json | wc -l)"
echo "GENERATED_TESTS=$(find "$MERGED" -name generated_tests.java | wc -l)"
echo "PROMPTS=$(find "$MERGED" -name prompt_final_used.txt | wc -l)"
echo "RESPONSES=$(find "$MERGED" -name response_raw.txt | wc -l)"

echo
echo "===== MODEL DIRS ====="
find "$MERGED" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort

echo
echo "===== DONE ====="
echo "IMPORT_ROOT=$IMPORT_ROOT"
echo "MERGED=$MERGED"
echo "AUDIT=$AUDIT"
