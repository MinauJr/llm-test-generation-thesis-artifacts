#!/usr/bin/env python3
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


FIG_DIR = Path.home() / "analysis_humanevalplus" / "figures"
SUMMARY_CSV = FIG_DIR / "humanevalplus_approach_summary_strict0.csv"
OUT_PNG = FIG_DIR / "humanevalplus_radar_tools_as_axes.png"


APPROACH_LABELS = {
    "Pynguin": "Pynguin",
    "GPT-4o": "GPT-4o",
    "GPT-5.5": "GPT-5.5",
    "Claude Opus 4.7": "Claude 4.7",
    "cluster-max-codellama-7b-instruct-ctx16k [structfix]": "CodeLlama",
    "cluster-safe-codestral-22b-ctx16k": "Codestral",
    "cluster-safe-deepseek-coder-v2-16b-ctx16k": "DeepSeek-Coder-V2",
    "cluster-safe-deepseek-v2-ctx32k [structfix]": "DeepSeek-V2",
    "cluster-safe-qwen2.5-coder-14b-ctx32k": "Qwen2.5-Coder",
    "cluster-safe-qwen3-coder-30b-official-ctx32k": "Qwen3-Coder",
    "cluster-safe-qwen3.5-9b-ctx32k": "Qwen3.5",
}

APPROACH_ORDER = [
    "Pynguin",
    "GPT-4o",
    "GPT-5.5",
    "Claude Opus 4.7",
    "cluster-max-codellama-7b-instruct-ctx16k [structfix]",
    "cluster-safe-codestral-22b-ctx16k",
    "cluster-safe-deepseek-coder-v2-16b-ctx16k",
    "cluster-safe-deepseek-v2-ctx32k [structfix]",
    "cluster-safe-qwen2.5-coder-14b-ctx32k",
    "cluster-safe-qwen3-coder-30b-official-ctx32k",
    "cluster-safe-qwen3.5-9b-ctx32k",
]

METRICS = [
    ("executable_suites_pct", "Executable suites"),
    ("line_coverage_pct", "Line coverage"),
    ("branch_coverage_pct", "Branch coverage"),
    ("mutation_score_pct", "Mutation score"),
]


def as_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def load_rows():
    with SUMMARY_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))

    by_approach = {r["approach"]: r for r in rows}
    return [by_approach[a] for a in APPROACH_ORDER if a in by_approach]


def text_alignment(angle_rad):
    x = np.cos(angle_rad)
    y = np.sin(angle_rad)

    if x > 0.25:
        ha = "left"
    elif x < -0.25:
        ha = "right"
    else:
        ha = "center"

    if y > 0.25:
        va = "bottom"
    elif y < -0.25:
        va = "top"
    else:
        va = "center"

    return ha, va


def plot(rows):
    labels = [APPROACH_LABELS[r["approach"]] for r in rows]

    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    angles_closed = list(angles) + [angles[0]]

    fig = plt.figure(figsize=(15.5, 11.0))
    ax = plt.subplot(111, polar=True)

    ax.set_xticks(angles)
    ax.set_xticklabels([])

    for metric_key, metric_label in METRICS:
        values = [as_float(r[metric_key]) for r in rows]
        values += values[:1]

        ax.plot(angles_closed, values, linewidth=2.8, label=metric_label)
        ax.fill(angles_closed, values, alpha=0.035)

    ax.set_ylim(0, 114)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=13)

    label_radius = 124
    for angle, label in zip(angles, labels):
        ha, va = text_alignment(angle)
        ax.text(
            angle,
            label_radius,
            label,
            size=16,
            ha=ha,
            va=va,
            clip_on=False,
        )

    # Sem título, como pedido pelo professor.

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=4,
        frameon=True,
        fontsize=16,
    )

    fig.subplots_adjust(
        top=0.91,
        bottom=0.17,
        left=0.09,
        right=0.91,
    )

    plt.savefig(OUT_PNG, dpi=300, bbox_inches="tight", pad_inches=0.45)
    plt.close()


def main():
    rows = load_rows()
    plot(rows)

    print(f"[FIG] {OUT_PNG}")
    print()
    print("===== APPROACHES USED =====")
    for r in rows:
        print(
            f"{APPROACH_LABELS[r['approach']]:20s} | "
            f"exec={as_float(r['executable_suites_pct']):6.2f} | "
            f"line={as_float(r['line_coverage_pct']):6.2f} | "
            f"branch={as_float(r['branch_coverage_pct']):6.2f} | "
            f"mut={as_float(r['mutation_score_pct']):6.2f}"
        )


if __name__ == "__main__":
    main()
