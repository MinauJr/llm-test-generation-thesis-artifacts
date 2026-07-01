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

REMOVE = {
    "DeepSeek-V2-Lite",
}


def canonical_label(raw):
    s = str(raw or "").strip()
    k = s.lower().replace("_", "-").replace(" ", "")

    if "dataset" in k and "test" in k:
        return "Dataset tests"
    if "evosuite" in k:
        return "EvoSuite"
    if "randoop" in k:
        return "Randoop"
    if "gpt-4o" in k or "gpt4o" in k:
        return "GPT-4o"
    if "gpt-5.5" in k or "gpt55" in k or "gpt-55" in k:
        return "GPT-5.5"
    if "claude" in k:
        return "Claude 4.7"
    if "codellama" in k:
        return "CodeLlama"
    if "codestral" in k:
        return "Codestral"
    if "deepseek-coder-v2" in k:
        return "DeepSeek-Coder-V2"
    if "deepseek-v2-lite" in k or "deepseekv2lite" in k or "v2-lite" in k:
        return "DeepSeek-V2-Lite"
    if "qwen2.5" in k or "qwen25" in k or "qwen2-5" in k:
        return "Qwen2.5-Coder"
    if "qwen3-coder" in k:
        return "Qwen3-Coder"
    if "qwen3.5" in k or "qwen35" in k or "qwen3-5" in k:
        return "Qwen3.5"

    return s


def f(row, col):
    raw = row.get(col)

    if raw is None or str(raw).strip() == "":
        raise RuntimeError(
            f"{row.get('label')}: valor vazio na coluna {col}"
        )

    value = float(str(raw).replace("%", "").strip())

    if value < -0.0001 or value > 100.0001:
        raise RuntimeError(
            f"{row.get('label')}: {col}={value}, fora de 0–100"
        )

    return max(0.0, min(100.0, value))


if not INPUT_CSV.exists():
    raise RuntimeError(f"Não encontrei o input CSV: {INPUT_CSV}")

with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as file:
    rows = list(csv.DictReader(file))

if not rows:
    raise RuntimeError(f"O CSV está vazio: {INPUT_CSV}")

print("===== INPUT HEADERS =====")
print(list(rows[0].keys()))

required_columns = [
    "label",
    "executable_suites_pct",
    "line_coverage_penalised_mean",
    "line_coverage_non_penalised_mean",
    "branch_coverage_penalised_mean",
    "branch_coverage_non_penalised_mean",
    "mutation_score_penalised_mean",
    "mutation_score_non_penalised_mean",
]

missing_cols = [
    col
    for col in required_columns
    if col not in rows[0]
]

if missing_cols:
    raise RuntimeError(
        "Faltam colunas esperadas: " + ", ".join(missing_cols)
    )

by_label = {}

for row in rows:
    label = canonical_label(row["label"])

    if label in REMOVE:
        continue

    if label in by_label:
        raise RuntimeError(f"Label duplicado depois de canonicalizar: {label}")

    by_label[label] = {
        "approach": label,
        "executable_pct": f(row, "executable_suites_pct"),
        "line_penalized": f(row, "line_coverage_penalised_mean"),
        "line_nonpenalized": f(row, "line_coverage_non_penalised_mean"),
        "branch_penalized": f(row, "branch_coverage_penalised_mean"),
        "branch_nonpenalized": f(row, "branch_coverage_non_penalised_mean"),
        "mutation_penalized": f(row, "mutation_score_penalised_mean"),
        "mutation_nonpenalized": f(row, "mutation_score_non_penalised_mean"),
    }

missing = [
    label
    for label in ORDER
    if label not in by_label
]

if missing:
    print("===== LABELS ENCONTRADOS =====")
    for label in sorted(by_label):
        print(label)

    raise RuntimeError(
        "Faltam labels depois de remover DeepSeek-V2-Lite: "
        + ", ".join(missing)
    )

clean = [
    by_label[label]
    for label in ORDER
]

# Validação para não usar outro dataset por engano.
dataset = clean[0]

expected_dataset = {
    "line_penalized": 98.803790,
    "branch_penalized": 97.253820,
    "mutation_penalized": 93.379190,
}

for metric, expected in expected_dataset.items():
    actual = dataset[metric]
    diff = abs(actual - expected)

    print(
        f"[CHECK] Dataset tests {metric}: "
        f"actual={actual:.6f} expected≈{expected:.6f} diff={diff:.6f}"
    )

    if diff > 0.25:
        raise RuntimeError(
            f"O Dataset tests não parece HumanEvalX Java: "
            f"{metric}={actual}, esperado≈{expected}"
        )

# Garantir non-penalized >= penalized.
for row in clean:
    for metric in ["line", "branch", "mutation"]:
        p = row[f"{metric}_penalized"]
        npv = row[f"{metric}_nonpenalized"]

        if npv + 0.000001 < p:
            raise RuntimeError(
                f"{row['approach']}: {metric}_nonpenalized={npv} "
                f"< {metric}_penalized={p}"
            )

# Guardar CSVs finais sem DeepSeek-V2-Lite.
with RADAR_CSV.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "approach",
            "executable_pct",
            "line_penalized",
            "branch_penalized",
            "mutation_penalized",
        ],
    )
    writer.writeheader()

    for row in clean:
        writer.writerow({
            "approach": row["approach"],
            "executable_pct": row["executable_pct"],
            "line_penalized": row["line_penalized"],
            "branch_penalized": row["branch_penalized"],
            "mutation_penalized": row["mutation_penalized"],
        })

with BAR_CSV.open("w", encoding="utf-8", newline="") as file:
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

    for row in clean:
        writer.writerow({
            "approach": row["approach"],
            "line_penalized": row["line_penalized"],
            "line_nonpenalized": row["line_nonpenalized"],
            "branch_penalized": row["branch_penalized"],
            "branch_nonpenalized": row["branch_nonpenalized"],
            "mutation_penalized": row["mutation_penalized"],
            "mutation_nonpenalized": row["mutation_nonpenalized"],
        })

labels = [
    row["approach"]
    for row in clean
]

exec_vals = np.array([
    row["executable_pct"]
    for row in clean
])

line_p = np.array([
    row["line_penalized"]
    for row in clean
])

branch_p = np.array([
    row["branch_penalized"]
    for row in clean
])

mutation_p = np.array([
    row["mutation_penalized"]
    for row in clean
])

line_np = np.array([
    row["line_nonpenalized"]
    for row in clean
])

branch_np = np.array([
    row["branch_nonpenalized"]
    for row in clean
])

mutation_np = np.array([
    row["mutation_nonpenalized"]
    for row in clean
])

# ============================================================
# RADAR / SPIDER
# ============================================================

n = len(labels)
angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
angles_closed = np.concatenate([angles, [angles[0]]])


def close(values):
    return np.concatenate([values, [values[0]]])


fig = plt.figure(figsize=(12.2, 11.2))
ax = plt.subplot(111, polar=True)

ax.set_theta_offset(0.0)
ax.set_theta_direction(1)

ax.set_xticks(angles)
ax.set_xticklabels(labels, fontsize=14)
ax.tick_params(axis="x", pad=34)

ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=11)
ax.grid(True, alpha=0.35)

ax.plot(angles_closed, close(exec_vals), linewidth=2.3, color="C0", label="Executable suites")
ax.fill(angles_closed, close(exec_vals), color="C0", alpha=0.08)

ax.plot(angles_closed, close(line_p), linewidth=2.3, color="C1", label="Line coverage")
ax.fill(angles_closed, close(line_p), color="C1", alpha=0.05)

ax.plot(angles_closed, close(branch_p), linewidth=2.3, color="C2", label="Branch coverage")
ax.fill(angles_closed, close(branch_p), color="C2", alpha=0.05)

ax.plot(angles_closed, close(mutation_p), linewidth=2.3, color="C3", label="Mutation score")
ax.fill(angles_closed, close(mutation_p), color="C3", alpha=0.05)

ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, -0.20),
    ncol=4,
    frameon=True,
    fontsize=12,
)

fig.subplots_adjust(
    top=0.95,
    bottom=0.20,
    left=0.05,
    right=0.95,
)

fig.savefig(
    RADAR_PNG,
    dpi=220,
    bbox_inches="tight",
)

plt.close(fig)

# ============================================================
# BARCHART
# ============================================================

x = np.arange(len(labels))
width = 0.22

line_u = np.maximum(line_np - line_p, 0.0)
branch_u = np.maximum(branch_np - branch_p, 0.0)
mutation_u = np.maximum(mutation_np - mutation_p, 0.0)

fig, ax = plt.subplots(figsize=(16, 7.2))

# Cores certas:
# line = laranja, branch = verde, mutation = vermelho.
ax.bar(x - width, line_p, width, color="C1", label="Line coverage")
ax.bar(x, branch_p, width, color="C2", label="Branch coverage")
ax.bar(x + width, mutation_p, width, color="C3", label="Mutation score")

ax.bar(
    x - width,
    line_u,
    width,
    bottom=line_p,
    color="C1",
    alpha=0.25,
    edgecolor="C1",
    hatch="///",
)

ax.bar(
    x,
    branch_u,
    width,
    bottom=branch_p,
    color="C2",
    alpha=0.25,
    edgecolor="C2",
    hatch="///",
)

ax.bar(
    x + width,
    mutation_u,
    width,
    bottom=mutation_p,
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
    bbox_to_anchor=(0.5, -0.41),
    ncol=3,
    frameon=True,
    fontsize=12,
)

fig.subplots_adjust(
    left=0.06,
    right=0.99,
    top=0.98,
    bottom=0.41,
)

fig.savefig(
    BAR_PNG,
    dpi=220,
    bbox_inches="tight",
)

plt.close(fig)

print("===== HUMANEVALX JAVA FIX OK =====")
print("[OK] DeepSeek-V2-Lite removido dos dois gráficos")
print("[OK] Barchart com cores certas: line=laranja, branch=verde, mutation=vermelho")
print("[OK] Dataset tests validado como HumanEvalX Java")
print()

for row in clean:
    print(
        f"{row['approach']:<20} "
        f"exec={row['executable_pct']:6.2f} "
        f"line={row['line_penalized']:6.2f}->{row['line_nonpenalized']:6.2f} "
        f"branch={row['branch_penalized']:6.2f}->{row['branch_nonpenalized']:6.2f} "
        f"mutation={row['mutation_penalized']:6.2f}->{row['mutation_nonpenalized']:6.2f}"
    )

print()
print(f"[RADAR PNG] {RADAR_PNG}")
print(f"[BAR PNG]   {BAR_PNG}")
print(f"[RADAR CSV] {RADAR_CSV}")
print(f"[BAR CSV]   {BAR_CSV}")
