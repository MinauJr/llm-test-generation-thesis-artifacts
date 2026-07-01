#!/usr/bin/env python3
import csv
import json
import math
import re
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


EXPECTED_SUTS = 378
EXPECTED_REPS = 1890

OUT_DIR = Path.home() / "analysis_mbppplus" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RAW_CSV = OUT_DIR / "mbppplus_repetition_level_extracted.csv"
SUMMARY_CSV = OUT_DIR / "mbppplus_approach_summary_strict0.csv"

RADAR_CSV = OUT_DIR / "mbppplus_radar_summary_with_official.csv"
STACKED_CSV = OUT_DIR / "mbppplus_stacked_3metrics_with_official_summary.csv"

RADAR_OUT = OUT_DIR / "mbppplus_radar_tools_as_axes_with_official.png"
STACKED_OUT = OUT_DIR / "mbppplus_stacked_3metrics_with_official.png"

OFFICIAL_ROOT = Path("/home/jpaiva/projetos/nonAI/python_workflow/out/_official_mbppplus_tests_strict0_FINAL_V10_REAL_WHERE_AVAILABLE_STRICT0_20260610_152401")
OFFICIAL_RESULTS_TSV = OFFICIAL_ROOT / "dataset_results.tsv"
OFFICIAL_SUMMARY_TXT = OFFICIAL_ROOT / "dataset_summary.txt"

PYNGUIN_ROOT = Path("/home/jpaiva/projetos/nonAI/python_workflow/out/_final_mbppplus_pynguin_strict0")

GPT4O_ROOT = Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_final_gpt4o_mbppplus_python_v6_retryempty_noextract")
GPT55_ROOT = Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_final_gpt55_mbppplus_python")
CLAUDE_ROOT = Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_final_claude47_mbppplus_python_merged_reruns")

CLUSTER_ALL_ROOT = Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_final_eval_cluster_mbppplus_all_try1_metrics")
CLUSTER_LOWPERF_ROOT = Path("/home/jpaiva/projetos/llm_test_generation_gpt4o/out/_final_eval_cluster_mbppplus_lowperf_r2_metrics")


RUNS_FIXED = [
    {
        "group": "Non-AI",
        "approach": "Pynguin",
        "root": PYNGUIN_ROOT,
    },
    {
        "group": "IAEdu",
        "approach": "GPT-4o",
        "root": GPT4O_ROOT,
    },
    {
        "group": "IAEdu",
        "approach": "GPT-5.5",
        "root": GPT55_ROOT,
    },
    {
        "group": "IAEdu",
        "approach": "Claude Opus 4.7",
        "root": CLAUDE_ROOT,
    },
]

CLUSTER_POLICY = [
    {
        "approach": "cluster-max-codellama-7b-instruct-ctx16k",
        "root": CLUSTER_LOWPERF_ROOT / "cluster-max-codellama-7b-instruct-ctx16k",
    },
    {
        "approach": "cluster-safe-codestral-22b-ctx16k",
        "root": CLUSTER_LOWPERF_ROOT / "cluster-safe-codestral-22b-ctx16k",
    },
    {
        "approach": "cluster-safe-deepseek-coder-v2-16b-ctx16k",
        "root": CLUSTER_ALL_ROOT / "cluster-safe-deepseek-coder-v2-16b-ctx16k",
    },
    {
        "approach": "cluster-safe-deepseek-v2-16b-ctx32k",
        "root": CLUSTER_ALL_ROOT / "cluster-safe-deepseek-v2-16b-ctx32k",
    },
    {
        "approach": "cluster-safe-qwen2.5-coder-14b-ctx32k",
        "root": CLUSTER_ALL_ROOT / "cluster-safe-qwen2.5-coder-14b-ctx32k",
    },
    {
        "approach": "cluster-safe-qwen3-coder-30b-official-ctx32k",
        "root": CLUSTER_ALL_ROOT / "cluster-safe-qwen3-coder-30b-official-ctx32k",
    },
    {
        "approach": "cluster-safe-qwen3.5-9b-ctx32k",
        "root": CLUSTER_ALL_ROOT / "cluster-safe-qwen3.5-9b-ctx32k",
    },
]

APPROACH_LABELS = {
    "Official dataset tests": "Dataset tests",
    "Pynguin": "Pynguin",
    "GPT-4o": "GPT-4o",
    "GPT-5.5": "GPT-5.5",
    "Claude Opus 4.7": "Claude 4.7",
    "cluster-max-codellama-7b-instruct-ctx16k": "CodeLlama",
    "cluster-safe-codestral-22b-ctx16k": "Codestral",
    "cluster-safe-deepseek-coder-v2-16b-ctx16k": "DeepSeek-Coder-V2",
    "cluster-safe-deepseek-v2-16b-ctx32k": "DeepSeek-V2",
    "cluster-safe-qwen2.5-coder-14b-ctx32k": "Qwen2.5-Coder",
    "cluster-safe-qwen3-coder-30b-official-ctx32k": "Qwen3-Coder",
    "cluster-safe-qwen3.5-9b-ctx32k": "Qwen3.5",
}

APPROACH_ORDER = [
    "Official dataset tests",
    "Pynguin",
    "GPT-4o",
    "GPT-5.5",
    "Claude Opus 4.7",
    "cluster-max-codellama-7b-instruct-ctx16k",
    "cluster-safe-codestral-22b-ctx16k",
    "cluster-safe-deepseek-coder-v2-16b-ctx16k",
    "cluster-safe-deepseek-v2-16b-ctx32k",
    "cluster-safe-qwen2.5-coder-14b-ctx32k",
    "cluster-safe-qwen3-coder-30b-official-ctx32k",
    "cluster-safe-qwen3.5-9b-ctx32k",
]

METRICS_RADAR = [
    ("executable_suites_pct", "Executable suites"),
    ("line_coverage_pct", "Line coverage"),
    ("branch_coverage_pct", "Branch coverage"),
    ("mutation_score_pct", "Mutation score"),
]

METRICS_STACKED = [
    ("line_coverage_pct", "Line coverage"),
    ("branch_coverage_pct", "Branch coverage"),
    ("mutation_score_pct", "Mutation score"),
]

METRIC_COLORS = {
    "Line coverage": "#1f77b4",
    "Branch coverage": "#ff7f0e",
    "Mutation score": "#2ca02c",
}


def as_float(x):
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(str(x).strip().replace("%", ""))
    except Exception:
        return None


def normalise_pct(v):
    v = as_float(v)
    if v is None:
        return None
    if 0 <= v <= 1:
        return v * 100.0
    return v


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


def read_text_float(path):
    try:
        return normalise_pct(path.read_text(errors="replace").strip().splitlines()[0])
    except Exception:
        return None


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
        if re.fullmatch(r"Mbpp_\d+", part):
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
            r"line\.line_pct$",
            r"line_pct$",
            r"line.*coverage",
            r"line_coverage_pct",
        ],
        "branch": [
            r"branch\.branch_pct$",
            r"branch_pct$",
            r"branch.*coverage",
            r"branch_coverage_pct",
        ],
        "mutation": [
            r"mutation\.mutation_pct$",
            r"mutation_pct$",
            r"mutation_score_pct$",
            r"mutation.*score",
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


def extract_rows_for_run(group, approach, root):
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
            "dataset": "MBPP+",
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


def write_raw_csv(rows):
    fields = [
        "dataset",
        "group",
        "approach",
        "sut",
        "rep",
        "exec_ok",
        "line_coverage_pct",
        "branch_coverage_pct",
        "mutation_score_pct",
        "source_metrics_dir",
    ]

    with RAW_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def aggregate_summary(rows):
    grouped = defaultdict(list)
    for r in rows:
        key = (r["dataset"], r["group"], r["approach"])
        grouped[key].append(r)

    summary = []

    for approach in APPROACH_ORDER:
        if approach == "Official dataset tests":
            continue

        matching_key = None
        for key in grouped:
            if key[2] == approach:
                matching_key = key
                break

        if not matching_key:
            continue

        dataset, group, approach = matching_key
        rs = grouped[matching_key]

        exec_ok = sum(int(r["exec_ok"]) for r in rs)

        def metric_sum(field):
            return sum(as_float(r[field]) or 0.0 for r in rs)

        def metric_n(field):
            return sum(1 for r in rs if as_float(r[field]) is not None)

        summary.append({
            "dataset": dataset,
            "group": group,
            "approach": approach,
            "expected_reps": EXPECTED_REPS,
            "rows_found": len(rs),
            "exec_ok_reps": exec_ok,
            "executable_suites_pct": 100.0 * exec_ok / EXPECTED_REPS,
            "line_coverage_pct": metric_sum("line_coverage_pct") / EXPECTED_REPS,
            "branch_coverage_pct": metric_sum("branch_coverage_pct") / EXPECTED_REPS,
            "mutation_score_pct": metric_sum("mutation_score_pct") / EXPECTED_REPS,
            "line_metric_reps": metric_n("line_coverage_pct"),
            "branch_metric_reps": metric_n("branch_coverage_pct"),
            "mutation_metric_reps": metric_n("mutation_score_pct"),
        })

    return summary


def write_summary_csv(summary):
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

    with SUMMARY_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in summary:
            w.writerow(r)


def load_official_rows():
    if not OFFICIAL_RESULTS_TSV.exists():
        raise SystemExit(f"[ERROR] Missing official TSV: {OFFICIAL_RESULTS_TSV}")

    with OFFICIAL_RESULTS_TSV.open(newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    return rows


def official_summary():
    rows = load_official_rows()

    line_values = []
    branch_values = []
    mutation_values = []
    mutation_non_zero = []
    line_non_zero = []
    branch_non_zero = []

    pytest_ok = 0

    for r in rows:
        if str(r.get("pytest_ok", "")).strip() == "1":
            pytest_ok += 1

        line = normalise_pct(r.get("line_pct"))
        branch = normalise_pct(r.get("branch_pct"))
        mutation = normalise_pct(r.get("mutation_pct"))

        line_values.append(line if line is not None else 0.0)
        branch_values.append(branch if branch is not None else 0.0)
        mutation_values.append(mutation if mutation is not None else 0.0)

        if line is not None and line > 0:
            line_non_zero.append(line)
        if branch is not None and branch > 0:
            branch_non_zero.append(branch)
        if mutation is not None and mutation > 0:
            mutation_non_zero.append(mutation)

    # Garantir denominador fixo de 378 SUTs.
    while len(line_values) < EXPECTED_SUTS:
        line_values.append(0.0)
    while len(branch_values) < EXPECTED_SUTS:
        branch_values.append(0.0)
    while len(mutation_values) < EXPECTED_SUTS:
        mutation_values.append(0.0)

    line_pen = sum(line_values) / EXPECTED_SUTS
    branch_pen = sum(branch_values) / EXPECTED_SUTS
    mutation_pen = sum(mutation_values) / EXPECTED_SUTS

    line_non = sum(line_non_zero) / len(line_non_zero) if line_non_zero else 0.0
    branch_non = sum(branch_non_zero) / len(branch_non_zero) if branch_non_zero else 0.0
    mutation_non = sum(mutation_non_zero) / len(mutation_non_zero) if mutation_non_zero else 0.0

    exec_pct = 100.0 * pytest_ok / EXPECTED_SUTS if EXPECTED_SUTS else 0.0

    return {
        "approach": "Official dataset tests",
        "label": "Dataset tests",
        "expected_reps": EXPECTED_SUTS,
        "rows_found": len(rows),
        "exec_ok_reps": pytest_ok,
        "executable_suites_pct": exec_pct,
        "line_coverage_pct": line_pen,
        "branch_coverage_pct": branch_pen,
        "mutation_score_pct": mutation_pen,
        "line_coverage_non_penalised_mean": line_non,
        "branch_coverage_non_penalised_mean": branch_non,
        "mutation_score_non_penalised_mean": mutation_non,
    }


def load_summary_rows_with_official(official, summary):
    out = []

    out.append({
        "approach": official["approach"],
        "label": official["label"],
        "executable_suites_pct": official["executable_suites_pct"],
        "line_coverage_pct": official["line_coverage_pct"],
        "branch_coverage_pct": official["branch_coverage_pct"],
        "mutation_score_pct": official["mutation_score_pct"],
    })

    for r in summary:
        out.append({
            "approach": r["approach"],
            "label": APPROACH_LABELS.get(r["approach"], r["approach"]),
            "executable_suites_pct": normalise_pct(r["executable_suites_pct"]),
            "line_coverage_pct": normalise_pct(r["line_coverage_pct"]),
            "branch_coverage_pct": normalise_pct(r["branch_coverage_pct"]),
            "mutation_score_pct": normalise_pct(r["mutation_score_pct"]),
        })

    by_approach = {r["approach"]: r for r in out}
    return [by_approach[a] for a in APPROACH_ORDER if a in by_approach]


def write_radar_csv(rows):
    fields = ["approach", "label", "executable_suites_pct", "line_coverage_pct", "branch_coverage_pct", "mutation_score_pct"]
    with RADAR_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def label_params(angle):
    deg = np.degrees(angle) % 360

    if 330 <= deg or deg < 30:
        return (18, 0, "left", "center")
    elif 30 <= deg < 60:
        return (18, 10, "left", "bottom")
    elif 60 <= deg < 120:
        return (0, 18, "center", "bottom")
    elif 120 <= deg < 150:
        return (-18, 10, "right", "bottom")
    elif 150 <= deg < 210:
        return (-18, 0, "right", "center")
    elif 210 <= deg < 240:
        return (-18, -10, "right", "top")
    elif 240 <= deg < 300:
        return (0, -18, "center", "top")
    else:
        return (18, -10, "left", "top")


def plot_radar(rows):
    labels = [r["label"] for r in rows]
    n = len(labels)

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    angles_closed = list(angles) + [angles[0]]

    fig = plt.figure(figsize=(16.0, 11.2))
    ax = plt.subplot(111, polar=True)

    ax.set_xticks(angles)
    ax.set_xticklabels([])

    for metric_key, metric_label in METRICS_RADAR:
        values = [normalise_pct(r[metric_key]) for r in rows]
        values += values[:1]

        ax.plot(angles_closed, values, linewidth=2.8, label=metric_label)
        ax.fill(angles_closed, values, alpha=0.035)

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=13)

    for angle, label in zip(angles, labels):
        dx, dy, ha, va = label_params(angle)
        ax.annotate(
            label,
            xy=(angle, 100),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=15,
            annotation_clip=False,
        )

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=4,
        frameon=True,
        fontsize=16,
    )

    fig.subplots_adjust(top=0.91, bottom=0.17, left=0.09, right=0.91)
    plt.savefig(RADAR_OUT, dpi=300, bbox_inches="tight", pad_inches=0.45)
    plt.close()


def compute_stacked_from_raw(rows):
    by_approach = defaultdict(list)
    for r in rows:
        by_approach[r["approach"]].append(r)

    summary = []

    for approach in APPROACH_ORDER:
        if approach == "Official dataset tests":
            continue

        rs = by_approach.get(approach, [])
        if not rs:
            continue

        row = {
            "approach": approach,
            "label": APPROACH_LABELS.get(approach, approach),
            "rows_found": len(rs),
        }

        for metric_key, _ in METRICS_STACKED:
            values_with_missing_as_zero = []
            non_zero_values = []

            for r in rs:
                v = normalise_pct(r.get(metric_key))

                if v is None:
                    values_with_missing_as_zero.append(0.0)
                else:
                    values_with_missing_as_zero.append(v)
                    if v > 0:
                        non_zero_values.append(v)

            missing_reps = max(0, EXPECTED_REPS - len(values_with_missing_as_zero))
            values_with_missing_as_zero.extend([0.0] * missing_reps)

            penalised_mean = sum(values_with_missing_as_zero) / EXPECTED_REPS
            non_penalised_mean = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0.0
            uplift = max(0.0, non_penalised_mean - penalised_mean)

            prefix = metric_key.replace("_pct", "")
            row[f"{prefix}_penalised_mean"] = penalised_mean
            row[f"{prefix}_non_penalised_mean"] = non_penalised_mean
            row[f"{prefix}_uplift"] = uplift
            row[f"{prefix}_non_zero_count"] = len(non_zero_values)

        summary.append(row)

    return summary


def stacked_summary_with_official(official, raw_rows):
    official_row = {
        "approach": official["approach"],
        "label": official["label"],
        "rows_found": official["rows_found"],
    }

    for metric_key, _ in METRICS_STACKED:
        prefix = metric_key.replace("_pct", "")
        pen = official[metric_key]
        non = official[f"{prefix}_non_penalised_mean"]
        official_row[f"{prefix}_penalised_mean"] = pen
        official_row[f"{prefix}_non_penalised_mean"] = non
        official_row[f"{prefix}_uplift"] = max(0.0, non - pen)
        official_row[f"{prefix}_non_zero_count"] = EXPECTED_SUTS if non > 0 else 0

    return [official_row] + compute_stacked_from_raw(raw_rows)


def write_stacked_csv(summary):
    fields = [
        "approach",
        "label",
        "rows_found",
        "line_coverage_penalised_mean",
        "line_coverage_non_penalised_mean",
        "line_coverage_uplift",
        "line_coverage_non_zero_count",
        "branch_coverage_penalised_mean",
        "branch_coverage_non_penalised_mean",
        "branch_coverage_uplift",
        "branch_coverage_non_zero_count",
        "mutation_score_penalised_mean",
        "mutation_score_non_penalised_mean",
        "mutation_score_uplift",
        "mutation_score_non_zero_count",
    ]

    with STACKED_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in summary:
            w.writerow(r)


def plot_stacked(summary):
    labels = [r["label"] for r in summary]
    x = np.arange(len(labels))
    width = 0.22

    fig, ax = plt.subplots(figsize=(19.2, 9.4))

    offsets = [-width, 0, width]

    for (metric_key, metric_label), offset in zip(METRICS_STACKED, offsets):
        prefix = metric_key.replace("_pct", "")
        penalised = [r[f"{prefix}_penalised_mean"] for r in summary]
        uplift = [r[f"{prefix}_uplift"] for r in summary]
        color = METRIC_COLORS[metric_label]

        ax.bar(x + offset, penalised, width, color=color, alpha=0.9)
        ax.bar(
            x + offset,
            uplift,
            width,
            bottom=penalised,
            color=color,
            alpha=0.35,
            hatch="///",
            edgecolor=color,
        )

    ax.set_ylabel("%", fontsize=16)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 10))

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=14)
    ax.tick_params(axis="y", labelsize=14)

    ax.grid(axis="y", alpha=0.25)

    legend_handles = [
        Patch(facecolor=METRIC_COLORS["Line coverage"], label="Line coverage"),
        Patch(facecolor=METRIC_COLORS["Branch coverage"], label="Branch coverage"),
        Patch(facecolor=METRIC_COLORS["Mutation score"], label="Mutation score"),
        Patch(facecolor="lightgray", edgecolor="black", label="Penalised mean"),
        Patch(facecolor="white", edgecolor="black", hatch="///",
              label="Additional uplift to non-penalised mean"),
    ]

    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.24),
        ncol=3,
        fontsize=14,
        frameon=True,
    )

    fig.subplots_adjust(bottom=0.34, left=0.06, right=0.99, top=0.97)
    plt.savefig(STACKED_OUT, dpi=300, bbox_inches="tight", pad_inches=0.30)
    plt.close()


def main():
    all_rows = []

    print("===== EXTRACT FIXED RUNS =====")
    for run in RUNS_FIXED:
        print(f"[RUN] {run['group']} / {run['approach']}")
        print(f"      {run['root']}")

        if not run["root"].exists():
            print("      [MISSING]")
            continue

        rows = extract_rows_for_run(run["group"], run["approach"], run["root"])
        print(f"      rows={len(rows)}")
        all_rows.extend(rows)

    print()
    print("===== EXTRACT CLUSTER RUNS =====")
    for run in CLUSTER_POLICY:
        print(f"[RUN] Cluster / {run['approach']}")
        print(f"      {run['root']}")

        if not run["root"].exists():
            print("      [MISSING]")
            continue

        rows = extract_rows_for_run("Cluster", run["approach"], run["root"])
        print(f"      rows={len(rows)}")
        all_rows.extend(rows)

    write_raw_csv(all_rows)
    print(f"[RAW CSV] {RAW_CSV}")

    summary = aggregate_summary(all_rows)
    write_summary_csv(summary)
    print(f"[SUMMARY CSV] {SUMMARY_CSV}")

    official = official_summary()

    radar_rows = load_summary_rows_with_official(official, summary)
    write_radar_csv(radar_rows)
    plot_radar(radar_rows)

    stacked_rows = stacked_summary_with_official(official, all_rows)
    write_stacked_csv(stacked_rows)
    plot_stacked(stacked_rows)

    print(f"[RADAR CSV] {RADAR_CSV}")
    print(f"[RADAR FIG] {RADAR_OUT}")
    print(f"[STACKED CSV] {STACKED_CSV}")
    print(f"[STACKED FIG] {STACKED_OUT}")

    print()
    print("===== RADAR DATA WITH OFFICIAL =====")
    for r in radar_rows:
        print(
            f"{r['label']:20s} | "
            f"exec={normalise_pct(r['executable_suites_pct']):6.2f} | "
            f"line={normalise_pct(r['line_coverage_pct']):6.2f} | "
            f"branch={normalise_pct(r['branch_coverage_pct']):6.2f} | "
            f"mut={normalise_pct(r['mutation_score_pct']):6.2f}"
        )

    print()
    print("===== STACKED DATA WITH OFFICIAL =====")
    for r in stacked_rows:
        print(
            f"{r['label']:20s} | "
            f"LINE pen={r['line_coverage_penalised_mean']:6.2f} nonpen={r['line_coverage_non_penalised_mean']:6.2f} | "
            f"BRANCH pen={r['branch_coverage_penalised_mean']:6.2f} nonpen={r['branch_coverage_non_penalised_mean']:6.2f} | "
            f"MUT pen={r['mutation_score_penalised_mean']:6.2f} nonpen={r['mutation_score_non_penalised_mean']:6.2f}"
        )


if __name__ == "__main__":
    main()
