#!/usr/bin/env python3

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


HOME = Path.home()
FIG_DIR = HOME / "analysis_humanevalx_java" / "figures"

RADAR_CSV = FIG_DIR / "humanevalx_java_radar_summary_with_official.csv"
BAR_CSV = FIG_DIR / "humanevalx_java_stacked_3metrics_with_official_summary.csv"

RADAR_PNG = FIG_DIR / "humanevalx_java_radar_tools_as_axes_with_official.png"
BAR_PNG = FIG_DIR / "humanevalx_java_stacked_3metrics_with_official.png"

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


def read_csv(path):
    if not path.exists():
        raise RuntimeError(f"Não encontrei o ficheiro: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise RuntimeError(f"CSV vazio: {path}")

    return rows


def f(row, key):
    raw = row.get(key)
    if raw is None or str(raw).strip() == "":
        raise RuntimeError(f"{row.get('approach')}: valor vazio em {key}")
    return float(str(raw).replace("%", "").strip())


# ============================================================
# LER DADOS JÁ CORRETOS
# ============================================================

radar_rows_raw = read_csv(RADAR_CSV)
bar_rows_raw = read_csv(BAR_CSV)

radar_by_name = {row["approach"]: row for row in radar_rows_raw}
bar_by_name = {row["approach"]: row for row in bar_rows_raw}

missing_radar = [x for x in ORDER if x not in radar_by_name]
missing_bar = [x for x in ORDER if x not in bar_by_name]

if missing_radar:
    raise RuntimeError("Faltam no radar CSV: " + ", ".join(missing_radar))

if missing_bar:
    raise RuntimeError("Faltam no bar CSV: " + ", ".join(missing_bar))

radar_rows = [radar_by_name[x] for x in ORDER]
bar_rows = [bar_by_name[x] for x in ORDER]

# validação: garantir que DeepSeek-V2-Lite já não está
for row in radar_rows_raw + bar_rows_raw:
    if row.get("approach") == "DeepSeek-V2-Lite":
        raise RuntimeError("DeepSeek-V2-Lite ainda está presente nos CSVs.")

labels = ORDER

exec_vals = np.array([f(row, "executable_pct") for row in radar_rows])
line_vals = np.array([f(row, "line_penalized") for row in radar_rows])
branch_vals = np.array([f(row, "branch_penalized") for row in radar_rows])
mutation_vals = np.array([f(row, "mutation_penalized") for row in radar_rows])

line_p = np.array([f(row, "line_penalized") for row in bar_rows])
branch_p = np.array([f(row, "branch_penalized") for row in bar_rows])
mutation_p = np.array([f(row, "mutation_penalized") for row in bar_rows])

line_np = np.array([f(row, "line_nonpenalized") for row in bar_rows])
branch_np = np.array([f(row, "branch_nonpenalized") for row in bar_rows])
mutation_np = np.array([f(row, "mutation_nonpenalized") for row in bar_rows])

# ============================================================
# SPYDER CHART — APENAS LABELS MAIS FORA
# ============================================================

n = len(labels)
angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
angles_closed = np.concatenate([angles, [angles[0]]])


def close(values):
    return np.concatenate([values, [values[0]]])


fig = plt.figure(figsize=(12.6, 11.6))
ax = plt.subplot(111, polar=True)

ax.set_theta_offset(0.0)
ax.set_theta_direction(1)

# Encolher ligeiramente a bola para dar espaço real aos nomes
ax.set_position([0.12, 0.19, 0.76, 0.72])

# Manter os raios/grelha, mas esconder os labels automáticos
ax.set_xticks(angles)
ax.set_xticklabels([])

ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=12)
ax.set_rlabel_position(22.5)
ax.grid(True, alpha=0.35)

# Mesmas cores do gráfico atual
ax.plot(angles_closed, close(exec_vals), linewidth=2.3, color="C0", label="Executable suites")
ax.fill(angles_closed, close(exec_vals), color="C0", alpha=0.08)

ax.plot(angles_closed, close(line_vals), linewidth=2.3, color="C1", label="Line coverage")
ax.fill(angles_closed, close(line_vals), color="C1", alpha=0.05)

ax.plot(angles_closed, close(branch_vals), linewidth=2.3, color="C2", label="Branch coverage")
ax.fill(angles_closed, close(branch_vals), color="C2", alpha=0.05)

ax.plot(angles_closed, close(mutation_vals), linewidth=2.3, color="C3", label="Mutation score")
ax.fill(angles_closed, close(mutation_vals), color="C3", alpha=0.05)

# Labels manuais FORA da bola.
# Isto resolve especificamente Dataset tests e CodeLlama.
for angle, label in zip(angles, labels):
    deg = math.degrees(angle)

    radius = 113
    fontsize = 15

    if label == "Dataset tests":
        radius = 118
        ha = "left"
    elif label == "CodeLlama":
        radius = 118
        ha = "right"
    elif 0 < deg < 90:
        ha = "left"
    elif 90 <= deg < 180:
        ha = "right"
    elif 180 <= deg < 270:
        ha = "right"
    else:
        ha = "left"

    if abs(deg - 90) < 10 or abs(deg - 270) < 10:
        ha = "center"

    ax.text(
        angle,
        radius,
        label,
        fontsize=fontsize,
        ha=ha,
        va="center",
        clip_on=False,
    )

ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, -0.145),
    ncol=4,
    frameon=True,
    fontsize=12,
)

fig.savefig(RADAR_PNG, dpi=220, bbox_inches="tight")
plt.close(fig)

# ============================================================
# BARCHART — APENAS LEGENDA MAIS BAIXO
# ============================================================

x = np.arange(len(labels))
width = 0.22

line_u = np.maximum(line_np - line_p, 0.0)
branch_u = np.maximum(branch_np - branch_p, 0.0)
mutation_u = np.maximum(mutation_np - mutation_p, 0.0)

fig, ax = plt.subplots(figsize=(16, 7.8))

ax.bar(x - width, line_p, width, color="C1", label="Line coverage")
ax.bar(x, branch_p, width, color="C2", label="Branch coverage")
ax.bar(x + width, mutation_p, width, color="C3", label="Mutation score")

ax.bar(x - width, line_u, width, bottom=line_p, color="C1", alpha=0.25, edgecolor="C1", hatch="///")
ax.bar(x, branch_u, width, bottom=branch_p, color="C2", alpha=0.25, edgecolor="C2", hatch="///")
ax.bar(x + width, mutation_u, width, bottom=mutation_p, color="C3", alpha=0.25, edgecolor="C3", hatch="///")

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

# Descer bem a legenda para não sobrepor DeepSeek-Coder-V2
ax.legend(
    handles=legend_handles,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.47),
    ncol=3,
    frameon=True,
    fontsize=12,
)

fig.subplots_adjust(
    left=0.06,
    right=0.99,
    top=0.98,
    bottom=0.43,
)

fig.savefig(BAR_PNG, dpi=220, bbox_inches="tight")
plt.close(fig)

print("===== HUMANEVALX JAVA LAYOUT FIX OK =====")
print("[OK] Spyder: labels desenhados manualmente fora da bola")
print("[OK] Spyder: Dataset tests e CodeLlama afastados")
print("[OK] Barchart: legenda baixada")
print("[OK] Valores/dados não foram alterados")
print()
print(f"[RADAR] {RADAR_PNG}")
print(f"[BAR]   {BAR_PNG}")
