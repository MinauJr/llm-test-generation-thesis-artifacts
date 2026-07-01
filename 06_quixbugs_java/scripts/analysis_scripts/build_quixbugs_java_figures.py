#!/usr/bin/env python3

import csv
import json
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


# ============================================================
# PATHS
# ============================================================

HOME = Path.home()
FIG_DIR = HOME / "analysis_quixbugs_java" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

OFFICIAL_ROOT = (
    HOME
    / "projetos/nonAI/java_workflow/out"
    / "_FINAL_OFFICIAL_QUIXBUGS_JAVA_ALL40_CORRECTED_20260614_184529"
)

EVOSUITE_ROOT = (
    HOME
    / "projetos/nonAI/java_workflow/out"
    / "_final_quixbugs_java_evosuite_40x5_cfg180_t200_corrected"
)

RANDOOP_ROOT = (
    HOME
    / "projetos/nonAI/java_workflow/out"
    / "_final_quixbugs_java_randoop_40x5_cfg180_t200_corrected"
)

GPT4O_ROOT = Path(
    "/second_disk/projetos/quixbugs/quixbugs_java_gpt4o/out/_final_gpt4o_quixbugs_java_40suts_x5_mutation"
)

GPT55_ROOT = Path(
    "/home/jpaiva/projetos/quixbugs_java_gpt55/out/_FINAL_GPT55_QUIXBUGS_JAVA_CLOSED_200_20260620_095218"
)

CLUSTER_COVERAGE_ROOT = Path(
    "/home/jpaiva/quixbugs_java_cluster_local_eval_v1/out/_FINAL_EFFECTIVE_V2_V32_20260617_111636"
)
CLUSTER_PIT_ROOT = Path(
    "/home/jpaiva/quixbugs_java_cluster_local_eval_v1/out/_PIT_FULL_V2_V32_20260617_112750"
)
CLUSTER_V41_ROOT = Path(
    "/home/jpaiva/quixbugs_java_cluster_local_eval_v1/out/_RESCUE_V41_ANSI_FULLCLASS_PILOT_20260617_125903"
)

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

EXPECTED = {
    "Dataset tests": 40,
    "EvoSuite": 200,
    "Randoop": 200,
    "GPT-4o": 200,
    "GPT-5.5": 200,
    "CodeLlama": 200,
    "Codestral": 200,
    "DeepSeek-Coder-V2": 200,
    "DeepSeek-V2": 200,
    "Qwen2.5-Coder": 200,
    "Qwen3-Coder": 200,
    "Qwen3.5": 200,
}

RADAR_OUT = FIG_DIR / "quixbugs_java_radar_tools_as_axes_with_official.png"
STACKED_OUT = FIG_DIR / "quixbugs_java_stacked_3metrics_with_official.png"
SUMMARY_CSV = FIG_DIR / "quixbugs_java_approach_summary_strict0.csv"
RADAR_CSV = FIG_DIR / "quixbugs_java_radar_summary_with_official.csv"
STACKED_CSV = FIG_DIR / "quixbugs_java_stacked_3metrics_with_official_summary.csv"


# ============================================================
# HELPERS
# ============================================================

def norm_label(name: str) -> str:
    x = name.strip()
    mapping = {
        "codellama": "CodeLlama",
        "codestral": "Codestral",
        "deepseek-coder-v2": "DeepSeek-Coder-V2",
        "deepseek_v2": "DeepSeek-V2",
        "deepseek-v2": "DeepSeek-V2",
        "deepseek-v2-lite": "DeepSeek-V2",
        "deepseek-v2-16b": "DeepSeek-V2",
        "qwen2.5-coder": "Qwen2.5-Coder",
        "qwen2_5_coder": "Qwen2.5-Coder",
        "qwen3-coder": "Qwen3-Coder",
        "qwen3.5": "Qwen3.5",
        "qwen3_5": "Qwen3.5",
        "gpt-4o": "GPT-4o",
        "gpt4o": "GPT-4o",
        "gpt-5.5": "GPT-5.5",
        "gpt55": "GPT-5.5",
        "evosuite": "EvoSuite",
        "randoop": "Randoop",
        "dataset tests": "Dataset tests",
    }
    key = x.lower().replace(" ", "").replace("_", "-")
    key2 = x.lower().replace("_", "-")
    return mapping.get(key, mapping.get(key2, x))


def to_float(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() in {"na", "n/a", "none", "null"}:
        return None
    s = s.replace("%", "").strip()
    try:
        return float(s)
    except Exception:
        return None


def to_int(v):
    f = to_float(v)
    if f is None:
        return None
    return int(round(f))


def to_bool(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "y", "ok"}:
        return True
    if s in {"0", "false", "no", "n"}:
        return False
    return None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path):
    return json.loads(read_text(path))


def read_table(path: Path):
    sample = read_text(path)[:4096]
    delimiter = "\t" if "\t" in sample else ","
    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


def row_get(row, *names):
    lowered = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
    for name in names:
        key = name.strip().lower()
        if key in lowered:
            return lowered[key]
    return None


def parse_key_value_text(path: Path):
    out = {}
    for line in read_text(path).splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
        elif ":" in line and not line.strip().startswith("-"):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def safe_mean(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def find_first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None


def find_files(root: Path, patterns, max_depth=4):
    if not root.exists():
        return []
    out = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_depth = len(path.relative_to(root).parts)
        if rel_depth > max_depth:
            continue
        for pat in patterns:
            if path.match(pat):
                out.append(path)
                break
    return sorted(out)


def normalised_row(
    approach,
    category,
    expected,
    found,
    executable_count,
    line_penalized,
    branch_penalized,
    mutation_penalized,
    line_nonpenalized,
    branch_nonpenalized,
    mutation_nonpenalized,
):
    executable_pct = 0.0 if not expected else 100.0 * executable_count / expected
    return {
        "approach": approach,
        "category": category,
        "expected": expected,
        "found": found,
        "executable_count": executable_count,
        "executable_pct": executable_pct,
        "line_penalized": line_penalized,
        "branch_penalized": branch_penalized,
        "mutation_penalized": mutation_penalized,
        "line_nonpenalized": line_nonpenalized,
        "branch_nonpenalized": branch_nonpenalized,
        "mutation_nonpenalized": mutation_nonpenalized,
    }


# ============================================================
# LOADERS
# ============================================================

def load_official():
    """
    QuixBugs Java official/original dataset tests.

    Final corrected output:
      _FINAL_OFFICIAL_QUIXBUGS_JAVA_ALL40_CORRECTED_20260614_184529

    The mutation value used in the main graph is the recommended
    strict mean over the 39 fully mutation-evaluable official suites.
    The one methodologically exceptional suite remains documented in
    methodological_exceptions.tsv and is not converted into an
    artificial zero.
    """

    required_files = [
        OFFICIAL_ROOT / "dataset_summary.txt",
        OFFICIAL_ROOT / "dataset_summary.json",
        OFFICIAL_ROOT / "dataset_aggregate.json",
        OFFICIAL_ROOT / "dataset_runs_index.tsv",
        OFFICIAL_ROOT / "graph_metrics_recommended.tsv",
        OFFICIAL_ROOT / "methodological_exceptions.tsv",
        OFFICIAL_ROOT / "zero_metrics.tsv",
        OFFICIAL_ROOT / "warnings.tsv",
    ]

    missing = [
        str(file)
        for file in required_files
        if not file.exists()
    ]

    if missing:
        raise RuntimeError(
            "Ficheiros finais dos dataset tests em falta:\n"
            + "\n".join(missing)
        )

    expected = 40
    found = 40
    executable_count = 40

    # Final values preserved by the corrected official evaluator.
    line_pen = 89.851796
    branch_pen = 96.529762
    mutation_pen = 93.198931

    # Dataset tests are evaluated once per SUT and do not represent
    # generated-suite failures. Therefore there is no separate uplift
    # from penalised to non-penalised means for this baseline.
    line_nonpen = line_pen
    branch_nonpen = branch_pen
    mutation_nonpen = mutation_pen

    print()
    print("===== OFFICIAL DATASET TESTS =====")
    print(f"[OK] root={OFFICIAL_ROOT}")
    print(f"[OK] executable={executable_count}/{expected}")
    print(f"[OK] line={line_pen:.6f}")
    print(f"[OK] branch={branch_pen:.6f}")
    print(f"[OK] mutation={mutation_pen:.6f}")

    return normalised_row(
        "Dataset tests",
        "official",
        expected,
        found,
        executable_count,
        line_pen,
        branch_pen,
        mutation_pen,
        line_nonpen,
        branch_nonpen,
        mutation_nonpen,
    )



def load_corrected_nonai(root: Path, label: str):
    """
    Lê o corrected_reps.tsv autoritativo de EvoSuite/Randoop.

    Política:
    - apenas status == valid_ok é uma suite executável;
    - média penalizada: denominador fixo de 200 repetições;
    - repetições inválidas, métricas ausentes e falhas contam como zero;
    - média não penalizada: apenas valores métricos > 0
      entre as repetições valid_ok.
    """

    reps_path = root / "corrected_reps.tsv"
    summary_path = root / "corrected_summary.json"

    if not reps_path.exists():
        raise RuntimeError(
            f"{label}: corrected_reps.tsv em falta: {reps_path}"
        )

    if not summary_path.exists():
        raise RuntimeError(
            f"{label}: corrected_summary.json em falta: "
            f"{summary_path}"
        )

    rows = read_table(reps_path)
    summary = read_json(summary_path)

    expected = 200
    found = len(rows)

    if found != expected:
        raise RuntimeError(
            f"{label}: encontradas {found}/{expected} "
            f"repetições em {reps_path}."
        )

    valid_rows = []

    strict_line = []
    strict_branch = []
    strict_mutation = []

    valid_line_all = []
    valid_branch_all = []
    valid_mutation_all = []

    positive_line = []
    positive_branch = []
    positive_mutation = []

    status_counts = {}

    for row in rows:
        raw_status = row_get(
            row,
            "corrected_status",
            "status",
        )

        status = str(raw_status or "").strip().lower()

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

        executable = status == "valid_ok"

        line = to_float(
            row_get(
                row,
                "line_pct",
                "line",
                "line_coverage_pct",
            )
        )

        branch = to_float(
            row_get(
                row,
                "branch_pct",
                "branch",
                "branch_coverage_pct",
            )
        )

        mutation = to_float(
            row_get(
                row,
                "pit_score",
                "mutation_pct",
                "mutation",
                "mutation_score",
            )
        )

        if executable:
            valid_rows.append(row)

            if line is not None:
                valid_line_all.append(line)
                if line > 0:
                    positive_line.append(line)

            if branch is not None:
                valid_branch_all.append(branch)
                if branch > 0:
                    positive_branch.append(branch)

            if mutation is not None:
                valid_mutation_all.append(mutation)
                if mutation > 0:
                    positive_mutation.append(mutation)

        # Strict-zero / penalised aggregation.
        strict_line.append(
            line
            if executable and line is not None
            else 0.0
        )

        strict_branch.append(
            branch
            if executable and branch is not None
            else 0.0
        )

        strict_mutation.append(
            mutation
            if executable and mutation is not None
            else 0.0
        )

    executable_count = len(valid_rows)

    if executable_count == 0:
        raise RuntimeError(
            f"{label}: nenhuma repetição valid_ok encontrada."
        )

    for metric_name, values in (
        ("line", positive_line),
        ("branch", positive_branch),
        ("mutation", positive_mutation),
    ):
        if not values:
            raise RuntimeError(
                f"{label}: nenhuma métrica positiva para "
                f"{metric_name}."
            )

    line_pen = sum(strict_line) / expected
    branch_pen = sum(strict_branch) / expected
    mutation_pen = sum(strict_mutation) / expected

    line_nonpen = sum(positive_line) / len(positive_line)
    branch_nonpen = (
        sum(positive_branch) / len(positive_branch)
    )
    mutation_nonpen = (
        sum(positive_mutation) / len(positive_mutation)
    )

    # Médias sobre repetições válidas, incluindo zeros.
    line_valid_mean = (
        sum(valid_line_all) / len(valid_line_all)
        if valid_line_all
        else None
    )

    branch_valid_mean = (
        sum(valid_branch_all) / len(valid_branch_all)
        if valid_branch_all
        else None
    )

    mutation_valid_mean = (
        sum(valid_mutation_all) / len(valid_mutation_all)
        if valid_mutation_all
        else None
    )

    summary_total = to_int(
        summary.get("total_reps")
    )

    summary_valid = to_int(
        summary.get("valid_ok_reps")
    )

    if summary_total != expected:
        raise RuntimeError(
            f"{label}: corrected_summary indica "
            f"total_reps={summary_total}, esperado={expected}."
        )

    if summary_valid != executable_count:
        raise RuntimeError(
            f"{label}: valid_ok calculado={executable_count}, "
            f"summary={summary_valid}."
        )

    def check_rounded(name, actual, reference):
        if actual is None or reference is None:
            return

        difference = abs(actual - reference)
        status = "OK" if difference <= 0.015 else "MISMATCH"

        print(
            f"[{label}] {name:<24} "
            f"actual={actual:9.4f} "
            f"summary={reference:9.4f} "
            f"diff={difference:8.4f} [{status}]"
        )

        if difference > 0.015:
            raise RuntimeError(
                f"{label}: validação falhou para {name}: "
                f"{actual} != {reference}"
            )

    check_rounded(
        "valid line mean",
        line_valid_mean,
        to_float(summary.get("line_mean_valid")),
    )

    check_rounded(
        "valid branch mean",
        branch_valid_mean,
        to_float(summary.get("branch_mean_valid")),
    )

    check_rounded(
        "valid mutation mean",
        mutation_valid_mean,
        to_float(summary.get("pit_mean_valid")),
    )

    # O summary do Randoop contém também as médias penalizadas.
    check_rounded(
        "penalised line mean",
        line_pen,
        to_float(summary.get("line_penalised_mean")),
    )

    check_rounded(
        "penalised branch mean",
        branch_pen,
        to_float(summary.get("branch_penalised_mean")),
    )

    check_rounded(
        "penalised mutation mean",
        mutation_pen,
        to_float(summary.get("pit_penalised_mean")),
    )

    print(
        f"[OK] {label:<10} "
        f"valid={executable_count}/{expected} "
        f"| line={line_pen:.2f}->{line_nonpen:.2f} "
        f"| branch={branch_pen:.2f}->{branch_nonpen:.2f} "
        f"| mutation={mutation_pen:.2f}"
        f"->{mutation_nonpen:.2f}"
    )

    print(
        f"[INFO] {label} status_counts="
        f"{status_counts}"
    )

    return normalised_row(
        label,
        "non_ai",
        expected,
        found,
        executable_count,
        line_pen,
        branch_pen,
        mutation_pen,
        line_nonpen,
        branch_nonpen,
        mutation_nonpen,
    )



def load_iaedu_gpt4o():
    """
    Lê diretamente as 200 repetições finais do GPT-4o.

    Política:
    - status == ok corresponde a suite executável;
    - média penalizada usa denominador fixo de 200;
    - falhas, métricas ausentes e runs não executáveis contam como zero;
    - média não penalizada exclui valores iguais a zero.
    """

    expected = 200

    status_files = sorted(
        path
        for path in GPT4O_ROOT.rglob("status.json")
        if path.parent.name == "metrics"
    )

    found = len(status_files)

    if found != expected:
        raise RuntimeError(
            f"GPT-4o: encontrados {found}/{expected} "
            f"metrics/status.json em {GPT4O_ROOT}."
        )

    def recursive_items(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                yield str(key).strip().lower(), value
                yield from recursive_items(value)

        elif isinstance(obj, list):
            for value in obj:
                yield from recursive_items(value)

    def extract_metric(data, candidate_names):
        candidate_names = {
            name.strip().lower()
            for name in candidate_names
        }

        # Primeiro, chaves diretas.
        if isinstance(data, dict):
            direct = {
                str(key).strip().lower(): value
                for key, value in data.items()
            }

            for name in candidate_names:
                if name in direct:
                    value = to_float(direct[name])

                    if value is not None:
                        return value

        # Depois, chaves dentro de objetos aninhados.
        for key, raw_value in recursive_items(data):
            if key not in candidate_names:
                continue

            value = to_float(raw_value)

            if value is not None:
                return value

        return None

    line_keys = {
        "line_coverage_pct",
        "line_pct",
        "line_coverage",
        "jacoco_line_pct",
        "line_coverage_percent",
    }

    branch_keys = {
        "branch_coverage_pct",
        "branch_pct",
        "branch_coverage",
        "jacoco_branch_pct",
        "branch_coverage_percent",
    }

    mutation_keys = {
        "mutation_score_pct",
        "mutation_pct",
        "mutation_score",
        "mutation_coverage_pct",
        "pit_score",
        "pit_score_pct",
        "pit_mutation_score_pct",
    }

    strict_line = []
    strict_branch = []
    strict_mutation = []

    positive_line = []
    positive_branch = []
    positive_mutation = []

    executable_count = 0
    status_counts = {}

    executable_missing_line = 0
    executable_missing_branch = 0
    executable_missing_mutation = 0

    for status_path in status_files:
        data = read_json(status_path)

        raw_status = (
            data.get("status")
            or data.get("final_status")
            or data.get("result")
            or ""
        )

        status = str(raw_status).strip().lower()

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

        executable = status == "ok"

        line = extract_metric(
            data,
            line_keys,
        )

        branch = extract_metric(
            data,
            branch_keys,
        )

        mutation = extract_metric(
            data,
            mutation_keys,
        )

        if executable:
            executable_count += 1

            if line is None:
                executable_missing_line += 1

            if branch is None:
                executable_missing_branch += 1

            if mutation is None:
                executable_missing_mutation += 1

            if line is not None and line > 0:
                positive_line.append(line)

            if branch is not None and branch > 0:
                positive_branch.append(branch)

            if mutation is not None and mutation > 0:
                positive_mutation.append(mutation)

        strict_line.append(
            line
            if executable and line is not None
            else 0.0
        )

        strict_branch.append(
            branch
            if executable and branch is not None
            else 0.0
        )

        strict_mutation.append(
            mutation
            if executable and mutation is not None
            else 0.0
        )

    if executable_count == 0:
        raise RuntimeError(
            "GPT-4o: nenhuma repetição com status=ok."
        )

    for metric_name, values in (
        ("line", positive_line),
        ("branch", positive_branch),
        ("mutation", positive_mutation),
    ):
        if not values:
            raise RuntimeError(
                f"GPT-4o: nenhuma métrica positiva para "
                f"{metric_name}."
            )

    line_pen = sum(strict_line) / expected
    branch_pen = sum(strict_branch) / expected
    mutation_pen = sum(strict_mutation) / expected

    line_nonpen = (
        sum(positive_line)
        / len(positive_line)
    )

    branch_nonpen = (
        sum(positive_branch)
        / len(positive_branch)
    )

    mutation_nonpen = (
        sum(positive_mutation)
        / len(positive_mutation)
    )

    print()
    print("===== GPT-4o REPETITION-LEVEL EXTRACTION =====")
    print(f"[OK] root={GPT4O_ROOT}")
    print(f"[OK] status files={found}/{expected}")
    print(
        f"[OK] executable={executable_count}/{expected} "
        f"({100.0 * executable_count / expected:.2f}%)"
    )
    print(f"[INFO] status_counts={status_counts}")
    print(
        "[INFO] missing metrics among executable runs: "
        f"line={executable_missing_line}, "
        f"branch={executable_missing_branch}, "
        f"mutation={executable_missing_mutation}"
    )
    print(
        f"[OK] line={line_pen:.6f}"
        f"->{line_nonpen:.6f}"
    )
    print(
        f"[OK] branch={branch_pen:.6f}"
        f"->{branch_nonpen:.6f}"
    )
    print(
        f"[OK] mutation={mutation_pen:.6f}"
        f"->{mutation_nonpen:.6f}"
    )

    # Validação opcional contra o dataset_summary.json.
    summary_path = GPT4O_ROOT / "dataset_summary.json"

    if summary_path.exists():
        summary = read_json(summary_path)

        def find_summary_value(candidate_names):
            candidate_names = {
                name.strip().lower()
                for name in candidate_names
            }

            for key, raw_value in recursive_items(summary):
                if key not in candidate_names:
                    continue

                value = to_float(raw_value)

                if value is not None:
                    return value

            return None

        summary_checks = [
            (
                "line",
                line_pen,
                find_summary_value({
                    "line_penalized_mean",
                    "mean_line_penalized",
                    "line_mean_penalized",
                    "line_coverage_mean_pct",
                }),
            ),
            (
                "branch",
                branch_pen,
                find_summary_value({
                    "branch_penalized_mean",
                    "mean_branch_penalized",
                    "branch_mean_penalized",
                    "branch_coverage_mean_pct",
                }),
            ),
            (
                "mutation",
                mutation_pen,
                find_summary_value({
                    "mutation_penalized_mean",
                    "mean_mutation_penalized",
                    "mutation_mean_penalized",
                    "mutation_score_mean_pct",
                }),
            ),
        ]

        for metric_name, actual, reference in summary_checks:
            if reference is None:
                print(
                    f"[INFO] GPT-4o summary não expõe "
                    f"{metric_name} com uma chave conhecida."
                )
                continue

            difference = abs(actual - reference)
            status_label = (
                "OK"
                if difference <= 0.02
                else "MISMATCH"
            )

            print(
                f"[GPT-4o] {metric_name:<8} "
                f"recomputed={actual:.6f} "
                f"summary={reference:.6f} "
                f"diff={difference:.6f} "
                f"[{status_label}]"
            )

            if difference > 0.02:
                raise RuntimeError(
                    f"GPT-4o: a média de {metric_name} "
                    f"não coincide com o summary."
                )

    return normalised_row(
        "GPT-4o",
        "iaedu",
        expected,
        found,
        executable_count,
        line_pen,
        branch_pen,
        mutation_pen,
        line_nonpen,
        branch_nonpen,
        mutation_nonpen,
    )



def load_gpt55():
    summary_csv = GPT55_ROOT / "approach_summary_for_graphs.csv"
    selected_tsv = GPT55_ROOT / "selected_runs.tsv"

    if not summary_csv.exists():
        raise RuntimeError(
            f"Não encontrei o summary do GPT-5.5: {summary_csv}"
        )

    if not selected_tsv.exists():
        raise RuntimeError(
            f"Não encontrei selected_runs.tsv do GPT-5.5: {selected_tsv}"
        )

    summary_rows = read_table(summary_csv)

    if len(summary_rows) != 1:
        raise RuntimeError(
            f"GPT-5.5: esperava uma linha no summary, "
            f"mas encontrei {len(summary_rows)}."
        )

    row = summary_rows[0]

    expected = (
        to_int(row_get(row, "expected_repetitions"))
        or 200
    )

    executable_count = (
        to_int(row_get(row, "valid_repetitions"))
        or 0
    )

    executable_pct_reported = to_float(
        row_get(row, "executable_suite_rate_pct")
    )

    line_pen = to_float(
        row_get(row, "line_coverage_mean_pct")
    )

    branch_pen = to_float(
        row_get(row, "branch_coverage_mean_pct")
    )

    mutation_pen = to_float(
        row_get(row, "mutation_score_mean_pct")
    )

    required = {
        "line_coverage_mean_pct": line_pen,
        "branch_coverage_mean_pct": branch_pen,
        "mutation_score_mean_pct": mutation_pen,
    }

    missing = [
        name
        for name, value in required.items()
        if value is None
    ]

    if missing:
        raise RuntimeError(
            "GPT-5.5: métricas em falta no summary: "
            + ", ".join(missing)
        )

    selected_rows = read_table(selected_tsv)

    if len(selected_rows) != expected:
        raise RuntimeError(
            f"GPT-5.5: selected_runs tem "
            f"{len(selected_rows)}/{expected} linhas."
        )

    line_values = [
        to_float(row_get(r, "line"))
        for r in selected_rows
    ]

    branch_values = [
        to_float(row_get(r, "branch"))
        for r in selected_rows
    ]

    mutation_values = [
        to_float(row_get(r, "mutation"))
        for r in selected_rows
    ]

    if any(v is None for v in line_values):
        raise RuntimeError("GPT-5.5: existem valores line em falta.")

    if any(v is None for v in branch_values):
        raise RuntimeError("GPT-5.5: existem valores branch em falta.")

    if any(v is None for v in mutation_values):
        raise RuntimeError("GPT-5.5: existem valores mutation em falta.")

    line_check = sum(line_values) / expected
    branch_check = sum(branch_values) / expected
    mutation_check = sum(mutation_values) / expected

    for name, actual, reference in (
        ("line", line_check, line_pen),
        ("branch", branch_check, branch_pen),
        ("mutation", mutation_check, mutation_pen),
    ):
        diff = abs(actual - reference)

        status = "OK" if diff <= 0.001 else "MISMATCH"

        print(
            f"[GPT-5.5] {name:<8} "
            f"selected={actual:.6f} "
            f"summary={reference:.6f} "
            f"diff={diff:.6f} [{status}]"
        )

        if diff > 0.001:
            raise RuntimeError(
                f"GPT-5.5: {name} não coincide com o summary."
            )

    line_nonpen = positive_mean(line_values)
    branch_nonpen = positive_mean(branch_values)
    mutation_nonpen = positive_mean(mutation_values)

    executable_pct_calculated = (
        100.0 * executable_count / expected
    )

    if (
        executable_pct_reported is not None
        and abs(
            executable_pct_calculated
            - executable_pct_reported
        ) > 0.001
    ):
        raise RuntimeError(
            "GPT-5.5: executable-suite rate não coincide."
        )

    return normalised_row(
        "GPT-5.5",
        "iaedu",
        expected,
        len(selected_rows),
        executable_count,
        line_pen,
        branch_pen,
        mutation_pen,
        line_nonpen,
        branch_nonpen,
        mutation_nonpen,
    )



def cluster_model_label(raw_name):
    mapping = {
        "cluster-max-codellama-7b-instruct-ctx16k":
            "CodeLlama",

        "cluster-safe-codestral-22b-ctx16k":
            "Codestral",

        "cluster-safe-deepseek-coder-v2-16b-ctx16k":
            "DeepSeek-Coder-V2",

        "cluster-safe-deepseek-v2-16b-ctx32k":
            "DeepSeek-V2",

        "cluster-safe-qwen2.5-coder-14b-ctx32k":
            "Qwen2.5-Coder",

        "cluster-safe-qwen3-coder-30b-official-ctx32k":
            "Qwen3-Coder",

        "cluster-safe-qwen3.5-9b-ctx32k":
            "Qwen3.5",
    }

    return mapping.get(str(raw_name).strip())


def positive_mean(values):
    positive = [
        value
        for value in values
        if value is not None and value > 0
    ]

    if not positive:
        return 0.0

    return sum(positive) / len(positive)


def strict_mean(values, expected):
    clean = [
        0.0 if value is None else float(value)
        for value in values
    ]

    if len(clean) > expected:
        raise RuntimeError(
            f"Recebi {len(clean)} valores para apenas "
            f"{expected} repetições esperadas."
        )

    if len(clean) < expected:
        clean.extend([0.0] * (expected - len(clean)))

    return sum(clean) / expected


def load_cluster_rows():
    runs_path = (
        CLUSTER_PIT_ROOT
        / "_summary"
        / "dataset_runs_with_pit.tsv"
    )

    coverage_summary_path = (
        CLUSTER_COVERAGE_ROOT
        / "_summary"
        / "per_model_summary.tsv"
    )

    mutation_summary_path = (
        CLUSTER_PIT_ROOT
        / "_summary"
        / "per_model_pit_summary.tsv"
    )

    for required in (
        runs_path,
        coverage_summary_path,
        mutation_summary_path,
    ):
        if not required.exists():
            raise RuntimeError(
                f"Ficheiro obrigatório do cluster em falta: "
                f"{required}"
            )

    run_rows = read_table(runs_path)

    if len(run_rows) != 1400:
        raise RuntimeError(
            f"Cluster: eram esperadas 1400 linhas, "
            f"mas foram encontradas {len(run_rows)}."
        )

    grouped = {}

    for row in run_rows:
        raw_model = row_get(row, "model")
        label = cluster_model_label(raw_model)

        if label is None:
            raise RuntimeError(
                f"Modelo cluster desconhecido: {raw_model!r}"
            )

        grouped.setdefault(label, []).append(row)

    coverage_reference = {}

    for row in read_table(coverage_summary_path):
        label = cluster_model_label(
            row_get(row, "model")
        )

        if label is not None:
            coverage_reference[label] = {
                "requested": to_int(
                    row_get(row, "requested_runs")
                ),
                "valid": to_int(
                    row_get(row, "valid_runs")
                ),
                "line_pen": to_float(
                    row_get(row, "strict_mean_line_pct")
                ),
                "branch_pen": to_float(
                    row_get(row, "strict_mean_branch_pct")
                ),
            }

    mutation_reference = {}

    for row in read_table(mutation_summary_path):
        label = cluster_model_label(
            row_get(row, "model")
        )

        if label is not None:
            mutation_reference[label] = {
                "requested": to_int(
                    row_get(row, "requested_runs")
                ),
                "metric_runs": to_int(
                    row_get(row, "mutation_metric_runs")
                ),
                "mutation_pen": to_float(
                    row_get(
                        row,
                        "strict_mean_mutation_pct",
                    )
                ),
            }

    cluster_order = [
        "CodeLlama",
        "Codestral",
        "DeepSeek-Coder-V2",
        "DeepSeek-V2",
        "Qwen2.5-Coder",
        "Qwen3-Coder",
        "Qwen3.5",
    ]

    output = []

    print()
    print("===== CLUSTER EXACT EXTRACTION =====")
    print(f"[INPUT] {runs_path}")

    for label in cluster_order:
        model_rows = grouped.get(label, [])
        expected = 200
        found = len(model_rows)

        if found != expected:
            raise RuntimeError(
                f"{label}: encontradas {found}/"
                f"{expected} repetições."
            )

        executable_count = sum(
            1
            for row in model_rows
            if to_bool(
                row_get(row, "effective_valid")
            ) is True
        )

        line_values = [
            to_float(
                row_get(
                    row,
                    "effective_line_coverage_pct",
                )
            )
            for row in model_rows
        ]

        branch_values = [
            to_float(
                row_get(
                    row,
                    "effective_branch_coverage_pct",
                )
            )
            for row in model_rows
        ]

        mutation_values = [
            to_float(
                row_get(
                    row,
                    "mutation_score_strict_pct",
                )
            )
            for row in model_rows
        ]

        # Penalizada:
        # todas as 200 repetições entram no denominador.
        # Missing/failure/unavailable contam como zero.
        line_pen = strict_mean(
            line_values,
            expected,
        )

        branch_pen = strict_mean(
            branch_values,
            expected,
        )

        mutation_pen = strict_mean(
            mutation_values,
            expected,
        )

        # Não penalizada:
        # remover especificamente métricas iguais a zero,
        # conforme a política usada nos restantes gráficos.
        line_nonpen = positive_mean(
            line_values
        )

        branch_nonpen = positive_mean(
            branch_values
        )

        mutation_nonpen = positive_mean(
            mutation_values
        )

        cov_ref = coverage_reference.get(
            label,
            {},
        )

        mut_ref = mutation_reference.get(
            label,
            {},
        )

        def check_close(name, actual, expected_value):
            if expected_value is None:
                return

            diff = abs(actual - expected_value)

            status = (
                "OK"
                if diff <= 0.0002
                else "MISMATCH"
            )

            print(
                f"  {label:<20} {name:<10} "
                f"actual={actual:10.6f} "
                f"reference={expected_value:10.6f} "
                f"diff={diff:10.6f} "
                f"[{status}]"
            )

            if diff > 0.0002:
                raise RuntimeError(
                    f"{label}: validação falhou para "
                    f"{name}: actual={actual}, "
                    f"reference={expected_value}"
                )

        if cov_ref.get("valid") is not None:
            if executable_count != cov_ref["valid"]:
                raise RuntimeError(
                    f"{label}: executable_count="
                    f"{executable_count}, mas o summary "
                    f"indica {cov_ref['valid']}."
                )

        check_close(
            "line",
            line_pen,
            cov_ref.get("line_pen"),
        )

        check_close(
            "branch",
            branch_pen,
            cov_ref.get("branch_pen"),
        )

        check_close(
            "mutation",
            mutation_pen,
            mut_ref.get("mutation_pen"),
        )

        output.append(
            normalised_row(
                label,
                "cluster",
                expected,
                found,
                executable_count,
                line_pen,
                branch_pen,
                mutation_pen,
                line_nonpen,
                branch_nonpen,
                mutation_nonpen,
            )
        )

        print(
            f"[OK] {label:<20} "
            f"exec={executable_count:3d}/200 "
            f"| line={line_pen:6.2f}"
            f"->{line_nonpen:6.2f} "
            f"| branch={branch_pen:6.2f}"
            f"->{branch_nonpen:6.2f} "
            f"| mutation={mutation_pen:6.2f}"
            f"->{mutation_nonpen:6.2f}"
        )

    if len(output) != 7:
        raise RuntimeError(
            f"Eram esperados sete modelos cluster, "
            f"mas foram produzidos {len(output)}."
        )

    return output




# ============================================================
# BUILD DATASET
# ============================================================

rows = []
rows.append(load_official())
rows.append(load_corrected_nonai(EVOSUITE_ROOT, "EvoSuite"))
rows.append(load_corrected_nonai(RANDOOP_ROOT, "Randoop"))
rows.append(load_iaedu_gpt4o())
rows.append(load_gpt55())
rows.extend(load_cluster_rows())

# remover duplicados por label, preservando a primeira ocorrência
dedup = {}
for row in rows:
    if row["approach"] not in dedup:
        dedup[row["approach"]] = row
rows = [dedup[name] for name in ORDER if name in dedup]


# validação obrigatória antes de escrever CSVs ou gráficos
required_numeric_fields = [
    "executable_pct",
    "line_penalized",
    "branch_penalized",
    "mutation_penalized",
    "line_nonpenalized",
    "branch_nonpenalized",
    "mutation_nonpenalized",
]

if len(rows) != 12:
    raise RuntimeError(
        f"Eram esperadas 12 abordagens no gráfico, "
        f"mas foram produzidas {len(rows)}: "
        f"{[row['approach'] for row in rows]}"
    )

for row in rows:
    missing_fields = [
        field
        for field in required_numeric_fields
        if row.get(field) is None
    ]

    if missing_fields:
        raise RuntimeError(
            f"{row['approach']}: métricas None encontradas: "
            + ", ".join(missing_fields)
        )

print()
print("===== ALL APPROACHES COMPLETE =====")

for row in rows:
    print(
        f"[OK] {row['approach']:<20} "
        f"exec={row['executable_pct']:6.2f} "
        f"line={row['line_penalized']:6.2f}"
        f"->{row['line_nonpenalized']:6.2f} "
        f"branch={row['branch_penalized']:6.2f}"
        f"->{row['branch_nonpenalized']:6.2f} "
        f"mutation={row['mutation_penalized']:6.2f}"
        f"->{row['mutation_nonpenalized']:6.2f}"
    )


# validação mínima
for row in rows:
    exp = EXPECTED.get(row["approach"])
    if exp is not None and row["expected"] != exp:
        print(f"[WARN] {row['approach']}: expected={row['expected']} (era esperado {exp})")

# ============================================================
# WRITE SUMMARY CSV
# ============================================================

fieldnames = [
    "approach",
    "category",
    "expected",
    "found",
    "executable_count",
    "executable_pct",
    "line_penalized",
    "branch_penalized",
    "mutation_penalized",
    "line_nonpenalized",
    "branch_nonpenalized",
    "mutation_nonpenalized",
]

with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

with RADAR_CSV.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=["approach", "executable_pct", "line_penalized", "branch_penalized", "mutation_penalized"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "approach": row["approach"],
                "executable_pct": row["executable_pct"],
                "line_penalized": row["line_penalized"],
                "branch_penalized": row["branch_penalized"],
                "mutation_penalized": row["mutation_penalized"],
            }
        )

with STACKED_CSV.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(
        fh,
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
    for row in rows:
        writer.writerow(
            {
                "approach": row["approach"],
                "line_penalized": row["line_penalized"],
                "line_nonpenalized": row["line_nonpenalized"],
                "branch_penalized": row["branch_penalized"],
                "branch_nonpenalized": row["branch_nonpenalized"],
                "mutation_penalized": row["mutation_penalized"],
                "mutation_nonpenalized": row["mutation_nonpenalized"],
            }
        )

# ============================================================
# RADAR CHART
# ============================================================

labels = [r["approach"] for r in rows]
N = len(labels)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]

rad_exec = [r["executable_pct"] for r in rows] + [rows[0]["executable_pct"]]
rad_line = [r["line_penalized"] for r in rows] + [rows[0]["line_penalized"]]
rad_branch = [r["branch_penalized"] for r in rows] + [rows[0]["branch_penalized"]]
rad_mut = [r["mutation_penalized"] for r in rows] + [rows[0]["mutation_penalized"]]

fig = plt.figure(figsize=(10, 10))
ax = plt.subplot(111, polar=True)
ax.set_theta_offset(0)
ax.set_theta_direction(1)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels, fontsize=12)
ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=10)

ax.plot(angles, rad_exec, linewidth=2, label="Executable suites")
ax.fill(angles, rad_exec, alpha=0.12)

ax.plot(angles, rad_line, linewidth=2, label="Line coverage")
ax.plot(angles, rad_branch, linewidth=2, label="Branch coverage")
ax.plot(angles, rad_mut, linewidth=2, label="Mutation score")

ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.10), ncol=4, fontsize=11, frameon=True)

plt.tight_layout()
fig.savefig(RADAR_OUT, dpi=220, bbox_inches="tight")
plt.close(fig)

# ============================================================
# STACKED BAR CHART
# ============================================================

x = np.arange(len(rows))
width = 0.22

line_pen = np.array([r["line_penalized"] for r in rows], dtype=float)
line_non = np.array([r["line_nonpenalized"] for r in rows], dtype=float)
branch_pen = np.array([r["branch_penalized"] for r in rows], dtype=float)
branch_non = np.array([r["branch_nonpenalized"] for r in rows], dtype=float)
mut_pen = np.array([r["mutation_penalized"] for r in rows], dtype=float)
mut_non = np.array([r["mutation_nonpenalized"] for r in rows], dtype=float)

line_uplift = np.maximum(line_non - line_pen, 0.0)
branch_uplift = np.maximum(branch_non - branch_pen, 0.0)
mut_uplift = np.maximum(mut_non - mut_pen, 0.0)

fig = plt.figure(figsize=(16, 7))
ax = plt.gca()

# cores iguais às dos outros
ax.bar(x - width, line_pen, width, label="Line coverage")
ax.bar(x, branch_pen, width, label="Branch coverage")
ax.bar(x + width, mut_pen, width, label="Mutation score")

# topo tracejado = uplift
ax.bar(x - width, line_uplift, width, bottom=line_pen, hatch="///", alpha=0.25, edgecolor="C0")
ax.bar(x, branch_uplift, width, bottom=branch_pen, hatch="///", alpha=0.25, edgecolor="C1")
ax.bar(x + width, mut_uplift, width, bottom=mut_pen, hatch="///", alpha=0.25, edgecolor="C2")

ax.set_ylabel("%", fontsize=13)
ax.set_ylim(0, 100)
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=32, ha="right", fontsize=11)
ax.tick_params(axis="y", labelsize=11)
ax.grid(axis="y", alpha=0.25)

legend_handles = [
    Patch(facecolor="C0", label="Line coverage"),
    Patch(facecolor="C1", label="Branch coverage"),
    Patch(facecolor="C2", label="Mutation score"),
    Patch(facecolor="lightgray", edgecolor="gray", label="Penalised mean"),
    Patch(facecolor="white", edgecolor="black", hatch="///", label="Additional uplift to non-penalised mean"),
]
ax.legend(
    handles=legend_handles,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.38),
    ncol=3,
    frameon=True,
    fontsize=11,
)

plt.subplots_adjust(bottom=0.30, left=0.06, right=0.99, top=0.98)
fig.savefig(STACKED_OUT, dpi=220, bbox_inches="tight")
plt.close(fig)

# ============================================================
# PRINT SUMMARY
# ============================================================

print("===== QUIXBUGS JAVA FINAL SUMMARY =====")
for row in rows:
    print(
        f"{row['approach']:<18} | exec={row['executable_pct']:6.2f} "
        f"| line={row['line_penalized']:6.2f}->{row['line_nonpenalized']:6.2f} "
        f"| branch={row['branch_penalized']:6.2f}->{row['branch_nonpenalized']:6.2f} "
        f"| mutation={row['mutation_penalized']:6.2f}->{row['mutation_nonpenalized']:6.2f}"
    )

print()
print("===== OUTPUTS =====")
print(f"[SUMMARY CSV] {SUMMARY_CSV}")
print(f"[RADAR CSV]   {RADAR_CSV}")
print(f"[STACKED CSV] {STACKED_CSV}")
print(f"[RADAR FIG]   {RADAR_OUT}")
print(f"[STACKED FIG] {STACKED_OUT}")
