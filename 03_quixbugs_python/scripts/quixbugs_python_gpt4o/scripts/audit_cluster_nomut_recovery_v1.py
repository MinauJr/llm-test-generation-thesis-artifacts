#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import collections
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(
            path.read_text(encoding="utf-8", errors="replace")
        )
    except Exception:
        return {}


def read_text(path: Path, limit: int | None = None) -> str:
    if not path.is_file():
        return ""

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if limit is not None:
        return text[-limit:]

    return text


def file_bytes(path: Path) -> int:
    try:
        return path.stat().st_size
    except Exception:
        return 0


def nonempty(path: Path) -> bool:
    return bool(read_text(path).strip())


def as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""

    h = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def recursive_strings(value: Any):
    if isinstance(value, str):
        yield value

    elif isinstance(value, dict):
        for child in value.values():
            yield from recursive_strings(child)

    elif isinstance(value, list):
        for child in value:
            yield from recursive_strings(child)


def json_code_candidate(path: Path) -> tuple[int, int]:
    data = read_json(path)

    candidates = []

    for value in recursive_strings(data):
        if (
            "def test_" in value
            or "import pytest" in value
            or "from pytest" in value
            or re.search(r"(^|\n)\s*assert\s+", value)
        ):
            candidates.append(value)

    return len(candidates), sum(len(x) for x in candidates)


def analyse_python(path: Path) -> dict[str, Any]:
    result = {
        "syntax_ok": False,
        "syntax_error": "",
        "test_functions": 0,
        "test_methods": 0,
        "all_functions": 0,
        "module_asserts": 0,
        "module_calls": 0,
        "imports": [],
        "uses_sut_name": False,
        "imports_sut": False,
        "imports_quixbugs_alias": False,
    }

    text = read_text(path)

    if not text.strip():
        return result

    try:
        tree = ast.parse(text)
        result["syntax_ok"] = True
    except Exception as exc:
        result["syntax_error"] = (
            f"{type(exc).__name__}: {exc}"
        )
        return result

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)

                if alias.name == "sut":
                    result["imports_sut"] = True

                if alias.name == "quixbugs_python_sut":
                    result["imports_quixbugs_alias"] = True

        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")

            if node.module == "sut":
                result["imports_sut"] = True

            if node.module == "quixbugs_python_sut":
                result["imports_quixbugs_alias"] = True

        elif isinstance(node, ast.Name):
            if node.id == "sut":
                result["uses_sut_name"] = True

        elif isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            result["all_functions"] += 1

            if node.name.startswith("test_"):
                result["test_functions"] += 1

    for node in tree.body:
        if isinstance(node, ast.Assert):
            result["module_asserts"] += 1

        elif isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Call):
                result["module_calls"] += 1

        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ) and child.name.startswith("test_"):
                    result["test_methods"] += 1

    result["imports"] = sorted(imports)

    return result


def classify_log(text: str) -> str:
    checks = [
        (
            "module_not_found",
            r"ModuleNotFoundError|No module named",
        ),
        (
            "import_error",
            r"ImportError|cannot import name",
        ),
        (
            "name_error",
            r"NameError:",
        ),
        (
            "fixture_error",
            r"fixture .* not found",
        ),
        (
            "collection_error",
            r"ERROR collecting|errors? during collection",
        ),
        (
            "pytest_timeout",
            r"timeout|Timed out|Alarm clock",
        ),
        (
            "recursion_error",
            r"RecursionError",
        ),
        (
            "type_error",
            r"TypeError:",
        ),
        (
            "attribute_error",
            r"AttributeError:",
        ),
        (
            "value_error",
            r"ValueError:",
        ),
        (
            "assertion_fail",
            r"AssertionError|FAILED ",
        ),
        (
            "no_tests",
            r"no tests ran|collected 0 items",
        ),
    ]

    for label, pattern in checks:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return label

    return "unclassified"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-root", required=True)
    parser.add_argument("--cluster-root", required=True)
    parser.add_argument("--sut-root", required=True)
    parser.add_argument("--models-file", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    full_root = Path(args.full_root).resolve()
    cluster_root = Path(args.cluster_root).resolve()
    sut_root = Path(args.sut_root).resolve()
    models_file = Path(args.models_file).resolve()
    out_dir = Path(args.out_dir).resolve()

    out_dir.mkdir(parents=True, exist_ok=True)

    models = [
        line.strip()
        for line in models_file.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    suts = sorted(
        path.name
        for path in sut_root.glob(
            "[0-9][0-9][0-9]_python_*"
        )
        if path.is_dir()
    )

    rows = []
    category_counts = collections.Counter()
    evaluator_reason_counts = collections.Counter()
    model_category_counts = collections.Counter()

    for model in models:
        for sut in suts:
            for rep in range(1, 6):
                eval_run = (
                    full_root
                    / model
                    / sut
                    / "run_0001"
                    / f"1-{rep}"
                )

                source_run = (
                    cluster_root
                    / model
                    / sut
                    / f"rep_{rep:02d}"
                )

                status_path = (
                    eval_run
                    / "metrics"
                    / "status.json"
                )

                source_status_path = (
                    source_run
                    / "status.json"
                )

                eval_status = read_json(status_path)
                source_status = read_json(
                    source_status_path
                )

                status = eval_status.get(
                    "status",
                    "missing_status",
                )

                source_state = source_status.get(
                    "status",
                    "missing_source_status",
                )

                line = as_float(
                    eval_status.get(
                        "line_coverage_pct"
                    )
                )

                branch = as_float(
                    eval_status.get(
                        "branch_coverage_pct"
                    )
                )

                generated = (
                    source_run
                    / "generated_tests.py"
                )

                response_raw_candidates = [
                    source_run / "response_raw.txt",
                    source_run / "raw_response.txt",
                ]

                response_raw = next(
                    (
                        path
                        for path in response_raw_candidates
                        if path.is_file()
                    ),
                    response_raw_candidates[0],
                )

                response_api_candidates = [
                    source_run / "response_api.json",
                    source_run / "api_response.json",
                ]

                response_api = next(
                    (
                        path
                        for path in response_api_candidates
                        if path.is_file()
                    ),
                    response_api_candidates[0],
                )

                nodeid_json = (
                    eval_run
                    / "metrics"
                    / "nodeid_sanitization.json"
                )

                nodeid_data = read_json(
                    nodeid_json
                )

                coverage_metrics_path = (
                    eval_run
                    / "metrics"
                    / "coverage_metrics.json"
                )

                coverage_metrics = read_json(
                    coverage_metrics_path
                )

                raw_log = (
                    eval_run
                    / "logs"
                    / "pytest_raw.log"
                )

                sanitizer_log = (
                    eval_run
                    / "logs"
                    / "nodeid_sanitizer.stdout.log"
                )

                collect_log = (
                    eval_run
                    / "logs"
                    / "nodeid_sanitizer.collect.log"
                )

                coverage_log = (
                    eval_run
                    / "logs"
                    / "coverage.log"
                )

                combined_log_text = "\n".join([
                    read_text(raw_log, 8000),
                    read_text(sanitizer_log, 8000),
                    read_text(collect_log, 8000),
                    read_text(coverage_log, 8000),
                ])

                log_reason = classify_log(
                    combined_log_text
                )

                ast_info = analyse_python(
                    generated
                )

                api_code_count, api_code_chars = (
                    json_code_candidate(
                        response_api
                    )
                )

                raw_text = read_text(
                    response_raw
                )

                raw_has_code = bool(
                    "def test_" in raw_text
                    or "import pytest" in raw_text
                    or re.search(
                        r"(^|\n)\s*assert\s+",
                        raw_text,
                    )
                )

                category = status
                evaluator_reason = ""

                if status == "ok":
                    if line is None or branch is None:
                        category = "ok_missing_metric"

                        cm_line = as_float(
                            coverage_metrics.get(
                                "line_coverage_pct"
                            )
                        )

                        cm_branch = as_float(
                            coverage_metrics.get(
                                "branch_coverage_pct"
                            )
                        )

                        if (
                            cm_line is not None
                            or cm_branch is not None
                        ):
                            evaluator_reason = (
                                "metrics_exist_but_status_missing"
                            )
                        else:
                            evaluator_reason = (
                                "ok_without_usable_metrics"
                            )

                    else:
                        category = "ok_complete"
                        evaluator_reason = "none"

                elif status == "coverage_fail":
                    if coverage_metrics:
                        evaluator_reason = (
                            "coverage_metrics_exist_despite_fail"
                        )

                    elif (
                        eval_run
                        / "runner"
                        / "coverage.xml"
                    ).is_file():
                        evaluator_reason = (
                            "coverage_xml_exists_despite_fail"
                        )

                    else:
                        evaluator_reason = log_reason

                elif status == "generation_failed":
                    if nonempty(generated):
                        evaluator_reason = (
                            "generated_tests_nonempty_gate_bug"
                        )

                    elif raw_has_code:
                        evaluator_reason = (
                            "raw_response_contains_test_code"
                        )

                    elif api_code_count > 0:
                        evaluator_reason = (
                            "api_json_contains_test_code"
                        )

                    else:
                        evaluator_reason = (
                            "no_test_content_found"
                        )

                elif status == (
                    "no_effective_tests_after_sanitization"
                ):
                    collected = int(
                        nodeid_data.get(
                            "collected_nodeids",
                            0,
                        )
                        or 0
                    )

                    passed = int(
                        nodeid_data.get(
                            "individual_pass_nodeids",
                            0,
                        )
                        or 0
                    )

                    timed_out = int(
                        nodeid_data.get(
                            "individual_timeout_nodeids",
                            0,
                        )
                        or 0
                    )

                    if not nodeid_data:
                        evaluator_reason = (
                            "missing_nodeid_metadata"
                        )

                    elif collected == 0:
                        if log_reason in {
                            "module_not_found",
                            "import_error",
                            "name_error",
                            "fixture_error",
                            "collection_error",
                        }:
                            evaluator_reason = (
                                "collection_or_harness_problem_"
                                + log_reason
                            )
                        else:
                            evaluator_reason = (
                                "zero_collected_nodeids"
                            )

                    elif passed == 0 and timed_out > 0:
                        evaluator_reason = (
                            "all_nodeids_fail_or_timeout"
                        )

                    elif passed == 0:
                        if log_reason in {
                            "module_not_found",
                            "import_error",
                            "name_error",
                            "fixture_error",
                            "collection_error",
                        }:
                            evaluator_reason = (
                                "harness_problem_"
                                + log_reason
                            )
                        else:
                            evaluator_reason = (
                                "all_nodeids_fail"
                            )

                    else:
                        evaluator_reason = (
                            "passing_nodeids_lost_or_unstable"
                        )

                elif status == "pytest_no_tests_raw":
                    if (
                        ast_info["test_functions"]
                        or ast_info["test_methods"]
                    ):
                        evaluator_reason = (
                            "ast_tests_exist_but_pytest_collected_zero"
                        )

                    elif (
                        ast_info["module_asserts"]
                        or ast_info["module_calls"]
                    ):
                        evaluator_reason = (
                            "module_level_test_like_code"
                        )

                    else:
                        evaluator_reason = (
                            "no_pytest_test_structure"
                        )

                else:
                    evaluator_reason = log_reason

                category_counts[category] += 1
                evaluator_reason_counts[
                    evaluator_reason
                ] += 1

                model_category_counts[
                    (model, category)
                ] += 1

                rows.append({
                    "model": model,
                    "sut_name": sut,
                    "repeat": rep,
                    "source_status": source_state,
                    "eval_status": status,
                    "audit_category": category,
                    "evaluator_reason": evaluator_reason,
                    "line_coverage_pct": (
                        "" if line is None else line
                    ),
                    "branch_coverage_pct": (
                        "" if branch is None else branch
                    ),
                    "status_line_metric": eval_status.get(
                        "line_coverage_pct"
                    ),
                    "status_branch_metric": eval_status.get(
                        "branch_coverage_pct"
                    ),
                    "coverage_json_line": coverage_metrics.get(
                        "line_coverage_pct",
                        "",
                    ),
                    "coverage_json_branch": coverage_metrics.get(
                        "branch_coverage_pct",
                        "",
                    ),
                    "generated_bytes": file_bytes(
                        generated
                    ),
                    "generated_nonempty": nonempty(
                        generated
                    ),
                    "generated_sha256": sha256_file(
                        generated
                    ),
                    "raw_response_bytes": file_bytes(
                        response_raw
                    ),
                    "raw_response_nonempty": nonempty(
                        response_raw
                    ),
                    "raw_response_has_test_code": raw_has_code,
                    "api_response_bytes": file_bytes(
                        response_api
                    ),
                    "api_code_candidate_count": api_code_count,
                    "api_code_candidate_chars": api_code_chars,
                    "python_syntax_ok": ast_info[
                        "syntax_ok"
                    ],
                    "python_syntax_error": ast_info[
                        "syntax_error"
                    ],
                    "ast_test_functions": ast_info[
                        "test_functions"
                    ],
                    "ast_test_methods": ast_info[
                        "test_methods"
                    ],
                    "ast_module_asserts": ast_info[
                        "module_asserts"
                    ],
                    "ast_module_calls": ast_info[
                        "module_calls"
                    ],
                    "imports_json": json.dumps(
                        ast_info["imports"]
                    ),
                    "uses_sut_name": ast_info[
                        "uses_sut_name"
                    ],
                    "imports_sut": ast_info[
                        "imports_sut"
                    ],
                    "imports_quixbugs_alias": ast_info[
                        "imports_quixbugs_alias"
                    ],
                    "nodeids_collected": nodeid_data.get(
                        "collected_nodeids",
                        "",
                    ),
                    "nodeids_pass": nodeid_data.get(
                        "individual_pass_nodeids",
                        "",
                    ),
                    "nodeids_fail": nodeid_data.get(
                        "individual_fail_nodeids",
                        "",
                    ),
                    "nodeids_timeout": nodeid_data.get(
                        "individual_timeout_nodeids",
                        "",
                    ),
                    "nodeids_final": nodeid_data.get(
                        "final_effective_nodeids",
                        "",
                    ),
                    "log_reason": log_reason,
                    "status_note": eval_status.get(
                        "note",
                        "",
                    ),
                    "eval_run": str(eval_run),
                    "source_run": str(source_run),
                    "status_json": str(status_path),
                    "source_status_json": str(
                        source_status_path
                    ),
                    "generated_tests": str(generated),
                    "raw_response": str(response_raw),
                    "response_api": str(response_api),
                    "raw_log": str(raw_log),
                    "collect_log": str(collect_log),
                    "coverage_log": str(coverage_log),
                })

    fields = list(rows[0].keys())

    with (
        out_dir / "all_runs_audit.tsv"
    ).open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)

    candidates = [
        row
        for row in rows
        if row["audit_category"] != "ok_complete"
    ]

    with (
        out_dir / "recovery_candidates.tsv"
    ).open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(candidates)

    with (
        out_dir / "category_counts.tsv"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write("category\tcount\n")

        for key, value in sorted(
            category_counts.items()
        ):
            handle.write(f"{key}\t{value}\n")

    with (
        out_dir / "evaluator_reason_counts.tsv"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write("reason\tcount\n")

        for key, value in sorted(
            evaluator_reason_counts.items()
        ):
            handle.write(f"{key}\t{value}\n")

    with (
        out_dir / "model_category_counts.tsv"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write("model\tcategory\tcount\n")

        for (
            model,
            category,
        ), value in sorted(
            model_category_counts.items()
        ):
            handle.write(
                f"{model}\t{category}\t{value}\n"
            )

    priority_reasons = {
        "metrics_exist_but_status_missing",
        "ok_without_usable_metrics",
        "coverage_metrics_exist_despite_fail",
        "coverage_xml_exists_despite_fail",
        "generated_tests_nonempty_gate_bug",
        "raw_response_contains_test_code",
        "api_json_contains_test_code",
        "missing_nodeid_metadata",
        "passing_nodeids_lost_or_unstable",
        "ast_tests_exist_but_pytest_collected_zero",
        "module_level_test_like_code",
    }

    high_priority = [
        row
        for row in rows
        if row["evaluator_reason"]
        in priority_reasons
        or "harness_problem" in row[
            "evaluator_reason"
        ]
        or "collection_or_harness_problem" in row[
            "evaluator_reason"
        ]
    ]

    with (
        out_dir / "high_priority_recovery.tsv"
    ).open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(high_priority)

    with (
        out_dir / "summary.txt"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            f"total_runs={len(rows)}\n"
        )
        handle.write(
            f"ok_complete={category_counts['ok_complete']}\n"
        )
        handle.write(
            f"recovery_candidates={len(candidates)}\n"
        )
        handle.write(
            f"high_priority_recovery={len(high_priority)}\n"
        )
        handle.write(
            "category_counts="
            + json.dumps(
                dict(
                    sorted(
                        category_counts.items()
                    )
                )
            )
            + "\n"
        )
        handle.write(
            "evaluator_reason_counts="
            + json.dumps(
                dict(
                    sorted(
                        evaluator_reason_counts.items()
                    )
                )
            )
            + "\n"
        )

    print(out_dir / "summary.txt")


if __name__ == "__main__":
    main()
