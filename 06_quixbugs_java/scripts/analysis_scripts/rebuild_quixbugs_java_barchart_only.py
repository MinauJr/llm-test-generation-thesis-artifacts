#!/usr/bin/env python3

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


HOME = Path.home()
FIG_DIR = HOME / "analysis_quixbugs_java" / "figures"

INPUT_CSV = (
    FIG_DIR
    / "quixbugs_java_approach_summary_strict0.csv"
)

OUTPUT_CSV = (
    FIG_DIR
    / "quixbugs_java_stacked_3metrics_with_official_summary.csv"
)

OUTPUT_PNG = (
    FIG_DIR
    / "quixbugs_java_stacked_3metrics_with_official.png"
)

EXPECTED_ORDER = [
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

REQUIRED_COLUMNS = [
    "approach",
    "line_penalized",
    "branch_penalized",
    "mutation_penalized",
    "line_nonpenalized",
    "branch_nonpenalized",
    "mutation_nonpenalized",
]


def as_float(row, column):
    raw = row.get(column)

    if raw is None or str(raw).strip() == "":
        raise RuntimeError(
            f"{row.get('approach')}: valor vazio em {column}."
        )

    value = float(raw)

    if not 0.0 <= value <= 100.0:
        raise RuntimeError(
            f"{row.get('approach')}: {column}={value}, "
            "fora do intervalo 0–100."
        )

    return value


if not INPUT_CSV.exists():
    raise RuntimeError(
        f"Não encontrei o CSV Java: {INPUT_CSV}"
    )

with INPUT_CSV.open(
    "r",
    encoding="utf-8",
    newline="",
) as file:
    source_rows = list(csv.DictReader(file))

if not source_rows:
    raise RuntimeError(
        f"O CSV Java está vazio: {INPUT_CSV}"
    )

missing_columns = [
    column
    for column in REQUIRED_COLUMNS
    if column not in source_rows[0]
]

if missing_columns:
    raise RuntimeError(
        "Faltam colunas no CSV Java: "
        + ", ".join(missing_columns)
    )

by_approach = {}

for row in source_rows:
    approach = str(row["approach"]).strip()

    if approach in by_approach:
        raise RuntimeError(
            f"Approach duplicada no CSV: {approach}"
        )

    by_approach[approach] = row

missing_approaches = [
    approach
    for approach in EXPECTED_ORDER
    if approach not in by_approach
]

unexpected_approaches = [
    approach
    for approach in by_approach
    if approach not in EXPECTED_ORDER
]

if missing_approaches:
    raise RuntimeError(
        "Faltam abordagens Java: "
        + ", ".join(missing_approaches)
    )

if unexpected_approaches:
    raise RuntimeError(
        "Existem abordagens inesperadas: "
        + ", ".join(unexpected_approaches)
    )

rows = [
    by_approach[approach]
    for approach in EXPECTED_ORDER
]

values = []

for row in rows:
    approach = row["approach"]

    line_pen = as_float(
        row,
        "line_penalized",
    )
    branch_pen = as_float(
        row,
        "branch_penalized",
    )
    mutation_pen = as_float(
        row,
        "mutation_penalized",
    )

    line_non = as_float(
        row,
        "line_nonpenalized",
    )
    branch_non = as_float(
        row,
        "branch_nonpenalized",
    )
    mutation_non = as_float(
        row,
        "mutation_nonpenalized",
    )

    for metric, penalised, nonpenalised in (
        ("line", line_pen, line_non),
        ("branch", branch_pen, branch_non),
        ("mutation", mutation_pen, mutation_non),
    ):
        if nonpenalised + 0.000001 < penalised:
            raise RuntimeError(
                f"{approach}: a média não penalizada de "
                f"{metric} ({nonpenalised}) é inferior à "
                f"penalizada ({penalised})."
            )

    values.append(
        {
            "approach": approach,
            "line_penalized": line_pen,
            "line_nonpenalized": line_non,
            "branch_penalized": branch_pen,
            "branch_nonpenalized": branch_non,
            "mutation_penalized": mutation_pen,
            "mutation_nonpenalized": mutation_non,
        }
    )

# Impede o uso acidental dos resultados de QuixBugs Python.
dataset_tests = values[0]

expected_official = {
    "line_penalized": 89.851796,
    "branch_penalized": 96.529762,
    "mutation_penalized": 93.198931,
}

for metric, expected in expected_official.items():
    actual = dataset_tests[metric]
    difference = abs(actual - expected)

    if difference > 0.001:
        raise RuntimeError(
            "Os Dataset tests não correspondem ao "
            f"QuixBugs Java: {metric}={actual}, "
            f"esperado={expected}."
        )

# Guardar o summary exato usado pelo gráfico.
with OUTPUT_CSV.open(
    "w",
    encoding="utf-8",
    newline="",
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "approach",
            "line_penalized",
            "line_nonpenalized",
            "branch_penalized",
            "branch_nonpenalized",
            "mutation_penalized",
            "mutation_nonpenalized",
        ],
    )
    writer.writeheader()
    writer.writerows(values)

labels = [
    row["approach"]
    for row in values
]

line_pen = np.array(
    [row["line_penalized"] for row in values]
)
line_non = np.array(
    [row["line_nonpenalized"] for row in values]
)

branch_pen = np.array(
    [row["branch_penalized"] for row in values]
)
branch_non = np.array(
    [row["branch_nonpenalized"] for row in values]
)

mutation_pen = np.array(
    [row["mutation_penalized"] for row in values]
)
mutation_non = np.array(
    [row["mutation_nonpenalized"] for row in values]
)

line_uplift = np.maximum(
    line_non - line_pen,
    0.0,
)
branch_uplift = np.maximum(
    branch_non - branch_pen,
    0.0,
)
mutation_uplift = np.maximum(
    mutation_non - mutation_pen,
    0.0,
)

x = np.arange(len(labels))
width = 0.22

fig, ax = plt.subplots(
    figsize=(16, 7.5)
)

# Parte sólida: média penalizada.
ax.bar(
    x - width,
    line_pen,
    width,
    label="Line coverage",
    color="C0",
)

ax.bar(
    x,
    branch_pen,
    width,
    label="Branch coverage",
    color="C1",
)

ax.bar(
    x + width,
    mutation_pen,
    width,
    label="Mutation score",
    color="C2",
)

# Parte tracejada: uplift até à média não penalizada.
ax.bar(
    x - width,
    line_uplift,
    width,
    bottom=line_pen,
    color="C0",
    alpha=0.24,
    edgecolor="C0",
    hatch="///",
)

ax.bar(
    x,
    branch_uplift,
    width,
    bottom=branch_pen,
    color="C1",
    alpha=0.24,
    edgecolor="C1",
    hatch="///",
)

ax.bar(
    x + width,
    mutation_uplift,
    width,
    bottom=mutation_pen,
    color="C2",
    alpha=0.24,
    edgecolor="C2",
    hatch="///",
)

ax.set_ylabel(
    "%",
    fontsize=15,
)

ax.set_ylim(
    0,
    100,
)

ax.set_yticks(
    np.arange(0, 101, 10)
)

ax.tick_params(
    axis="y",
    labelsize=12,
)

ax.set_xticks(x)

ax.set_xticklabels(
    labels,
    rotation=33,
    ha="right",
    fontsize=12,
)

ax.grid(
    axis="y",
    alpha=0.24,
)

ax.set_axisbelow(True)

legend_handles = [
    Patch(
        facecolor="C0",
        label="Line coverage",
    ),
    Patch(
        facecolor="C1",
        label="Branch coverage",
    ),
    Patch(
        facecolor="C2",
        label="Mutation score",
    ),
    Patch(
        facecolor="lightgray",
        edgecolor="gray",
        label="Penalised mean",
    ),
    Patch(
        facecolor="white",
        edgecolor="black",
        hatch="///",
        label="Additional uplift to non-penalised mean",
    ),
]

ax.legend(
    handles=legend_handles,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.37),
    ncol=3,
    frameon=True,
    fontsize=12,
)

fig.subplots_adjust(
    left=0.06,
    right=0.99,
    top=0.98,
    bottom=0.31,
)

fig.savefig(
    OUTPUT_PNG,
    dpi=220,
    bbox_inches="tight",
)

plt.close(fig)

print("===== QUIXBUGS JAVA BARCHART DATA =====")

for row in values:
    print(
        f"{row['approach']:<20} "
        f"| LINE {row['line_penalized']:6.2f}"
        f"->{row['line_nonpenalized']:6.2f} "
        f"| BRANCH {row['branch_penalized']:6.2f}"
        f"->{row['branch_nonpenalized']:6.2f} "
        f"| MUTATION {row['mutation_penalized']:6.2f}"
        f"->{row['mutation_nonpenalized']:6.2f}"
    )

print()
print("[OK] Foram usados exclusivamente dados QuixBugs Java.")
print(f"[INPUT]  {INPUT_CSV}")
print(f"[CSV]    {OUTPUT_CSV}")
print(f"[FIGURE] {OUTPUT_PNG}")
