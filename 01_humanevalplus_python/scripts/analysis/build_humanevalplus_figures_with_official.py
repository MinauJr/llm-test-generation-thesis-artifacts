#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


FIG_DIR = Path.home() / "analysis_humanevalplus" / "figures"
RAW_CSV = FIG_DIR / "humanevalplus_repetition_level_extracted.csv"
SUMMARY_CSV = FIG_DIR / "humanevalplus_approach_summary_strict0.csv"

OFFICIAL_JSON = Path("/second_disk/projetos/out/_official_humanevalplus_dataset_tests/official_humanevalplus_aggregate_metrics.json")
OFFICIAL_TSV = Path("/second_disk/projetos/out/_official_humanevalplus_dataset_tests/official_humanevalplus_aggregate_metrics.tsv")

RADAR_OUT = FIG_DIR / "humanevalplus_radar_tools_as_axes_with_official.png"
STACKED_OUT = FIG_DIR / "humanevalplus_stacked_3metrics_with_official.png"

RADAR_CSV = FIG_DIR / "humanevalplus_radar_summary_with_official.csv"
STACKED_CSV = FIG_DIR / "humanevalplus_stacked_3metrics_with_official_summary.csv"

EXPECTED_REPS = 820


APPROACH_LABELS = {
    "Official dataset tests": "Dataset tests",
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
    "Official dataset tests",
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

METRICS_RADAR = [
    ("executable_suites_pct", "Executable suites"),
    ("line_coverage_pct", "Line coverage"),
    ("branch_coverage_pct", "Branch coverage"),
    ("mutation_score_pct", "Mutation score"),
]

METRICS_STACKED = [
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
        return float(str(x).strip().replace("%", ""))
    except Exception:
        return None


def normalise_pct(v):
    v = as_float(v)
    if v is None:
        return None
    if 0 <= v <= 1:
        return v * 100.0
    return v


def load_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}.{i}" if prefix else str(i)
            out.update(flatten(v, key))
    else:
        out[prefix] = obj
    return out


def load_official_flat():
    flat = {}

    if OFFICIAL_JSON.exists():
        try:
            data = json.loads(OFFICIAL_JSON.read_text(errors="replace"))
            flat.update(flatten(data))
        except Exception as e:
            print(f"[WARN] Could not parse official JSON: {e}")

    if OFFICIAL_TSV.exists():
        try:
            rows = load_csv(OFFICIAL_TSV)
            for i, row in enumerate(rows):
                for k, v in row.items():
                    flat[f"tsv.{i}.{k}"] = v
                    if i == 0:
                        flat[f"tsv.{k}"] = v
        except Exception as e:
            print(f"[WARN] Could not parse official TSV: {e}")

    if not flat:
        raise SystemExit("[ERROR] Could not read official aggregate JSON/TSV.")

    return flat


def find_metric(flat, patterns, required=True, label="metric"):
    candidates = []

    for pat in patterns:
        rx = re.compile(pat, re.I)
        for k, v in flat.items():
            if rx.search(k):
                val = normalise_pct(v)
                if val is not None and 0 <= val <= 100:
                    candidates.append((k, val))

    if candidates:
        # Prefer keys that look explicitly like percentages/means.
        candidates.sort(key=lambda kv: (
            0 if re.search(r"pct|percent|mean|rate|score|coverage", kv[0], re.I) else 1,
            len(kv[0])
        ))
        key, val = candidates[0]
        print(f"[OFFICIAL] {label}: {val:.2f} from {key}")
        return val

    if required:
        print()
        print("[ERROR] Could not infer official", label)
        print("Available official keys:")
        for k in sorted(flat.keys()):
            print("  ", k)
        raise SystemExit(1)

    return None


def official_values():
    flat = load_official_flat()

    line_pen = find_metric(flat, [
        r"line.*penal",
        r"penal.*line",
        r"line_coverage_pct$",
        r"line_pct$",
        r"line.*mean",
        r"mean.*line",
    ], label="line penalised")

    branch_pen = find_metric(flat, [
        r"branch.*penal",
        r"penal.*branch",
        r"branch_coverage_pct$",
        r"branch_pct$",
        r"branch.*mean",
        r"mean.*branch",
    ], label="branch penalised")

    mut_pen = find_metric(flat, [
        r"mutation.*penal",
        r"penal.*mutation",
        r"mutation_score_pct$",
        r"mutation_pct$",
        r"mutation.*mean",
        r"mean.*mutation",
    ], label="mutation penalised")

    # Non-penalised, if present. If not present, assume equal to penalised and print a warning.
    line_non = find_metric(flat, [
        r"line.*non.*penal",
        r"non.*penal.*line",
        r"line.*nonzero",
        r"line.*valid.*mean",
    ], required=False, label="line non-penalised")

    branch_non = find_metric(flat, [
        r"branch.*non.*penal",
        r"non.*penal.*branch",
        r"branch.*nonzero",
        r"branch.*valid.*mean",
    ], required=False, label="branch non-penalised")

    mut_non = find_metric(flat, [
        r"mutation.*non.*penal",
        r"non.*penal.*mutation",
        r"mutation.*nonzero",
        r"mutation.*valid.*mean",
    ], required=False, label="mutation non-penalised")

    if line_non is None:
        line_non = line_pen
        print("[WARN] Official line non-penalised not found; using penalised value.")
    if branch_non is None:
        branch_non = branch_pen
        print("[WARN] Official branch non-penalised not found; using penalised value.")
    if mut_non is None:
        mut_non = mut_pen
        print("[WARN] Official mutation non-penalised not found; using penalised value.")

    exec_pct = find_metric(flat, [
        r"executable.*pct",
        r"execution.*pct",
        r"ok.*pct",
        r"success.*pct",
        r"pass.*pct",
    ], required=False, label="executable suites")

    if exec_pct is None:
        # Dataset tests are not generated suites; if no execution success field exists, keep 100
        # as the comparability baseline and make the assumption explicit in the log.
        exec_pct = 100.0
        print("[WARN] Official executable suites pct not found; assuming 100.00 for dataset tests.")

    return {
        "approach": "Official dataset tests",
        "label": "Dataset tests",
        "expected_reps": EXPECTED_REPS,
        "rows_found": EXPECTED_REPS,
        "exec_ok_reps": round(EXPECTED_REPS * exec_pct / 100.0),
        "executable_suites_pct": exec_pct,
        "line_coverage_pct": line_pen,
        "branch_coverage_pct": branch_pen,
        "mutation_score_pct": mut_pen,
        "line_coverage_non_penalised_mean": line_non,
        "branch_coverage_non_penalised_mean": branch_non,
        "mutation_score_non_penalised_mean": mut_non,
    }


def load_radar_summary_with_official(official):
    rows = load_csv(SUMMARY_CSV)
    out = []

    out.append({
        "approach": official["approach"],
        "label": official["label"],
        "executable_suites_pct": official["executable_suites_pct"],
        "line_coverage_pct": official["line_coverage_pct"],
        "branch_coverage_pct": official["branch_coverage_pct"],
        "mutation_score_pct": official["mutation_score_pct"],
    })

    for r in rows:
        out.append({
            "approach": r["approach"],
            "label": APPROACH_LABELS.get(r["approach"], r["approach"]),
            "executable_suites_pct": normalise_pct(r["executable_suites_pct"]),
            "line_coverage_pct": normalise_pct(r["line_coverage_pct"]),
            "branch_coverage_pct": normalise_pct(r["branch_coverage_pct"]),
            "mutation_score_pct": normalise_pct(r["mutation_score_pct"]),
        })

    by_approach = {r["approach"]: r for r in out}
    return [by_approach[a] for a in APPROACH_ORDER if a in by_approach]


def write_radar_csv(rows):
    fields = ["approach", "label", "executable_suites_pct", "line_coverage_pct", "branch_coverage_pct", "mutation_score_pct"]
    with RADAR_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def text_alignment(angle_rad):
    x = np.cos(angle_rad)
    y = np.sin(angle_rad)

    if x > 0.25:
        ha = "left"
    elif x < -0.25:
        ha = "right"
    else:
        ha = "center"

    if y > 0.25:
        va = "bottom"
    elif y < -0.25:
        va = "top"
    else:
        va = "center"

    return ha, va


def plot_radar(rows):
    labels = [r["label"] for r in rows]
    n = len(labels)

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    angles_closed = list(angles) + [angles[0]]

    fig = plt.figure(figsize=(16.0, 11.2))
    ax = plt.subplot(111, polar=True)

    ax.set_xticks(angles)
    ax.set_xticklabels([])

    for metric_key, metric_label in METRICS_RADAR:
        values = [normalise_pct(r[metric_key]) for r in rows]
        values += values[:1]
        ax.plot(angles_closed, values, linewidth=2.8, label=metric_label)
        ax.fill(angles_closed, values, alpha=0.035)

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=13)

    def label_params(angle):
        deg = np.degrees(angle) % 360

        if 330 <= deg or deg < 30:
            return (18, 0, "left", "center")
        elif 30 <= deg < 60:
            return (18, 10, "left", "bottom")
        elif 60 <= deg < 120:
            return (0, 18, "center", "bottom")
        elif 120 <= deg < 150:
            return (-18, 10, "right", "bottom")
        elif 150 <= deg < 210:
            return (-18, 0, "right", "center")
        elif 210 <= deg < 240:
            return (-18, -10, "right", "top")
        elif 240 <= deg < 300:
            return (0, -18, "center", "top")
        else:
            return (18, -10, "left", "top")

    for angle, label in zip(angles, labels):
        dx, dy, ha, va = label_params(angle)
        ax.annotate(
            label,
            xy=(angle, 100),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=15,
            annotation_clip=False,
        )

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=4,
        frameon=True,
        fontsize=16,
    )

    fig.subplots_adjust(top=0.91, bottom=0.17, left=0.09, right=0.91)
    plt.savefig(RADAR_OUT, dpi=300, bbox_inches="tight", pad_inches=0.45)
    plt.close()


def load_raw():
    with RAW_CSV.open(newline="") as f:
        return list(csv.DictReader(f))


def compute_stacked_from_raw():
    raw = load_raw()
    by_approach = defaultdict(list)
    for r in raw:
        by_approach[r["approach"]].append(r)

    summary = []

    for approach in APPROACH_ORDER:
        if approach == "Official dataset tests":
            continue

        rs = by_approach.get(approach, [])
        if not rs:
            continue

        row = {
            "approach": approach,
            "label": APPROACH_LABELS.get(approach, approach),
            "rows_found": len(rs),
        }

        for metric_key, metric_label in METRICS_STACKED:
            values_with_missing_as_zero = []
            non_zero_values = []

            for r in rs:
                v = normalise_pct(r.get(metric_key))

                if v is None:
                    values_with_missing_as_zero.append(0.0)
                else:
                    values_with_missing_as_zero.append(v)
                    if v > 0:
                        non_zero_values.append(v)

            missing_reps = max(0, EXPECTED_REPS - len(values_with_missing_as_zero))
            values_with_missing_as_zero.extend([0.0] * missing_reps)

            penalised_mean = sum(values_with_missing_as_zero) / EXPECTED_REPS
            non_penalised_mean = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0.0
            uplift = max(0.0, non_penalised_mean - penalised_mean)

            prefix = metric_key.replace("_pct", "")
            row[f"{prefix}_penalised_mean"] = penalised_mean
            row[f"{prefix}_non_penalised_mean"] = non_penalised_mean
            row[f"{prefix}_uplift"] = uplift
            row[f"{prefix}_non_zero_count"] = len(non_zero_values)

        summary.append(row)

    return summary


def stacked_summary_with_official(official):
    official_row = {
        "approach": official["approach"],
        "label": official["label"],
        "rows_found": EXPECTED_REPS,
    }

    for metric_key, _ in METRICS_STACKED:
        prefix = metric_key.replace("_pct", "")
        pen = official[metric_key]
        non = official[f"{prefix}_non_penalised_mean"]
        official_row[f"{prefix}_penalised_mean"] = pen
        official_row[f"{prefix}_non_penalised_mean"] = non
        official_row[f"{prefix}_uplift"] = max(0.0, non - pen)
        official_row[f"{prefix}_non_zero_count"] = EXPECTED_REPS if non > 0 else 0

    return [official_row] + compute_stacked_from_raw()


def write_stacked_csv(summary):
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

    with STACKED_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in summary:
            w.writerow(r)


def plot_stacked(summary):
    labels = [r["label"] for r in summary]
    x = np.arange(len(labels))
    width = 0.22

    fig, ax = plt.subplots(figsize=(19.2, 9.4))

    offsets = [-width, 0, width]

    for (metric_key, metric_label), offset in zip(METRICS_STACKED, offsets):
        prefix = metric_key.replace("_pct", "")
        penalised = [r[f"{prefix}_penalised_mean"] for r in summary]
        uplift = [r[f"{prefix}_uplift"] for r in summary]
        color = METRIC_COLORS[metric_label]

        ax.bar(x + offset, penalised, width, color=color, alpha=0.9)
        ax.bar(
            x + offset,
            uplift,
            width,
            bottom=penalised,
            color=color,
            alpha=0.35,
            hatch="///",
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
        Patch(facecolor="white", edgecolor="black", hatch="///",
              label="Additional uplift to non-penalised mean"),
    ]

    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.24),
        ncol=3,
        fontsize=14,
        frameon=True,
    )

    fig.subplots_adjust(bottom=0.34, left=0.06, right=0.99, top=0.97)
    plt.savefig(STACKED_OUT, dpi=300, bbox_inches="tight", pad_inches=0.30)
    plt.close()


def main():
    official = official_values()

    radar_rows = load_radar_summary_with_official(official)
    write_radar_csv(radar_rows)
    plot_radar(radar_rows)

    stacked_rows = stacked_summary_with_official(official)
    write_stacked_csv(stacked_rows)
    plot_stacked(stacked_rows)

    print(f"[RADAR CSV] {RADAR_CSV}")
    print(f"[RADAR FIG] {RADAR_OUT}")
    print(f"[STACKED CSV] {STACKED_CSV}")
    print(f"[STACKED FIG] {STACKED_OUT}")

    print()
    print("===== RADAR DATA WITH OFFICIAL =====")
    for r in radar_rows:
        print(
            f"{r['label']:20s} | "
            f"exec={normalise_pct(r['executable_suites_pct']):6.2f} | "
            f"line={normalise_pct(r['line_coverage_pct']):6.2f} | "
            f"branch={normalise_pct(r['branch_coverage_pct']):6.2f} | "
            f"mut={normalise_pct(r['mutation_score_pct']):6.2f}"
        )

    print()
    print("===== STACKED DATA WITH OFFICIAL =====")
    for r in stacked_rows:
        print(
            f"{r['label']:20s} | "
            f"LINE pen={r['line_coverage_penalised_mean']:6.2f} nonpen={r['line_coverage_non_penalised_mean']:6.2f} | "
            f"BRANCH pen={r['branch_coverage_penalised_mean']:6.2f} nonpen={r['branch_coverage_non_penalised_mean']:6.2f} | "
            f"MUT pen={r['mutation_score_penalised_mean']:6.2f} nonpen={r['mutation_score_non_penalised_mean']:6.2f}"
        )


if __name__ == "__main__":
    main()
