#!/usr/bin/env python3
import csv
import json
import math
import statistics
from pathlib import Path
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


FIG_DIR = Path.home() / "analysis_humanevalx_java" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

OFFICIAL_ROOT = Path("/home/jpaiva/projetos/humanevalx_gpt4o/out/_official_humanevalx_java_dataset_tests_JAVA17_FINAL_20260610_161233")
EVOSUITE_ROOT = Path("/home/jpaiva/projetos/nonAI/java_workflow/out/_final_run_humanevalx_evosuite")
RANDOOP_ROOT = Path("/home/jpaiva/projetos/nonAI/java_workflow/out/_final_run_humanevalx_randoop")

GPT4O_ROOT = Path("/home/jpaiva/projetos/humanevalx_gpt4o/out/_final_gpt4o_humanevalx_java_retryempty")
GPT55_ROOT = Path("/home/jpaiva/projetos/humanevalx_gpt4o/out/_final_gpt55_humanevalx_java")
CLAUDE_ROOT = Path("/home/jpaiva/projetos/humanevalx_gpt4o/out/_final_claude_humanevalx_java")

CLUSTER_ROOT = Path("/home/jpaiva/projetos/humanevalx_gpt4o/out/_cluster_humanevalx_java_try1_v2_eval_all_sanitizefix")

EXPECTED_SUTS = 164
EXPECTED_REPS = 820
EXPECTED_CLUSTER_REPS_PER_MODEL = 820

RADAR_OUT = FIG_DIR / "humanevalx_java_radar_tools_as_axes_with_official.png"
STACKED_OUT = FIG_DIR / "humanevalx_java_stacked_3metrics_with_official.png"

RAW_CSV = FIG_DIR / "humanevalx_java_repetition_level_extracted.csv"
SUMMARY_CSV = FIG_DIR / "humanevalx_java_approach_summary_strict0.csv"
RADAR_CSV = FIG_DIR / "humanevalx_java_radar_summary_with_official.csv"
STACKED_CSV = FIG_DIR / "humanevalx_java_stacked_3metrics_with_official_summary.csv"

ORDER = [
    "Dataset tests",
    "EvoSuite",
    "Randoop",
    "GPT-4o",
    "GPT-5.5",
    "Claude 4.7",
    "CodeLlama",
    "Codestral",
    "DeepSeek-Coder-V2",
    "DeepSeek-V2-Lite",
    "Qwen2.5-Coder",
    "Qwen3-Coder",
    "Qwen3.5",
]

MODEL_LABELS = {
    "cluster-max-codellama-7b-instruct-ctx16k": "CodeLlama",
    "cluster-safe-codestral-22b-ctx16k": "Codestral",
    "cluster-safe-deepseek-coder-v2-16b-ctx16k": "DeepSeek-Coder-V2",
    "cluster-safe-deepseek-v2-lite-ctx32k": "DeepSeek-V2-Lite",
    "cluster-safe-qwen2.5-coder-14b-ctx32k": "Qwen2.5-Coder",
    "cluster-safe-qwen3-coder-30b-official-ctx8k": "Qwen3-Coder",
    "cluster-safe-qwen3.5-9b-ctx32k": "Qwen3.5",
}

STATUS_OK_VALUES = {"ok", "passed", "success", "valid"}

COLORS = {
    "Executable suites": "#1f77b4",
    "Line coverage": "#ff7f0e",
    "Branch coverage": "#2ca02c",
    "Mutation score": "#d62728",
    "Line bar": "#1f77b4",
    "Branch bar": "#ff7f0e",
    "Mutation bar": "#2ca02c",
}


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Cannot read JSON {path}: {e}")


def to_float(v):
    if v is None:
        return None
    try:
        if isinstance(v, str) and not v.strip():
            return None
        x = float(v)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None


def first(d, keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def metric(d, kind):
    if kind == "line":
        keys = [
            "line_pct", "line_coverage_pct", "line_coverage",
            "coverage_line_pct", "jacoco_line_pct", "lineCoverage"
        ]
    elif kind == "branch":
        keys = [
            "branch_pct", "branch_coverage_pct", "branch_coverage",
            "coverage_branch_pct", "jacoco_branch_pct", "branchCoverage"
        ]
    else:
        keys = [
            "mutation_score_pct", "mutation_pct", "pit_score", "pit_score_pct",
            "mutation_score", "pitScore"
        ]

    v = first(d, keys)
    if v is not None:
        return to_float(v)

    for parent in ["metrics", "coverage", "jacoco", "pit", "mutation"]:
        sub = d.get(parent) if isinstance(d, dict) else None
        if isinstance(sub, dict):
            v = first(sub, keys)
            if v is not None:
                return to_float(v)

    return None


def status_value(d):
    raw = first(d, ["status", "final_status", "result", "outcome"])
    if raw is None:
        if first(d, ["ok", "success", "passed"]) is True:
            return "ok"
        return "unknown"
    return str(raw).strip().lower()


def is_executable(d):
    st = status_value(d)
    if st in STATUS_OK_VALUES:
        return True

    for k in ["line", "branch", "mutation"]:
        if metric(d, k) is not None:
            return True
    return False


def collect_status_rows(root, approach, expected_total, model_filter=None):
    rows = []
    for p in sorted(root.rglob("metrics/status.json")):
        rel = p.relative_to(root).as_posix()
        parts = rel.split("/")

        model = parts[0] if parts else ""
        if model_filter is not None and model != model_filter:
            continue

        sut = ""
        rep = ""
        for part in parts:
            if part.startswith("Java_"):
                sut = part
            if part.startswith("rep_") or part.startswith("run_"):
                rep = part

        data = read_json(p)

        rows.append({
            "approach": approach,
            "model": model_filter or "",
            "sut": sut,
            "rep": rep,
            "rel_path": rel,
            "status": status_value(data),
            "executable": is_executable(data),
            "line_pct": metric(data, "line"),
            "branch_pct": metric(data, "branch"),
            "mutation_score_pct": metric(data, "mutation"),
        })

    return rows


def summarise_status_rows(label, rows, expected_total):
    status_counts = Counter(r["status"] for r in rows)

    def penalised_mean(key):
        return sum((r[key] if r[key] is not None else 0.0) for r in rows) / expected_total

    def valid_mean(key):
        vals = [r[key] for r in rows if r[key] is not None]
        return statistics.mean(vals) if vals else 0.0

    return {
        "label": label,
        "expected_total": expected_total,
        "observed_total": len(rows),
        "executable_suites_pct": 100.0 * sum(1 for r in rows if r["executable"]) / expected_total,
        "line_coverage_pct": penalised_mean("line_pct"),
        "branch_coverage_pct": penalised_mean("branch_pct"),
        "mutation_score_pct": penalised_mean("mutation_score_pct"),
        "line_coverage_penalised_mean": penalised_mean("line_pct"),
        "line_coverage_non_penalised_mean": valid_mean("line_pct"),
        "branch_coverage_penalised_mean": penalised_mean("branch_pct"),
        "branch_coverage_non_penalised_mean": valid_mean("branch_pct"),
        "mutation_score_penalised_mean": penalised_mean("mutation_score_pct"),
        "mutation_score_non_penalised_mean": valid_mean("mutation_score_pct"),
        "status_counts": dict(status_counts),
    }


def official_summary():
    data = read_json(OFFICIAL_ROOT / "dataset_summary.json")

    line_pen = float(data["line_coverage_mean_strict0"])
    branch_pen = float(data["branch_coverage_mean_strict0"])
    mut_pen = float(data["mutation_score_mean_strict0"])

    return {
        "label": "Dataset tests",
        "expected_total": EXPECTED_SUTS,
        "observed_total": int(data.get("suts_with_status", EXPECTED_SUTS)),
        "executable_suites_pct": float(data.get("executable_pct", 100.0)),
        "line_coverage_pct": line_pen,
        "branch_coverage_pct": branch_pen,
        "mutation_score_pct": mut_pen,
        "line_coverage_penalised_mean": line_pen,
        "line_coverage_non_penalised_mean": line_pen,
        "branch_coverage_penalised_mean": branch_pen,
        "branch_coverage_non_penalised_mean": branch_pen,
        "mutation_score_penalised_mean": mut_pen,
        "mutation_score_non_penalised_mean": mut_pen,
        "status_counts": dict(data.get("status_counts", {})),
    }


def evosuite_summary():
    data = read_json(EVOSUITE_ROOT / "final_dataset_summary.json")
    m = data["mean"]

    line_pen = float(m["line_pct"])
    branch_pen = float(m["branch_pct"])
    mut_pen = float(m["pit_score"])

    reps_expected = int(data.get("reps_expected", EXPECTED_REPS))
    reps_ok = int(data.get("reps_ok", reps_expected))

    return {
        "label": "EvoSuite",
        "expected_total": reps_expected,
        "observed_total": reps_ok,
        "executable_suites_pct": 100.0 * reps_ok / reps_expected,
        "line_coverage_pct": line_pen,
        "branch_coverage_pct": branch_pen,
        "mutation_score_pct": mut_pen,
        "line_coverage_penalised_mean": line_pen,
        "line_coverage_non_penalised_mean": line_pen,
        "branch_coverage_penalised_mean": branch_pen,
        "branch_coverage_non_penalised_mean": branch_pen,
        "mutation_score_penalised_mean": mut_pen,
        "mutation_score_non_penalised_mean": mut_pen,
        "status_counts": {"ok": reps_ok},
    }


def randoop_summary():
    data = read_json(RANDOOP_ROOT / "final_dataset_summary.json")
    m = data["mean_of_sut_means"]

    line_pen = float(m["line_pct"])
    branch_pen = float(m["branch_pct"])
    mut_pen = float(m["mutation_pct"])

    suts_total = int(data.get("total_suts_with_summary", EXPECTED_SUTS))
    missing = int(data.get("total_suts_missing_summary", 0))

    return {
        "label": "Randoop",
        "expected_total": EXPECTED_SUTS,
        "observed_total": suts_total,
        "executable_suites_pct": 100.0 * suts_total / EXPECTED_SUTS,
        "line_coverage_pct": line_pen,
        "branch_coverage_pct": branch_pen,
        "mutation_score_pct": mut_pen,
        "line_coverage_penalised_mean": line_pen,
        "line_coverage_non_penalised_mean": line_pen,
        "branch_coverage_penalised_mean": branch_pen,
        "branch_coverage_non_penalised_mean": branch_pen,
        "mutation_score_penalised_mean": mut_pen,
        "mutation_score_non_penalised_mean": mut_pen,
        "status_counts": {"summary_ok_suts": suts_total, "missing": missing},
    }


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            out = {}
            for k in fields:
                v = r.get(k, "")
                if isinstance(v, dict):
                    v = json.dumps(v, sort_keys=True)
                out[k] = v
            w.writerow(out)


def ordered(rows):
    pos = {x: i for i, x in enumerate(ORDER)}
    return sorted(rows, key=lambda r: pos.get(r["label"], 9999))


def build_radar(rows):
    rows = ordered(rows)

    labels = [r["label"] for r in rows]
    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    angles_closed = list(angles) + [angles[0]]

    fig = plt.figure(figsize=(17.5, 12.8))
    ax = plt.subplot(111, polar=True)

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=13)
    ax.set_rlabel_position(18)

    ax.set_xticks(angles)
    ax.set_xticklabels([])

    series = [
        ("Executable suites", "executable_suites_pct", COLORS["Executable suites"]),
        ("Line coverage", "line_coverage_pct", COLORS["Line coverage"]),
        ("Branch coverage", "branch_coverage_pct", COLORS["Branch coverage"]),
        ("Mutation score", "mutation_score_pct", COLORS["Mutation score"]),
    ]

    for name, key, color in series:
        vals = [float(r[key]) for r in rows]
        vals_closed = vals + vals[:1]
        ax.plot(angles_closed, vals_closed, linewidth=2.7, color=color, label=name)
        ax.fill(angles_closed, vals_closed, alpha=0.035, color=color)

    for angle, label in zip(angles, labels):
        c = np.cos(angle)
        s = np.sin(angle)

        dx = 42 * c
        dy = 42 * s

        ha = "left" if c > 0.20 else "right" if c < -0.20 else "center"
        va = "bottom" if s > 0.20 else "top" if s < -0.20 else "center"

        if label in {"Dataset tests", "EvoSuite", "Randoop"}:
            dx += 8
        if label in {"DeepSeek-Coder-V2", "DeepSeek-V2-Lite"}:
            dx -= 10
        if label == "Qwen3-Coder":
            dx += 8
            dy -= 8
            ha = "left"
        if label == "Qwen3.5":
            dx += 10

        ax.annotate(
            label,
            xy=(angle, 100),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=14,
            annotation_clip=False,
        )

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=4,
        frameon=True,
        fontsize=15,
    )

    fig.subplots_adjust(top=0.91, bottom=0.18, left=0.08, right=0.92)
    fig.savefig(RADAR_OUT, dpi=300, bbox_inches="tight", pad_inches=0.45)
    plt.close(fig)


def build_stacked(rows):
    rows = ordered(rows)

    labels = [r["label"] for r in rows]

    line_pen = [float(r["line_coverage_penalised_mean"]) for r in rows]
    line_non = [float(r["line_coverage_non_penalised_mean"]) for r in rows]

    branch_pen = [float(r["branch_coverage_penalised_mean"]) for r in rows]
    branch_non = [float(r["branch_coverage_non_penalised_mean"]) for r in rows]

    mut_pen = [float(r["mutation_score_penalised_mean"]) for r in rows]
    mut_non = [float(r["mutation_score_non_penalised_mean"]) for r in rows]

    line_uplift = [max(0.0, n - p) for p, n in zip(line_pen, line_non)]
    branch_uplift = [max(0.0, n - p) for p, n in zip(branch_pen, branch_non)]
    mut_uplift = [max(0.0, n - p) for p, n in zip(mut_pen, mut_non)]

    x = np.arange(len(labels))
    width = 0.22

    fig, ax = plt.subplots(figsize=(20.0, 9.8))

    ax.bar(x - width, line_pen, width, color=COLORS["Line bar"], alpha=0.92)
    ax.bar(x, branch_pen, width, color=COLORS["Branch bar"], alpha=0.92)
    ax.bar(x + width, mut_pen, width, color=COLORS["Mutation bar"], alpha=0.92)

    ax.bar(x - width, line_uplift, width, bottom=line_pen,
           color=COLORS["Line bar"], alpha=0.35, hatch="///", edgecolor=COLORS["Line bar"])
    ax.bar(x, branch_uplift, width, bottom=branch_pen,
           color=COLORS["Branch bar"], alpha=0.35, hatch="///", edgecolor=COLORS["Branch bar"])
    ax.bar(x + width, mut_uplift, width, bottom=mut_pen,
           color=COLORS["Mutation bar"], alpha=0.35, hatch="///", edgecolor=COLORS["Mutation bar"])

    ax.set_ylabel("%", fontsize=16)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 10))
    ax.tick_params(axis="y", labelsize=14)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=13)

    ax.grid(axis="y", alpha=0.25)

    legend_handles = [
        Patch(facecolor=COLORS["Line bar"], label="Line coverage"),
        Patch(facecolor=COLORS["Branch bar"], label="Branch coverage"),
        Patch(facecolor=COLORS["Mutation bar"], label="Mutation score"),
        Patch(facecolor="lightgray", edgecolor="black", label="Penalised mean"),
        Patch(facecolor="white", edgecolor="black", hatch="///",
              label="Additional uplift to non-penalised mean"),
    ]

    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.26),
        ncol=3,
        fontsize=14,
        frameon=True,
    )

    fig.subplots_adjust(bottom=0.38, left=0.06, right=0.99, top=0.97)
    fig.savefig(STACKED_OUT, dpi=300, bbox_inches="tight", pad_inches=0.32)
    plt.close(fig)


def main():
    raw_rows = []
    summary_rows = []

    summary_rows.append(official_summary())
    summary_rows.append(evosuite_summary())
    summary_rows.append(randoop_summary())

    for label, root in [
        ("GPT-4o", GPT4O_ROOT),
        ("GPT-5.5", GPT55_ROOT),
        ("Claude 4.7", CLAUDE_ROOT),
    ]:
        rows = collect_status_rows(root, label, EXPECTED_REPS)
        raw_rows.extend(rows)
        summary_rows.append(summarise_status_rows(label, rows, EXPECTED_REPS))

    for model_dir in sorted(CLUSTER_ROOT.glob("cluster-*")):
        model_name = model_dir.name
        label = MODEL_LABELS.get(model_name, model_name)
        rows = collect_status_rows(CLUSTER_ROOT, label, EXPECTED_CLUSTER_REPS_PER_MODEL, model_filter=model_name)
        raw_rows.extend(rows)
        summary_rows.append(summarise_status_rows(label, rows, EXPECTED_CLUSTER_REPS_PER_MODEL))

    summary_rows = ordered(summary_rows)

    raw_fields = [
        "approach", "model", "sut", "rep", "rel_path", "status",
        "executable", "line_pct", "branch_pct", "mutation_score_pct",
    ]

    summary_fields = [
        "label",
        "expected_total",
        "observed_total",
        "executable_suites_pct",
        "line_coverage_pct",
        "branch_coverage_pct",
        "mutation_score_pct",
        "line_coverage_penalised_mean",
        "line_coverage_non_penalised_mean",
        "branch_coverage_penalised_mean",
        "branch_coverage_non_penalised_mean",
        "mutation_score_penalised_mean",
        "mutation_score_non_penalised_mean",
        "status_counts",
    ]

    write_csv(RAW_CSV, raw_rows, raw_fields)
    write_csv(SUMMARY_CSV, summary_rows, summary_fields)
    write_csv(RADAR_CSV, summary_rows, summary_fields)
    write_csv(STACKED_CSV, summary_rows, summary_fields)

    build_radar(summary_rows)
    build_stacked(summary_rows)

    print("===== HUMAN EVAL X JAVA FINAL SUMMARY =====")
    for r in summary_rows:
        print(
            f"{r['label']}: "
            f"exec={float(r['executable_suites_pct']):.2f} | "
            f"line={float(r['line_coverage_pct']):.2f} | "
            f"branch={float(r['branch_coverage_pct']):.2f} | "
            f"mutation={float(r['mutation_score_pct']):.2f}"
        )

    print()
    print("[OK] wrote:")
    for p in [RAW_CSV, SUMMARY_CSV, RADAR_CSV, STACKED_CSV, RADAR_OUT, STACKED_OUT]:
        print(f"[OUT] {p}")


if __name__ == "__main__":
    main()
