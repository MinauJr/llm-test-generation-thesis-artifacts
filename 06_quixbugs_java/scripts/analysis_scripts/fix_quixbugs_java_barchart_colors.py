#!/usr/bin/env python3

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


HOME = Path.home()
FIG_DIR = HOME / "analysis_quixbugs_java" / "figures"

BAR_CSV = FIG_DIR / "quixbugs_java_stacked_3metrics_with_official_summary.csv"
RADAR_CSV = FIG_DIR / "quixbugs_java_radar_summary_with_official.csv"
APPROACH_CSV = FIG_DIR / "quixbugs_java_approach_summary_strict0.csv"
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

LINE_COLOR = "#ff7f0e"      # laranja
BRANCH_COLOR = "#2ca02c"    # verde
MUT_COLOR = "#d62728"       # vermelho

def read_csv(path: Path):
    if not path.exists():
        return []
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

def normalize_rows(rows, source_name):
    out = {}
    for row in rows:
        label = pick(row, "approach", "label")
        if not label or label not in ORDER:
            continue

        exec_val = pick(row, "executable_pct", "executable_suites_pct")

        line_pen = pick(
            row,
            "line_penalized",
            "line_coverage_penalised_mean",
            "line_coverage_penalized_mean",
        )
        line_non = pick(
            row,
            "line_nonpenalized",
            "line_coverage_non_penalised_mean",
            "line_coverage_non_penalized_mean",
        )

        branch_pen = pick(
            row,
            "branch_penalized",
            "branch_coverage_penalised_mean",
            "branch_coverage_penalized_mean",
        )
        branch_non = pick(
            row,
            "branch_nonpenalized",
            "branch_coverage_non_penalised_mean",
            "branch_coverage_non_penalized_mean",
        )

        mut_pen = pick(
            row,
            "mutation_penalized",
            "mutation_score_penalised_mean",
            "mutation_score_penalized_mean",
        )
        mut_non = pick(
            row,
            "mutation_nonpenalized",
            "mutation_score_non_penalised_mean",
            "mutation_score_non_penalized_mean",
        )

        out[label] = {
            "exec_pct": None if exec_val in (None, "") else to_float(exec_val, label, "exec_pct"),
            "line_pen": to_float(line_pen, label, "line_pen"),
            "line_non": to_float(line_non, label, "line_non"),
            "branch_pen": to_float(branch_pen, label, "branch_pen"),
            "branch_non": to_float(branch_non, label, "branch_non"),
            "mut_pen": to_float(mut_pen, label, "mut_pen"),
            "mut_non": to_float(mut_non, label, "mut_non"),
            "source": source_name,
        }
    return out

bar_rows = read_csv(BAR_CSV)
if not bar_rows:
    raise RuntimeError(f"Não consegui ler o ficheiro do barchart: {BAR_CSV}")

bar_data = normalize_rows(bar_rows, "bar")

missing = [label for label in ORDER if label not in bar_data]
if missing:
    raise RuntimeError("Faltam abordagens no CSV do barchart: " + ", ".join(missing))

radar_rows = read_csv(RADAR_CSV)
radar_data = normalize_rows(radar_rows, "radar") if radar_rows else {}

print("===== QUIXBUGS JAVA CHECK =====")
for label in ORDER:
    d = bar_data[label]
    exec_txt = "n/a" if d["exec_pct"] is None else f"{d['exec_pct']:6.2f}"
    print(
        f"{label:<18} | exec={exec_txt} | "
        f"line={d['line_pen']:6.2f}->{d['line_non']:6.2f} | "
        f"branch={d['branch_pen']:6.2f}->{d['branch_non']:6.2f} | "
        f"mutation={d['mut_pen']:6.2f}->{d['mut_non']:6.2f}"
    )

print()

if radar_data:
    print("===== BAR VS RADAR CHECK =====")
    for label in ORDER:
        if label not in radar_data:
            print(f"[WARN] {label}: não encontrei linha correspondente no radar CSV")
            continue

        b = bar_data[label]
        r = radar_data[label]

        diffs = {
            "line_pen": abs(b["line_pen"] - r["line_pen"]),
            "branch_pen": abs(b["branch_pen"] - r["branch_pen"]),
            "mut_pen": abs(b["mut_pen"] - r["mut_pen"]),
        }

        max_diff = max(diffs.values())
        status = "OK" if max_diff <= 0.01 else "WARN"

        print(
            f"{label:<18} | "
            f"line diff={diffs['line_pen']:.6f} | "
            f"branch diff={diffs['branch_pen']:.6f} | "
            f"mutation diff={diffs['mut_pen']:.6f} [{status}]"
        )

labels = ORDER
line_pen = np.array([bar_data[x]["line_pen"] for x in labels])
line_non = np.array([bar_data[x]["line_non"] for x in labels])
branch_pen = np.array([bar_data[x]["branch_pen"] for x in labels])
branch_non = np.array([bar_data[x]["branch_non"] for x in labels])
mut_pen = np.array([bar_data[x]["mut_pen"] for x in labels])
mut_non = np.array([bar_data[x]["mut_non"] for x in labels])

line_uplift = np.maximum(0, line_non - line_pen)
branch_uplift = np.maximum(0, branch_non - branch_pen)
mut_uplift = np.maximum(0, mut_non - mut_pen)

x = np.arange(len(labels))
w = 0.22

fig, ax = plt.subplots(figsize=(18.5, 8.5))

ax.bar(x - w, line_pen, width=w, color=LINE_COLOR, label="Line coverage")
ax.bar(x, branch_pen, width=w, color=BRANCH_COLOR, label="Branch coverage")
ax.bar(x + w, mut_pen, width=w, color=MUT_COLOR, label="Mutation score")

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
print(f"      {BAR_PNG}")
