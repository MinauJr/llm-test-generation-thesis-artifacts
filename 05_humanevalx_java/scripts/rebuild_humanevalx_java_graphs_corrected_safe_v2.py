#!/usr/bin/env python3

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


HOME = Path.home()
FIG_DIR = HOME / "analysis_humanevalx_java" / "figures"

INPUTS = [
    FIG_DIR / "humanevalx_java_approach_summary_strict0.csv",
    FIG_DIR / "humanevalx_java_radar_summary_with_official.csv",
    FIG_DIR / "humanevalx_java_stacked_3metrics_with_official_summary.csv",
]

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

IGNORE_CANONICAL = {"DeepSeek-V2-Lite"}


def norm_key(x):
    return str(x or "").strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")


def canonical(raw):
    s = str(raw or "").strip()
    k = s.lower().replace("_", "-").replace(" ", "")

    if not s:
        return ""

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
    if "deepseek-v2-lite" in k or "v2-lite" in k or "deepseekv2lite" in k:
        return "DeepSeek-V2-Lite"
    if "qwen2.5" in k or "qwen25" in k or "qwen2-5" in k:
        return "Qwen2.5-Coder"
    if "qwen3-coder" in k:
        return "Qwen3-Coder"
    if "qwen3.5" in k or "qwen35" in k or "qwen3-5" in k:
        return "Qwen3.5"

    return s


ALIASES = {
    "approach": [
        "approach", "model", "name", "tool", "method", "generator"
    ],
    "executable_pct": [
        "executable_pct", "executable_suite_rate_pct", "executable_suites",
        "exec_pct", "execution_rate", "executable_rate"
    ],
    "line_penalized": [
        "line_penalized", "line_penalised", "line_strict_zero_mean",
        "line_strict0", "line_coverage_mean_strict0",
        "line_coverage_mean_pct", "line_pct", "line"
    ],
    "branch_penalized": [
        "branch_penalized", "branch_penalised", "branch_strict_zero_mean",
        "branch_strict0", "branch_coverage_mean_strict0",
        "branch_coverage_mean_pct", "branch_pct", "branch"
    ],
    "mutation_penalized": [
        "mutation_penalized", "mutation_penalised", "mutation_strict_zero_mean",
        "mutation_strict0", "mutation_score_mean_strict0",
        "mutation_score_mean_pct", "mutation_pct", "mutation", "pit_score"
    ],
    "line_nonpenalized": [
        "line_nonpenalized", "line_nonpenalised", "line_non_penalized",
        "line_non_penalised", "line_coverage_mean_available",
        "line_available_mean", "line_nonpen_mean"
    ],
    "branch_nonpenalized": [
        "branch_nonpenalized", "branch_nonpenalised", "branch_non_penalized",
        "branch_non_penalised", "branch_coverage_mean_available",
        "branch_available_mean", "branch_nonpen_mean"
    ],
    "mutation_nonpenalized": [
        "mutation_nonpenalized", "mutation_nonpenalised", "mutation_non_penalized",
        "mutation_non_penalised", "mutation_score_mean_available",
        "mutation_available_mean", "mutation_nonpen_mean"
    ],
}


def get(row, logical):
    lookup = {norm_key(k): v for k, v in row.items() if k is not None}

    for alias in ALIASES[logical]:
        key = norm_key(alias)
        if key in lookup and str(lookup[key]).strip() != "":
            return lookup[key]

    return None


def score_rows(rows):
    if not rows:
        return -1

    headers = rows[0].keys()
    header_score = 0

    for logical in ["approach", "line_penalized", "branch_penalized", "mutation_penalized"]:
        keys = {norm_key(k) for k in headers if k is not None}
        if any(norm_key(alias) in keys for alias in ALIASES[logical]):
            header_score += 10

    approach_count = 0
    for row in rows:
        raw = get(row, "approach")
        if raw is None:
            # fallback: primeira coluna
            first_key = next(iter(row.keys()))
            raw = row.get(first_key)
        if canonical(raw):
            approach_count += 1

    return header_score + approach_count


def read_best(path):
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    trials = []

    for delim in [",", "\t", ";"]:
        try:
            rows = list(csv.DictReader(text.splitlines(), delimiter=delim))
            trials.append((score_rows(rows), delim, rows))
        except Exception:
            pass

    if not trials:
        return []

    trials.sort(key=lambda x: x[0], reverse=True)
    score, delim, rows = trials[0]

    print(f"[INFO] {path}")
    print(f"       delimiter={repr(delim)} score={score} rows={len(rows)}")
    if rows:
        print(f"       headers={list(rows[0].keys())}")

    return rows


def to_float(v, approach, field):
    if v is None or str(v).strip() == "":
        raise RuntimeError(f"{approach}: valor em falta para {field}")
    return float(str(v).replace("%", "").strip())


data = {}

for path in INPUTS:
    rows = read_best(path)

    for row in rows:
        raw_approach = get(row, "approach")
        if raw_approach is None:
            first_key = next(iter(row.keys()))
            raw_approach = row.get(first_key)

        approach = canonical(raw_approach)

        if not approach or approach in IGNORE_CANONICAL:
            continue

        if approach not in data:
            data[approach] = {"approach": approach}

        for field in [
            "executable_pct",
            "line_penalized",
            "branch_penalized",
            "mutation_penalized",
            "line_nonpenalized",
            "branch_nonpenalized",
            "mutation_nonpenalized",
        ]:
            value = get(row, field)
            if value is not None and str(value).strip() != "":
                data[approach][field] = value


missing = [a for a in ORDER if a not in data]
if missing:
    print("[DEBUG] approaches found:")
    for k in sorted(data):
        print(f"  - {k}: {data[k]}")
    raise RuntimeError("Faltam abordagens: " + ", ".join(missing))


clean = []

for approach in ORDER:
    row = data[approach]

    exec_pct = to_float(row.get("executable_pct"), approach, "executable_pct")
    line_p = to_float(row.get("line_penalized"), approach, "line_penalized")
    branch_p = to_float(row.get("branch_penalized"), approach, "branch_penalized")
    mut_p = to_float(row.get("mutation_penalized"), approach, "mutation_penalized")

    line_np = row.get("line_nonpenalized")
    branch_np = row.get("branch_nonpenalized")
    mut_np = row.get("mutation_nonpenalized")

    line_np = to_float(line_np, approach, "line_nonpenalized") if line_np is not None else line_p
    branch_np = to_float(branch_np, approach, "branch_nonpenalized") if branch_np is not None else branch_p
    mut_np = to_float(mut_np, approach, "mutation_nonpenalized") if mut_np is not None else mut_p

    clean.append({
        "approach": approach,
        "executable_pct": exec_pct,
        "line_penalized": line_p,
        "branch_penalized": branch_p,
        "mutation_penalized": mut_p,
        "line_nonpenalized": max(line_np, line_p),
        "branch_nonpenalized": max(branch_np, branch_p),
        "mutation_nonpenalized": max(mut_np, mut_p),
    })

# Validar que é HumanEvalX Java e não outro dataset
expected_ds = {
    "line_penalized": 98.803790,
    "branch_penalized": 97.253820,
    "mutation_penalized": 93.379190,
}
for key, expected in expected_ds.items():
    actual = clean[0][key]
    if abs(actual - expected) > 0.25:
        raise RuntimeError(
            f"Dataset tests não parece HumanEvalX Java: {key}={actual}, esperado≈{expected}"
        )

# Escrever CSVs finais sem DeepSeek-V2-Lite
with RADAR_CSV.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["approach", "executable_pct", "line_penalized", "branch_penalized", "mutation_penalized"],
    )
    writer.writeheader()
    for row in clean:
        writer.writerow({k: row[k] for k in ["approach", "executable_pct", "line_penalized", "branch_penalized", "mutation_penalized"]})

with BAR_CSV.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["approach", "line_penalized", "branch_penalized", "mutation_penalized", "line_nonpenalized", "branch_nonpenalized", "mutation_nonpenalized"],
    )
    writer.writeheader()
    for row in clean:
        writer.writerow({k: row[k] for k in ["approach", "line_penalized", "branch_penalized", "mutation_penalized", "line_nonpenalized", "branch_nonpenalized", "mutation_nonpenalized"]})

labels = [r["approach"] for r in clean]

exec_vals = np.array([r["executable_pct"] for r in clean])
line_p = np.array([r["line_penalized"] for r in clean])
branch_p = np.array([r["branch_penalized"] for r in clean])
mut_p = np.array([r["mutation_penalized"] for r in clean])

line_np = np.array([r["line_nonpenalized"] for r in clean])
branch_np = np.array([r["branch_nonpenalized"] for r in clean])
mut_np = np.array([r["mutation_nonpenalized"] for r in clean])

# RADAR
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

def radar_plot(vals, label, color, alpha):
    closed = np.concatenate([vals, [vals[0]]])
    ax.plot(angles_closed, closed, linewidth=2.2, color=color, label=label)
    ax.fill(angles_closed, closed, color=color, alpha=alpha)

radar_plot(exec_vals, "Executable suites", "C0", 0.08)
radar_plot(line_p, "Line coverage", "C1", 0.05)
radar_plot(branch_p, "Branch coverage", "C2", 0.05)
radar_plot(mut_p, "Mutation score", "C3", 0.05)

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

# BARCHART com cores iguais ao SF110/radar:
# line=lARANJA, branch=VERDE, mutation=VERMELHO
x = np.arange(len(labels))
width = 0.22

line_u = np.maximum(line_np - line_p, 0.0)
branch_u = np.maximum(branch_np - branch_p, 0.0)
mut_u = np.maximum(mut_np - mut_p, 0.0)

fig, ax = plt.subplots(figsize=(16, 7.2))

ax.bar(x - width, line_p, width, color="C1", label="Line coverage")
ax.bar(x, branch_p, width, color="C2", label="Branch coverage")
ax.bar(x + width, mut_p, width, color="C3", label="Mutation score")

ax.bar(x - width, line_u, width, bottom=line_p, color="C1", alpha=0.25, edgecolor="C1", hatch="///")
ax.bar(x, branch_u, width, bottom=branch_p, color="C2", alpha=0.25, edgecolor="C2", hatch="///")
ax.bar(x + width, mut_u, width, bottom=mut_p, color="C3", alpha=0.25, edgecolor="C3", hatch="///")

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
print("[OK] Barchart com cores corretas")
print("[OK] Dataset tests confirma HumanEvalX Java")
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
