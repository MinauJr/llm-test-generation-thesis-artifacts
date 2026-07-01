#!/usr/bin/env python3
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


FIG_DIR = Path.home() / "analysis_mbppplus" / "figures"

RADAR_CSV = FIG_DIR / "mbppplus_radar_summary_with_official.csv"
STACKED_CSV = FIG_DIR / "mbppplus_stacked_3metrics_with_official_summary.csv"

RADAR_OUT = FIG_DIR / "mbppplus_radar_tools_as_axes_with_official.png"
STACKED_OUT = FIG_DIR / "mbppplus_stacked_3metrics_with_official.png"


ORDER = [
    "Dataset tests",
    "Pynguin",
    "GPT-4o",
    "GPT-5.5",
    "Claude 4.7",
    "CodeLlama",
    "Codestral",
    "DeepSeek-Coder-V2",
    "DeepSeek-V2",
    "Qwen2.5-Coder",
    "Qwen3-Coder",
    "Qwen3.5",
]

COLORS = {
    "Executable suites": "#1f77b4",
    "Line coverage": "#1f77b4",
    "Branch coverage": "#ff7f0e",
    "Mutation score": "#2ca02c",
    "Mutation radar": "#d62728",
}


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def f(v):
    try:
        if v is None or str(v).strip() == "":
            return 0.0
        return float(str(v).strip())
    except Exception:
        return 0.0


def label_of(row):
    raw = (row.get("label") or row.get("approach") or "").strip()

    mapping = {
        "Official dataset tests": "Dataset tests",
        "Dataset tests": "Dataset tests",
        "Pynguin": "Pynguin",
        "GPT-4o": "GPT-4o",
        "GPT-5.5": "GPT-5.5",
        "Claude Opus 4.7": "Claude 4.7",
        "Claude 4.7": "Claude 4.7",
        "cluster-max-codellama-7b-instruct-ctx16k": "CodeLlama",
        "cluster-safe-codestral-22b-ctx16k": "Codestral",
        "cluster-safe-deepseek-coder-v2-16b-ctx16k": "DeepSeek-Coder-V2",
        "cluster-safe-deepseek-v2-16b-ctx32k": "DeepSeek-V2",
        "cluster-safe-qwen2.5-coder-14b-ctx32k": "Qwen2.5-Coder",
        "cluster-safe-qwen3-coder-30b-official-ctx32k": "Qwen3-Coder",
        "cluster-safe-qwen3.5-9b-ctx32k": "Qwen3.5",
        "CodeLlama": "CodeLlama",
        "Codestral": "Codestral",
        "DeepSeek-Coder-V2": "DeepSeek-Coder-V2",
        "DeepSeek-V2": "DeepSeek-V2",
        "Qwen2.5-Coder": "Qwen2.5-Coder",
        "Qwen3-Coder": "Qwen3-Coder",
        "Qwen3.5": "Qwen3.5",
    }

    return mapping.get(raw, raw)


def sort_rows(rows):
    pos = {name: i for i, name in enumerate(ORDER)}
    return sorted(rows, key=lambda r: pos.get(label_of(r), 9999))


def force_dataset_tests_no_uplift(stacked_rows):
    for r in stacked_rows:
        if label_of(r) == "Dataset tests":
            for prefix in ["line_coverage", "branch_coverage", "mutation_score"]:
                pen_key = f"{prefix}_penalised_mean"
                non_key = f"{prefix}_non_penalised_mean"
                uplift_key = f"{prefix}_uplift"

                if pen_key in r:
                    r[non_key] = r[pen_key]
                if uplift_key in r:
                    r[uplift_key] = "0.0"


def build_radar():
    rows = sort_rows(load_csv(RADAR_CSV))
    labels = [label_of(r) for r in rows]

    n = len(rows)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    angles_closed = list(angles) + [angles[0]]

    fig = plt.figure(figsize=(16.0, 11.2))
    ax = plt.subplot(111, polar=True)

    ax.set_xticks(angles)
    ax.set_xticklabels([])

    series = [
        ("Executable suites", "executable_suites_pct", COLORS["Executable suites"]),
        ("Line coverage", "line_coverage_pct", COLORS["Branch coverage"]),
        ("Branch coverage", "branch_coverage_pct", COLORS["Mutation score"]),
        ("Mutation score", "mutation_score_pct", COLORS["Mutation radar"]),
    ]

    for name, key, color in series:
        values = [f(r.get(key)) for r in rows]
        values_closed = values + values[:1]
        ax.plot(angles_closed, values_closed, linewidth=2.8, color=color, label=name)
        ax.fill(angles_closed, values_closed, alpha=0.035, color=color)

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=13)
    ax.set_rlabel_position(18)

    # Labels fora do anel de 100, sem criar escala 110.
    for angle, label in zip(angles, labels):
        c = np.cos(angle)
        s = np.sin(angle)

        dx = 40 * c
        dy = 40 * s

        if c > 0.20:
            ha = "left"
        elif c < -0.20:
            ha = "right"
        else:
            ha = "center"

        if s > 0.20:
            va = "bottom"
        elif s < -0.20:
            va = "top"
        else:
            va = "center"

        # Ajuste extra para não ficarem colados ao polígono.
        if label == "Qwen3-Coder":
            dx += 8
            dy -= 10
            ha = "left"
            va = "top"
        elif label == "Qwen3.5":
            dx += 10
            dy -= 2
            ha = "left"
        elif label == "Dataset tests":
            dx += 12
            ha = "left"
        elif label == "CodeLlama":
            dx -= 8
            ha = "right"
        elif label == "DeepSeek-Coder-V2":
            dx -= 10
            dy -= 2
            ha = "right"

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


def build_stacked():
    rows = sort_rows(load_csv(STACKED_CSV))
    force_dataset_tests_no_uplift(rows)
    save_csv(STACKED_CSV, rows)

    labels = [label_of(r) for r in rows]

    line_pen = [f(r.get("line_coverage_penalised_mean")) for r in rows]
    line_non = [f(r.get("line_coverage_non_penalised_mean")) for r in rows]

    branch_pen = [f(r.get("branch_coverage_penalised_mean")) for r in rows]
    branch_non = [f(r.get("branch_coverage_non_penalised_mean")) for r in rows]

    mut_pen = [f(r.get("mutation_score_penalised_mean")) for r in rows]
    mut_non = [f(r.get("mutation_score_non_penalised_mean")) for r in rows]

    line_uplift = [max(0.0, non - pen) for pen, non in zip(line_pen, line_non)]
    branch_uplift = [max(0.0, non - pen) for pen, non in zip(branch_pen, branch_non)]
    mut_uplift = [max(0.0, non - pen) for pen, non in zip(mut_pen, mut_non)]

    x = np.arange(len(labels))
    width = 0.22

    fig, ax = plt.subplots(figsize=(19.2, 9.4))

    # 3 barras por ferramenta/modelo: line, branch, mutation
    ax.bar(x - width, line_pen, width, color=COLORS["Line coverage"], alpha=0.9)
    ax.bar(x, branch_pen, width, color=COLORS["Branch coverage"], alpha=0.9)
    ax.bar(x + width, mut_pen, width, color=COLORS["Mutation score"], alpha=0.9)

    # uplift até à média não penalizada
    ax.bar(
        x - width,
        line_uplift,
        width,
        bottom=line_pen,
        color=COLORS["Line coverage"],
        alpha=0.35,
        hatch="///",
        edgecolor=COLORS["Line coverage"],
    )
    ax.bar(
        x,
        branch_uplift,
        width,
        bottom=branch_pen,
        color=COLORS["Branch coverage"],
        alpha=0.35,
        hatch="///",
        edgecolor=COLORS["Branch coverage"],
    )
    ax.bar(
        x + width,
        mut_uplift,
        width,
        bottom=mut_pen,
        color=COLORS["Mutation score"],
        alpha=0.35,
        hatch="///",
        edgecolor=COLORS["Mutation score"],
    )

    ax.set_ylabel("%", fontsize=16)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 10))
    ax.tick_params(axis="y", labelsize=14)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=14)

    ax.grid(axis="y", alpha=0.25)

    legend_handles = [
        Patch(facecolor=COLORS["Line coverage"], label="Line coverage"),
        Patch(facecolor=COLORS["Branch coverage"], label="Branch coverage"),
        Patch(facecolor=COLORS["Mutation score"], label="Mutation score"),
        Patch(facecolor="lightgray", edgecolor="black", label="Penalised mean"),
        Patch(facecolor="white", edgecolor="black", hatch="///",
              label="Additional uplift to non-penalised mean"),
    ]

    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.25),
        ncol=3,
        fontsize=14,
        frameon=True,
    )

    fig.subplots_adjust(bottom=0.36, left=0.06, right=0.99, top=0.97)
    plt.savefig(STACKED_OUT, dpi=300, bbox_inches="tight", pad_inches=0.30)
    plt.close()


def main():
    build_radar()
    build_stacked()

    print("[OK] regenerated radar and stacked charts with corrected layout")
    print(f"[FIG] {RADAR_OUT}")
    print(f"[FIG] {STACKED_OUT}")

    print()
    print("===== DATASET TESTS VALUES USED =====")
    for r in sort_rows(load_csv(RADAR_CSV)):
        if label_of(r) == "Dataset tests":
            print(
                f"Radar Dataset tests | "
                f"exec={f(r.get('executable_suites_pct')):.2f} | "
                f"line={f(r.get('line_coverage_pct')):.2f} | "
                f"branch={f(r.get('branch_coverage_pct')):.2f} | "
                f"mutation={f(r.get('mutation_score_pct')):.2f}"
            )

    for r in sort_rows(load_csv(STACKED_CSV)):
        if label_of(r) == "Dataset tests":
            print(
                f"Stacked Dataset tests | "
                f"line pen={f(r.get('line_coverage_penalised_mean')):.2f} nonpen={f(r.get('line_coverage_non_penalised_mean')):.2f} | "
                f"branch pen={f(r.get('branch_coverage_penalised_mean')):.2f} nonpen={f(r.get('branch_coverage_non_penalised_mean')):.2f} | "
                f"mutation pen={f(r.get('mutation_score_penalised_mean')):.2f} nonpen={f(r.get('mutation_score_non_penalised_mean')):.2f}"
            )


if __name__ == "__main__":
    main()
