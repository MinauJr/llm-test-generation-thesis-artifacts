#!/usr/bin/env python3

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


HOME = Path.home()
FIG_DIR = HOME / "analysis_humanevalplus" / "figures"

BAR_CSV = FIG_DIR / "humanevalplus_stacked_3metrics_with_official_summary.csv"
RADAR_CSV = FIG_DIR / "humanevalplus_radar_summary_with_official.csv"
BAR_PNG = FIG_DIR / "humanevalplus_stacked_3metrics_with_official.png"

ORDER = [
    "Dataset tests",
    "Pynguin",
    "GPT-4o",
    "GPT-5.5",
    "Claude 4.7",
    "CodeLlama",
    "Codestral",
    "DeepSeek-Coder-V2",
    "DeepSeek-V2",
    "Qwen2.5-Coder",
    "Qwen3-Coder",
    "Qwen3.5",
]

# Cores corretas usadas nos outros gráficos finais
COLOR_EXEC = "tab:blue"
COLOR_LINE = "tab:orange"
COLOR_BRANCH = "tab:green"
COLOR_MUT = "tab:red"


def read_csv_rows(path: Path):
    if not path.exists():
        raise RuntimeError(f"Ficheiro em falta: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def get_label(row):
    for key in ("label", "approach", "model"):
        val = row.get(key)
        if val:
            return val.strip()
    raise RuntimeError(f"Linha sem label/approach/model: {row}")


def pick_float(row, label, field_names):
    for name in field_names:
        val = row.get(name)
        if val is not None and str(val).strip() != "":
            return float(str(val).strip())
    raise RuntimeError(f"{label}: campo em falta. Esperava um de {field_names}")


def load_bar_rows():
    rows = read_csv_rows(BAR_CSV)
    out = {}
    for row in rows:
        label = get_label(row)
        out[label] = {
            "line_pen": pick_float(row, label, [
                "line_penalized",
                "line_penalised",
                "line_coverage_penalised_mean",
                "line_coverage_penalized_mean",
                "line_coverage_pct",
            ]),
            "line_nonpen": pick_float(row, label, [
                "line_nonpenalized",
                "line_non_penalized",
                "line_nonpenalised",
                "line_non_penalised",
                "line_coverage_non_penalised_mean",
                "line_coverage_non_penalized_mean",
                "line_coverage_pct",
            ]),
            "branch_pen": pick_float(row, label, [
                "branch_penalized",
                "branch_penalised",
                "branch_coverage_penalised_mean",
                "branch_coverage_penalized_mean",
                "branch_coverage_pct",
            ]),
            "branch_nonpen": pick_float(row, label, [
                "branch_nonpenalized",
                "branch_non_penalized",
                "branch_nonpenalised",
                "branch_non_penalised",
                "branch_coverage_non_penalised_mean",
                "branch_coverage_non_penalized_mean",
                "branch_coverage_pct",
            ]),
            "mut_pen": pick_float(row, label, [
                "mutation_penalized",
                "mutation_penalised",
                "mutation_score_penalised_mean",
                "mutation_score_penalized_mean",
                "mutation_score_pct",
            ]),
            "mut_nonpen": pick_float(row, label, [
                "mutation_nonpenalized",
                "mutation_non_penalized",
                "mutation_nonpenalised",
                "mutation_non_penalised",
                "mutation_score_non_penalised_mean",
                "mutation_score_non_penalized_mean",
                "mutation_score_pct",
            ]),
        }
    return out


def load_radar_rows():
    rows = read_csv_rows(RADAR_CSV)
    out = {}
    for row in rows:
        label = get_label(row)
        out[label] = {
            "exec_pct": pick_float(row, label, [
                "executable_pct",
                "executable_suites_pct",
            ]),
            "line_pct": pick_float(row, label, [
                "line_coverage_pct",
                "line_penalized",
                "line_penalised",
                "line_coverage_penalised_mean",
            ]),
            "branch_pct": pick_float(row, label, [
                "branch_coverage_pct",
                "branch_penalized",
                "branch_penalised",
                "branch_coverage_penalised_mean",
            ]),
            "mut_pct": pick_float(row, label, [
                "mutation_score_pct",
                "mutation_penalized",
                "mutation_penalised",
                "mutation_score_penalised_mean",
            ]),
        }
    return out


bar = load_bar_rows()
radar = load_radar_rows()

print("===== HUMANEVAL+ CHECK =====")
for label in ORDER:
    if label not in bar:
        raise RuntimeError(f"Em falta no BAR_CSV: {label}")
    if label not in radar:
        raise RuntimeError(f"Em falta no RADAR_CSV: {label}")

    line_pen = bar[label]["line_pen"]
    branch_pen = bar[label]["branch_pen"]
    mut_pen = bar[label]["mut_pen"]

    line_pct = radar[label]["line_pct"]
    branch_pct = radar[label]["branch_pct"]
    mut_pct = radar[label]["mut_pct"]
    exec_pct = radar[label]["exec_pct"]

    if abs(line_pen - line_pct) > 0.15:
        raise RuntimeError(f"{label}: line mismatch ({line_pen} vs {line_pct})")
    if abs(branch_pen - branch_pct) > 0.15:
        raise RuntimeError(f"{label}: branch mismatch ({branch_pen} vs {branch_pct})")
    if abs(mut_pen - mut_pct) > 0.15:
        raise RuntimeError(f"{label}: mutation mismatch ({mut_pen} vs {mut_pct})")

    print(
        f"{label:<18} | exec={exec_pct:6.2f} | "
        f"line={line_pen:6.2f}->{bar[label]['line_nonpen']:6.2f} | "
        f"branch={branch_pen:6.2f}->{bar[label]['branch_nonpen']:6.2f} | "
        f"mutation={mut_pen:6.2f}->{bar[label]['mut_nonpen']:6.2f}"
    )

labels = ORDER
x = np.arange(len(labels))
w = 0.22

line_pen = np.array([bar[k]["line_pen"] for k in labels])
line_non = np.array([bar[k]["line_nonpen"] for k in labels])
branch_pen = np.array([bar[k]["branch_pen"] for k in labels])
branch_non = np.array([bar[k]["branch_nonpen"] for k in labels])
mut_pen = np.array([bar[k]["mut_pen"] for k in labels])
mut_non = np.array([bar[k]["mut_nonpen"] for k in labels])

line_uplift = np.maximum(0, line_non - line_pen)
branch_uplift = np.maximum(0, branch_non - branch_pen)
mut_uplift = np.maximum(0, mut_non - mut_pen)

fig, ax = plt.subplots(figsize=(16, 7), dpi=160)

# Penalised means
ax.bar(x - w, line_pen, width=w, color=COLOR_LINE)
ax.bar(x, branch_pen, width=w, color=COLOR_BRANCH)
ax.bar(x + w, mut_pen, width=w, color=COLOR_MUT)

# Additional uplift to non-penalised mean
ax.bar(
    x - w, line_uplift, width=w, bottom=line_pen,
    color=COLOR_LINE, alpha=0.25, hatch="///", edgecolor=COLOR_LINE
)
ax.bar(
    x, branch_uplift, width=w, bottom=branch_pen,
    color=COLOR_BRANCH, alpha=0.25, hatch="///", edgecolor=COLOR_BRANCH
)
ax.bar(
    x + w, mut_uplift, width=w, bottom=mut_pen,
    color=COLOR_MUT, alpha=0.25, hatch="///", edgecolor=COLOR_MUT
)

ax.set_ylabel("%", fontsize=14)
ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 10))
ax.grid(axis="y", alpha=0.3)

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=11)
ax.tick_params(axis="y", labelsize=11)

legend_handles = [
    Patch(facecolor=COLOR_LINE, edgecolor=COLOR_LINE, label="Line coverage"),
    Patch(facecolor=COLOR_BRANCH, edgecolor=COLOR_BRANCH, label="Branch coverage"),
    Patch(facecolor=COLOR_MUT, edgecolor=COLOR_MUT, label="Mutation score"),
    Patch(facecolor="lightgray", edgecolor="lightgray", label="Penalised mean"),
    Patch(facecolor="white", edgecolor="black", hatch="///", label="Additional uplift to non-penalised mean"),
]
ax.legend(
    handles=legend_handles,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.18),
    ncol=3,
    frameon=True,
    fontsize=10
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.24)
fig.savefig(BAR_PNG, bbox_inches="tight")
plt.close(fig)

print()
print("[OK] Barchart regenerado com as cores corrigidas:")
print(f"      {BAR_PNG}")
