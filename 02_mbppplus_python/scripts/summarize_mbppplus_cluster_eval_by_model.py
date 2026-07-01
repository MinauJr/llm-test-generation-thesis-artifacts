#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path
from collections import defaultdict, Counter


def fnum(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def inum(x):
    try:
        return int(x)
    except Exception:
        return 0


def bval(x):
    if isinstance(x, bool):
        return x
    return str(x).lower() in {"1", "true", "yes"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", required=True)
    args = ap.parse_args()

    out = Path(args.out_root).resolve()
    index = out / "dataset_runs_index.tsv"

    if not index.is_file():
        raise SystemExit(f"Missing dataset_runs_index.tsv: {index}")

    rows = []
    with index.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows.append(r)

    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)

    out_tsv = out / "dataset_summary_by_model.tsv"
    out_txt = out / "dataset_summary_by_model.txt"

    fields = [
        "model",
        "evaluated_repetitions",
        "distinct_suts",
        "ok_local",
        "cluster_generation_non_ok",
        "pytest_final_failed",
        "coverage_failed",
        "mutation_run_failed",
        "sanitized_repetitions",
        "line_coverage_mean_pct_strict0",
        "branch_coverage_mean_pct_strict0",
        "mutation_score_mean_pct_strict0",
        "cluster_status_counts",
        "local_status_counts",
    ]

    summary_rows = []

    for model, rs in sorted(by_model.items()):
        local_counts = Counter(r.get("status", "") for r in rs)
        cluster_counts = Counter(r.get("cluster_generation_status", "") for r in rs)
        n = len(rs)

        summary_rows.append({
            "model": model,
            "evaluated_repetitions": n,
            "distinct_suts": len({r.get("sut_id", "") for r in rs}),
            "ok_local": local_counts.get("ok", 0),
            "cluster_generation_non_ok": local_counts.get("cluster_generation_non_ok", 0),
            "pytest_final_failed": sum(1 for r in rs if inum(r.get("pytest_final_exit_code")) != 0 and r.get("status") != "cluster_generation_non_ok"),
            "coverage_failed": sum(1 for r in rs if inum(r.get("coverage_exit_code")) != 0 and r.get("status") != "cluster_generation_non_ok"),
            "mutation_run_failed": sum(1 for r in rs if inum(r.get("mutation_exit_code")) != 0 and r.get("status") != "cluster_generation_non_ok"),
            "sanitized_repetitions": sum(1 for r in rs if bval(r.get("sanitized"))),
            "line_coverage_mean_pct_strict0": round(sum(fnum(r.get("line_coverage_pct")) for r in rs) / n, 6) if n else 0.0,
            "branch_coverage_mean_pct_strict0": round(sum(fnum(r.get("branch_coverage_pct")) for r in rs) / n, 6) if n else 0.0,
            "mutation_score_mean_pct_strict0": round(sum(fnum(r.get("mutation_score_pct")) for r in rs) / n, 6) if n else 0.0,
            "cluster_status_counts": dict(cluster_counts),
            "local_status_counts": dict(local_counts),
        })

    with out_tsv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fields, delimiter="\t")
        w.writeheader()
        w.writerows(summary_rows)

    with out_txt.open("w", encoding="utf-8") as f:
        f.write("===== MBPP+ CLUSTER-GENERATED LOCAL EVALUATION — SUMMARY BY MODEL =====\n")
        for r in summary_rows:
            f.write("\n")
            for k in fields:
                f.write(f"{k}: {r[k]}\n")

    print("WROTE:", out_tsv)
    print("WROTE:", out_txt)
    print()
    for r in summary_rows:
        print(
            r["model"],
            "line=", r["line_coverage_mean_pct_strict0"],
            "branch=", r["branch_coverage_mean_pct_strict0"],
            "mutation=", r["mutation_score_mean_pct_strict0"],
            "local_status=", r["local_status_counts"],
        )


if __name__ == "__main__":
    main()
