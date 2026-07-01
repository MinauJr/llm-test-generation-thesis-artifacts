#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "projetos/llm_test_generation_gpt4o/defects4j_gpt4o"
ZIP_PATHS = [
    Path.home() / "d4j_part1.zip",
    Path.home() / "d4j_qwen35.zip",
]

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
import_root = ROOT / "out" / f"_cluster_raw_defects4j_java_import_{stamp}"
unpack_root = import_root / "unpacked"
merged_root = import_root / "merged" / "defects4j_java_zero_shot_cluster_v1"
audit_root = import_root / "audit"

for p in [unpack_root, merged_root, audit_root]:
    p.mkdir(parents=True, exist_ok=True)

print("===== IMPORT DEFECTS4J CLUSTER GENERATION ZIPS V2 NO RSYNC =====")
print(f"ROOT={ROOT}")
print(f"IMPORT_ROOT={import_root}")
print(f"MERGED={merged_root}")
print()

missing = [str(p) for p in ZIP_PATHS if not p.exists()]
if missing:
    print("ERRO: zips em falta:")
    for p in missing:
        print(f"  {p}")
    raise SystemExit(2)

print("===== ZIP INPUTS =====")
for z in ZIP_PATHS:
    print(f"{z}\t{z.stat().st_size} bytes")
print()

print("===== UNZIP =====")
for z in ZIP_PATHS:
    dest = unpack_root / z.stem
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {z} -> {dest}")
    with zipfile.ZipFile(z, "r") as xf:
        xf.extractall(dest)

print()
print("===== FIND GENERATION ROOTS =====")
generation_roots = sorted(
    p for p in unpack_root.rglob("defects4j_java_zero_shot_cluster_v1")
    if p.is_dir()
)

with (audit_root / "found_generation_roots.txt").open("w", encoding="utf-8") as f:
    for p in generation_roots:
        print(p)
        f.write(str(p) + "\n")

print(f"FOUND_GENERATION_ROOTS={len(generation_roots)}")
if not generation_roots:
    raise SystemExit(3)

print()
print("===== MERGE MODEL DIRS =====")
merged_models = []

for genroot in generation_roots:
    print(f"--- SOURCE_ROOT={genroot}")
    model_dirs = sorted(p for p in genroot.iterdir() if p.is_dir() and p.name.startswith("cluster-"))

    if not model_dirs:
        print(f"  WARN: no cluster-* model dirs under {genroot}")
        continue

    for model_dir in model_dirs:
        dest = merged_root / model_dir.name
        print(f"  MERGE_MODEL={model_dir.name}")
        shutil.copytree(model_dir, dest, dirs_exist_ok=True)
        merged_models.append(model_dir.name)

    for extra_name in ["dataset_generation_index.tsv", "master_generation.log"]:
        src = genroot / extra_name
        if src.exists():
            safe = str(genroot).replace("/", "_").replace(" ", "_")
            shutil.copy2(src, audit_root / f"{extra_name}_from_{safe}")

print()
print("===== BUILD INVENTORY =====")

rows = []
status_counts = Counter()
model_counts = Counter()
sut_counts = Counter()
model_sut_runs = defaultdict(int)

for status_path in sorted(merged_root.glob("cluster-*/*/run_*/status.json")):
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

inventory_path = audit_root / "raw_generation_inventory.tsv"
with inventory_path.open("w", encoding="utf-8") as f:
    f.write("\t".join(headers) + "\n")
    for r in rows:
        f.write("\t".join(r[h].replace("\t", " ").replace("\n", " ") for h in headers) + "\n")

summary_path = audit_root / "raw_generation_summary.txt"
with summary_path.open("w", encoding="utf-8") as f:
    f.write(f"IMPORT_ROOT={import_root}\n")
    f.write(f"MERGED={merged_root}\n")
    f.write(f"TOTAL_STATUS_JSON={len(rows)}\n")
    f.write(f"MODELS={len(model_counts)}\n")
    f.write(f"SUTS={len(sut_counts)}\n")

    f.write("\nSTATUS_COUNTS\n")
    for k, v in sorted(status_counts.items()):
        f.write(f"{k}\t{v}\n")

    f.write("\nMODEL_COUNTS\n")
    for k, v in sorted(model_counts.items()):
        f.write(f"{k}\t{v}\n")

    f.write("\nSUT_COUNTS\n")
    for k, v in sorted(sut_counts.items()):
        f.write(f"{k}\t{v}\n")

    f.write("\nMODEL_SUT_RUNS_NOT_5\n")
    bad = 0
    for (m, s), v in sorted(model_sut_runs.items()):
        if v != 5:
            bad += 1
            f.write(f"{m}\t{s}\t{v}\n")
    if bad == 0:
        f.write("ALL_MODEL_SUT_PAIRS_HAVE_5_RUNS\n")

latest = ROOT / "out" / "_cluster_raw_defects4j_java_import_latest"
try:
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(import_root, target_is_directory=True)
except Exception as e:
    print(f"WARN: não consegui criar symlink latest: {e}")

print(summary_path.read_text(encoding="utf-8"))
print(f"INVENTORY={inventory_path}")

print()
print("===== FILE COUNTS =====")
print(f"STATUS_JSON={len(list(merged_root.rglob('status.json')))}")
print(f"GENERATED_TESTS={len(list(merged_root.rglob('generated_tests.java')))}")
print(f"PROMPTS={len(list(merged_root.rglob('prompt_final_used.txt')))}")
print(f"RESPONSES={len(list(merged_root.rglob('response_raw.txt')))}")

print()
print("===== MODEL DIRS =====")
for p in sorted(merged_root.iterdir()):
    if p.is_dir():
        print(p.name)

print()
print("===== DONE =====")
print(f"IMPORT_ROOT={import_root}")
print(f"MERGED={merged_root}")
print(f"AUDIT={audit_root}")
