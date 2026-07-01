#!/usr/bin/env python3
import csv
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np


FIG_DIR = Path.home() / "analysis_humanevalplus" / "figures"
RAW_CSV = FIG_DIR / "humanevalplus_repetition_level_extracted.csv"

OUT_CSV = FIG_DIR / "humanevalplus_mutation_3views.csv"
OUT_PNG = FIG_DIR / "humanevalplus_mutation_3views_bar.png"

EXPECTED_REPS = 820
METRIC_KEY = "mutation_score_pct"


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

        values_with_missing_as_zero = []
        non_zero_values = []
        all_valid_values = []

        for r in rs:
            v = as_float(r.get(METRIC_KEY))

            # Penalised: missing metric/failure counts as 0.
            if v is None:
                values_with_missing_as_zero.append(0.0)
            else:
                values_with_missing_as_zero.append(v)
                all_valid_values.append(v)

                # Non-penalised: exclude all zero values.
                if v > 0:
                    non_zero_values.append(v)

        # Garante denominador fixo do dataset.
        # Se houver menos rows do que EXPECTED_REPS, as ausentes entram como 0.
        missing_reps = max(0, EXPECTED_REPS - len(values_with_missing_as_zero))
        values_with_missing_as_zero.extend([0.0] * missing_reps)

        penalised_mean = sum(values_with_missing_as_zero) / EXPECTED_REPS

        non_penalised_mean = (
            sum(non_zero_values) / len(non_zero_values)
            if non_zero_values else 0.0
        )

        best_performance = (
            max(all_valid_values)
            if all_valid_values else 0.0
        )

        summary.append({
            "approach": approach,
            "label": APPROACH_LABELS.get(approach, approach),
            "rows_found": len(rs),
            "valid_metric_values": len(all_valid_values),
            "non_zero_metric_values": len(non_zero_values),
            "zero_or_missing_values": EXPECTED_REPS - len(non_zero_values),
            "penalised_mean": penalised_mean,
            "non_penalised_mean": non_penalised_mean,
            "best_performance": best_performance,
        })

    return summary


def write_csv(summary):
    fields = [
        "approach",
        "label",
        "rows_found",
        "valid_metric_values",
        "non_zero_metric_values",
        "zero_or_missing_values",
        "penalised_mean",
        "non_penalised_mean",
        "best_performance",
    ]

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in summary:
            w.writerow(r)


def plot(summary):
    labels = [r["label"] for r in summary]

    penalised = [r["penalised_mean"] for r in summary]
    non_penalised = [r["non_penalised_mean"] for r in summary]
    best = [r["best_performance"] for r in summary]

    x = np.arange(len(labels))
    width = 0.24

    fig, ax = plt.subplots(figsize=(17, 8.8))

    ax.bar(x - width, penalised, width, label="Penalised mean")
    ax.bar(x, non_penalised, width, label="Non-penalised mean")
    ax.bar(x + width, best, width, label="Best performance")

    ax.set_ylabel("Mutation score (%)", fontsize=16)
    ax.set_ylim(0, 100)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=14)
    ax.tick_params(axis="y", labelsize=14)

    ax.grid(axis="y", alpha=0.25)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.20),
        ncol=3,
        fontsize=16,
        frameon=True,
    )

    fig.subplots_adjust(bottom=0.30, left=0.07, right=0.99, top=0.96)

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
    print("===== MUTATION 3-VIEW BAR DATA =====")
    for r in summary:
        print(
            f"{r['label']:20s} | "
            f"penalised={r['penalised_mean']:6.2f} | "
            f"non_penalised={r['non_penalised_mean']:6.2f} | "
            f"best={r['best_performance']:6.2f} | "
            f"valid={r['valid_metric_values']:4d} | "
            f"non_zero={r['non_zero_metric_values']:4d} | "
            f"zero_or_missing={r['zero_or_missing_values']:4d}"
        )


if __name__ == "__main__":
    main()
