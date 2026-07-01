#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

def as_num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None

def penalized(v):
    n = as_num(v)
    return 0.0 if n is None else n

parser = argparse.ArgumentParser()
parser.add_argument("--out-root", required=True)
args = parser.parse_args()

out_root = Path(args.out_root).expanduser().resolve()
if not out_root.exists():
    raise SystemExit(f"missing out root: {out_root}")

status_files = sorted(out_root.glob("*/run_*/1-*/metrics/status.json"))

rows = []
for sf in status_files:
    try:
        d = json.loads(sf.read_text(encoding="utf-8"))
    except Exception as e:
        d = {
            "status": "status_json_read_fail",
            "note": f"{type(e).__name__}: {e}",
            "run_dir": str(sf.parent.parent),
        }

    sut_name = d.get("sut_name") or sf.parts[-5]
    run_id = d.get("run_id") or sf.parts[-4]
    rep_id = d.get("rep_id") or sf.parts[-3]

    line = as_num(d.get("line_coverage_pct"))
    branch = as_num(d.get("branch_coverage_pct"))
    mutation = as_num(d.get("mutation_score_pct"))

    row = {
        "dataset": d.get("dataset", "quixbugs_python"),
        "language": d.get("language", "python"),
        "model": d.get("model", "gpt-4o"),
        "sut_name": sut_name,
        "run_id": run_id,
        "rep_id": rep_id,
        "repeat": d.get("repeat", ""),
        "status": d.get("status", ""),
        "note": d.get("note", ""),

        "generation_exit_code": d.get("generation_exit_code", ""),
        "generation_attempts": d.get("generation_attempts", ""),
        "generation_empty_attempts": d.get("generation_empty_attempts", ""),
        "generation_final_attempt": d.get("generation_final_attempt", ""),

        "pytest_raw_exit_code": d.get("pytest_raw_exit_code", ""),
        "pytest_final_exit_code": d.get("pytest_final_exit_code", ""),
        "coverage_exit_code": d.get("coverage_exit_code", ""),
        "mutmut_exit_code": d.get("mutmut_exit_code", ""),

        "sanitized_used": d.get("sanitized_used", ""),
        "top_level_test_functions": d.get("top_level_test_functions", ""),
        "skipped_test_functions": d.get("skipped_test_functions", ""),
        "effective_test_functions": d.get("effective_test_functions", ""),
        "run_mutation": d.get("run_mutation", ""),

        "line_coverage_pct": "" if line is None else line,
        "branch_coverage_pct": "" if branch is None else branch,
        "mutation_score_pct": "" if mutation is None else mutation,

        "line_pct_penalized": penalized(line),
        "branch_pct_penalized": penalized(branch),
        "mutation_pct_penalized": penalized(mutation),

        "status_path": str(sf),
        "run_dir": d.get("run_dir", str(sf.parent.parent)),
    }
    rows.append(row)

fieldnames = [
    "dataset", "language", "model",
    "sut_name", "run_id", "rep_id", "repeat",
    "status", "note",

    "generation_exit_code",
    "generation_attempts",
    "generation_empty_attempts",
    "generation_final_attempt",

    "pytest_raw_exit_code",
    "pytest_final_exit_code",
    "coverage_exit_code",
    "mutmut_exit_code",

    "sanitized_used",
    "top_level_test_functions",
    "skipped_test_functions",
    "effective_test_functions",
    "run_mutation",

    "line_coverage_pct",
    "branch_coverage_pct",
    "mutation_score_pct",

    "line_pct_penalized",
    "branch_pct_penalized",
    "mutation_pct_penalized",

    "status_path",
    "run_dir",
]

runs_index = out_root / "dataset_runs_index.tsv"
with runs_index.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
    w.writeheader()
    for r in rows:
        w.writerow(r)

status_counts = Counter(r["status"] for r in rows)
suts = sorted(set(r["sut_name"] for r in rows))

by_sut = defaultdict(list)
for r in rows:
    by_sut[r["sut_name"]].append(r)

per_sut_rows = []
for sut in sorted(by_sut):
    rs = by_sut[sut]
    ok = sum(1 for r in rs if r["status"] == "ok")
    per_sut_rows.append({
        "sut_name": sut,
        "total_reps": len(rs),
        "ok_reps": ok,
        "failed_reps": len(rs) - ok,
        "statuses_json": json.dumps(dict(Counter(r["status"] for r in rs)), sort_keys=True),
        "line_penalized_mean": round(mean(float(r["line_pct_penalized"]) for r in rs), 4) if rs else 0.0,
        "branch_penalized_mean": round(mean(float(r["branch_pct_penalized"]) for r in rs), 4) if rs else 0.0,
        "mutation_penalized_mean": round(mean(float(r["mutation_pct_penalized"]) for r in rs), 4) if rs else 0.0,
        "effective_test_functions_mean": round(mean(float(r["effective_test_functions"] or 0) for r in rs), 4) if rs else 0.0,
    })

per_sut_path = out_root / "dataset_per_sut_summary.tsv"
with per_sut_path.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "sut_name",
        "total_reps",
        "ok_reps",
        "failed_reps",
        "statuses_json",
        "line_penalized_mean",
        "branch_penalized_mean",
        "mutation_penalized_mean",
        "effective_test_functions_mean",
    ]
    w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
    w.writeheader()
    for r in per_sut_rows:
        w.writerow(r)

total = len(rows)
ok_reps = status_counts.get("ok", 0)

summary = {
    "out_root": str(out_root),
    "total_status_files": total,
    "total_suts": len(suts),
    "ok_reps": ok_reps,
    "failed_reps": total - ok_reps,
    "status_counts": dict(sorted(status_counts.items())),
    "line_penalized_mean": round(mean(float(r["line_pct_penalized"]) for r in rows), 4) if rows else 0.0,
    "branch_penalized_mean": round(mean(float(r["branch_pct_penalized"]) for r in rows), 4) if rows else 0.0,
    "mutation_penalized_mean": round(mean(float(r["mutation_pct_penalized"]) for r in rows), 4) if rows else 0.0,
    "effective_test_functions_mean": round(mean(float(r["effective_test_functions"] or 0) for r in rows), 4) if rows else 0.0,
    "suts_5of5_ok": sum(1 for r in per_sut_rows if r["ok_reps"] == 5),
    "suts_0of5_ok": sum(1 for r in per_sut_rows if r["ok_reps"] == 0 and r["total_reps"] == 5),
    "generation_attempt_histogram": dict(sorted(Counter(str(r["generation_attempts"]) for r in rows).items())),
    "generation_empty_attempt_histogram": dict(sorted(Counter(str(r["generation_empty_attempts"]) for r in rows).items())),
}

summary_json = out_root / "dataset_summary.json"
summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

summary_tsv = out_root / "dataset_summary.tsv"
with summary_tsv.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "out_root",
        "total_status_files",
        "total_suts",
        "ok_reps",
        "failed_reps",
        "status_counts_json",
        "line_penalized_mean",
        "branch_penalized_mean",
        "mutation_penalized_mean",
        "effective_test_functions_mean",
        "suts_5of5_ok",
        "suts_0of5_ok",
        "generation_attempt_histogram_json",
        "generation_empty_attempt_histogram_json",
    ]
    w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
    w.writeheader()
    w.writerow({
        "out_root": summary["out_root"],
        "total_status_files": summary["total_status_files"],
        "total_suts": summary["total_suts"],
        "ok_reps": summary["ok_reps"],
        "failed_reps": summary["failed_reps"],
        "status_counts_json": json.dumps(summary["status_counts"], sort_keys=True),
        "line_penalized_mean": summary["line_penalized_mean"],
        "branch_penalized_mean": summary["branch_penalized_mean"],
        "mutation_penalized_mean": summary["mutation_penalized_mean"],
        "effective_test_functions_mean": summary["effective_test_functions_mean"],
        "suts_5of5_ok": summary["suts_5of5_ok"],
        "suts_0of5_ok": summary["suts_0of5_ok"],
        "generation_attempt_histogram_json": json.dumps(summary["generation_attempt_histogram"], sort_keys=True),
        "generation_empty_attempt_histogram_json": json.dumps(summary["generation_empty_attempt_histogram"], sort_keys=True),
    })

summary_txt = out_root / "dataset_summary.txt"
summary_txt.write_text(
    "\n".join([
        f"out_root={summary['out_root']}",
        f"total_status_files={summary['total_status_files']}",
        f"total_suts={summary['total_suts']}",
        f"ok_reps={summary['ok_reps']}",
        f"failed_reps={summary['failed_reps']}",
        f"status_counts={json.dumps(summary['status_counts'], sort_keys=True)}",
        f"line_penalized_mean={summary['line_penalized_mean']}",
        f"branch_penalized_mean={summary['branch_penalized_mean']}",
        f"mutation_penalized_mean={summary['mutation_penalized_mean']}",
        f"effective_test_functions_mean={summary['effective_test_functions_mean']}",
        f"suts_5of5_ok={summary['suts_5of5_ok']}",
        f"suts_0of5_ok={summary['suts_0of5_ok']}",
        f"generation_attempt_histogram={json.dumps(summary['generation_attempt_histogram'], sort_keys=True)}",
        f"generation_empty_attempt_histogram={json.dumps(summary['generation_empty_attempt_histogram'], sort_keys=True)}",
    ]) + "\n",
    encoding="utf-8",
)

print(f"WROTE {runs_index}")
print(f"WROTE {per_sut_path}")
print(f"WROTE {summary_tsv}")
print(f"WROTE {summary_json}")
print(f"WROTE {summary_txt}")
print(json.dumps(summary, indent=2, sort_keys=True))
