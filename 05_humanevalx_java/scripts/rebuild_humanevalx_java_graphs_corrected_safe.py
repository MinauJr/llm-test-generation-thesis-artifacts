#!/usr/bin/env python3

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


HOME = Path.home()
FIG_DIR = HOME / "analysis_humanevalx_java" / "figures"

APPROACH_CSV = FIG_DIR / "humanevalx_java_approach_summary_strict0.csv"
RADAR_CSV_IN = FIG_DIR / "humanevalx_java_radar_summary_with_official.csv"
BAR_CSV_IN = FIG_DIR / "humanevalx_java_stacked_3metrics_with_official_summary.csv"

RADAR_PNG = FIG_DIR / "humanevalx_java_radar_tools_as_axes_with_official.png"
BAR_PNG = FIG_DIR / "humanevalx_java_stacked_3metrics_with_official.png"

RADAR_CSV_OUT = FIG_DIR / "humanevalx_java_radar_summary_with_official.csv"
BAR_CSV_OUT = FIG_DIR / "humanevalx_java_stacked_3metrics_with_official_summary.csv"

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

IGNORE = {
    "DeepSeek-V2-Lite",
}


def canonical_name(raw):
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


def detect_delimiter(path):
    text = path.read_text(encoding="utf-8", errors="replace")[:8192]
    candidates = [",", "\t", ";"]
    return max(candidates, key=lambda d: text.count(d))


def read_table(path):
    if not path.exists():
        return []

    delimiter = detect_delimiter(path)

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)

    return rows


def norm_key(key):
    return str(key or "").strip().lower().replace(" ", "_").replace("-", "_")


ALIASES = {
    "approach": [
        "approach", "model", "name", "tool",
    ],
    "executable_pct": [
        "executable_pct", "executable_suites", "executable_suite_rate_pct",
        "exec_pct", "execution_rate", "executable_rate",
    ],
    "line_penalized": [
        "line_penalized", "line_strict_zero_mean", "line_coverage_mean_strict0",
        "line_coverage_mean_pct", "line_pct", "line",
    ],
    "branch_penalized": [
        "branch_penalized", "branch_strict_zero_mean", "branch_coverage_mean_strict0",
        "branch_coverage_mean_pct", "branch_pct", "branch",
    ],
    "mutation_penalized": [
        "mutation_penalized", "mutation_strict_zero_mean", "mutation_score_mean_strict0",
        "mutation_score_mean_pct", "mutation_pct", "mutation", "pit_score",
    ],
    "line_nonpenalized": [
        "line_nonpenalized", "line_non_penalized", "line_available_mean",
        "line_coverage_mean_available", "line_nonpen_mean",
    ],
    "branch_nonpenalized": [
        "branch_nonpenalized", "branch_non_penalized", "branch_available_mean",
        "branch_coverage_mean_available", "branch_nonpen_mean",
    ],
    "mutation_nonpenalized": [
        "mutation_nonpenalized", "mutation_non_penalized", "mutation_available_mean",
        "mutation_score_mean_available", "mutation_nonpen_mean",
    ],
}


def get_value(row, logical_name):
    lookup = {norm_key(k): v for k, v in row.items() if k is not None}

    for alias in ALIASES[logical_name]:
        key = norm_key(alias)
        if key in lookup and str(lookup[key]).strip() != "":
            return lookup[key]

    return None


def as_float(value, approach, field):
    if value is None or str(value).strip() == "":
        raise RuntimeError(f"{approach}: valor vazio em {field}")

    return float(str(value).replace("%", "").strip())


def merge_sources():
    data = {}

    sources = [
        ("approach", APPROACH_CSV),
        ("radar", RADAR_CSV_IN),
        ("bar", BAR_CSV_IN),
    ]

    for source_name, path in sources:
        rows = read_table(path)
        print(f"[INFO] {source_name}: {path} rows={len(rows)}")

        for row in rows:
            raw_approach = get_value(row, "approach")
            approach = canonical_name(raw_approach)

            if not approach or approach in IGNORE:
                continue

            if approach not in data:
                data[approach] = {"approach": approach}

            target = data[approach]

            for field in [
                "executable_pct",
                "line_penalized",
                "branch_penalized",
                "mutation_penalized",
                "line_nonpenalized",
                "branch_nonpenalized",
                "mutation_nonpenalized",
            ]:
                value = get_value(row, field)
                if value is not None and str(value).strip() != "":
                    target[field] = value

    return data


data = merge_sources()

missing_approaches = [a for a in ORDER if a not in data]
if missing_approaches:
    raise RuntimeError("Faltam abordagens: " + ", ".join(missing_approaches))

clean = []

for approach in ORDER:
    row = data[approach]

    executable = as_float(row.get("executable_pct"), approach, "executable_pct")
    line_pen = as_float(row.get("line_penalized"), approach, "line_penalized")
    branch_pen = as_float(row.get("branch_penalized"), approach, "branch_penalized")
    mutation_pen = as_float(row.get("mutation_penalized"), approach, "mutation_penalized")

    line_non = row.get("line_nonpenalized")
    branch_non = row.get("branch_nonpenalized")
    mutation_non = row.get("mutation_nonpenalized")

    line_non = as_float(line_non, approach, "line_nonpenalized") if line_non is not None else line_pen
    branch_non = as_float(branch_non, approach, "branch_nonpenalized") if branch_non is not None else branch_pen
    mutation_non = as_float(mutation_non, approach, "mutation_nonpenalized") if mutation_non is not None else mutation_pen

    clean.append({
        "approach": approach,
        "executable_pct": executable,
        "line_penalized": line_pen,
        "branch_penalized": branch_pen,
        "mutation_penalized": mutation_pen,
        "line_nonpenalized": max(line_non, line_pen),
        "branch_nonpenalized": max(branch_non, branch_pen),
        "mutation_nonpenalized": max(mutation_non, mutation_pen),
    })

# Garantir que é mesmo HumanEvalX Java, não QuixBugs/MBPP/etc.
ds = clean[0]
expected_dataset = {
    "line_penalized": 98.803790,
    "branch_penalized": 97.253820,
    "mutation_penalized": 93.379190,
}
for key, expected in expected_dataset.items():
    actual = ds[key]
    if abs(actual - expected) > 0.20:
        raise RuntimeError(
            f"Dataset tests não parecem ser HumanEvalX Java: {key}={actual}, esperado≈{expected}"
        )

# Guardar CSVs novos sem DeepSeek-V2-Lite.
with RADAR_CSV_OUT.open("w", encoding="utf-8", newline="") as f:
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
    for row in clean:
        writer.writerow({
            "approach": row["approach"],
            "executable_pct": row["executable_pct"],
            "line_penalized": row["line_penalized"],
            "branch_penalized": row["branch_penalized"],
            "mutation_penalized": row["mutation_penalized"],
        })

with BAR_CSV_OUT.open("w", encoding="utf-8", newline="") as f:
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
    for row in clean:
        writer.writerow({
            "approach": row["approach"],
            "line_penalized": row["line_penalized"],
            "branch_penalized": row["branch_penalized"],
            "mutation_penalized": row["mutation_penalized"],
            "line_nonpenalized": row["line_nonpenalized"],
            "branch_nonpenalized": row["branch_nonpenalized"],
            "mutation_nonpenalized": row["mutation_nonpenalized"],
        })

labels = [row["approach"] for row in clean]

exec_vals = np.array([row["executable_pct"] for row in clean])
line_pen = np.array([row["line_penalized"] for row in clean])
branch_pen = np.array([row["branch_penalized"] for row in clean])
mutation_pen = np.array([row["mutation_penalized"] for row in clean])

line_non = np.array([row["line_nonpenalized"] for row in clean])
branch_non = np.array([row["branch_nonpenalized"] for row in clean])
mutation_non = np.array([row["mutation_nonpenalized"] for row in clean])

# Radar
N = len(labels)
angles = np.linspace(0, 2 * math.pi, N, endpoint=False)
angles_closed = np.concatenate([angles, [angles[0]]])

fig = plt.figure(figsize=(11, 10.5))
ax = plt.subplot(111, polar=True)

ax.set_theta_offset(0.0)
ax.set_theta_direction(1)

ax.set_xticks(angles)
ax.set_xticklabels(labels, fontsize=14)
ax.tick_params(axis="x", pad=24)

ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=11)
ax.grid(True, alpha=0.35)

def plot_radar(values, label, color, fill_alpha=0.06):
    closed = np.concatenate([values, [values[0]]])
    ax.plot(angles_closed, closed, linewidth=2.2, color=color, label=label)
    ax.fill(angles_closed, closed, color=color, alpha=fill_alpha)

plot_radar(exec_vals, "Executable suites", "C0", 0.08)
plot_radar(line_pen, "Line coverage", "C1", 0.05)
plot_radar(branch_pen, "Branch coverage", "C2", 0.05)
plot_radar(mutation_pen, "Mutation score", "C3", 0.05)

ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, -0.16),
    ncol=4,
    frameon=True,
    fontsize=12,
)

fig.subplots_adjust(top=0.96, bottom=0.17, left=0.07, right=0.93)
fig.savefig(RADAR_PNG, dpi=220, bbox_inches="tight")
plt.close(fig)

# Barchart: cores como SF110/radar:
# line = orange, branch = green, mutation = red
x = np.arange(len(labels))
width = 0.22

line_uplift = np.maximum(line_non - line_pen, 0.0)
branch_uplift = np.maximum(branch_non - branch_pen, 0.0)
mutation_uplift = np.maximum(mutation_non - mutation_pen, 0.0)

fig, ax = plt.subplots(figsize=(16, 7.2))

ax.bar(x - width, line_pen, width, color="C1", label="Line coverage")
ax.bar(x, branch_pen, width, color="C2", label="Branch coverage")
ax.bar(x + width, mutation_pen, width, color="C3", label="Mutation score")

ax.bar(x - width, line_uplift, width, bottom=line_pen, color="C1", alpha=0.25, edgecolor="C1", hatch="///")
ax.bar(x, branch_uplift, width, bottom=branch_pen, color="C2", alpha=0.25, edgecolor="C2", hatch="///")
ax.bar(x + width, mutation_uplift, width, bottom=mutation_pen, color="C3", alpha=0.25, edgecolor="C3", hatch="///")

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

print("===== HUMANEVALX JAVA FIX OK =====")
print("[OK] DeepSeek-V2-Lite removido")
print("[OK] Barchart com cores corretas: line=C1 laranja, branch=C2 verde, mutation=C3 vermelho")
print("[OK] Dataset tests valida HumanEvalX Java")
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
print(f"[RADAR] {RADAR_PNG}")
print(f"[BAR]   {BAR_PNG}")
