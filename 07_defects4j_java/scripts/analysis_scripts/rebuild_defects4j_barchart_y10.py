#!/usr/bin/env python3

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

HOME = Path.home()
FIG_DIR = HOME / "analysis_defects4j" / "figures"

CSV_PATH = FIG_DIR / "defects4j_stacked_3metrics_with_official_summary.csv"
OUT_PATH = FIG_DIR / "defects4j_stacked_3metrics_with_official.png"

def pick(row, candidates):
    for c in candidates:
        if c in row and row[c] not in (None, ""):
            return row[c]
    return None

def get_float(row, candidates, label):
    value = pick(row, candidates)
    if value is None:
        raise RuntimeError(f"{label}: valor em falta nas colunas {candidates}")
    return float(str(value).replace("%", "").strip())

with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise RuntimeError("O CSV está vazio.")

labels = []
line_pen = []
line_non = []
branch_pen = []
branch_non = []
mutation_pen = []
mutation_non = []

for row in rows:
    label = pick(row, ["label", "approach"])
    if not label:
        raise RuntimeError("Encontrei uma linha sem label/approach.")
    labels.append(label)

    line_pen.append(get_float(row, ["line_coverage_penalised_mean", "line_penalized"], f"{label} line_pen"))
    line_non.append(get_float(row, ["line_coverage_non_penalised_mean", "line_nonpenalized"], f"{label} line_non"))

    branch_pen.append(get_float(row, ["branch_coverage_penalised_mean", "branch_penalized"], f"{label} branch_pen"))
    branch_non.append(get_float(row, ["branch_coverage_non_penalised_mean", "branch_nonpenalized"], f"{label} branch_non"))

    mutation_pen.append(get_float(row, ["mutation_score_penalised_mean", "mutation_penalized"], f"{label} mutation_pen"))
    mutation_non.append(get_float(row, ["mutation_score_non_penalised_mean", "mutation_nonpenalized"], f"{label} mutation_non"))

labels = np.array(labels)
line_pen = np.array(line_pen, dtype=float)
line_non = np.array(line_non, dtype=float)
branch_pen = np.array(branch_pen, dtype=float)
branch_non = np.array(branch_non, dtype=float)
mutation_pen = np.array(mutation_pen, dtype=float)
mutation_non = np.array(mutation_non, dtype=float)

line_uplift = np.maximum(0, line_non - line_pen)
branch_uplift = np.maximum(0, branch_non - branch_pen)
mutation_uplift = np.maximum(0, mutation_non - mutation_pen)

x = np.arange(len(labels))
width = 0.22

line_color = "#ff7f0e"
branch_color = "#2ca02c"
mutation_color = "#d62728"

fig, ax = plt.subplots(figsize=(20, 8))

ax.bar(x - width, line_pen, width, label="Line coverage", color=line_color)
ax.bar(
    x - width,
    line_uplift,
    width,
    bottom=line_pen,
    color=line_color,
    alpha=0.25,
    hatch="///",
    edgecolor=line_color,
)

ax.bar(x, branch_pen, width, label="Branch coverage", color=branch_color)
ax.bar(
    x,
    branch_uplift,
    width,
    bottom=branch_pen,
    color=branch_color,
    alpha=0.25,
    hatch="///",
    edgecolor=branch_color,
)

ax.bar(x + width, mutation_pen, width, label="Mutation score", color=mutation_color)
ax.bar(
    x + width,
    mutation_uplift,
    width,
    bottom=mutation_pen,
    color=mutation_color,
    alpha=0.25,
    hatch="///",
    edgecolor=mutation_color,
)

ax.set_ylabel("%", fontsize=22)
ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 10))   # <<< AQUI fica 10 em 10
ax.tick_params(axis="y", labelsize=17)

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=13)

ax.grid(axis="y", alpha=0.25)

legend_handles = [
    Patch(facecolor=line_color, edgecolor=line_color, label="Line coverage"),
    Patch(facecolor=branch_color, edgecolor=branch_color, label="Branch coverage"),
    Patch(facecolor=mutation_color, edgecolor=mutation_color, label="Mutation score"),
    Patch(facecolor="lightgray", edgecolor="lightgray", label="Penalised mean"),
    Patch(facecolor="white", edgecolor="black", hatch="///", label="Additional uplift to non-penalised mean"),
]

ax.legend(
    handles=legend_handles,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.18),
    ncol=3,
    frameon=True,
    fontsize=14,
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.30)
plt.savefig(OUT_PATH, dpi=200, bbox_inches="tight")

print("===== DONE =====")
print(f"INPUT_CSV={CSV_PATH}")
print(f"OUTPUT_PNG={OUT_PATH}")
print(f"APPROACHES={len(labels)}")
print("Y_TICKS=" + ", ".join(str(v) for v in range(0, 101, 10)))
