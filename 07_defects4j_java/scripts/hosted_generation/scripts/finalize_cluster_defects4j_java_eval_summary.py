#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

def as_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default

def main() -> int:
    if len(sys.argv) != 2:
        print("usage: finalize_cluster_defects4j_java_eval_summary.py OUT_ROOT", file=sys.stderr)
        return 2

    out_root = Path(sys.argv[1]).resolve()
    summaries = out_root / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)

    rows = []

    for status_path in sorted(out_root.glob("cluster-*/*/run_0001/*/metrics/status.json")):
        rel = status_path.relative_to(out_root)
        parts = rel.parts
        model = parts[0] if len(parts) > 0 else ""
        sut_id = parts[1] if len(parts) > 1 else ""

        try:
            data = json.loads(status_path.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            data = {"final_status": "bad_status_json", "json_error": str(e)}

        rep = data.get("rep", "")
        run_dir = str(status_path.parents[1])

        final_status = data.get("final_status") or data.get("status") or "unknown"

        line = as_float(
            data.get("line_pct_penalized",
            data.get("line_coverage_pct",
            data.get("line_pct", 0.0)))
        )
        branch = as_float(
            data.get("branch_pct_penalized",
            data.get("branch_coverage_pct",
            data.get("branch_pct", 0.0)))
        )
        pit = as_float(
            data.get("pit_score_pct_penalized",
            data.get("mutation_score_pct",
            data.get("pit_score_pct",
            data.get("mutation_score", 0.0))))
        )

        rows.append({
            "model": model,
            "sut_id": sut_id,
            "rep": str(rep),
            "final_status": str(final_status),
            "line_pct_penalized": f"{line:.6f}",
            "branch_pct_penalized": f"{branch:.6f}",
            "pit_score_pct_penalized": f"{pit:.6f}",
            "status_json": str(status_path),
            "run_dir": run_dir,
        })

    run_headers = [
        "model", "sut_id", "rep", "final_status",
        "line_pct_penalized", "branch_pct_penalized", "pit_score_pct_penalized",
        "status_json", "run_dir"
    ]

    runs_tsv = summaries / "cluster_defects4j_eval_runs.tsv"
    with runs_tsv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=run_headers, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)

    model_headers = [
        "model", "runs",
        "mean_line_pct_penalized",
        "mean_branch_pct_penalized",
        "mean_pit_score_pct_penalized",
        "ok_like_runs",
        "non_ok_runs",
        "status_counts"
    ]

    by_model_tsv = summaries / "cluster_defects4j_eval_by_model.tsv"
    by_model_json = summaries / "cluster_defects4j_eval_by_model.json"

    model_summary = []

    with by_model_tsv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=model_headers, delimiter="\t")
        w.writeheader()

        for model, rs in sorted(by_model.items()):
            statuses = Counter(r["final_status"] for r in rs)
            lines = [as_float(r["line_pct_penalized"]) for r in rs]
            branches = [as_float(r["branch_pct_penalized"]) for r in rs]
            pits = [as_float(r["pit_score_pct_penalized"]) for r in rs]

            ok_like = sum(v for k, v in statuses.items() if k in {"ok", "final_ok", "tests_ok", "success"})
            non_ok = len(rs) - ok_like

            row = {
                "model": model,
                "runs": len(rs),
                "mean_line_pct_penalized": round(statistics.mean(lines), 6) if lines else 0.0,
                "mean_branch_pct_penalized": round(statistics.mean(branches), 6) if branches else 0.0,
                "mean_pit_score_pct_penalized": round(statistics.mean(pits), 6) if pits else 0.0,
                "ok_like_runs": ok_like,
                "non_ok_runs": non_ok,
                "status_counts": json.dumps(dict(sorted(statuses.items())), sort_keys=True),
            }
            model_summary.append(row)
            w.writerow(row)

    by_model_json.write_text(json.dumps(model_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    status_counts = Counter(r["final_status"] for r in rows)
    status_tsv = summaries / "cluster_defects4j_eval_status_counts.tsv"
    with status_tsv.open("w", encoding="utf-8") as f:
        f.write("final_status\tcount\n")
        for k, v in sorted(status_counts.items()):
            f.write(f"{k}\t{v}\n")

    meta = summaries / "cluster_defects4j_eval_summary.txt"
    with meta.open("w", encoding="utf-8") as f:
        f.write(f"OUT_ROOT={out_root}\n")
        f.write(f"TOTAL_RUNS={len(rows)}\n")
        f.write(f"MODELS={len(by_model)}\n")
        f.write("\nSTATUS_COUNTS\n")
        for k, v in sorted(status_counts.items()):
            f.write(f"{k}\t{v}\n")
        f.write("\nFILES\n")
        f.write(f"runs_tsv={runs_tsv}\n")
        f.write(f"by_model_tsv={by_model_tsv}\n")
        f.write(f"by_model_json={by_model_json}\n")
        f.write(f"status_tsv={status_tsv}\n")

    print(meta.read_text(encoding="utf-8"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
