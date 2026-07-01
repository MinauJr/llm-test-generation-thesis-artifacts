#!/usr/bin/env python3

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


HOME = Path.home()
FIG_DIR = HOME / "analysis_quixbugs_java" / "figures"

BAR_CSV = FIG_DIR / "quixbugs_java_stacked_3metrics_with_official_summary.csv"
BAR_PNG = FIG_DIR / "quixbugs_java_stacked_3metrics_with_official.png"

ORDER = [
    "Dataset tests",
    "EvoSuite",
    "Randoop",
    "GPT-4o",
    "GPT-5.5",
    "CodeLlama",
    "Codestral",
    "DeepSeek-Coder-V2",
    "DeepSeek-V2",
    "Qwen2.5-Coder",
    "Qwen3-Coder",
    "Qwen3.5",
]

# CORES CERTAS — iguais ao spider/radar
LINE_COLOR = "#ff7f0e"      # laranja
BRANCH_COLOR = "#2ca02c"    # verde
MUT_COLOR = "#d62728"       # vermelho


def read_rows(path: Path):
    if not path.exists():
        raise RuntimeError(f"Não encontrei o CSV: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pick(row, *names):
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


def to_float(value, label, field):
    if value in (None, ""):
        raise RuntimeError(f"{label}: valor em falta para {field}")
    return float(str(value).replace("%", "").strip())


rows = read_rows(BAR_CSV)

data = {}
for row in rows:
    label = pick(row, "approach", "label")
    if not label or label not in ORDER:
        continue

    data[label] = {
        "line_pen": to_float(
            pick(row, "line_penalized", "line_coverage_penalised_mean", "line_coverage_penalized_mean"),
            label,
            "line_penalized",
        ),
        "line_non": to_float(
            pick(row, "line_nonpenalized", "line_coverage_non_penalised_mean", "line_coverage_non_penalized_mean"),
            label,
            "line_nonpenalized",
        ),
        "branch_pen": to_float(
            pick(row, "branch_penalized", "branch_coverage_penalised_mean", "branch_coverage_penalized_mean"),
            label,
            "branch_penalized",
        ),
        "branch_non": to_float(
            pick(row, "branch_nonpenalized", "branch_coverage_non_penalised_mean", "branch_coverage_non_penalized_mean"),
            label,
            "branch_nonpenalized",
        ),
        "mut_pen": to_float(
            pick(row, "mutation_penalized", "mutation_score_penalised_mean", "mutation_score_penalized_mean"),
            label,
            "mutation_penalized",
        ),
        "mut_non": to_float(
            pick(row, "mutation_nonpenalized", "mutation_score_non_penalised_mean", "mutation_score_non_penalized_mean"),
            label,
            "mutation_nonpenalized",
        ),
    }

missing = [x for x in ORDER if x not in data]
if missing:
    raise RuntimeError("Faltam abordagens no CSV: " + ", ".join(missing))

print("===== QUIXBUGS JAVA CHECK =====")
for label in ORDER:
    d = data[label]
    print(
        f"{label:<18} | "
        f"line={d['line_pen']:6.2f}->{d['line_non']:6.2f} | "
        f"branch={d['branch_pen']:6.2f}->{d['branch_non']:6.2f} | "
        f"mutation={d['mut_pen']:6.2f}->{d['mut_non']:6.2f}"
    )

labels = ORDER
line_pen = np.array([data[x]["line_pen"] for x in labels])
line_non = np.array([data[x]["line_non"] for x in labels])
branch_pen = np.array([data[x]["branch_pen"] for x in labels])
branch_non = np.array([data[x]["branch_non"] for x in labels])
mut_pen = np.array([data[x]["mut_pen"] for x in labels])
mut_non = np.array([data[x]["mut_non"] for x in labels])

line_uplift = np.maximum(0, line_non - line_pen)
branch_uplift = np.maximum(0, branch_non - branch_pen)
mut_uplift = np.maximum(0, mut_non - mut_pen)

x = np.arange(len(labels))
w = 0.22

fig, ax = plt.subplots(figsize=(18.5, 8.5))

# BARRAS BASE — agora com as cores CERTAS
ax.bar(x - w, line_pen, width=w, color=LINE_COLOR, label="Line coverage")
ax.bar(x, branch_pen, width=w, color=BRANCH_COLOR, label="Branch coverage")
ax.bar(x + w, mut_pen, width=w, color=MUT_COLOR, label="Mutation score")

# UPLIFT HATCHED com a mesma cor de base
ax.bar(
    x - w,
    line_uplift,
    width=w,
    bottom=line_pen,
    color=LINE_COLOR,
    alpha=0.25,
    hatch="///",
    edgecolor=LINE_COLOR,
    linewidth=1.0,
)
ax.bar(
    x,
    branch_uplift,
    width=w,
    bottom=branch_pen,
    color=BRANCH_COLOR,
    alpha=0.25,
    hatch="///",
    edgecolor=BRANCH_COLOR,
    linewidth=1.0,
)
ax.bar(
    x + w,
    mut_uplift,
    width=w,
    bottom=mut_pen,
    color=MUT_COLOR,
    alpha=0.25,
    hatch="///",
    edgecolor=MUT_COLOR,
    linewidth=1.0,
)

ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 10))
ax.set_ylabel("%", fontsize=22)
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=32, ha="right", fontsize=16)
ax.tick_params(axis="y", labelsize=18)
ax.grid(axis="y", alpha=0.3)

legend_handles = [
    Patch(facecolor=LINE_COLOR, edgecolor=LINE_COLOR, label="Line coverage"),
    Patch(facecolor=BRANCH_COLOR, edgecolor=BRANCH_COLOR, label="Branch coverage"),
    Patch(facecolor=MUT_COLOR, edgecolor=MUT_COLOR, label="Mutation score"),
    Patch(facecolor="lightgray", edgecolor="gray", label="Penalised mean"),
    Patch(facecolor="white", edgecolor="black", hatch="///", label="Additional uplift to non-penalised mean"),
]

ax.legend(
    handles=legend_handles,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.18),
    ncol=3,
    fontsize=17,
    frameon=True,
)

fig.subplots_adjust(left=0.05, right=0.995, top=0.98, bottom=0.28)
fig.savefig(BAR_PNG, dpi=200)

print()
print("[OK] Barchart regenerado com as cores corrigidas:")
print(BAR_PNG)
