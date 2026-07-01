#!/usr/bin/env python3

import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch


# ============================================================
# Authoritative SF110 sources
# ============================================================

EXPECTED_REPETITIONS = 110 * 5

GPT4O_ROOT = Path(
    "/home/jpaiva/projetos/llm_test_generation_gpt4o/"
    "sf110_gpt4o/out/"
    "_FINAL_EFFECTIVE_gpt4o_sf110_bytecode_v2_110x5_stage38_39_40_closed"
)

GPT55_ROOT = Path(
    "/home/jpaiva/projetos/llm_test_generation_gpt4o/"
    "sf110_gpt4o/out/"
    "_rerun_gpt55_sf110_java_110suts_x5_stage14c"
)

CLUSTER_ROOT = Path(
    "/home/jpaiva/projetos/llm_test_generation_gpt4o/"
    "sf110_gpt4o/out/"
    "_FINAL_EFFECTIVE_cluster_sf110_try1_V3_PIT_20260613_082636"
)

RANDOOP_ROOT = Path(
    "/home/jpaiva/projetos/nonAI/java_workflow/out/"
    "_final_sf110_randoop_20260403_114624"
)

EVOSUITE_ROOT = Path(
    "/home/jpaiva/projetos/nonAI/java_workflow/out/"
    "_night_sf110_evosuite_109x5_cfg180_t200_20260406"
)

ANALYSIS_ROOT = Path("/home/jpaiva/analysis_sf110")
FIG_DIR = ANALYSIS_ROOT / "figures"

SUMMARY_TSV = FIG_DIR / "sf110_final_graph_summary.tsv"
VALIDATION_TXT = FIG_DIR / "sf110_final_graph_validation.txt"

BARCHART_PNG = FIG_DIR / "sf110_stacked_barchart_final.png"
BARCHART_SVG = FIG_DIR / "sf110_stacked_barchart_final.svg"

SPYDER_PNG = FIG_DIR / "sf110_spyder_chart_final.png"
SPYDER_SVG = FIG_DIR / "sf110_spyder_chart_final.svg"

FIG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Shared helpers
# ============================================================

def safe_float(value, default=0.0):
    if value is None:
        return default

    text = str(value).strip()

    if not text:
        return default

    try:
        result = float(text)
    except (TypeError, ValueError):
        return default

    if not math.isfinite(result):
        return default

    return result


def safe_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def read_delimited(path: Path, delimiter: str):
    if not path.is_file():
        raise FileNotFoundError(f"Missing required file: {path}")

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def deduplicate_records(records):
    deduplicated = {}

    for record in records:
        key = (
            str(record.get("sut_id", "")).strip(),
            str(record.get("rep", "")).strip(),
        )

        if key == ("", ""):
            raise RuntimeError(
                "A record without sut_id and rep was found."
            )

        deduplicated[key] = record

    return list(deduplicated.values())


def summarise_individual_records(
    method,
    category,
    records,
    status_field,
    line_field,
    branch_field,
    mutation_field,
    source,
):
    records = deduplicate_records(records)

    attempted = len(records)

    if attempted > EXPECTED_REPETITIONS:
        raise RuntimeError(
            f"{method}: found {attempted} records, "
            f"more than expected {EXPECTED_REPETITIONS}."
        )

    ok_records = [
        record
        for record in records
        if str(record.get(status_field, "")).strip().lower() == "ok"
    ]

    ok_count = len(ok_records)

    metric_fields = {
        "line": line_field,
        "branch": branch_field,
        "mutation": mutation_field,
    }

    result = {
        "method": method,
        "category": category,
        "source": source,
        "expected_repetitions": EXPECTED_REPETITIONS,
        "attempted_repetitions": attempted,
        "missing_repetitions_penalised_as_zero":
            EXPECTED_REPETITIONS - attempted,
        "ok_repetitions": ok_count,
        "executable_suites_pct":
            100.0 * ok_count / EXPECTED_REPETITIONS,
    }

    for metric_name, field_name in metric_fields.items():
        total_penalised = sum(
            safe_float(record.get(field_name))
            for record in records
        )

        total_ok_only = sum(
            safe_float(record.get(field_name))
            for record in ok_records
        )

        result[f"{metric_name}_mean_penalised"] = (
            total_penalised / EXPECTED_REPETITIONS
        )

        result[f"{metric_name}_mean_non_penalised"] = (
            total_ok_only / ok_count
            if ok_count
            else 0.0
        )

    return result


def find_batch_summaries(root: Path):
    candidates = set()

    patterns = [
        "*/run_0001/aggregate/batch_summary.json",
        "*/aggregate/batch_summary.json",
    ]

    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file():
                candidates.add(path.resolve())

    return sorted(candidates)


def summarise_non_ai(method, root: Path):
    """
    Aggregate the two SF110 non-AI workflows according to their real,
    preserved output schemas.

    EvoSuite:
      - repetition-level data are stored in batch_summary.json -> runs;
      - failed repetitions and unavailable metrics contribute zero to the
        penalised means;
      - non-penalised means use only repetitions with a numeric metric.

    Randoop:
      - the 109-SUT main batch stores SUT-level repetition aggregates;
      - 26_jipa is added as the documented rescued structural reporting case;
      - its line and branch values are preserved, while mutation remains
        unavailable and therefore contributes zero to the penalised mean.
    """

    import math

    REPETITIONS_PER_SUT = 5

    def numeric_or_none(value):
        if value is None:
            return None

        text_value = str(value).strip()

        if text_value in {"", "None", "null", "NaN", "nan"}:
            return None

        try:
            result = float(text_value)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(result):
            return None

        return result

    summaries = find_batch_summaries(root)

    if not summaries:
        raise RuntimeError(
            f"{method}: no batch_summary.json files found under {root}"
        )

    per_sut = {}

    for summary_path in summaries:
        with summary_path.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            data = json.load(handle)

        sut_id = str(
            data.get("sut_id")
            or summary_path.parents[2].name
        ).strip()

        if not sut_id:
            raise RuntimeError(
                f"{method}: could not identify SUT for {summary_path}"
            )

        if sut_id in per_sut:
            previous_path, _ = per_sut[sut_id]

            raise RuntimeError(
                f"{method}: duplicate summary for {sut_id}: "
                f"{previous_path} and {summary_path}"
            )

        per_sut[sut_id] = (summary_path, data)

    # ========================================================
    # EvoSuite: use the real repetition-level runs array
    # ========================================================

    if method == "EvoSuite":
        attempted_slots = len(per_sut) * REPETITIONS_PER_SUT
        ok_count = 0

        penalised_sums = {
            "line": 0.0,
            "branch": 0.0,
            "mutation": 0.0,
        }

        available_sums = {
            "line": 0.0,
            "branch": 0.0,
            "mutation": 0.0,
        }

        available_counts = {
            "line": 0,
            "branch": 0,
            "mutation": 0,
        }

        metric_fields = {
            "line": "line_pct",
            "branch": "branch_pct",
            "mutation": "pit_score",
        }

        malformed_suts = []

        for sut_id in sorted(per_sut):
            summary_path, data = per_sut[sut_id]

            runs = data.get("runs")

            if not isinstance(runs, list):
                runs = []

            if len(runs) != REPETITIONS_PER_SUT:
                malformed_suts.append(
                    f"{sut_id}: runs={len(runs)}"
                )

            # Extra records, if any, are not part of the requested five.
            for run in runs[:REPETITIONS_PER_SUT]:
                overall_status = str(
                    run.get("overall_status", "")
                ).strip().upper()

                run_ok = (
                    run.get("ok") is True
                    or overall_status == "PASS"
                )

                if run_ok:
                    ok_count += 1

                for metric, field in metric_fields.items():
                    value = numeric_or_none(run.get(field))

                    # Strict-zero/penalised policy:
                    # non-PASS or unavailable metric -> zero.
                    if run_ok and value is not None:
                        penalised_sums[metric] += value
                        available_sums[metric] += value
                        available_counts[metric] += 1

        print(
            "[NON-AI EVOSUITE] "
            f"suts={len(per_sut)}, "
            f"slots={attempted_slots}, "
            f"ok={ok_count}, "
            f"line_n={available_counts['line']}, "
            f"branch_n={available_counts['branch']}, "
            f"mutation_n={available_counts['mutation']}"
        )

        for item in malformed_suts[:5]:
            print(f"[NON-AI EVOSUITE WARNING] {item}")

        if len(malformed_suts) > 5:
            print(
                "[NON-AI EVOSUITE WARNING] "
                f"{len(malformed_suts) - 5} additional warnings omitted"
            )

        return {
            "method": method,
            "category": "Non-AI",
            "source": str(root),
            "sut_count_found": len(per_sut),
            "expected_repetitions": EXPECTED_REPETITIONS,
            "attempted_repetitions": attempted_slots,
            "missing_repetitions_penalised_as_zero":
                max(0, EXPECTED_REPETITIONS - attempted_slots),
            "ok_repetitions": ok_count,
            "executable_suites_pct":
                100.0 * ok_count / EXPECTED_REPETITIONS,

            "line_mean_penalised":
                penalised_sums["line"] / EXPECTED_REPETITIONS,
            "branch_mean_penalised":
                penalised_sums["branch"] / EXPECTED_REPETITIONS,
            "mutation_mean_penalised":
                penalised_sums["mutation"] / EXPECTED_REPETITIONS,

            "line_mean_non_penalised":
                available_sums["line"] / available_counts["line"]
                if available_counts["line"]
                else 0.0,
            "branch_mean_non_penalised":
                available_sums["branch"] / available_counts["branch"]
                if available_counts["branch"]
                else 0.0,
            "mutation_mean_non_penalised":
                available_sums["mutation"] /
                available_counts["mutation"]
                if available_counts["mutation"]
                else 0.0,
        }

    # ========================================================
    # Randoop: use its actual aggregate schema
    # ========================================================

    if method == "Randoop":
        main_slots = len(per_sut) * REPETITIONS_PER_SUT

        executable_count = 0

        line_total = 0.0
        branch_total = 0.0
        mutation_total = 0.0

        line_available_count = 0
        branch_available_count = 0
        mutation_available_count = 0

        for sut_id in sorted(per_sut):
            summary_path, data = per_sut[sut_id]

            repetitions_found = safe_int(
                data.get("repetitions_found"),
                safe_int(
                    data.get("generated_reps"),
                    REPETITIONS_PER_SUT,
                ),
            )

            repetitions_found = max(
                0,
                min(REPETITIONS_PER_SUT, repetitions_found),
            )

            test_ok = safe_int(
                data.get("mvn_test_exit_zero"),
                repetitions_found,
            )

            pit_ok = safe_int(
                data.get("pit_exit_zero"),
                0,
            )

            test_ok = max(
                0,
                min(repetitions_found, test_ok),
            )

            pit_ok = max(
                0,
                min(repetitions_found, pit_ok),
            )

            executable_count += test_ok

            line_mean = numeric_or_none(
                data.get("line_pct_mean")
            )

            branch_mean = numeric_or_none(
                data.get("branch_pct_mean")
            )

            mutation_mean = numeric_or_none(
                data.get("pit_score_mean")
            )

            if line_mean is not None and test_ok > 0:
                line_total += line_mean * test_ok
                line_available_count += test_ok

            if branch_mean is not None and test_ok > 0:
                branch_total += branch_mean * test_ok
                branch_available_count += test_ok

            if mutation_mean is not None and pit_ok > 0:
                mutation_total += mutation_mean * pit_ok
                mutation_available_count += pit_ok

        # Final reporting rescue documented for 26_jipa.
        # It contributes structural metrics for five reporting slots,
        # but no ordinary executable/PIT closure.
        rescue_added = "26_jipa" not in per_sut

        if rescue_added:
            attempted_slots = main_slots + REPETITIONS_PER_SUT

            rescued_line = 12.14
            rescued_branch = 9.066

            line_total += rescued_line * REPETITIONS_PER_SUT
            branch_total += rescued_branch * REPETITIONS_PER_SUT

            line_available_count += REPETITIONS_PER_SUT
            branch_available_count += REPETITIONS_PER_SUT
        else:
            attempted_slots = main_slots

        print(
            "[NON-AI RANDOOP] "
            f"main_suts={len(per_sut)}, "
            f"slots={attempted_slots}, "
            f"test_ok={executable_count}, "
            f"line_n={line_available_count}, "
            f"branch_n={branch_available_count}, "
            f"mutation_n={mutation_available_count}, "
            f"jipa_rescue_added={rescue_added}"
        )

        result = {
            "method": method,
            "category": "Non-AI",
            "source":
                f"{root}; 26_jipa rescued structural reporting",
            "sut_count_found":
                len(per_sut) + (1 if rescue_added else 0),
            "expected_repetitions": EXPECTED_REPETITIONS,
            "attempted_repetitions": attempted_slots,
            "missing_repetitions_penalised_as_zero":
                max(0, EXPECTED_REPETITIONS - attempted_slots),
            "ok_repetitions": executable_count,
            "executable_suites_pct":
                100.0 * executable_count / EXPECTED_REPETITIONS,

            "line_mean_penalised":
                line_total / EXPECTED_REPETITIONS,
            "branch_mean_penalised":
                branch_total / EXPECTED_REPETITIONS,
            "mutation_mean_penalised":
                mutation_total / EXPECTED_REPETITIONS,

            "line_mean_non_penalised":
                line_total / line_available_count
                if line_available_count
                else 0.0,
            "branch_mean_non_penalised":
                branch_total / branch_available_count
                if branch_available_count
                else 0.0,
            "mutation_mean_non_penalised":
                mutation_total / mutation_available_count
                if mutation_available_count
                else 0.0,
        }

        print(
            "[NON-AI RANDOOP METRICS] "
            f"line={result['line_mean_penalised']:.4f} -> "
            f"{result['line_mean_non_penalised']:.4f}, "
            f"branch={result['branch_mean_penalised']:.4f} -> "
            f"{result['branch_mean_non_penalised']:.4f}, "
            f"mutation={result['mutation_mean_penalised']:.4f} -> "
            f"{result['mutation_mean_non_penalised']:.4f}"
        )

        return result

    raise RuntimeError(
        f"Unsupported non-AI SF110 method: {method}"
    )


def clean_cluster_model_name(raw_name):
    name = raw_name.lower()

    if "codellama" in name:
        return "CodeLlama"

    if "codestral" in name:
        return "Codestral"

    if "deepseek-coder-v2" in name:
        return "DeepSeek-Coder-V2"

    if "deepseek-v2-16b" in name:
        return "DeepSeek-V2"

    if "qwen2.5-coder" in name:
        return "Qwen2.5-Coder"

    if "qwen3-coder" in name:
        return "Qwen3-Coder"

    if "qwen3.5" in name:
        return "Qwen3.5"

    raise RuntimeError(
        f"Unknown cluster model name: {raw_name}"
    )


def summarise_cluster():
    path = CLUSTER_ROOT / "final_model_summary.tsv"
    source_rows = read_delimited(path, "\t")

    by_name = {}

    for source_row in source_rows:
        label = clean_cluster_model_name(source_row["model"])

        requested = safe_int(
            source_row.get("requested_repetitions"),
            EXPECTED_REPETITIONS,
        )

        ok_final = safe_int(source_row.get("ok_final"), 0)

        by_name[label] = {
            "method": label,
            "category": "Cluster LLM",
            "source": str(path),
            "expected_repetitions": EXPECTED_REPETITIONS,
            "attempted_repetitions": requested,
            "missing_repetitions_penalised_as_zero":
                max(0, EXPECTED_REPETITIONS - requested),
            "ok_repetitions": ok_final,
            "executable_suites_pct":
                safe_float(
                    source_row.get("operational_closure_pct")
                ),
            "line_mean_penalised":
                safe_float(
                    source_row.get("line_mean_penalized")
                ),
            "branch_mean_penalised":
                safe_float(
                    source_row.get("branch_mean_penalized")
                ),
            "mutation_mean_penalised":
                safe_float(
                    source_row.get("mutation_mean_penalized")
                ),
            "line_mean_non_penalised":
                safe_float(
                    source_row.get("line_mean_ok_only")
                ),
            "branch_mean_non_penalised":
                safe_float(
                    source_row.get("branch_mean_ok_only")
                ),
            "mutation_mean_non_penalised":
                safe_float(
                    source_row.get("mutation_mean_ok_only")
                ),
        }

    desired_order = [
        "CodeLlama",
        "Codestral",
        "DeepSeek-Coder-V2",
        "DeepSeek-V2",
        "Qwen2.5-Coder",
        "Qwen3-Coder",
        "Qwen3.5",
    ]

    missing = [
        model
        for model in desired_order
        if model not in by_name
    ]

    if missing:
        raise RuntimeError(
            f"Missing expected cluster models: {missing}"
        )

    return [by_name[model] for model in desired_order]


# ============================================================
# Load and normalise all methods
# ============================================================

rows = []

# Non-AI order follows the previous Java figures.
rows.append(summarise_non_ai("EvoSuite", EVOSUITE_ROOT))
rows.append(summarise_non_ai("Randoop", RANDOOP_ROOT))

# GPT-4o final effective combined result.
gpt4o_path = GPT4O_ROOT / "final_effective_combined_index.tsv"
gpt4o_records = read_delimited(gpt4o_path, "\t")

rows.append(
    summarise_individual_records(
        method="GPT-4o",
        category="IAEdu LLM",
        records=gpt4o_records,
        status_field="status",
        line_field="line_pct",
        branch_field="branch_pct",
        mutation_field="mutation_pct",
        source=str(gpt4o_path),
    )
)

# GPT-5.5 final rerun.
gpt55_path = GPT55_ROOT / "dataset_summary.tsv"
gpt55_records = read_delimited(gpt55_path, "\t")

rows.append(
    summarise_individual_records(
        method="GPT-5.5",
        category="IAEdu LLM",
        records=gpt55_records,
        status_field="final_status",
        line_field="line_pct_penalized",
        branch_field="branch_pct_penalized",
        mutation_field="pit_score_pct_penalized",
        source=str(gpt55_path),
    )
)

# Cluster models.
rows.extend(summarise_cluster())


# ============================================================
# Validation and output table
# ============================================================

metric_keys = [
    "executable_suites_pct",
    "line_mean_penalised",
    "line_mean_non_penalised",
    "branch_mean_penalised",
    "branch_mean_non_penalised",
    "mutation_mean_penalised",
    "mutation_mean_non_penalised",
]

for row in rows:
    for key in metric_keys:
        value = safe_float(row.get(key))

        if value < -1e-9 or value > 100.0001:
            raise RuntimeError(
                f"{row['method']}: invalid {key}={value}"
            )

        row[key] = max(0.0, min(100.0, value))

    for metric in ("line", "branch", "mutation"):
        penalised = row[f"{metric}_mean_penalised"]
        non_penalised = row[f"{metric}_mean_non_penalised"]

        if non_penalised + 1e-6 < penalised:
            raise RuntimeError(
                f"{row['method']}: "
                f"{metric} non-penalised mean "
                f"({non_penalised}) is below penalised mean "
                f"({penalised})."
            )


fieldnames = [
    "method",
    "category",
    "expected_repetitions",
    "attempted_repetitions",
    "missing_repetitions_penalised_as_zero",
    "ok_repetitions",
    "executable_suites_pct",
    "line_mean_penalised",
    "line_mean_non_penalised",
    "branch_mean_penalised",
    "branch_mean_non_penalised",
    "mutation_mean_penalised",
    "mutation_mean_non_penalised",
    "source",
]

with SUMMARY_TSV.open(
    "w",
    encoding="utf-8",
    newline="",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=fieldnames,
        delimiter="\t",
        extrasaction="ignore",
    )

    writer.writeheader()

    for row in rows:
        output_row = dict(row)

        for key in metric_keys:
            output_row[key] = f"{safe_float(row[key]):.4f}"

        writer.writerow(output_row)


with VALIDATION_TXT.open(
    "w",
    encoding="utf-8",
) as handle:
    handle.write("SF110 final graph validation\n")
    handle.write("=" * 80 + "\n")
    handle.write(
        f"Expected repetitions per method: "
        f"{EXPECTED_REPETITIONS}\n\n"
    )

    for row in rows:
        handle.write(
            f"{row['method']}\n"
            f"  category: {row['category']}\n"
            f"  attempted: {row['attempted_repetitions']}\n"
            f"  missing penalised as zero: "
            f"{row['missing_repetitions_penalised_as_zero']}\n"
            f"  ok: {row['ok_repetitions']}\n"
            f"  executable: "
            f"{row['executable_suites_pct']:.4f}%\n"
            f"  line: "
            f"{row['line_mean_penalised']:.4f}% -> "
            f"{row['line_mean_non_penalised']:.4f}%\n"
            f"  branch: "
            f"{row['branch_mean_penalised']:.4f}% -> "
            f"{row['branch_mean_non_penalised']:.4f}%\n"
            f"  mutation: "
            f"{row['mutation_mean_penalised']:.4f}% -> "
            f"{row['mutation_mean_non_penalised']:.4f}%\n"
            f"  source: {row['source']}\n\n"
        )


# ============================================================
# Shared graphical conventions
# ============================================================

METHODS = [row["method"] for row in rows]

LINE_COLOR = "#ff7f0e"
BRANCH_COLOR = "#2ca02c"
MUTATION_COLOR = "#d62728"
EXECUTABLE_COLOR = "#1f77b4"

PENALISED_ALPHA = 1.0
UPLIFT_ALPHA = 0.20
UPLIFT_HATCH = "///"


# ============================================================
# Stacked/grouped bar chart
# ============================================================

x = np.arange(len(rows))
width = 0.22

fig, ax = plt.subplots(figsize=(18, 8))

bar_metrics = [
    (
        "line",
        "Line coverage",
        LINE_COLOR,
        -width,
    ),
    (
        "branch",
        "Branch coverage",
        BRANCH_COLOR,
        0.0,
    ),
    (
        "mutation",
        "Mutation score",
        MUTATION_COLOR,
        width,
    ),
]

for metric, label, colour, offset in bar_metrics:
    penalised = np.array(
        [
            row[f"{metric}_mean_penalised"]
            for row in rows
        ],
        dtype=float,
    )

    non_penalised = np.array(
        [
            row[f"{metric}_mean_non_penalised"]
            for row in rows
        ],
        dtype=float,
    )

    uplift = np.maximum(
        0.0,
        non_penalised - penalised,
    )

    ax.bar(
        x + offset,
        penalised,
        width=width,
        color=colour,
        edgecolor=colour,
        linewidth=0.6,
        alpha=PENALISED_ALPHA,
        zorder=3,
    )

    ax.bar(
        x + offset,
        uplift,
        width=width,
        bottom=penalised,
        color=to_rgba(colour, UPLIFT_ALPHA),
        edgecolor=to_rgba(colour, 0.55),
        linewidth=0.7,
        hatch=UPLIFT_HATCH,
        zorder=3,
    )

ax.set_ylabel("%", fontsize=13)
ax.set_ylim(0, 100)
ax.set_yticks(np.arange(0, 101, 10))

ax.set_xticks(x)
ax.set_xticklabels(
    METHODS,
    rotation=27,
    ha="right",
    rotation_mode="anchor",
    fontsize=11,
)

ax.tick_params(axis="y", labelsize=11)
ax.grid(axis="y", alpha=0.25, zorder=0)

legend_handles = [
    Patch(
        facecolor=LINE_COLOR,
        edgecolor=LINE_COLOR,
        label="Line coverage",
    ),
    Patch(
        facecolor=BRANCH_COLOR,
        edgecolor=BRANCH_COLOR,
        label="Branch coverage",
    ),
    Patch(
        facecolor=MUTATION_COLOR,
        edgecolor=MUTATION_COLOR,
        label="Mutation score",
    ),
    Patch(
        facecolor="#bdbdbd",
        edgecolor="#666666",
        label="Penalised mean",
    ),
    Patch(
        facecolor="white",
        edgecolor="#666666",
        hatch=UPLIFT_HATCH,
        label="Additional uplift to non-penalised mean",
    ),
]

ax.legend(
    handles=legend_handles,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.29),
    ncol=3,
    frameon=True,
    fontsize=10,
)

fig.subplots_adjust(
    left=0.06,
    right=0.99,
    top=0.98,
    bottom=0.36,
)

fig.savefig(
    BARCHART_PNG,
    dpi=320,
    bbox_inches="tight",
    pad_inches=0.12,
)

fig.savefig(
    BARCHART_SVG,
    bbox_inches="tight",
    pad_inches=0.12,
)

plt.close(fig)


# ============================================================
# Spyder/radar chart
# ============================================================

angles = np.linspace(
    0,
    2 * np.pi,
    len(METHODS),
    endpoint=False,
)

closed_angles = np.concatenate(
    [angles, angles[:1]]
)

fig = plt.figure(figsize=(13, 13))
ax = fig.add_subplot(111, polar=True)

ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(
    ["20", "40", "60", "80", "100"],
    fontsize=10,
)
ax.set_rlabel_position(13)

ax.set_xticks(angles)
ax.set_xticklabels([])

# Place method names beyond the chart so they do not overlap it.
for angle, label in zip(angles, METHODS):
    cosine = math.cos(angle)
    sine = math.sin(angle)

    if cosine > 0.25:
        horizontal_alignment = "left"
    elif cosine < -0.25:
        horizontal_alignment = "right"
    else:
        horizontal_alignment = "center"

    if sine > 0.25:
        vertical_alignment = "bottom"
    elif sine < -0.25:
        vertical_alignment = "top"
    else:
        vertical_alignment = "center"

    ax.text(
        angle,
        106.5,
        label,
        ha=horizontal_alignment,
        va=vertical_alignment,
        fontsize=11,
        clip_on=False,
    )

radar_metrics = [
    (
        "executable_suites_pct",
        "Executable suites",
        EXECUTABLE_COLOR,
    ),
    (
        "line_mean_penalised",
        "Line coverage",
        LINE_COLOR,
    ),
    (
        "branch_mean_penalised",
        "Branch coverage",
        BRANCH_COLOR,
    ),
    (
        "mutation_mean_penalised",
        "Mutation score",
        MUTATION_COLOR,
    ),
]

for key, label, colour in radar_metrics:
    values = np.array(
        [safe_float(row[key]) for row in rows],
        dtype=float,
    )

    closed_values = np.concatenate(
        [values, values[:1]]
    )

    ax.plot(
        closed_angles,
        closed_values,
        linewidth=2.0,
        color=colour,
        label=label,
    )

    ax.fill(
        closed_angles,
        closed_values,
        color=colour,
        alpha=0.045,
    )

ax.grid(alpha=0.45)

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.13),
    ncol=4,
    frameon=True,
    fontsize=10,
)

fig.subplots_adjust(
    left=0.11,
    right=0.89,
    top=0.90,
    bottom=0.18,
)

fig.savefig(
    SPYDER_PNG,
    dpi=320,
    bbox_inches="tight",
    pad_inches=0.20,
)

fig.savefig(
    SPYDER_SVG,
    bbox_inches="tight",
    pad_inches=0.20,
)

plt.close(fig)


# ============================================================
# Compact terminal output
# ============================================================

print("===== SF110 FINAL GRAPH SUMMARY =====")

header = (
    f"{'Method':<22}"
    f"{'Found':>8}"
    f"{'OK':>8}"
    f"{'Exec %':>10}"
    f"{'Line P':>10}"
    f"{'Branch P':>11}"
    f"{'Mutation P':>13}"
)

print(header)
print("-" * len(header))

for row in rows:
    print(
        f"{row['method']:<22}"
        f"{row['attempted_repetitions']:>8}"
        f"{row['ok_repetitions']:>8}"
        f"{row['executable_suites_pct']:>10.2f}"
        f"{row['line_mean_penalised']:>10.2f}"
        f"{row['branch_mean_penalised']:>11.2f}"
        f"{row['mutation_mean_penalised']:>13.2f}"
    )

print()
print("===== GENERATED FILES =====")
print(f"Summary TSV: {SUMMARY_TSV}")
print(f"Validation:  {VALIDATION_TXT}")
print(f"Barchart:    {BARCHART_PNG}")
print(f"Barchart SVG:{BARCHART_SVG}")
print(f"Spyder:      {SPYDER_PNG}")
print(f"Spyder SVG:  {SPYDER_SVG}")
