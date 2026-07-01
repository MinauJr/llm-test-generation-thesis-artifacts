#!/usr/bin/env python3

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


HOME = Path.home()
FIG_DIR = HOME / "analysis_humanevalx_java" / "figures"

INPUT_CSV = FIG_DIR / "humanevalx_java_approach_summary_strict0.csv"

RADAR_PNG = FIG_DIR / "humanevalx_java_radar_tools_as_axes_with_official.png"
BAR_PNG = FIG_DIR / "humanevalx_java_stacked_3metrics_with_official.png"

RADAR_CSV = FIG_DIR / "humanevalx_java_radar_summary_with_official.csv"
BAR_CSV = FIG_DIR / "humanevalx_java_stacked_3metrics_with_official_summary.csv"

# Ordem final pretendida: sem DeepSeek-V2-Lite
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
    "Qwen2.5-Coder",
    "Qwen3-Coder",
    "Qwen3.5",
]

REQUIRED_COLUMNS = [
    "approach",
    "executable_pct",
    "line_penalized",
    "branch_penalized",
    "mutation_penalized",
    "line_nonpenalized",
    "branch_nonpenalized",
    "mutation_nonpenalized",
]

IGNORE_APPROACHES = {
    "DeepSeek-V2-Lite",
}


def as_float(row, key):
    raw = row.get(key, "")
    if raw is None or str(raw).strip() == "":
        raise RuntimeError(f"{row.get('approach')}: campo vazio em {key}")
    return float(raw)


if not INPUT_CSV.exists():
    raise RuntimeError(f"Não encontrei o CSV de input: {INPUT_CSV}")

with INPUT_CSV.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

if not rows:
    raise RuntimeError(f"O CSV está vazio: {INPUT_CSV}")

missing_cols = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
if missing_cols:
    raise RuntimeError(
        "Faltam colunas no CSV: " + ", ".join(missing_cols)
    )

by_approach = {}
for row in rows:
    approach = str(row["approach"]).strip()
    if approach in IGNORE_APPROACHES:
        continue
    by_approach[approach] = row

missing = [a for a in ORDER if a not in by_approach]
if missing:
    raise RuntimeError(
        "Faltam abordagens necessárias no CSV: " + ", ".join(missing)
    )

ordered_rows = [by_approach[a] for a in ORDER]

# -----------------------------
# Guardar CSVs filtrados
# -----------------------------
with RADAR_CSV.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "approach",
            "executable_pct",
            "line_penalized",
            "branch_penalized",
            "mutation_penalized",
        ],
    )
    writer.writeheader()
    for row in ordered_rows:
        writer.writerow({
            "approach": row["approach"],
            "executable_pct": row["executable_pct"],
            "line_penalized": row["line_penalized"],
            "branch_penalized": row["branch_penalized"],
            "mutation_penalized": row["mutation_penalized"],
        })

with BAR_CSV.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "approach",
            "line_penalized",
            "branch_penalized",
            "mutation_penalized",
            "line_nonpenalized",
            "branch_nonpenalized",
            "mutation_nonpenalized",
        ],
    )
    writer.writeheader()
    for row in ordered_rows:
        writer.writerow({
            "approach": row["approach"],
            "line_penalized": row["line_penalized"],
            "branch_penalized": row["branch_penalized"],
            "mutation_penalized": row["mutation_penalized"],
            "line_nonpenalized": row["line_nonpenalized"],
            "branch_nonpenalized": row["branch_nonpenalized"],
            "mutation_nonpenalized": row["mutation_nonpenalized"],
        })

# -----------------------------
# Preparar arrays
# -----------------------------
labels = [row["approach"] for row in ordered_rows]

exec_vals = np.array([as_float(row, "executable_pct") for row in ordered_rows])
line_pen = np.array([as_float(row, "line_penalized") for row in ordered_rows])
branch_pen = np.array([as_float(row, "branch_penalized") for row in ordered_rows])
mutation_pen = np.array([as_float(row, "mutation_penalized") for row in ordered_rows])

line_non = np.array([as_float(row, "line_nonpenalized") for row in ordered_rows])
branch_non = np.array([as_float(row, "branch_nonpenalized") for row in ordered_rows])
mutation_non = np.array([as_float(row, "mutation_nonpenalized") for row in ordered_rows])

line_uplift = np.maximum(line_non - line_pen, 0.0)
branch_uplift = np.maximum(branch_non - branch_pen, 0.0)
mutation_uplift = np.maximum(mutation_non - mutation_pen, 0.0)

# -----------------------------
# SPIDER / RADAR
# -----------------------------
N = len(labels)
angles = np.linspace(0, 2 * math.pi, N, endpoint=False).tolist()
angles += angles[:1]

def close(vals):
    return np.concatenate([vals, vals[:1]])

fig = plt.figure(figsize=(10.5, 10.5))
ax = plt.subplot(111, polar=True)

ax.set_theta_offset(0.0)
ax.set_theta_direction(1)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels, fontsize=15)
ax.tick_params(axis="x", pad=20)

ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=12)

# Cores iguais ao spider correto:
# executable blue, line orange, branch green, mutation red
ax.plot(angles, close(exec_vals), linewidth=2.4, color="C0", label="Executable suites")
ax.fill(angles, close(exec_vals), color="C0", alpha=0.08)

ax.plot(angles, close(line_pen), linewidth=2.4, color="C1", label="Line coverage")
ax.plot(angles, close(branch_pen), linewidth=2.4, color="C2", label="Branch coverage")
ax.plot(angles, close(mutation_pen), linewidth=2.4, color="C3", label="Mutation score")

ax.fill(angles, close(line_pen), color="C1", alpha=0.06)
ax.fill(angles, close(branch_pen), color="C2", alpha=0.06)
ax.fill(angles, close(mutation_pen), color="C3", alpha=0.06)

ax.grid(alpha=0.35)

ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, -0.16),
    ncol=4,
    frameon=True,
    fontsize=12,
)

fig.subplots_adjust(top=0.96, bottom=0.16, left=0.06, right=0.94)
fig.savefig(RADAR_PNG, dpi=220, bbox_inches="tight")
plt.close(fig)

# -----------------------------
# BARCHART
# -----------------------------
x = np.arange(len(labels))
width = 0.22

fig, ax = plt.subplots(figsize=(16, 7.2))

# Cores corretas:
# line = orange (C1)
# branch = green (C2)
# mutation = red (C3)
ax.bar(x - width, line_pen, width, color="C1", label="Line coverage")
ax.bar(x, branch_pen, width, color="C2", label="Branch coverage")
ax.bar(x + width, mutation_pen, width, color="C3", label="Mutation score")

ax.bar(
    x - width,
    line_uplift,
    width,
    bottom=line_pen,
    color="C1",
    alpha=0.25,
    edgecolor="C1",
    hatch="///",
)

ax.bar(
    x,
    branch_uplift,
    width,
    bottom=branch_pen,
    color="C2",
    alpha=0.25,
    edgecolor="C2",
    hatch="///",
)

ax.bar(
    x + width,
    mutation_uplift,
    width,
    bottom=mutation_pen,
    color="C3",
    alpha=0.25,
    edgecolor="C3",
    hatch="///",
)

ax.set_ylabel("%", fontsize=18)
ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 10))
ax.tick_params(axis="y", labelsize=12)

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=33, ha="right", fontsize=12)

ax.grid(axis="y", alpha=0.24)
ax.set_axisbelow(True)

legend_handles = [
    Patch(facecolor="C1", label="Line coverage"),
    Patch(facecolor="C2", label="Branch coverage"),
    Patch(facecolor="C3", label="Mutation score"),
    Patch(facecolor="lightgray", edgecolor="gray", label="Penalised mean"),
    Patch(facecolor="white", edgecolor="black", hatch="///", label="Additional uplift to non-penalised mean"),
]

ax.legend(
    handles=legend_handles,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.34),
    ncol=3,
    frameon=True,
    fontsize=12,
)

fig.subplots_adjust(left=0.06, right=0.99, top=0.98, bottom=0.33)
fig.savefig(BAR_PNG, dpi=220, bbox_inches="tight")
plt.close(fig)

print("===== HUMANEVALX JAVA CORRECTED FIGURES =====")
print("[OK] Removed approach: DeepSeek-V2-Lite")
print("[OK] Barchart colours fixed to match spider chart")
print()
print("Approaches plotted:")
for label in labels:
    print(f" - {label}")
print()
print(f"[INPUT CSV] {INPUT_CSV}")
print(f"[OUT RADAR PNG] {RADAR_PNG}")
print(f"[OUT BAR PNG]   {BAR_PNG}")
print(f"[OUT RADAR CSV] {RADAR_CSV}")
print(f"[OUT BAR CSV]   {BAR_CSV}")
