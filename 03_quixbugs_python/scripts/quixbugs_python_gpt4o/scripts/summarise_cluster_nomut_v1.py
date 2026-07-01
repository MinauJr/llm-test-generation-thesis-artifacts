#!/usr/bin/env python3

import argparse
import collections
import csv
import json
from pathlib import Path
from statistics import mean


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def as_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


parser = argparse.ArgumentParser()
parser.add_argument("--full-root", required=True)
parser.add_argument("--cluster-root", required=True)
parser.add_argument("--sut-root", required=True)
parser.add_argument("--models-file", required=True)
args = parser.parse_args()

full_root = Path(args.full_root).resolve()
cluster_root = Path(args.cluster_root).resolve()
sut_root = Path(args.sut_root).resolve()
models_file = Path(args.models_file).resolve()

summary_root = full_root / "_summaries"
summary_root.mkdir(parents=True, exist_ok=True)

models = [
    line.strip()
    for line in models_file.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

suts = sorted(
    p.name
    for p in sut_root.iterdir()
    if p.is_dir()
    and len(p.name) >= 12
    and p.name[:3].isdigit()
    and "_python_" in p.name
)

records = []
status_counts = collections.Counter()
model_status_counts = collections.Counter()

for model in models:
    for sut in suts:
        for rep in range(1, 6):
            eval_status_path = (
                full_root
                / model
                / sut
                / "run_0001"
                / f"1-{rep}"
                / "metrics"
                / "status.json"
            )

            source_status_path = (
                cluster_root
                / model
                / sut
                / f"rep_{rep:02d}"
                / "status.json"
            )

            eval_status = read_json(eval_status_path)
            source_status = read_json(source_status_path)

            if eval_status_path.is_file():
                status = eval_status.get("status", "UNKNOWN")
            else:
                status = "missing_status"

            line = as_float(eval_status.get("line_coverage_pct"))
            branch = as_float(eval_status.get("branch_coverage_pct"))

            valid = (
                status == "ok"
                and line is not None
                and branch is not None
            )

            line_strict = line if valid else 0.0
            branch_strict = branch if valid else 0.0

            status_counts[status] += 1
            model_status_counts[(model, status)] += 1

            records.append({
                "model": model,
                "sut_name": sut,
                "repeat": rep,
                "source_cluster_status": source_status.get(
                    "status",
                    "missing_source_status",
                ),
                "eval_status": status,
                "valid_metrics": valid,
                "line_coverage_pct": (
                    "" if line is None else line
                ),
                "branch_coverage_pct": (
                    "" if branch is None else branch
                ),
                "line_coverage_strict_zero_pct": line_strict,
                "branch_coverage_strict_zero_pct": branch_strict,
                "status_json": str(eval_status_path),
                "source_status_json": str(source_status_path),
            })

fields = [
    "model",
    "sut_name",
    "repeat",
    "source_cluster_status",
    "eval_status",
    "valid_metrics",
    "line_coverage_pct",
    "branch_coverage_pct",
    "line_coverage_strict_zero_pct",
    "branch_coverage_strict_zero_pct",
    "status_json",
    "source_status_json",
]

with (summary_root / "dataset_runs_index.tsv").open(
    "w",
    encoding="utf-8",
    newline="",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=fields,
        delimiter="\t",
    )
    writer.writeheader()
    writer.writerows(records)

with (summary_root / "status_counts.tsv").open(
    "w",
    encoding="utf-8",
) as handle:
    handle.write("status\tcount\n")
    for status, count in sorted(status_counts.items()):
        handle.write(f"{status}\t{count}\n")

with (summary_root / "status_counts_by_model.tsv").open(
    "w",
    encoding="utf-8",
) as handle:
    handle.write("model\tstatus\tcount\n")
    for (model, status), count in sorted(
        model_status_counts.items()
    ):
        handle.write(f"{model}\t{status}\t{count}\n")

model_rows = []

for model in models:
    group = [
        row
        for row in records
        if row["model"] == model
    ]

    observed = sum(
        row["eval_status"] != "missing_status"
        for row in group
    )

    ok = sum(
        row["valid_metrics"]
        for row in group
    )

    line_strict = mean(
        row["line_coverage_strict_zero_pct"]
        for row in group
    ) if group else 0.0

    branch_strict = mean(
        row["branch_coverage_strict_zero_pct"]
        for row in group
    ) if group else 0.0

    model_rows.append({
        "model": model,
        "expected": len(suts) * 5,
        "observed": observed,
        "ok_metrics": ok,
        "line_strict_zero_mean": round(line_strict, 4),
        "branch_strict_zero_mean": round(branch_strict, 4),
    })

with (summary_root / "model_summary.tsv").open(
    "w",
    encoding="utf-8",
    newline="",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "model",
            "expected",
            "observed",
            "ok_metrics",
            "line_strict_zero_mean",
            "branch_strict_zero_mean",
        ],
        delimiter="\t",
    )
    writer.writeheader()
    writer.writerows(model_rows)

expected_total = len(models) * len(suts) * 5
observed_total = sum(
    row["eval_status"] != "missing_status"
    for row in records
)
ok_total = sum(row["valid_metrics"] for row in records)

line_total = mean(
    row["line_coverage_strict_zero_pct"]
    for row in records
) if records else 0.0

branch_total = mean(
    row["branch_coverage_strict_zero_pct"]
    for row in records
) if records else 0.0

with (summary_root / "latest_summary.txt").open(
    "w",
    encoding="utf-8",
) as handle:
    handle.write(f"expected_total={expected_total}\n")
    handle.write(f"observed_total={observed_total}\n")
    handle.write(f"missing_total={expected_total - observed_total}\n")
    handle.write(f"ok_metrics_total={ok_total}\n")
    handle.write(
        f"line_strict_zero_mean={line_total:.4f}\n"
    )
    handle.write(
        f"branch_strict_zero_mean={branch_total:.4f}\n"
    )
    handle.write(
        "status_counts="
        + json.dumps(dict(sorted(status_counts.items())))
        + "\n"
    )

    for row in model_rows:
        handle.write(
            f"{row['model']}\t"
            f"observed={row['observed']}/{row['expected']}\t"
            f"ok={row['ok_metrics']}\t"
            f"line_strict0={row['line_strict_zero_mean']}\t"
            f"branch_strict0={row['branch_strict_zero_mean']}\n"
        )

print(summary_root / "latest_summary.txt")
