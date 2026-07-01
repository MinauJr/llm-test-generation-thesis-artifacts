#!/usr/bin/env python3
import csv
import json
import math
import re
from pathlib import Path
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


FIG_DIR = Path.home() / "analysis_defects4j" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Final roots confirmed
# -----------------------------

OFFICIAL_ROOT = Path("/home/jpaiva/projetos/d4j_cluster/out/_official_defects4j_dataset_tests_RELEVANT_FINAL_20260611_112409")

EVOSUITE_ROOT = Path("/second_disk/nonAI/java_workflow/out/_final_defects4j_evosuite")
RANDOOP_ROOT = Path("/second_disk/nonAI/java_workflow/out/_final_defects4j_randoop_20260330_132501")

GPT4O_ROOT = Path("/home/jpaiva/defects4j_gpt4o/out/_final_defects4j_gpt4o_retryempty15")
GPT55_ROOT = Path("/home/jpaiva/defects4j_gpt4o/out/_final_gpt55_defects4j_java_retryempty15")
CLAUDE_ROOT = Path("/home/jpaiva/defects4j_gpt4o/out/_final_claude47_defects4j_java_retryempty15")

# Complete cluster evaluation: 8 models x 17 SUTs x 5 reps = 680.
# Do not use v2_cleanerfix as final because it is partial.
CLUSTER_ROOT = Path("/home/jpaiva/defects4j_gpt4o/out/_cluster_defects4j_java_openweight_eval_all_v1")

EXPECTED_SUTS = 17
EXPECTED_REPS = 85
EXPECTED_OFFICIAL_REPS = 17

SUT_NAMES = {
    "Chart_5f", "Cli_23f", "Closure_77f", "Codec_15f", "Collections_18f",
    "Compress_13f", "Csv_4f", "Gson_17f", "JacksonCore_13f",
    "JacksonDatabind_17f", "JacksonXml_5f", "Jsoup_91f", "JxPath_22f",
    "Lang_52f", "Math_9f", "Mockito_19f", "Time_24f",
}

CLUSTER_MODELS = [
    ("cluster-max-codellama-7b-instruct-ctx16k", "CodeLlama"),
    ("cluster-safe-codestral-22b-ctx16k", "Codestral"),
    ("cluster-safe-deepseek-coder-v2-16b-ctx16k", "DeepSeek-Coder-V2"),
    ("cluster-safe-deepseek-v2-16b-ctx32k", "DeepSeek-V2-16B"),
    ("cluster-safe-deepseek-v2-lite-ctx32k", "DeepSeek-V2-Lite"),
    ("cluster-safe-qwen2.5-coder-14b-ctx32k", "Qwen2.5-Coder"),
    ("cluster-safe-qwen3-coder-30b-official-ctx8k", "Qwen3-Coder"),
    ("cluster-safe-qwen3.5-9b-ctx32k", "Qwen3.5"),
]

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
    "DeepSeek-V2-16B",
    "DeepSeek-V2-Lite",
    "Qwen2.5-Coder",
    "Qwen3-Coder",
    "Qwen3.5",
]

RADAR_OUT = FIG_DIR / "defects4j_radar_tools_as_axes_with_official.png"
STACKED_OUT = FIG_DIR / "defects4j_stacked_3metrics_with_official.png"

RAW_CSV = FIG_DIR / "defects4j_repetition_level_extracted.csv"
SUMMARY_CSV = FIG_DIR / "defects4j_approach_summary_strict0.csv"
RADAR_CSV = FIG_DIR / "defects4j_radar_summary_with_official.csv"
STACKED_CSV = FIG_DIR / "defects4j_stacked_3metrics_with_official_summary.csv"


# -----------------------------
# Generic helpers
# -----------------------------

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def flatten_json(obj, prefix=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten_json(v, prefix + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten_json(v, prefix + (str(i),))
    else:
        yield prefix, obj


def to_float(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace(",", ".")
        s = s.replace("%", "")
        try:
            return float(s)
        except Exception:
            return None
    return None


def normalize_pct(value, keypath=""):
    v = to_float(value)
    if v is None:
        return None
    if v < 0:
        return None
    # Many tools store ratios in [0, 1].
    if v <= 1.0:
        return v * 100.0
    # Coverage/mutation percentages should not exceed 100.
    if v > 100.0:
        return None
    return v


def has_bad_count_word(key):
    bad = [
        "total", "count", "available", "missing", "covered", "missed",
        "valid", "invalid", "killed", "survived", "detected", "mutants",
        "tests", "classes", "methods"
    ]
    return any(b in key for b in bad)


def extract_metric(data, metric):
    """
    Robust extraction across several status.json / summary.json formats.
    Returns a percentage in [0, 100] or None.
    """
    flat = []
    for path, value in flatten_json(data):
        key = ".".join(path).lower()
        v = normalize_pct(value, key)
        if v is None:
            continue
        flat.append((key, v))

    if metric == "line":
        priority = [
            "line_coverage_pct",
            "line_coverage_percent",
            "line_coverage_percentage",
            "linecoveragepct",
            "linecoveragepercent",
            "line_pct",
            "line_percent",
            "line_rate",
            "line_coverage",
            "jacoco.line",
        ]

        def ok_key(k):
            return (
                "line" in k
                and ("coverage" in k or "pct" in k or "percent" in k or "rate" in k or "ratio" in k)
                and (not has_bad_count_word(k) or "pct" in k or "percent" in k or "rate" in k or "ratio" in k)
            )

    elif metric == "branch":
        priority = [
            "branch_coverage_pct",
            "branch_coverage_percent",
            "branch_coverage_percentage",
            "branchcoveragepct",
            "branchcoveragepercent",
            "branch_pct",
            "branch_percent",
            "branch_rate",
            "branch_coverage",
            "jacoco.branch",
        ]

        def ok_key(k):
            return (
                "branch" in k
                and ("coverage" in k or "pct" in k or "percent" in k or "rate" in k or "ratio" in k)
                and (not has_bad_count_word(k) or "pct" in k or "percent" in k or "rate" in k or "ratio" in k)
            )

    elif metric == "mutation":
        priority = [
            "mutation_score_pct",
            "mutation_score_percent",
            "mutation_score_percentage",
            "pit_score_pct",
            "pit_score_percent",
            "pit_score",
            "mutation_score",
            "mutation_pct",
            "mutation_percent",
            "mutation_coverage",
            "mutation_rate",
        ]

        def ok_key(k):
            return (
                ("mutation" in k or "pit" in k)
                and ("score" in k or "coverage" in k or "pct" in k or "percent" in k or "rate" in k or "ratio" in k)
                and (not has_bad_count_word(k) or "score" in k or "pct" in k or "percent" in k or "rate" in k or "ratio" in k)
            )

    else:
        raise ValueError(metric)

    candidates = []
    for key, value in flat:
        if not ok_key(key):
            continue
        rank = 999
        for i, frag in enumerate(priority):
            if frag in key:
                rank = i
                break
        candidates.append((rank, key, value))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], len(x[1]), x[1]))
    return candidates[0][2]


def extract_status(data):
    # Prefer top-level status-like fields.
    for k in ["status", "final_status", "result", "outcome"]:
        if isinstance(data, dict) and k in data:
            return str(data[k])

    # Then search recursively.
    for path, value in flatten_json(data):
        last = path[-1].lower() if path else ""
        if last in {"status", "final_status", "result", "outcome"}:
            return str(value)

    # Some older summaries only have success booleans.
    for path, value in flatten_json(data):
        last = path[-1].lower() if path else ""
        if last in {"success", "ok", "passed"} and isinstance(value, bool):
            return "ok" if value else "failed"

    return "unknown"


def is_executable_status(status):
    return str(status).strip().lower() == "ok"


def find_sut(path: Path):
    for part in path.parts:
        if part in SUT_NAMES:
            return part
    return ""


def find_run(path: Path):
    for part in path.parts:
        if re.fullmatch(r"run_\d+", part):
            return part
        if re.fullmatch(r"\d+-\d+", part):
            return part
    return ""


def read_records_from_metric_status(root: Path, approach: str, category: str):
    records = []
    files = sorted(p for p in root.rglob("status.json") if "/metrics/status.json" in str(p))

    for p in files:
        if not any(sut in p.parts for sut in SUT_NAMES):
            continue

        data = load_json(p)
        status = extract_status(data)
        executable = is_executable_status(status)

        records.append({
            "approach": approach,
            "category": category,
            "source_file": str(p),
            "sut": find_sut(p),
            "run": find_run(p),
            "status": status,
            "executable": executable,
            "line": extract_metric(data, "line"),
            "branch": extract_metric(data, "branch"),
            "mutation": extract_metric(data, "mutation"),
        })

    return records


def read_records_from_randoop_summary(root: Path):
    records = []
    files = sorted(p for p in root.rglob("summary.json") if "aggregate" not in p.parts)

    for p in files:
        if not any(sut in p.parts for sut in SUT_NAMES):
            continue

        data = load_json(p)
        line = extract_metric(data, "line")
        branch = extract_metric(data, "branch")
        mutation = extract_metric(data, "mutation")
        status = extract_status(data)

        # Older Randoop summaries may not have a clean "status" field.
        # If metrics exist and no explicit status is present, treat it as ok.
        if status == "unknown" and any(v is not None for v in [line, branch, mutation]):
            status = "ok"

        executable = is_executable_status(status)

        records.append({
            "approach": "Randoop",
            "category": "non_ai",
            "source_file": str(p),
            "sut": find_sut(p),
            "run": find_run(p),
            "status": status,
            "executable": executable,
            "line": line,
            "branch": branch,
            "mutation": mutation,
        })

    return records


def parse_official_summary(root: Path):
    txt = root / "dataset_summary.txt"
    vals = {}
    if txt.exists():
        for line in txt.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*([A-Za-z0-9_]+)\s*=\s*([0-9.]+)\s*$", line)
            if m:
                vals[m.group(1)] = float(m.group(2))

    suts_expected = int(vals.get("suts_expected", EXPECTED_OFFICIAL_REPS))
    suts_ok = int(vals.get("suts_valid_ok", suts_expected))
    executable_pct = (suts_ok / suts_expected * 100.0) if suts_expected else 0.0

    return {
        "approach": "Dataset tests",
        "category": "official",
        "expected": suts_expected,
        "found": int(vals.get("suts_with_status", suts_expected)),
        "executable_count": suts_ok,
        "executable_pct": executable_pct,
        "status_counts": "ok:%d" % suts_ok,
        "line_penalized": vals.get("line_coverage_mean_strict0", vals.get("line_coverage_mean_available")),
        "branch_penalized": vals.get("branch_coverage_mean_strict0", vals.get("branch_coverage_mean_available")),
        "mutation_penalized": vals.get("mutation_score_mean_strict0", vals.get("mutation_score_mean_available")),
        "line_nonpenalized": vals.get("line_coverage_mean_available", vals.get("line_coverage_mean_strict0")),
        "branch_nonpenalized": vals.get("branch_coverage_mean_available", vals.get("branch_coverage_mean_strict0")),
        "mutation_nonpenalized": vals.get("mutation_score_mean_available", vals.get("mutation_score_mean_strict0")),
        "line_available": int(vals.get("line_metric_available", suts_ok)),
        "branch_available": int(vals.get("branch_metric_available", suts_ok)),
        "mutation_available": int(vals.get("mutation_metric_available", suts_ok)),
    }


def summarize_records(records, approach, category, expected):
    status_counts = Counter(r["status"] for r in records)
    executable_records = [r for r in records if r["executable"]]

    def metric_summary(metric):
        vals = [
            r[metric]
            for r in executable_records
            if r.get(metric) is not None
        ]
        penalized = sum(vals) / expected if expected else 0.0
        nonpenalized = sum(vals) / len(vals) if vals else 0.0
        return penalized, nonpenalized, len(vals)

    line_p, line_np, line_avail = metric_summary("line")
    branch_p, branch_np, branch_avail = metric_summary("branch")
    mut_p, mut_np, mut_avail = metric_summary("mutation")

    executable_count = len(executable_records)
    executable_pct = executable_count / expected * 100.0 if expected else 0.0

    return {
        "approach": approach,
        "category": category,
        "expected": expected,
        "found": len(records),
        "executable_count": executable_count,
        "executable_pct": executable_pct,
        "status_counts": ";".join(f"{k}:{v}" for k, v in sorted(status_counts.items())),
        "line_penalized": line_p,
        "branch_penalized": branch_p,
        "mutation_penalized": mut_p,
        "line_nonpenalized": line_np,
        "branch_nonpenalized": branch_np,
        "mutation_nonpenalized": mut_np,
        "line_available": line_avail,
        "branch_available": branch_avail,
        "mutation_available": mut_avail,
    }


def fmt(v):
    if v is None:
        return ""
    return f"{float(v):.4f}"


# -----------------------------
# Collect data
# -----------------------------

all_records = []
summary_rows = []

# Official dataset tests.
summary_rows.append(parse_official_summary(OFFICIAL_ROOT))

# EvoSuite.
evosuite_records = read_records_from_metric_status(EVOSUITE_ROOT, "EvoSuite", "non_ai")
all_records.extend(evosuite_records)
summary_rows.append(summarize_records(evosuite_records, "EvoSuite", "non_ai", EXPECTED_REPS))

# Randoop.
randoop_records = read_records_from_randoop_summary(RANDOOP_ROOT)
all_records.extend(randoop_records)
summary_rows.append(summarize_records(randoop_records, "Randoop", "non_ai", EXPECTED_REPS))

# Proprietary LLMs.
for root, approach in [
    (GPT4O_ROOT, "GPT-4o"),
    (GPT55_ROOT, "GPT-5.5"),
    (CLAUDE_ROOT, "Claude 4.7"),
]:
    recs = read_records_from_metric_status(root, approach, "iaedu")
    all_records.extend(recs)
    summary_rows.append(summarize_records(recs, approach, "iaedu", EXPECTED_REPS))

# Cluster open-weight models.
for model_dir, label in CLUSTER_MODELS:
    root = CLUSTER_ROOT / model_dir
    recs = read_records_from_metric_status(root, label, "cluster")
    all_records.extend(recs)
    summary_rows.append(summarize_records(recs, label, "cluster", EXPECTED_REPS))


# -----------------------------
# Sanity checks
# -----------------------------

summary_by_name = {r["approach"]: r for r in summary_rows}

print("===== DEFECTS4J FINAL SUMMARY =====")
for name in ORDER:
    r = summary_by_name.get(name)
    if not r:
        print(f"[MISSING] {name}")
        continue

    print(
        f"{name}: "
        f"found={r['found']}/{r['expected']} | "
        f"exec={r['executable_pct']:.2f} | "
        f"line={r['line_penalized']:.2f} -> {r['line_nonpenalized']:.2f} | "
        f"branch={r['branch_penalized']:.2f} -> {r['branch_nonpenalized']:.2f} | "
        f"mutation={r['mutation_penalized']:.2f} -> {r['mutation_nonpenalized']:.2f}"
    )

print()
print("===== WARNINGS =====")
warnings = 0
for name in ORDER:
    r = summary_by_name.get(name)
    if not r:
        warnings += 1
        print(f"[WARN] missing approach: {name}")
        continue

    if r["found"] != r["expected"]:
        warnings += 1
        print(f"[WARN] {name}: found {r['found']} records but expected {r['expected']}")

    for m in ["line", "branch", "mutation"]:
        if r[f"{m}_available"] == 0:
            warnings += 1
            print(f"[WARN] {name}: no available {m} metrics")

if warnings == 0:
    print("none")


# -----------------------------
# Write CSVs
# -----------------------------

raw_fields = [
    "approach", "category", "sut", "run", "status", "executable",
    "line", "branch", "mutation", "source_file"
]

with RAW_CSV.open("w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=raw_fields)
    writer.writeheader()
    for r in all_records:
        row = dict(r)
        for m in ["line", "branch", "mutation"]:
            row[m] = fmt(row.get(m))
        writer.writerow(row)

summary_fields = [
    "approach", "category", "expected", "found", "executable_count", "executable_pct",
    "line_penalized", "branch_penalized", "mutation_penalized",
    "line_nonpenalized", "branch_nonpenalized", "mutation_nonpenalized",
    "line_available", "branch_available", "mutation_available",
    "status_counts"
]

ordered_summary = [summary_by_name[name] for name in ORDER if name in summary_by_name]

for out_csv in [SUMMARY_CSV, RADAR_CSV, STACKED_CSV]:
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=summary_fields)
        writer.writeheader()
        for r in ordered_summary:
            row = dict(r)
            for k in [
                "executable_pct",
                "line_penalized", "branch_penalized", "mutation_penalized",
                "line_nonpenalized", "branch_nonpenalized", "mutation_nonpenalized",
            ]:
                row[k] = fmt(row.get(k))
            writer.writerow(row)


# -----------------------------
# Plot 1: radar, tools/models as axes
# -----------------------------

labels = [r["approach"] for r in ordered_summary]
n = len(labels)

angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
angles += angles[:1]

metric_series = [
    ("Executable suites", "executable_pct"),
    ("Line coverage", "line_penalized"),
    ("Branch coverage", "branch_penalized"),
    ("Mutation score", "mutation_penalized"),
]

fig = plt.figure(figsize=(18, 11))
ax = plt.subplot(111, polar=True)

for label, key in metric_series:
    values = [float(r[key]) for r in ordered_summary]
    values += values[:1]
    ax.plot(angles, values, linewidth=2, marker="o", label=label)
    ax.fill(angles, values, alpha=0.05)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels, fontsize=9)
ax.tick_params(axis="x", pad=16)

ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8)
ax.set_title(
    "Defects4J Java — final comparison by approach/model\n"
    "Strict/penalized means: missing, failed, or unavailable metrics count as 0",
    fontsize=14,
    pad=35,
)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=4, frameon=False)

fig.tight_layout()
fig.savefig(RADAR_OUT, dpi=220, bbox_inches="tight")
plt.close(fig)


# -----------------------------
# Plot 2: stacked bars, penalized + non-penalized uplift
# -----------------------------

x = np.arange(len(ordered_summary))
width = 0.23

bar_metrics = [
    ("Line", "line_penalized", "line_nonpenalized"),
    ("Branch", "branch_penalized", "branch_nonpenalized"),
    ("Mutation", "mutation_penalized", "mutation_nonpenalized"),
]

fig, ax = plt.subplots(figsize=(22, 9))

offsets = [-width, 0, width]

base_handles = []

for i, (metric_label, penalized_key, nonpenalized_key) in enumerate(bar_metrics):
    penalized = np.array([float(r[penalized_key]) for r in ordered_summary])
    nonpenalized = np.array([float(r[nonpenalized_key]) for r in ordered_summary])
    uplift = np.maximum(nonpenalized - penalized, 0)

    bars = ax.bar(
        x + offsets[i],
        penalized,
        width,
        label=f"{metric_label} penalized",
    )
    base_handles.append(bars[0])

    ax.bar(
        x + offsets[i],
        uplift,
        width,
        bottom=penalized,
        hatch="///",
        edgecolor="black",
        linewidth=0.6,
        alpha=0.35,
        label=f"{metric_label} non-penalized uplift",
    )

ax.set_title(
    "Defects4J Java — coverage and mutation score\n"
    "Solid bar = strict/penalized mean; hatched top = uplift to non-penalized mean",
    fontsize=14,
)
ax.set_ylabel("Percentage (%)")
ax.set_ylim(0, 105)

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=35, ha="right")

ax.grid(axis="y", alpha=0.25)

legend_handles = [
    base_handles[0],
    base_handles[1],
    base_handles[2],
    Patch(facecolor="white", edgecolor="black", hatch="///", label="Uplift to non-penalized"),
]
legend_labels = ["Line", "Branch", "Mutation", "Uplift to non-penalized"]

ax.legend(
    legend_handles,
    legend_labels,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.18),
    ncol=4,
    frameon=False,
)

fig.tight_layout()
fig.savefig(STACKED_OUT, dpi=220, bbox_inches="tight")
plt.close(fig)


print()
print("[OK] wrote:")
for p in [RAW_CSV, SUMMARY_CSV, RADAR_CSV, STACKED_CSV, RADAR_OUT, STACKED_OUT]:
    print(f"[OUT] {p}")
