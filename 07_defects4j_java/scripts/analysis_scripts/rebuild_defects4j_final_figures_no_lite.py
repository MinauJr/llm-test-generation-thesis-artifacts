#!/usr/bin/env python3
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

FIG_DIR = Path("/home/jpaiva/analysis_defects4j/figures")

RADAR_CSV = FIG_DIR / "defects4j_radar_summary_with_official.csv"
STACKED_CSV = FIG_DIR / "defects4j_stacked_3metrics_with_official_summary.csv"

RADAR_OUT = FIG_DIR / "defects4j_radar_tools_as_axes_with_official.png"
RADAR_OUT_FINAL = FIG_DIR / "defects4j_radar_tools_as_axes_with_official_no_deepseek_v2_lite.png"

STACKED_OUT = FIG_DIR / "defects4j_stacked_3metrics_with_official.png"
STACKED_OUT_FINAL = FIG_DIR / "defects4j_stacked_3metrics_with_official_spyder_colours_no_deepseek_v2_lite.png"

FILTERED_RADAR_CSV = FIG_DIR / "defects4j_radar_summary_with_official_no_deepseek_v2_lite.csv"
FILTERED_STACKED_CSV = FIG_DIR / "defects4j_stacked_3metrics_with_official_summary_barchart_no_deepseek_v2_lite.csv"

COLORS = {
    "Executable suites": "#1f77b4",
    "Line coverage": "#ff7f0e",
    "Branch coverage": "#2ca02c",
    "Mutation score": "#d62728",
}

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
    "DeepSeek-V2",
    "Qwen2.5-Coder",
    "Qwen3-Coder",
    "Qwen3.5",
]

def load_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows):
    if not rows:
        raise SystemExit(f"ERROR: no rows to write for {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

def find_col(rows, candidates):
    if not rows:
        raise SystemExit("ERROR: empty rows")
    cols = list(rows[0].keys())
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for c in cols:
        cl = c.lower()
        for cand in candidates:
            if cand.lower() in cl:
                return c
    raise SystemExit(f"ERROR: could not find one of {candidates}; columns={cols}")

def clean_label(label):
    s = str(label).strip()

    replacements = {
        "Official Relevant Tests": "Dataset tests",
        "Official Tests": "Dataset tests",
        "Dataset Tests": "Dataset tests",
        "Dataset tests": "Dataset tests",

        "DeepSeek Coder V2": "DeepSeek-Coder-V2",
        "DeepSeek-Coder-V2": "DeepSeek-Coder-V2",

        "DeepSeek-V2-16B": "DeepSeek-V2",
        "DeepSeek V2 16B": "DeepSeek-V2",
        "DeepSeek-V2 16B": "DeepSeek-V2",
        "DeepSeek-V2-16b": "DeepSeek-V2",
        "DeepSeek-V2": "DeepSeek-V2",

        "Qwen 2.5 Coder": "Qwen2.5-Coder",
        "Qwen2.5 Coder": "Qwen2.5-Coder",
        "Qwen2.5-Coder": "Qwen2.5-Coder",

        "Qwen 3 Coder": "Qwen3-Coder",
        "Qwen3 Coder": "Qwen3-Coder",
        "Qwen3-Coder": "Qwen3-Coder",

        "Qwen 3.5": "Qwen3.5",
        "Qwen3.5": "Qwen3.5",
    }

    return replacements.get(s, s)

def should_remove(row):
    joined = "|".join(str(v) for v in row.values())
    return "DeepSeek-V2-Lite" in joined or "deepseek-v2-lite" in joined.lower()

def normalise_and_filter(rows, label_col):
    out = []
    removed = 0
    for r in rows:
        if should_remove(r):
            removed += 1
            continue
        rr = dict(r)
        rr[label_col] = clean_label(rr[label_col])
        out.append(rr)

    seen = set()
    dedup = []
    for r in out:
        lab = r[label_col]
        if lab in seen:
            print(f"[WARN] duplicate label after cleaning, keeping first only: {lab}")
            continue
        seen.add(lab)
        dedup.append(r)

    order_index = {name: i for i, name in enumerate(ORDER)}
    dedup.sort(key=lambda r: order_index.get(r[label_col], 999))

    return dedup, removed

def as_float(row, col):
    v = row.get(col, "")
    if v in ("", "None", "null", None):
        return 0.0
    return float(v)

def build_radar():
    rows_all = load_csv(RADAR_CSV)

    label_col = find_col(rows_all, ["label", "approach", "method", "model", "tool", "name", "display_name"])
    exec_col = find_col(rows_all, ["executable_pct", "executable_suites_pct", "Executable suites"])
    line_col = find_col(rows_all, ["line_penalized", "line_coverage_pct", "line_coverage", "Line coverage"])
    branch_col = find_col(rows_all, ["branch_penalized", "branch_coverage_pct", "branch_coverage", "Branch coverage"])
    mutation_col = find_col(rows_all, ["mutation_penalized", "mutation_score_pct", "mutation_score", "Mutation score"])

    rows, removed = normalise_and_filter(rows_all, label_col)
    write_csv(FILTERED_RADAR_CSV, rows)

    labels = [r[label_col] for r in rows]

    series = [
        ("Executable suites", [as_float(r, exec_col) for r in rows]),
        ("Line coverage", [as_float(r, line_col) for r in rows]),
        ("Branch coverage", [as_float(r, branch_col) for r in rows]),
        ("Mutation score", [as_float(r, mutation_col) for r in rows]),
    ]

    n = len(labels)
    angles = [2 * math.pi * i / n for i in range(n)]
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(13.2, 13.2), subplot_kw=dict(polar=True))

    for name, values in series:
        values_closed = values + values[:1]
        ax.plot(
            angles_closed,
            values_closed,
            linewidth=2.4,
            color=COLORS[name],
            label=name,
        )
        ax.fill(
            angles_closed,
            values_closed,
            alpha=0.035,
            color=COLORS[name],
        )

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=12)
    ax.grid(True, alpha=0.65)

    ax.set_xticks(angles)
    ax.set_xticklabels([])

    # Custom outer labels: farther from the chart, not on top of the lines.
    label_radius = 112
    for angle, label in zip(angles, labels):
        deg = math.degrees(angle)
        if 90 < deg < 270:
            ha = "right"
        elif deg == 90 or deg == 270:
            ha = "center"
        else:
            ha = "left"

        va = "center"
        if 70 <= deg <= 110:
            va = "bottom"
        elif 250 <= deg <= 290:
            va = "top"

        ax.text(
            angle,
            label_radius,
            label,
            fontsize=13,
            ha=ha,
            va=va,
            clip_on=False,
        )

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.17),
        ncol=4,
        frameon=True,
        fontsize=13,
    )

    fig.subplots_adjust(left=0.08, right=0.92, top=0.90, bottom=0.18)

    for out in [RADAR_OUT, RADAR_OUT_FINAL]:
        fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.75)
    plt.close(fig)

    print(f"[RADAR] removed DeepSeek-V2-Lite rows: {removed}")
    print(f"[RADAR] labels: {labels}")
    print(f"[RADAR] wrote: {RADAR_OUT}")
    print(f"[RADAR] wrote: {RADAR_OUT_FINAL}")
    print(f"[RADAR] filtered csv: {FILTERED_RADAR_CSV}")

def build_stacked():
    rows_all = load_csv(STACKED_CSV)

    label_col = find_col(rows_all, ["label", "approach", "method", "model", "tool", "name", "display_name"])

    line_pen_col = find_col(rows_all, ["line_penalized", "line_pen", "line_coverage_pct_penalized", "Line coverage penalized"])
    line_non_col = find_col(rows_all, ["line_nonpenalized", "line_non_penalized", "line_available", "line_nonpen", "Line coverage non"])

    branch_pen_col = find_col(rows_all, ["branch_penalized", "branch_pen", "branch_coverage_pct_penalized", "Branch coverage penalized"])
    branch_non_col = find_col(rows_all, ["branch_nonpenalized", "branch_non_penalized", "branch_available", "branch_nonpen", "Branch coverage non"])

    mutation_pen_col = find_col(rows_all, ["mutation_penalized", "mutation_pen", "mutation_score_pct_penalized", "Mutation score penalized"])
    mutation_non_col = find_col(rows_all, ["mutation_nonpenalized", "mutation_non_penalized", "mutation_available", "mutation_nonpen", "Mutation score non"])

    rows, removed = normalise_and_filter(rows_all, label_col)
    write_csv(FILTERED_STACKED_CSV, rows)

    labels = [r[label_col] for r in rows]
    x = list(range(len(rows)))
    width = 0.23

    line_pen = [as_float(r, line_pen_col) for r in rows]
    line_non = [as_float(r, line_non_col) for r in rows]
    branch_pen = [as_float(r, branch_pen_col) for r in rows]
    branch_non = [as_float(r, branch_non_col) for r in rows]
    mutation_pen = [as_float(r, mutation_pen_col) for r in rows]
    mutation_non = [as_float(r, mutation_non_col) for r in rows]

    line_uplift = [max(0.0, n - p) for p, n in zip(line_pen, line_non)]
    branch_uplift = [max(0.0, n - p) for p, n in zip(branch_pen, branch_non)]
    mutation_uplift = [max(0.0, n - p) for p, n in zip(mutation_pen, mutation_non)]

    fig, ax = plt.subplots(figsize=(20, 8.8))

    ax.bar(
        [i - width for i in x],
        line_pen,
        width,
        color=COLORS["Line coverage"],
        edgecolor=COLORS["Line coverage"],
        alpha=0.95,
    )
    ax.bar(
        [i - width for i in x],
        line_uplift,
        width,
        bottom=line_pen,
        color=COLORS["Line coverage"],
        edgecolor=COLORS["Line coverage"],
        alpha=0.25,
        hatch="///",
        linewidth=0.7,
    )

    ax.bar(
        x,
        branch_pen,
        width,
        color=COLORS["Branch coverage"],
        edgecolor=COLORS["Branch coverage"],
        alpha=0.95,
    )
    ax.bar(
        x,
        branch_uplift,
        width,
        bottom=branch_pen,
        color=COLORS["Branch coverage"],
        edgecolor=COLORS["Branch coverage"],
        alpha=0.25,
        hatch="///",
        linewidth=0.7,
    )

    ax.bar(
        [i + width for i in x],
        mutation_pen,
        width,
        color=COLORS["Mutation score"],
        edgecolor=COLORS["Mutation score"],
        alpha=0.95,
    )
    ax.bar(
        [i + width for i in x],
        mutation_uplift,
        width,
        bottom=mutation_pen,
        color=COLORS["Mutation score"],
        edgecolor=COLORS["Mutation score"],
        alpha=0.25,
        hatch="///",
        linewidth=0.7,
    )

    ax.set_ylim(0, 100)
    ax.set_ylabel("%", fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=12)
    ax.tick_params(axis="y", labelsize=13)
    ax.grid(axis="y", alpha=0.25)

    legend_handles = [
        Patch(facecolor=COLORS["Line coverage"], edgecolor=COLORS["Line coverage"], label="Line coverage"),
        Patch(facecolor=COLORS["Branch coverage"], edgecolor=COLORS["Branch coverage"], label="Branch coverage"),
        Patch(facecolor=COLORS["Mutation score"], edgecolor=COLORS["Mutation score"], label="Mutation score"),
        Patch(facecolor="white", edgecolor="black", hatch="///", label="Additional uplift to non-penalised mean"),
        Patch(facecolor="lightgray", edgecolor="gray", label="Penalised mean"),
    ]

    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.22),
        ncol=5,
        frameon=True,
        fontsize=12,
    )

    fig.subplots_adjust(left=0.055, right=0.995, top=0.98, bottom=0.34)

    for out in [STACKED_OUT, STACKED_OUT_FINAL]:
        fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)

    print(f"[STACKED] removed DeepSeek-V2-Lite rows: {removed}")
    print(f"[STACKED] labels: {labels}")
    print(f"[STACKED] wrote: {STACKED_OUT}")
    print(f"[STACKED] wrote: {STACKED_OUT_FINAL}")
    print(f"[STACKED] filtered csv: {FILTERED_STACKED_CSV}")

def main():
    build_radar()
    build_stacked()

if __name__ == "__main__":
    main()
