#!/usr/bin/env python3
import csv
from pathlib import Path
from collections import defaultdict

EXPECTED_SUTS = 378
EXPECTED_REPS = 1890
TOL = 0.03

FIG_DIR = Path.home() / "analysis_mbppplus" / "figures"

RAW_CSV = FIG_DIR / "mbppplus_repetition_level_extracted.csv"
RADAR_CSV = FIG_DIR / "mbppplus_radar_summary_with_official.csv"
STACKED_CSV = FIG_DIR / "mbppplus_stacked_3metrics_with_official_summary.csv"

OFFICIAL_TSV = Path("/home/jpaiva/projetos/nonAI/python_workflow/out/_official_mbppplus_tests_strict0_FINAL_V6_MERGED_20260610_110046/dataset_results.tsv")

METRICS_RAW = [
    ("line_coverage_pct", "line_coverage", "line_pct"),
    ("branch_coverage_pct", "branch_coverage", "branch_pct"),
    ("mutation_score_pct", "mutation_score", "mutation_pct"),
]

RADAR_METRICS = [
    "executable_suites_pct",
    "line_coverage_pct",
    "branch_coverage_pct",
    "mutation_score_pct",
]


def fnum(x):
    try:
        if x is None:
            return None
        s = str(x).strip().replace("%", "")
        if s == "":
            return None
        v = float(s)
        if 0 <= v <= 1:
            return v * 100.0
        return v
    except Exception:
        return None


def inum(x):
    try:
        return int(str(x).strip())
    except Exception:
        return 0


def load_csv(path, delimiter=","):
    with path.open(newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = []
        for row in reader:
            rows.append({(k or "").strip(): (v or "").strip() for k, v in row.items()})
        return rows


def close(a, b):
    a = fnum(a)
    b = fnum(b)
    if a is None or b is None:
        return False
    return abs(a - b) <= TOL


def check_value(name, got, expected, errors):
    if close(got, expected):
        print(f"[OK]  {name}: got={fnum(got):.4f} expected={expected:.4f}")
    else:
        print(f"[BAD] {name}: got={fnum(got)} expected={expected:.4f}")
        errors.append(name)


def compute_generated(raw_rows):
    by_approach = defaultdict(list)
    for r in raw_rows:
        by_approach[r["approach"]].append(r)

    out = {}

    for approach, rows in by_approach.items():
        item = {}
        exec_ok = sum(inum(r.get("exec_ok")) for r in rows)
        item["executable_suites_pct"] = 100.0 * exec_ok / EXPECTED_REPS

        for raw_key, prefix, _official_key in METRICS_RAW:
            all_values = []
            non_zero_values = []

            for r in rows:
                v = fnum(r.get(raw_key))
                if v is None:
                    all_values.append(0.0)
                else:
                    all_values.append(v)
                    if v > 0:
                        non_zero_values.append(v)

            while len(all_values) < EXPECTED_REPS:
                all_values.append(0.0)

            item[f"{prefix}_penalised_mean"] = sum(all_values) / EXPECTED_REPS
            item[f"{prefix}_non_penalised_mean"] = (
                sum(non_zero_values) / len(non_zero_values)
                if non_zero_values else 0.0
            )
            item[raw_key] = item[f"{prefix}_penalised_mean"]

        out[approach] = item

    return out


def compute_official():
    rows = load_csv(OFFICIAL_TSV, delimiter="\t")

    item = {}
    pytest_ok = sum(1 for r in rows if str(r.get("pytest_ok", "")).strip() == "1")
    item["executable_suites_pct"] = 100.0 * pytest_ok / EXPECTED_SUTS

    for raw_key, prefix, official_key in METRICS_RAW:
        all_values = []
        non_zero_values = []

        for r in rows:
            v = fnum(r.get(official_key))
            if v is None:
                all_values.append(0.0)
            else:
                all_values.append(v)
                if v > 0:
                    non_zero_values.append(v)

        while len(all_values) < EXPECTED_SUTS:
            all_values.append(0.0)

        item[f"{prefix}_penalised_mean"] = sum(all_values) / EXPECTED_SUTS
        item[f"{prefix}_non_penalised_mean"] = (
            sum(non_zero_values) / len(non_zero_values)
            if non_zero_values else 0.0
        )
        item[raw_key] = item[f"{prefix}_penalised_mean"]

    return item


def main():
    errors = []

    print("===== FILE CHECK =====")
    for p in [RAW_CSV, RADAR_CSV, STACKED_CSV, OFFICIAL_TSV]:
        if p.exists():
            print(f"[OK] {p}")
        else:
            print(f"[MISSING] {p}")
            errors.append(str(p))

    if errors:
        raise SystemExit("[FAIL] Missing files.")

    raw_rows = load_csv(RAW_CSV)
    radar_rows = load_csv(RADAR_CSV)
    stacked_rows = load_csv(STACKED_CSV)

    print()
    print("===== RAW ROW COUNTS =====")
    by_approach = defaultdict(int)
    for r in raw_rows:
        by_approach[r["approach"]] += 1

    for approach, n in sorted(by_approach.items()):
        status = "OK" if n == EXPECTED_REPS else "BAD"
        print(f"[{status}] {approach}: rows={n}")

    official = compute_official()
    generated = compute_generated(raw_rows)
    generated["Official dataset tests"] = official

    print()
    print("===== VALIDATE STACKED CSV =====")
    for r in stacked_rows:
        approach = r["approach"]
        label = r["label"]
        expected = generated.get(approach)

        if expected is None:
            print(f"[BAD] Missing expected data for {approach}")
            errors.append(approach)
            continue

        for _raw_key, prefix, _official_key in METRICS_RAW:
            check_value(
                f"{label} / {prefix} penalised",
                r.get(f"{prefix}_penalised_mean"),
                expected[f"{prefix}_penalised_mean"],
                errors,
            )
            check_value(
                f"{label} / {prefix} non-penalised",
                r.get(f"{prefix}_non_penalised_mean"),
                expected[f"{prefix}_non_penalised_mean"],
                errors,
            )

    print()
    print("===== VALIDATE RADAR CSV =====")
    for r in radar_rows:
        approach = r["approach"]
        label = r["label"]
        expected = generated.get(approach)

        if expected is None:
            print(f"[BAD] Missing expected radar data for {approach}")
            errors.append(approach)
            continue

        for metric in RADAR_METRICS:
            check_value(
                f"{label} / radar {metric}",
                r.get(metric),
                expected[metric],
                errors,
            )

    print()
    print("===== FORMULA CONFIRMATION =====")
    print("Penalised mean: sum(metric values, missing/zero kept as 0) / expected total")
    print("Non-penalised mean: average only metric values > 0")
    print("Generated tools denominator:", EXPECTED_REPS)
    print("Dataset tests denominator:", EXPECTED_SUTS)

    print()
    if errors:
        print(f"[FAIL] Validation found {len(errors)} issue(s).")
        raise SystemExit(1)

    print("[OK] All MBPP+ penalised and non-penalised calculations match the requested formulas.")


if __name__ == "__main__":
    main()
