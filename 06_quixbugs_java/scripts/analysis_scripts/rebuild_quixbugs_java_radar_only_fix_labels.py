#!/usr/bin/env python3

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HOME = Path.home()
FIG_DIR = HOME / "analysis_quixbugs_java" / "figures"

IN_CANDIDATES = [
    FIG_DIR / "quixbugs_java_radar_summary_with_official.csv",
    FIG_DIR / "quixbugs_java_approach_summary_strict0.csv",
]

INPUT = None
for candidate in IN_CANDIDATES:
    if candidate.exists():
        INPUT = candidate
        break

if INPUT is None:
    raise RuntimeError(
        "Não encontrei nenhum ficheiro de input para o radar chart em:\n"
        f"  - {IN_CANDIDATES[0]}\n"
        f"  - {IN_CANDIDATES[1]}"
    )

OUT = FIG_DIR / "quixbugs_java_radar_tools_as_axes_with_official.png"

with INPUT.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise RuntimeError(f"O ficheiro está vazio: {INPUT}")

required_cols = [
    "approach",
    "executable_pct",
    "line_penalized",
    "branch_penalized",
    "mutation_penalized",
]

missing = [c for c in required_cols if c not in rows[0]]
if missing:
    raise RuntimeError(
        f"Faltam colunas no ficheiro {INPUT}: {', '.join(missing)}"
    )

labels = [r["approach"] for r in rows]

def vals(col):
    out = []
    for r in rows:
        raw = r[col]
        if raw is None or str(raw).strip() == "":
            raise RuntimeError(
                f"Valor vazio na coluna {col} para approach={r['approach']}"
            )
        out.append(float(raw))
    return out

series = {
    "Executable suites": vals("executable_pct"),
    "Line coverage": vals("line_penalized"),
    "Branch coverage": vals("branch_penalized"),
    "Mutation score": vals("mutation_penalized"),
}

n = len(labels)
angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
angles_closed = angles + angles[:1]

fig = plt.figure(figsize=(11, 10))
ax = plt.subplot(111, polar=True)

# Mantém a orientação igual à que tens usado:
# primeiro label à direita, sentido anti-horário.
ax.set_theta_offset(0.0)
ax.set_theta_direction(1)

ax.set_xticks(angles)
ax.set_xticklabels(labels, fontsize=15)

# AQUI está a correção principal:
# afasta os nomes do círculo do gráfico
ax.tick_params(axis="x", pad=26)

# Dá mais espaço à volta do radar para não tocar nos labels
ax.set_position([0.08, 0.20, 0.84, 0.75])

ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=12)
ax.grid(True, alpha=0.35)

plot_order = [
    ("Executable suites", "C0"),
    ("Line coverage", "C1"),
    ("Branch coverage", "C2"),
    ("Mutation score", "C3"),
]

for name, color in plot_order:
    values = series[name]
    closed = values + values[:1]
    ax.plot(angles_closed, closed, linewidth=2.2, label=name, color=color)
    ax.fill(angles_closed, closed, color=color, alpha=0.08)

ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, -0.14),
    ncol=4,
    frameon=True,
    fontsize=12,
)

fig.savefig(OUT, dpi=200, bbox_inches="tight")
plt.close(fig)

print("===== QUIXBUGS JAVA RADAR REBUILT =====")
print(f"[INPUT]  {INPUT}")
print(f"[OUTPUT] {OUT}")
