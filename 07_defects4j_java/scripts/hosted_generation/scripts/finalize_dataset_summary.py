#!/usr/bin/env python3
from __future__ import annotations
import json, statistics, sys
from pathlib import Path

def read_statuses(out_root: Path):
    for p in sorted(out_root.glob("*/run_*/[0-9]*-[0-9]*/metrics/status.json")):
        try:
            yield p, json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

def main() -> int:
    if len(sys.argv) != 2:
        print("usage: finalize_dataset_summary.py OUT_ROOT", file=sys.stderr)
        return 2
    out_root = Path(sys.argv[1]).resolve()
    rows = []
    line_vals = []
    branch_vals = []
    pit_vals = []
    summary_by_status = {}
    for path, st in read_statuses(out_root):
        status = st.get("final_status", "unknown")
        summary_by_status[status] = summary_by_status.get(status, 0) + 1
        rows.append((path, status))
        if isinstance(st.get("line_pct_penalized"), (int, float)): line_vals.append(float(st["line_pct_penalized"]))
        if isinstance(st.get("branch_pct_penalized"), (int, float)): branch_vals.append(float(st["branch_pct_penalized"]))
        if isinstance(st.get("pit_score_pct_penalized"), (int, float)): pit_vals.append(float(st["pit_score_pct_penalized"]))
    (out_root / "dataset_summary.tsv").write_text(
        "metric\tvalue\n" +
        f"repetitions\t{len(rows)}\n" +
        f"line_pct_penalized_mean\t{statistics.mean(line_vals) if line_vals else 0.0}\n" +
        f"branch_pct_penalized_mean\t{statistics.mean(branch_vals) if branch_vals else 0.0}\n" +
        f"pit_score_pct_penalized_mean\t{statistics.mean(pit_vals) if pit_vals else 0.0}\n",
        encoding="utf-8")
    (out_root / "dataset_summary.json").write_text(json.dumps({
        "repetitions": len(rows),
        "by_final_status": summary_by_status,
        "line_pct_penalized_mean": statistics.mean(line_vals) if line_vals else 0.0,
        "branch_pct_penalized_mean": statistics.mean(branch_vals) if branch_vals else 0.0,
        "pit_score_pct_penalized_mean": statistics.mean(pit_vals) if pit_vals else 0.0,
    }, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
