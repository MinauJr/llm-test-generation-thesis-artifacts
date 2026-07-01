#!/usr/bin/env python3
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


FIG_DIR = Path.home() / "analysis_defects4j" / "figures"

RADAR_CSV = FIG_DIR / "defects4j_radar_summary_with_official.csv"
STACKED_CSV = FIG_DIR / "defects4j_stacked_3metrics_with_official_summary.csv"

RADAR_OUT = FIG_DIR / "defects4j_radar_tools_as_axes_with_official.png"
STACKED_OUT = FIG_DIR / "defects4j_stacked_3metrics_with_official.png"


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def f(row, key):
    return float(row[key])


def build_radar(rows):
    labels = [r["approach"] for r in rows]

    executable = [f(r, "executable_pct") for r in rows]
    line = [f(r, "line_penalized") for r in rows]
    branch = [f(r, "branch_penalized") for r in rows]
    mutation = [f(r, "mutation_penalized") for r in rows]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    executable += executable[:1]
    line += line[:1]
    branch += branch[:1]
    mutation += mutation[:1]

    fig = plt.figure(figsize=(14, 14))
    ax = plt.subplot(111, polar=True)

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=11)
    ax.set_rlabel_position(22)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.tick_params(axis='x', pad=22)   # afasta os nomes do gráfico

    # Pequeno ajuste extra para labels mais problemáticas
    for lbl in ax.get_xticklabels():
        txt = lbl.get_text()
        if txt in {"Qwen2.5-Coder", "Qwen3-Coder", "Qwen3.5"}:
            lbl.set_fontsize(10.5)
        if txt in {"Dataset tests", "Claude 4.7"}:
            lbl.set_fontsize(10.5)

    ax.plot(angles, executable, linewidth=2.3, label="Executable suites")
    ax.fill(angles, executable, alpha=0.08)

    ax.plot(angles, line, linewidth=2.3, label="Line coverage")
    ax.fill(angles, line, alpha=0.05)

    ax.plot(angles, branch, linewidth=2.3, label="Branch coverage")
    ax.fill(angles, branch, alpha=0.05)

    ax.plot(angles, mutation, linewidth=2.3, label="Mutation score")
    ax.fill(angles, mutation, alpha=0.05)

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=4,
        fontsize=11,
        frameon=True
    )

    plt.subplots_adjust(top=0.96, bottom=0.18, left=0.05, right=0.95)
    fig.savefig(RADAR_OUT, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_stacked(rows):
    labels = [r["approach"] for r in rows]

    line_pen = [f(r, "line_penalized") for r in rows]
    line_non = [f(r, "line_nonpenalized") for r in rows]
    line_uplift = [max(0.0, n - p) for p, n in zip(line_pen, line_non)]

    branch_pen = [f(r, "branch_penalized") for r in rows]
    branch_non = [f(r, "branch_nonpenalized") for r in rows]
    branch_uplift = [max(0.0, n - p) for p, n in zip(branch_pen, branch_non)]

    mut_pen = [f(r, "mutation_penalized") for r in rows]
    mut_non = [f(r, "mutation_nonpenalized") for r in rows]
    mut_uplift = [max(0.0, n - p) for p, n in zip(mut_pen, mut_non)]

    x = np.arange(len(labels))
    width = 0.22

    fig, ax = plt.subplots(figsize=(18, 9))

    b1 = ax.bar(x - width, line_pen, width, label="Line coverage")
    ax.bar(
        x - width, line_uplift, width, bottom=line_pen,
        hatch="///", alpha=0.25
    )

    b2 = ax.bar(x, branch_pen, width, label="Branch coverage")
    ax.bar(
        x, branch_uplift, width, bottom=branch_pen,
        hatch="///", alpha=0.25
    )

    b3 = ax.bar(x + width, mut_pen, width, label="Mutation score")
    ax.bar(
        x + width, mut_uplift, width, bottom=mut_pen,
        hatch="///", alpha=0.25
    )

    ax.set_ylabel("%", fontsize=16)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 10))
    ax.tick_params(axis='y', labelsize=12)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=11)

    legend_handles = [
        b1[0],
        b2[0],
        b3[0],
        Patch(facecolor="lightgray", edgecolor="gray", label="Penalised mean"),
        Patch(facecolor="white", edgecolor="black", hatch="///", label="Additional uplift to non-penalised mean"),
    ]

    ax.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.23),
        ncol=3,
        fontsize=11,
        frameon=True
    )

    ax.grid(axis="y", alpha=0.25)

    plt.subplots_adjust(bottom=0.30, left=0.06, right=0.99, top=0.98)
    fig.savefig(STACKED_OUT, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main():
    radar_rows = load_csv(RADAR_CSV)
    stacked_rows = load_csv(STACKED_CSV)

    build_radar(radar_rows)
    build_stacked(stacked_rows)

    print("[OK] refined radar + stacked presentation")
    print(f"[FIG] {RADAR_OUT}")
    print(f"[FIG] {STACKED_OUT}")


if __name__ == "__main__":
    main()
