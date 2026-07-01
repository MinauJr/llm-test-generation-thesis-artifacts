#!/usr/bin/env python3
import csv
from pathlib import Path

FIG_DIR = Path.home() / "analysis_humanevalplus" / "figures"
RAW = FIG_DIR / "humanevalplus_repetition_level_extracted.csv"
SUMMARY = FIG_DIR / "humanevalplus_approach_summary_strict0.csv"
EXPECTED = 820
TOL = 0.01

METRICS = [
    "executable_suites_pct",
    "line_coverage_pct",
    "branch_coverage_pct",
    "mutation_score_pct",
]

def f(x):
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None

def load_csv(path):
    with path.open(newline="") as fp:
        return list(csv.DictReader(fp))

raw = load_csv(RAW)
summary = load_csv(SUMMARY)

print("===== VALIDATE FILES =====")
print(f"RAW={RAW}")
print(f"SUMMARY={SUMMARY}")
print(f"raw rows={len(raw)}")
print(f"summary rows={len(summary)}")

print("\n===== CHECK RAW SOURCE PATHS EXIST =====")
missing_dirs = 0
missing_status = 0

for r in raw:
    d = Path(r["source_metrics_dir"])
    if not d.exists():
        missing_dirs += 1
    if not (d / "status.json").exists():
        missing_status += 1

print(f"missing metrics dirs: {missing_dirs}")
print(f"missing status.json:  {missing_status}")

groups = {}
for r in raw:
    key = (r["dataset"], r["group"], r["approach"])
    groups.setdefault(key, []).append(r)

recomputed = {}

for key, rows in groups.items():
    dataset, group, approach = key

    exec_ok = sum(int(r["exec_ok"]) for r in rows)
    line_sum = sum(f(r["line_coverage_pct"]) or 0.0 for r in rows)
    branch_sum = sum(f(r["branch_coverage_pct"]) or 0.0 for r in rows)
    mut_sum = sum(f(r["mutation_score_pct"]) or 0.0 for r in rows)

    recomputed[key] = {
        "rows_found": len(rows),
        "exec_ok_reps": exec_ok,
        "executable_suites_pct": 100.0 * exec_ok / EXPECTED,
        "line_coverage_pct": line_sum / EXPECTED,
        "branch_coverage_pct": branch_sum / EXPECTED,
        "mutation_score_pct": mut_sum / EXPECTED,
    }

print("\n===== COMPARE RECOMPUTED RAW CSV VS SUMMARY CSV =====")

all_ok = True

for s in summary:
    key = (s["dataset"], s["group"], s["approach"])
    r = recomputed.get(key)

    if r is None:
        print(f"[MISSING IN RAW] {key}")
        all_ok = False
        continue

    label = f"{s['group']} / {s['approach']}"
    print(f"\n{label}")

    for field in ["rows_found", "exec_ok_reps"] + METRICS:
        a = f(s[field])
        b = f(r[field])
        diff = abs(a - b)

        status = "OK" if diff <= TOL else "DIFF"
        if status != "OK":
            all_ok = False

        print(f"  {field:24s} summary={a:8.2f} recomputed={b:8.2f} diff={diff:8.4f} [{status}]")

print("\n===== RESULT =====")
if all_ok and missing_dirs == 0 and missing_status == 0:
    print("[OK] O CSV usado pelo gráfico bate com os dados por repetição e os caminhos reais existem.")
else:
    print("[CHECK] Há diferenças ou caminhos em falta. Rever antes de usar na tese.")
