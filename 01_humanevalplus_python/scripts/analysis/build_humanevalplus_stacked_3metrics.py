#!/usr/bin/env python3
import csv
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


FIG_DIR = Path.home() / "analysis_humanevalplus" / "figures"
RAW_CSV = FIG_DIR / "humanevalplus_repetition_level_extracted.csv"

OUT_CSV = FIG_DIR / "humanevalplus_stacked_3metrics_summary.csv"
OUT_PNG = FIG_DIR / "humanevalplus_stacked_3metrics.png"

EXPECTED_REPS = 820

APPROACH_LABELS = {
    "Pynguin": "Pynguin",
    "GPT-4o": "GPT-4o",
    "GPT-5.5": "GPT-5.5",
    "Claude Opus 4.7": "Claude 4.7",
    "cluster-max-codellama-7b-instruct-ctx16k [structfix]": "CodeLlama",
    "cluster-safe-codestral-22b-ctx16k": "Codestral",
    "cluster-safe-deepseek-coder-v2-16b-ctx16k": "DeepSeek-Coder-V2",
    "cluster-safe-deepseek-v2-ctx32k [structfix]": "DeepSeek-V2",
    "cluster-safe-qwen2.5-coder-14b-ctx32k": "Qwen2.5-Coder",
    "cluster-safe-qwen3-coder-30b-official-ctx32k": "Qwen3-Coder",
    "cluster-safe-qwen3.5-9b-ctx32k": "Qwen3.5",
}

APPROACH_ORDER = [
    "Pynguin",
    "GPT-4o",
    "GPT-5.5",
    "Claude Opus 4.7",
    "cluster-max-codellama-7b-instruct-ctx16k [structfix]",
    "cluster-safe-codestral-22b-ctx16k",
    "cluster-safe-deepseek-coder-v2-16b-ctx16k",
    "cluster-safe-deepseek-v2-ctx32k [structfix]",
    "cluster-safe-qwen2.5-coder-14b-ctx32k",
    "cluster-safe-qwen3-coder-30b-official-ctx32k",
    "cluster-safe-qwen3.5-9b-ctx32k",
]

METRICS = [
    ("line_coverage_pct", "Line coverage"),
    ("branch_coverage_pct", "Branch coverage"),
    ("mutation_score_pct", "Mutation score"),
]

METRIC_COLORS = {
    "Line coverage": "#1f77b4",
    "Branch coverage": "#ff7f0e",
    "Mutation score": "#2ca02c",
}


def as_float(x):
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None


def load_rows():
    with RAW_CSV.open(newline="") as f:
        return list(csv.DictReader(f))


def compute(rows):
    by_approach = defaultdict(list)
    for r in rows:
        by_approach[r["approach"]].append(r)

    summary = []

    for approach in APPROACH_ORDER:
        rs = by_approach.get(approach, [])
        if not rs:
            continue

        row = {
            "approach": approach,
            "label": APPROACH_LABELS.get(approach, approach),
            "rows_found": len(rs),
        }

        for metric_key, metric_label in METRICS:
            values_with_missing_as_zero = []
            non_zero_values = []

            for r in rs:
                v = as_float(r.get(metric_key))

                if v is None:
                    values_with_missing_as_zero.append(0.0)
                else:
                    values_with_missing_as_zero.append(v)
                    if v > 0:
                        non_zero_values.append(v)

            missing_reps = max(0, EXPECTED_REPS - len(values_with_missing_as_zero))
            values_with_missing_as_zero.extend([0.0] * missing_reps)

            penalised_mean = sum(values_with_missing_as_zero) / EXPECTED_REPS
            non_penalised_mean = (
                sum(non_zero_values) / len(non_zero_values)
                if non_zero_values else 0.0
            )
            uplift = max(0.0, non_penalised_mean - penalised_mean)

            prefix = metric_key.replace("_pct", "")
            row[f"{prefix}_penalised_mean"] = penalised_mean
            row[f"{prefix}_non_penalised_mean"] = non_penalised_mean
            row[f"{prefix}_uplift"] = uplift
            row[f"{prefix}_non_zero_count"] = len(non_zero_values)

        summary.append(row)

    return summary


def write_csv(summary):
    fields = [
        "approach",
        "label",
        "rows_found",
        "line_coverage_penalised_mean",
        "line_coverage_non_penalised_mean",
        "line_coverage_uplift",
        "line_coverage_non_zero_count",
        "branch_coverage_penalised_mean",
        "branch_coverage_non_penalised_mean",
        "branch_coverage_uplift",
        "branch_coverage_non_zero_count",
        "mutation_score_penalised_mean",
        "mutation_score_non_penalised_mean",
        "mutation_score_uplift",
        "mutation_score_non_zero_count",
    ]

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in summary:
            w.writerow(r)


def plot(summary):
    labels = [r["label"] for r in summary]
    x = np.arange(len(labels))
    width = 0.22

    fig, ax = plt.subplots(figsize=(18, 9.2))

    offsets = [-width, 0, width]

    for (metric_key, metric_label), offset in zip(METRICS, offsets):
        prefix = metric_key.replace("_pct", "")
        penalised = [r[f"{prefix}_penalised_mean"] for r in summary]
        uplift = [r[f"{prefix}_uplift"] for r in summary]
        color = METRIC_COLORS[metric_label]

        ax.bar(
            x + offset,
            penalised,
            width,
            color=color,
            alpha=0.9,
        )

        ax.bar(
            x + offset,
            uplift,
            width,
            bottom=penalised,
            color=color,
            alpha=0.35,
            hatch='///',
            edgecolor=color,
        )

    ax.set_ylabel("%", fontsize=16)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 10))

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=14)
    ax.tick_params(axis="y", labelsize=14)

    ax.grid(axis="y", alpha=0.25)

    legend_handles = [
        Patch(facecolor=METRIC_COLORS["Line coverage"], label="Line coverage"),
        Patch(facecolor=METRIC_COLORS["Branch coverage"], label="Branch coverage"),
        Patch(facecolor=METRIC_COLORS["Mutation score"], label="Mutation score"),
        Patch(facecolor="lightgray", edgecolor="black", label="Penalised mean"),
        Patch(facecolor="white", edgecolor="black", hatch='///',
              label="Additional uplift to non-penalised mean"),
    ]

    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.23),
        ncol=3,
        fontsize=14,
        frameon=True,
    )

    fig.subplots_adjust(bottom=0.33, left=0.06, right=0.99, top=0.97)

    plt.savefig(OUT_PNG, dpi=300, bbox_inches="tight", pad_inches=0.30)
    plt.close()


def main():
    rows = load_rows()
    summary = compute(rows)

    write_csv(summary)
    plot(summary)

    print(f"[CSV] {OUT_CSV}")
    print(f"[FIG] {OUT_PNG}")
    print()

    print("===== STACKED 3-METRICS DATA =====")
    for r in summary:
        print(f"{r['label']:20s} | "
              f"LINE pen={r['line_coverage_penalised_mean']:6.2f} nonpen={r['line_coverage_non_penalised_mean']:6.2f} | "
              f"BRANCH pen={r['branch_coverage_penalised_mean']:6.2f} nonpen={r['branch_coverage_non_penalised_mean']:6.2f} | "
              f"MUT pen={r['mutation_score_penalised_mean']:6.2f} nonpen={r['mutation_score_non_penalised_mean']:6.2f}")


if __name__ == "__main__":
    main()
