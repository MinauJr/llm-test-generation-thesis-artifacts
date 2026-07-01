#!/usr/bin/env python3

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HOME = Path.home()
FIG_DIR = HOME / "analysis_quixbugs_java" / "figures"

INPUT = FIG_DIR / "quixbugs_java_radar_summary_with_official.csv"
OUTPUT = FIG_DIR / "quixbugs_java_radar_tools_as_axes_with_official.png"

if not INPUT.exists():
    raise RuntimeError(f"Não encontrei o ficheiro de input: {INPUT}")

with INPUT.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise RuntimeError(f"Ficheiro vazio: {INPUT}")

required = [
    "approach",
    "executable_pct",
    "line_penalized",
    "branch_penalized",
    "mutation_penalized",
]
missing = [c for c in required if c not in rows[0]]
if missing:
    raise RuntimeError(f"Faltam colunas no CSV: {', '.join(missing)}")

labels = [r["approach"] for r in rows]

def get_vals(col):
    vals = []
    for r in rows:
        raw = r[col]
        if raw is None or str(raw).strip() == "":
            raise RuntimeError(f"Valor vazio em {col} para {r['approach']}")
        vals.append(float(raw))
    return vals

series = {
    "Executable suites": get_vals("executable_pct"),
    "Line coverage": get_vals("line_penalized"),
    "Branch coverage": get_vals("branch_penalized"),
    "Mutation score": get_vals("mutation_penalized"),
}

n = len(labels)
angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
angles_closed = np.concatenate([angles, [angles[0]]])

fig = plt.figure(figsize=(13, 11))
ax = plt.subplot(111, polar=True)

# mesma orientação de antes
ax.set_theta_offset(0.0)
ax.set_theta_direction(1)

# ENCOLHER o radar dentro da figura para sobrar espaço aos nomes
ax.set_position([0.11, 0.20, 0.78, 0.69])

# MOVER MESMO os labels para fora
ax.set_thetagrids(np.degrees(angles), labels=labels, frac=1.22)

for lbl in ax.get_xticklabels():
    lbl.set_fontsize(17)

ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=13)
ax.grid(True, alpha=0.35)

plot_order = [
    ("Executable suites", "C0"),
    ("Line coverage", "C1"),
    ("Branch coverage", "C2"),
    ("Mutation score", "C3"),
]

for name, color in plot_order:
    vals = series[name]
    vals_closed = vals + vals[:1]
    ax.plot(angles_closed, vals_closed, linewidth=2.4, label=name, color=color)
    ax.fill(angles_closed, vals_closed, color=color, alpha=0.08)

ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, -0.14),
    ncol=4,
    frameon=True,
    fontsize=13,
)

fig.savefig(OUTPUT, dpi=200, bbox_inches="tight")
plt.close(fig)

print("===== QUIXBUGS JAVA RADAR REBUILT V2 =====")
print(f"[INPUT]  {INPUT}")
print(f"[OUTPUT] {OUTPUT}")
