#!/usr/bin/env python3
import csv
import json
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


EXPECTED_REPS = 820

OUT_DIR = Path.home() / "analysis_humanevalplus" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RUNS_FIXED = [
    {
        "dataset": "HumanEval+",
        "group": "Non-AI",
        "approach": "Pynguin",
        "root": Path("/home/jpaiva/projetos/nonAI/python_workflow/out/pynguin_humanevalplus_strict0"),
        "expected": EXPECTED_REPS,
    },
    {
        "dataset": "HumanEval+",
        "group": "IAEdu",
        "approach": "GPT-4o",
        "root": Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_final_gpt4o_humanevalplus_python_v3_retryempty"),
        "expected": EXPECTED_REPS,
    },
    {
        "dataset": "HumanEval+",
        "group": "IAEdu",
        "approach": "GPT-5.5",
        "root": Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_final_gpt55_humanevalplus_python_v1"),
        "expected": EXPECTED_REPS,
    },
    {
        "dataset": "HumanEval+",
        "group": "IAEdu",
        "approach": "Claude Opus 4.7",
        "root": Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_final_claude47_humanevalplus_python_v1"),
        "expected": EXPECTED_REPS,
    },
]

CLUSTER_EVAL_ALL = Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_cluster_humanevalplus_v4_eval_all")
CLUSTER_STRUCTFIX = Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_cluster_humanevalplus_v4_eval_structfix")


def as_float(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return None
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace("%", "")
        if not s or s.lower() in {"none", "null", "nan", "na", "n/a"}:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def normalise_pct(value):
    v = as_float(value)
    if v is None:
        return None
    if 0 <= v <= 1:
        return v * 100.0
    return v


def read_text_float(path):
    try:
        return normalise_pct(path.read_text(errors="replace").strip().splitlines()[0])
    except Exception:
        return None


def read_json(path):
    try:
        return json.loads(path.read_text(errors="replace"))
    except Exception:
        return {}


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}.{i}" if prefix else str(i)
            out.update(flatten(v, key))
    else:
        out[prefix] = obj
    return out


def find_flat_pct(flat, patterns):
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for k, v in flat.items():
            if rx.search(k):
                value = normalise_pct(v)
                if value is not None:
                    return value
    return None


def find_flat_int(flat, patterns):
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for k, v in flat.items():
            if rx.search(k):
                try:
                    return int(v)
                except Exception:
                    pass
    return None


def collect_metric_dirs(root):
    metric_dirs = set()

    if not root.exists():
        return []

    for p in root.rglob("metrics"):
        if p.is_dir():
            metric_dirs.add(p)

    for fname in [
        "status.json",
        "line_coverage_pct.txt",
        "branch_coverage_pct.txt",
        "mutation_score_pct.txt",
    ]:
        for p in root.rglob(fname):
            if p.parent.name == "metrics":
                metric_dirs.add(p.parent)

    return sorted(metric_dirs)


def infer_sut_rep(metric_dir):
    sut = ""
    rep = ""

    for part in metric_dir.parts:
        if re.fullmatch(r"HumanEval_\d+", part):
            sut = part
        if re.fullmatch(r"run_\d+", part):
            rep = part

    return sut, rep


def metric_from_files_or_status(metric_dir, flat, metric_name):
    file_map = {
        "line": "line_coverage_pct.txt",
        "branch": "branch_coverage_pct.txt",
        "mutation": "mutation_score_pct.txt",
    }

    value = read_text_float(metric_dir / file_map[metric_name])
    if value is not None:
        return value

    patterns = {
        "line": [
            r"line.*coverage",
            r"line.*pct",
            r"line_pct",
            r"line_coverage_pct",
        ],
        "branch": [
            r"branch.*coverage",
            r"branch.*pct",
            r"branch_pct",
            r"branch_coverage_pct",
        ],
        "mutation": [
            r"mutation\.mutation_pct$",
            r"mutation_pct$",
            r"mutation_score_pct$",
            r"mutmut.*score",
        ],
    }

    return find_flat_pct(flat, patterns[metric_name])


def exit_code_from_file_or_status(metric_dir, flat, name):
    file_value = metric_dir / f"{name}.txt"
    if file_value.exists():
        try:
            return int(file_value.read_text(errors="replace").strip().splitlines()[0])
        except Exception:
            pass

    return find_flat_int(flat, [rf"{re.escape(name)}", rf"{name.replace('_', '.*')}"])


def determine_exec_ok(metric_dir, flat, line, branch, mutation):
    pytest_final = exit_code_from_file_or_status(metric_dir, flat, "pytest_final_exit_code")
    if pytest_final is None:
        pytest_final = exit_code_from_file_or_status(metric_dir, flat, "pytest_exit_code_final")
    sanitized_compile = exit_code_from_file_or_status(metric_dir, flat, "sanitized_test_compile_exit_code")
    generated_compile = exit_code_from_file_or_status(metric_dir, flat, "generated_test_compile_exit_code")
    import_exit = exit_code_from_file_or_status(metric_dir, flat, "import_exit_code")

    if pytest_final == 0:
        return 1

    status_candidates = []
    for k, v in flat.items():
        lk = k.lower()
        if lk.endswith("status") or lk.endswith("outcome") or lk.endswith("result"):
            status_candidates.append(str(v).lower())

    joined = " ".join(status_candidates)
    if any(x in joined for x in ["ok", "success", "passed", "pass"]):
        return 1

    if pytest_final is None and (line is not None or branch is not None or mutation is not None):
        return 1

    return 0


def extract_rows_for_run(dataset, group, approach, root):
    rows = []

    metric_dirs = collect_metric_dirs(root)

    for metric_dir in metric_dirs:
        status = read_json(metric_dir / "status.json")
        flat = flatten(status)

        line = metric_from_files_or_status(metric_dir, flat, "line")
        branch = metric_from_files_or_status(metric_dir, flat, "branch")
        mutation = metric_from_files_or_status(metric_dir, flat, "mutation")

        exec_ok = determine_exec_ok(metric_dir, flat, line, branch, mutation)
        sut, rep = infer_sut_rep(metric_dir)

        rows.append({
            "dataset": dataset,
            "group": group,
            "approach": approach,
            "sut": sut,
            "rep": rep,
            "exec_ok": exec_ok,
            "line_coverage_pct": line,
            "branch_coverage_pct": branch,
            "mutation_score_pct": mutation,
            "source_metrics_dir": str(metric_dir),
        })

    return rows


def is_structfix_model(model_name):
    s = model_name.lower().replace("_", "-")
    if "codellama" in s:
        return True
    if "deepseek-v2" in s and "coder" not in s:
        return True
    return False


def cluster_model_dirs(root):
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")])


def extract_cluster_rows():
    rows = []

    for model_dir in cluster_model_dirs(CLUSTER_EVAL_ALL):
        if is_structfix_model(model_dir.name):
            print(f"[SKIP eval_all, replaced by structfix] {model_dir.name}")
            continue

        print(f"[CLUSTER eval_all] {model_dir.name}")
        rows.extend(extract_rows_for_run(
            "HumanEval+",
            "Cluster",
            model_dir.name,
            model_dir,
        ))

    for model_dir in cluster_model_dirs(CLUSTER_STRUCTFIX):
        if not is_structfix_model(model_dir.name):
            print(f"[SKIP structfix non-recovery model] {model_dir.name}")
            continue

        print(f"[CLUSTER structfix] {model_dir.name}")
        rows.extend(extract_rows_for_run(
            "HumanEval+",
            "Cluster",
            model_dir.name + " [structfix]",
            model_dir,
        ))

    return rows


def write_csv(rows, path):
    if not rows:
        return

    fields = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def aggregate(rows):
    grouped = {}
    for r in rows:
        key = (r["dataset"], r["group"], r["approach"])
        grouped.setdefault(key, []).append(r)

    summary = []

    for (dataset, group, approach), rs in sorted(grouped.items()):
        expected = EXPECTED_REPS
        exec_ok = sum(int(r["exec_ok"]) for r in rs)

        line_sum = sum(as_float(r["line_coverage_pct"]) or 0.0 for r in rs)
        branch_sum = sum(as_float(r["branch_coverage_pct"]) or 0.0 for r in rs)
        mutation_sum = sum(as_float(r["mutation_score_pct"]) or 0.0 for r in rs)

        line_n = sum(1 for r in rs if as_float(r["line_coverage_pct"]) is not None)
        branch_n = sum(1 for r in rs if as_float(r["branch_coverage_pct"]) is not None)
        mutation_n = sum(1 for r in rs if as_float(r["mutation_score_pct"]) is not None)

        summary.append({
            "dataset": dataset,
            "group": group,
            "approach": approach,
            "expected_reps": expected,
            "rows_found": len(rs),
            "exec_ok_reps": exec_ok,
            "executable_suites_pct": 100.0 * exec_ok / expected,
            "line_coverage_pct": line_sum / expected,
            "branch_coverage_pct": branch_sum / expected,
            "mutation_score_pct": mutation_sum / expected,
            "line_metric_reps": line_n,
            "branch_metric_reps": branch_n,
            "mutation_metric_reps": mutation_n,
        })

    return summary


def write_summary(summary, path):
    fields = [
        "dataset",
        "group",
        "approach",
        "expected_reps",
        "rows_found",
        "exec_ok_reps",
        "executable_suites_pct",
        "line_coverage_pct",
        "branch_coverage_pct",
        "mutation_score_pct",
        "line_metric_reps",
        "branch_metric_reps",
        "mutation_metric_reps",
    ]

    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in summary:
            w.writerow(r)


def plot_radar(summary, title, filename, group_filter=None, approaches=None):
    selected = []
    for r in summary:
        if group_filter and r["group"] != group_filter:
            continue
        if approaches and r["approach"] not in approaches:
            continue
        selected.append(r)

    if not selected:
        print(f"[SKIP FIG] {title}")
        return

    metrics = [
        ("executable_suites_pct", "Executable suites"),
        ("line_coverage_pct", "Line coverage"),
        ("branch_coverage_pct", "Branch coverage"),
        ("mutation_score_pct", "Mutation score"),
    ]

    labels = [m[1] for m in metrics]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig = plt.figure(figsize=(9, 9))
    ax = plt.subplot(111, polar=True)

    for r in selected:
        values = [float(r[m[0]]) for m in metrics]
        values += values[:1]
        ax.plot(angles, values, linewidth=2, label=r["approach"])
        ax.fill(angles, values, alpha=0.06)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"])
    ax.set_title(title, pad=25)
    ax.legend(loc="upper right", bbox_to_anchor=(1.65, 1.15))

    out = OUT_DIR / filename
    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[FIG] {out}")


def main():
    all_rows = []

    for run in RUNS_FIXED:
        print(f"[RUN] {run['group']} / {run['approach']}")
        print(f"      {run['root']}")

        if not run["root"].exists():
            print("      [MISSING]")
            continue

        rows = extract_rows_for_run(
            run["dataset"],
            run["group"],
            run["approach"],
            run["root"],
        )
        print(f"      rows={len(rows)}")
        all_rows.extend(rows)

    all_rows.extend(extract_cluster_rows())

    raw_csv = OUT_DIR / "humanevalplus_repetition_level_extracted.csv"
    write_csv(all_rows, raw_csv)
    print(f"[CSV] {raw_csv}")

    summary = aggregate(all_rows)

    summary_csv = OUT_DIR / "humanevalplus_approach_summary_strict0.csv"
    write_summary(summary, summary_csv)
    print(f"[CSV] {summary_csv}")

    print()
    print("===== SUMMARY STRICT-ZERO =====")
    for r in summary:
        print(
            f"{r['group']:8s} | {r['approach'][:70]:70s} | "
            f"rows={r['rows_found']:4d} | "
            f"exec={r['executable_suites_pct']:6.2f} | "
            f"line={r['line_coverage_pct']:6.2f} | "
            f"branch={r['branch_coverage_pct']:6.2f} | "
            f"mut={r['mutation_score_pct']:6.2f} | "
            f"metric_n=({r['line_metric_reps']},{r['branch_metric_reps']},{r['mutation_metric_reps']})"
        )

    plot_radar(
        summary,
        "HumanEval+ Python — Non-AI baseline",
        "humanevalplus_radar_nonai.png",
        group_filter="Non-AI",
    )

    plot_radar(
        summary,
        "HumanEval+ Python — IAEdu proprietary LLMs",
        "humanevalplus_radar_iaedu.png",
        group_filter="IAEdu",
    )

    plot_radar(
        summary,
        "HumanEval+ Python — Cluster open-weight LLMs",
        "humanevalplus_radar_cluster.png",
        group_filter="Cluster",
    )

    best_overall = []

    for group in ["Non-AI", "IAEdu"]:
        best_overall.extend([r["approach"] for r in summary if r["group"] == group])

    cluster_sorted = sorted(
        [r for r in summary if r["group"] == "Cluster"],
        key=lambda x: float(x["mutation_score_pct"]),
        reverse=True,
    )
    best_overall.extend([r["approach"] for r in cluster_sorted[:3]])

    plot_radar(
        summary,
        "HumanEval+ Python — Selected best approaches",
        "humanevalplus_radar_best_overall.png",
        approaches=best_overall,
    )

    plot_radar(
        summary,
        "HumanEval+ Python — All approaches",
        "humanevalplus_radar_all_approaches.png",
    )


if __name__ == "__main__":
    main()
