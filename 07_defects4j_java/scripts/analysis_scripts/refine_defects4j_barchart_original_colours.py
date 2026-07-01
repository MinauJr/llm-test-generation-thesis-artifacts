#!/usr/bin/env python3
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


FIG_DIR = Path.home() / "analysis_defects4j" / "figures"
STACKED_CSV = FIG_DIR / "defects4j_stacked_3metrics_with_official_summary.csv"
STACKED_OUT = FIG_DIR / "defects4j_stacked_3metrics_with_official.png"


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def val(row, key):
    return float(row[key])


rows = load_csv(STACKED_CSV)
labels = [r["approach"] for r in rows]

line_pen = [val(r, "line_penalized") for r in rows]
line_non = [val(r, "line_nonpenalized") for r in rows]
line_uplift = [max(0.0, n - p) for p, n in zip(line_pen, line_non)]

branch_pen = [val(r, "branch_penalized") for r in rows]
branch_non = [val(r, "branch_nonpenalized") for r in rows]
branch_uplift = [max(0.0, n - p) for p, n in zip(branch_pen, branch_non)]

mut_pen = [val(r, "mutation_penalized") for r in rows]
mut_non = [val(r, "mutation_nonpenalized") for r in rows]
mut_uplift = [max(0.0, n - p) for p, n in zip(mut_pen, mut_non)]

x = np.arange(len(labels))
width = 0.22

# Original matplotlib colours used in the other final charts
LINE_COLOR = "#1f77b4"
BRANCH_COLOR = "#ff7f0e"
MUTATION_COLOR = "#2ca02c"

fig, ax = plt.subplots(figsize=(18, 9))

# Solid part = penalised mean
ax.bar(
    x - width,
    line_pen,
    width,
    color=LINE_COLOR,
    edgecolor=LINE_COLOR,
    linewidth=0.6,
)

ax.bar(
    x,
    branch_pen,
    width,
    color=BRANCH_COLOR,
    edgecolor=BRANCH_COLOR,
    linewidth=0.6,
)

ax.bar(
    x + width,
    mut_pen,
    width,
    color=MUTATION_COLOR,
    edgecolor=MUTATION_COLOR,
    linewidth=0.6,
)

# Hatched part = uplift to non-penalised mean
ax.bar(
    x - width,
    line_uplift,
    width,
    bottom=line_pen,
    color=LINE_COLOR,
    edgecolor=LINE_COLOR,
    hatch="///",
    alpha=0.25,
    linewidth=0.8,
)

ax.bar(
    x,
    branch_uplift,
    width,
    bottom=branch_pen,
    color=BRANCH_COLOR,
    edgecolor=BRANCH_COLOR,
    hatch="///",
    alpha=0.25,
    linewidth=0.8,
)

ax.bar(
    x + width,
    mut_uplift,
    width,
    bottom=mut_pen,
    color=MUTATION_COLOR,
    edgecolor=MUTATION_COLOR,
    hatch="///",
    alpha=0.25,
    linewidth=0.8,
)

ax.set_ylabel("%", fontsize=16)
ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 10))
ax.tick_params(axis="y", labelsize=12)

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=11)

ax.grid(axis="y", alpha=0.25)

legend_handles = [
    Patch(facecolor=LINE_COLOR, edgecolor=LINE_COLOR, label="Line coverage"),
    Patch(facecolor=BRANCH_COLOR, edgecolor=BRANCH_COLOR, label="Branch coverage"),
    Patch(facecolor=MUTATION_COLOR, edgecolor=MUTATION_COLOR, label="Mutation score"),
    Patch(facecolor="lightgray", edgecolor="gray", label="Penalised mean"),
    Patch(facecolor="white", edgecolor="black", hatch="///", label="Additional uplift to non-penalised mean"),
]

ax.legend(
    handles=legend_handles,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.23),
    ncol=3,
    fontsize=11,
    frameon=True,
)

plt.subplots_adjust(bottom=0.30, left=0.06, right=0.99, top=0.98)
fig.savefig(STACKED_OUT, dpi=220, bbox_inches="tight")
plt.close(fig)

print("[OK] rebuilt only Defects4J stacked bar chart with original colours")
print(f"[FIG] {STACKED_OUT}")
