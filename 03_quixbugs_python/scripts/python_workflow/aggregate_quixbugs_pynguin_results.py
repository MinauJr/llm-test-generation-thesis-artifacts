from __future__ import annotations
from pathlib import Path
import json
import statistics as stats
import sys

root = Path(sys.argv[1]).resolve()
out = root / "dataset_aggregate"
out.mkdir(parents=True, exist_ok=True)

sut_dirs = sorted([p for p in root.iterdir() if p.is_dir() and "_python_" in p.name])

rows = []
reason_counts = {}
suts_0_of_5 = []

def classify_reason(status: dict) -> str:
    note = (status.get("note") or "").lower()
    gen = status.get("generate_exit_code")
    pr = status.get("pytest_exit_code_raw")
    pf = status.get("pytest_exit_code_final")
    cov = status.get("coverage_exit_code")
    mut = status.get("mutation_exit_code")

    if gen not in (None, 0):
        if "nothing we can test" in note or "not testable" in note:
            return "not_testable"
        return "generation_failed"
    if pr == 124 or pf == 124 or "timeout" in note:
        return "timeout"
    if pr not in (None, 0):
        return "pytest_raw_failed"
    if pf not in (None, 0):
        return "pytest_final_failed"
    if cov not in (None, 0):
        return "coverage_failed"
    if mut not in (None, 0):
        return "mutation_failed"
    return "ok"

all_line = []
all_branch = []
all_mut = []

reps_total = 0
gen_fail_reps = 0
pytest_final_fail_reps = 0
sanitized_reps = 0
coverage_missing_reps = 0
mutation_missing_reps = 0

for sut in sut_dirs:
    run_dirs = sorted([p for p in sut.glob("run_*") if p.is_dir()])
    statuses = []
    for run_dir in run_dirs:
        for status_file in sorted(run_dir.glob("*-*/metrics/status.json")):
            try:
                status = json.loads(status_file.read_text())
            except Exception:
                continue
            statuses.append((status_file, status))

    if not statuses:
        suts_0_of_5.append(sut.name)
        continue

    closed = 0
    for status_file, status in statuses:
        reps_total += 1

        gen = status.get("generate_exit_code")
        pf = status.get("pytest_exit_code_final")
        sanitized = bool(status.get("sanitized"))
        cov = status.get("coverage")
        mut = status.get("mutation")

        if gen not in (None, 0):
            gen_fail_reps += 1
        if pf not in (None, 0):
            pytest_final_fail_reps += 1
        if sanitized:
            sanitized_reps += 1
        if not cov:
            coverage_missing_reps += 1
        if not mut:
            mutation_missing_reps += 1

        line = float(cov["line_pct"]) if cov and cov.get("line_pct") is not None else 0.0
        branch = float(cov["branch_pct"]) if cov and cov.get("branch_pct") is not None else 0.0
        mpct = float(mut["mutation_pct"]) if mut and mut.get("mutation_pct") is not None else 0.0

        all_line.append(line)
        all_branch.append(branch)
        all_mut.append(mpct)

        reason = classify_reason(status)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        if gen == 0 and (pf == 0):
            closed += 1

        rows.append({
            "sut": sut.name,
            "run_status": str(status_file),
            "run_id": status.get("run_id"),
            "seed": status.get("seed"),
            "generate_exit_code": gen,
            "pytest_exit_code_raw": status.get("pytest_exit_code_raw"),
            "pytest_exit_code_final": pf,
            "coverage_exit_code": status.get("coverage_exit_code"),
            "mutation_exit_code": status.get("mutation_exit_code"),
            "sanitized": sanitized,
            "line_pct_penalized": line,
            "branch_pct_penalized": branch,
            "mutation_pct_penalized": mpct,
            "reason": reason,
            "note": status.get("note") or "",
        })

    if closed == 0:
        suts_0_of_5.append(sut.name)

summary = {
    "dataset_root": str(root),
    "suts_total": len(sut_dirs),
    "reps_total": reps_total,
    "gen_fail_reps": gen_fail_reps,
    "pytest_final_fail_reps": pytest_final_fail_reps,
    "sanitized_reps": sanitized_reps,
    "coverage_missing_reps": coverage_missing_reps,
    "mutation_missing_reps": mutation_missing_reps,
    "mean_line_penalized": round(stats.mean(all_line), 2) if all_line else 0.0,
    "mean_branch_penalized": round(stats.mean(all_branch), 2) if all_branch else 0.0,
    "mean_mutation_penalized": round(stats.mean(all_mut), 2) if all_mut else 0.0,
    "reason_counts": reason_counts,
    "suts_0_of_5_count": len(suts_0_of_5),
}

(out / "dataset_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

with (out / "dataset_summary.txt").open("w", encoding="utf-8") as f:
    f.write(f"DATASET ROOT: {root}\n")
    f.write(f"SUTS_TOTAL: {summary['suts_total']}\n")
    f.write(f"REPS_TOTAL: {summary['reps_total']}\n")
    f.write(f"GEN_FAIL_REPS: {summary['gen_fail_reps']}\n")
    f.write(f"PYTEST_FINAL_FAIL_REPS: {summary['pytest_final_fail_reps']}\n")
    f.write(f"SANITIZED_REPS: {summary['sanitized_reps']}\n")
    f.write(f"COVERAGE_MISSING_REPS: {summary['coverage_missing_reps']}\n")
    f.write(f"MUTATION_MISSING_REPS: {summary['mutation_missing_reps']}\n")
    f.write(f"MEAN_LINE_PENALIZED: {summary['mean_line_penalized']}\n")
    f.write(f"MEAN_BRANCH_PENALIZED: {summary['mean_branch_penalized']}\n")
    f.write(f"MEAN_MUTATION_PENALIZED: {summary['mean_mutation_penalized']}\n")
    f.write("\nREASON_COUNTS:\n")
    for k, v in sorted(reason_counts.items()):
        f.write(f"  {k}: {v}\n")
    f.write("\nSUTS_0_OF_5:\n")
    for s in suts_0_of_5:
        f.write(f"  {s}\n")

(out / "suts_0_of_5.txt").write_text("\n".join(suts_0_of_5) + ("\n" if suts_0_of_5 else ""))

with (out / "reps_detailed.tsv").open("w", encoding="utf-8") as f:
    headers = [
        "sut","run_id","seed","generate_exit_code","pytest_exit_code_raw","pytest_exit_code_final",
        "coverage_exit_code","mutation_exit_code","sanitized",
        "line_pct_penalized","branch_pct_penalized","mutation_pct_penalized",
        "reason","note","run_status"
    ]
    f.write("\t".join(headers) + "\n")
    for r in rows:
        f.write("\t".join(str(r[h]).replace("\t"," ").replace("\n"," ") for h in headers) + "\n")

print("OK")
print(out)
