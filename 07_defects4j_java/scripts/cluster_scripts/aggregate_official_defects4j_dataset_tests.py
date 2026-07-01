#!/usr/bin/env python3
import csv
import json
import statistics
import sys
from pathlib import Path
from collections import Counter

if len(sys.argv) != 3:
    print("usage: aggregate_official_defects4j_dataset_tests.py OUT_BASE EXPECTED_SUTS_FILE", file=sys.stderr)
    sys.exit(2)

out = Path(sys.argv[1])
expected_file = Path(sys.argv[2])

expected = [x.strip() for x in expected_file.read_text(encoding="utf-8").splitlines() if x.strip()]
expected_ids = [Path(x).name for x in expected]

rows = []
missing = []

for sid in expected_ids:
    p = out / sid / "run_0001" / "metrics" / "status.json"
    if not p.exists():
        missing.append(sid)
        rows.append({
            "sut_id": sid,
            "status": "missing_status",
            "ok": False,
            "line_pct": None,
            "branch_pct": None,
            "mutation_score_pct": None,
            "warnings": ["missing_status"],
        })
        continue
    data = json.loads(p.read_text(encoding="utf-8"))
    rows.append(data)

def fval(row, key):
    v = row.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None

def mean_available(key):
    vals = [fval(r, key) for r in rows if fval(r, key) is not None]
    return statistics.mean(vals) if vals else None

def mean_strict0(key):
    vals = [(fval(r, key) if fval(r, key) is not None else 0.0) for r in rows]
    return statistics.mean(vals) if vals else None

status_counts = Counter(r.get("status", "unknown") for r in rows)

zero_rows = []
warning_rows = []
for r in rows:
    sid = r.get("sut_id")
    for key in ["line_pct", "branch_pct", "mutation_score_pct"]:
        v = fval(r, key)
        if v == 0.0:
            zero_rows.append((sid, key, v, r.get("status")))
    for w in r.get("warnings", []) or []:
        warning_rows.append((sid, w, r.get("status")))

summary = {
    "dataset": "Defects4J official/original relevant tests",
    "suts_expected": len(expected_ids),
    "suts_with_status": len(rows) - len(missing),
    "suts_missing_status": len(missing),
    "suts_valid_ok": sum(1 for r in rows if r.get("status") == "ok"),
    "suts_non_ok": sum(1 for r in rows if r.get("status") != "ok"),
    "status_counts": dict(status_counts),
    "line_metric_available": sum(1 for r in rows if fval(r, "line_pct") is not None),
    "branch_metric_available": sum(1 for r in rows if fval(r, "branch_pct") is not None),
    "mutation_metric_available": sum(1 for r in rows if fval(r, "mutation_score_pct") is not None),
    "line_coverage_mean_available": mean_available("line_pct"),
    "branch_coverage_mean_available": mean_available("branch_pct"),
    "mutation_score_mean_available": mean_available("mutation_score_pct"),
    "line_coverage_mean_strict0": mean_strict0("line_pct"),
    "branch_coverage_mean_strict0": mean_strict0("branch_pct"),
    "mutation_score_mean_strict0": mean_strict0("mutation_score_pct"),
    "zero_metric_count": len(zero_rows),
    "warning_count": len(warning_rows),
}

(out / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

with (out / "dataset_runs_index.tsv").open("w", encoding="utf-8", newline="") as fh:
    fieldnames = [
        "sut_id", "status", "ok",
        "line_pct", "branch_pct", "mutation_score_pct",
        "total_mutants", "killed_mutants",
        "warnings", "status_json"
    ]
    wr = csv.DictWriter(fh, delimiter="\t", fieldnames=fieldnames)
    wr.writeheader()
    for r in rows:
        sid = r.get("sut_id")
        wr.writerow({
            "sut_id": sid,
            "status": r.get("status"),
            "ok": r.get("ok"),
            "line_pct": r.get("line_pct"),
            "branch_pct": r.get("branch_pct"),
            "mutation_score_pct": r.get("mutation_score_pct"),
            "total_mutants": r.get("total_mutants"),
            "killed_mutants": r.get("killed_mutants"),
            "warnings": ",".join(r.get("warnings", []) or []),
            "status_json": str(out / sid / "run_0001" / "metrics" / "status.json"),
        })

with (out / "zero_metrics.tsv").open("w", encoding="utf-8") as fh:
    fh.write("sut_id\tmetric\tvalue\tstatus\n")
    for row in zero_rows:
        fh.write("\t".join(map(str, row)) + "\n")

with (out / "warnings.tsv").open("w", encoding="utf-8") as fh:
    fh.write("sut_id\twarning\tstatus\n")
    for row in warning_rows:
        fh.write("\t".join(map(str, row)) + "\n")

lines = []
lines.append("Defects4J official/original relevant dataset tests")
lines.append("")
for k, v in summary.items():
    if isinstance(v, float):
        lines.append(f"{k} = {v:.4f}")
    else:
        lines.append(f"{k} = {v}")
lines.append("")
lines.append("status_counts:")
for k, v in sorted(status_counts.items()):
    lines.append(f"  {k}: {v}")
lines.append("")
lines.append("zero_metrics:")
if zero_rows:
    for z in zero_rows:
        lines.append(f"  {z[0]} {z[1]}={z[2]} status={z[3]}")
else:
    lines.append("  none")
lines.append("")
lines.append("warnings:")
if warning_rows:
    for w in warning_rows:
        lines.append(f"  {w[0]} {w[1]} status={w[2]}")
else:
    lines.append("  none")

(out / "dataset_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
