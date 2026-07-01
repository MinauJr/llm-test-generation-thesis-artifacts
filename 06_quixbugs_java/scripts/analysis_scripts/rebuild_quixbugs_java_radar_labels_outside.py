#!/usr/bin/env python3

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HOME = Path.home()
FIG_DIR = HOME / "analysis_quixbugs_java" / "figures"

INPUT_CSV = FIG_DIR / "quixbugs_java_radar_summary_with_official.csv"
OUTPUT_PNG = FIG_DIR / "quixbugs_java_radar_tools_as_axes_with_official.png"

if not INPUT_CSV.exists():
    raise RuntimeError(f"Não encontrei o CSV do radar: {INPUT_CSV}")

with INPUT_CSV.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise RuntimeError("O CSV do radar está vazio.")

required = [
    "approach",
    "executable_pct",
    "line_penalized",
    "branch_penalized",
    "mutation_penalized",
]
for col in required:
    if col not in rows[0]:
        raise RuntimeError(f"Falta a coluna obrigatória: {col}")

labels = [r["approach"] for r in rows]

def col_values(name):
    vals = []
    for r in rows:
        raw = str(r[name]).strip()
        if raw == "":
            raise RuntimeError(f"Valor vazio em {name} para {r['approach']}")
        vals.append(float(raw))
    return vals

series = {
    "Executable suites": col_values("executable_pct"),
    "Line coverage": col_values("line_penalized"),
    "Branch coverage": col_values("branch_penalized"),
    "Mutation score": col_values("mutation_penalized"),
}

plot_order = [
    ("Executable suites", "C0"),
    ("Line coverage", "C1"),
    ("Branch coverage", "C2"),
    ("Mutation score", "C3"),
]

N = len(labels)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False)
angles_closed = np.concatenate([angles, [angles[0]]])

fig = plt.figure(figsize=(14, 12))
ax = plt.subplot(111, polar=True)

# orientação igual à que já tinhas
ax.set_theta_offset(0.0)
ax.set_theta_direction(1)

# encolher a área do radar para sobrar espaço aos nomes
ax.set_position([0.10, 0.16, 0.80, 0.80])

# esconder labels automáticos
ax.set_xticks(angles)
ax.set_xticklabels([])

ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=13)
ax.set_rlabel_position(22.5)
ax.grid(True, alpha=0.35)

# desenhar séries
for name, color in plot_order:
    vals = series[name]
    vals_closed = vals + vals[:1]
    ax.plot(angles_closed, vals_closed, linewidth=2.4, color=color, label=name)
    ax.fill(angles_closed, vals_closed, color=color, alpha=0.08)

# desenhar labels MANUALMENTE fora da circunferência
label_radius = 115

for angle, label in zip(angles, labels):
    deg = np.degrees(angle)

    # alinhamento horizontal consoante a posição angular
    if deg < 15 or deg > 345:
        ha = "left"
    elif 15 <= deg < 165:
        ha = "center"
    elif 165 <= deg <= 195:
        ha = "right"
    else:
        ha = "center"

    # pequenos ajustes extra para os casos chatos
    radius = label_radius
    if label == "Dataset tests":
        radius = 118
        ha = "left"
    elif label == "DeepSeek-Coder-V2":
        radius = 119
        ha = "center"
    elif label == "GPT-4o":
        radius = 116
    elif label == "GPT-5.5":
        radius = 117

    ax.text(
        angle,
        radius,
        label,
        fontsize=18,
        ha=ha,
        va="center",
        clip_on=False,
    )

ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, -0.14),
    ncol=4,
    frameon=True,
    fontsize=13,
)

fig.savefig(OUTPUT_PNG, dpi=200, bbox_inches="tight")
plt.close(fig)

print("===== QUIXBUGS JAVA RADAR REBUILT =====")
print(f"[INPUT]  {INPUT_CSV}")
print(f"[OUTPUT] {OUTPUT_PNG}")
