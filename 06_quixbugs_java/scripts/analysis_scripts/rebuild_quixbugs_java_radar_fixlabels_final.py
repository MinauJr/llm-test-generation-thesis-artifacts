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
    raise RuntimeError(f"Não encontrei o CSV: {INPUT_CSV}")

with INPUT_CSV.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise RuntimeError("O CSV do radar está vazio.")

required_cols = [
    "approach",
    "executable_pct",
    "line_penalized",
    "branch_penalized",
    "mutation_penalized",
]
for col in required_cols:
    if col not in rows[0]:
        raise RuntimeError(f"Falta a coluna obrigatória: {col}")

labels = [r["approach"] for r in rows]

def get_float_series(col):
    vals = []
    for r in rows:
        raw = str(r[col]).strip()
        if raw == "":
            raise RuntimeError(f"Valor vazio em {col} para {r['approach']}")
        vals.append(float(raw))
    return vals

series = {
    "Executable suites": get_float_series("executable_pct"),
    "Line coverage": get_float_series("line_penalized"),
    "Branch coverage": get_float_series("branch_penalized"),
    "Mutation score": get_float_series("mutation_penalized"),
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

fig = plt.figure(figsize=(13.5, 11.5))
ax = plt.subplot(111, polar=True)

# manter orientação semelhante à anterior
ax.set_theta_offset(0.0)
ax.set_theta_direction(1)

# ENCOLHER a área do radar para sobrar espaço aos nomes
ax.set_position([0.12, 0.17, 0.76, 0.72])

# labels do eixo angular
ax.set_xticks(angles)
ax.set_xticklabels(labels, fontsize=18)

# AFASTAR MESMO os labels do gráfico
ax.tick_params(axis="x", pad=34)

# ajuste fino para não ficarem colados ao topo
for lbl in ax.get_xticklabels():
    lbl.set_va("center")
    lbl.set_ha("center")

# raio
ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=13)

# meter os números radiais um pouco mais à direita
ax.set_rlabel_position(22.5)

ax.grid(True, alpha=0.35)

for name, color in plot_order:
    vals = series[name]
    vals_closed = vals + vals[:1]
    ax.plot(angles_closed, vals_closed, linewidth=2.4, color=color, label=name)
    ax.fill(angles_closed, vals_closed, color=color, alpha=0.08)

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
