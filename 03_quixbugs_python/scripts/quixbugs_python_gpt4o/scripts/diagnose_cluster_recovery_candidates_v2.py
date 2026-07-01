#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import collections
import csv
import json
import re
from pathlib import Path
from typing import Any


NAME_ERROR_RE = re.compile(
    r"NameError:\s+name\s+['\"]([^'\"]+)['\"]\s+is not defined"
)

UNBOUND_RE = re.compile(
    r"UnboundLocalError:\s+.*?['\"]([^'\"]+)['\"]"
)

IMPORT_ERROR_RE = re.compile(
    r"ImportError:\s+cannot import name\s+['\"]([^'\"]+)['\"]"
    r"\s+from\s+['\"]([^'\"]+)['\"]"
)

MODULE_NOT_FOUND_RE = re.compile(
    r"ModuleNotFoundError:\s+No module named\s+['\"]([^'\"]+)['\"]"
)

FIXTURE_RE = re.compile(
    r"fixture\s+['\"]([^'\"]+)['\"]\s+not found",
    flags=re.IGNORECASE,
)

ATTRIBUTE_RE = re.compile(
    r"AttributeError:\s+(.*)"
)

COLLECTION_RE = re.compile(
    r"(ERROR collecting|errors? during collection)",
    flags=re.IGNORECASE,
)


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(read_text(path))
    except Exception:
        return {}


def top_level_symbols(path: Path) -> list[str]:
    text = read_text(path)

    if not text.strip():
        return []

    try:
        tree = ast.parse(text)
    except Exception:
        return []

    symbols = set()

    for node in tree.body:
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            symbols.add(node.name)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols.add(target.id)

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                symbols.add(node.target.id)

    return sorted(symbols)


def test_defined_names(path: Path) -> list[str]:
    text = read_text(path)

    if not text.strip():
        return []

    try:
        tree = ast.parse(text)
    except Exception:
        return []

    names = set()

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            names.add(node.name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)

        elif isinstance(node, ast.arg):
            names.add(node.arg)

        elif isinstance(node, ast.Name):
            if isinstance(
                node.ctx,
                (
                    ast.Store,
                    ast.Param,
                ),
            ):
                names.add(node.id)

    return sorted(names)


def extract_matches(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {
        "name_errors": [],
        "unbound_names": [],
        "import_errors": [],
        "missing_modules": [],
        "fixture_errors": [],
        "attribute_errors": [],
    }

    result["name_errors"] = sorted(
        set(NAME_ERROR_RE.findall(text))
    )

    result["unbound_names"] = sorted(
        set(UNBOUND_RE.findall(text))
    )

    result["import_errors"] = sorted(
        {
            f"{name} from {module}"
            for name, module in IMPORT_ERROR_RE.findall(text)
        }
    )

    result["missing_modules"] = sorted(
        set(MODULE_NOT_FOUND_RE.findall(text))
    )

    result["fixture_errors"] = sorted(
        set(FIXTURE_RE.findall(text))
    )

    result["attribute_errors"] = sorted(
        set(
            match.strip()
            for match in ATTRIBUTE_RE.findall(text)
        )
    )

    return result


def first_nonempty(values: list[str]) -> str:
    for value in values:
        if value:
            return value

    return ""


def coverage_from_xml(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "coverage_xml_exists": path.is_file(),
        "coverage_xml_line_rate": "",
        "coverage_xml_branch_rate": "",
        "coverage_xml_error": "",
    }

    if not path.is_file():
        return result

    try:
        import xml.etree.ElementTree as ET

        root = ET.parse(path).getroot()

        line_rate = root.attrib.get("line-rate")
        branch_rate = root.attrib.get("branch-rate")

        if line_rate is not None:
            result["coverage_xml_line_rate"] = (
                100.0 * float(line_rate)
            )

        if branch_rate is not None:
            result["coverage_xml_branch_rate"] = (
                100.0 * float(branch_rate)
            )

    except Exception as exc:
        result["coverage_xml_error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--sut-root", required=True)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    out_dir = Path(args.out_dir).resolve()
    sut_root = Path(args.sut_root).resolve()

    out_dir.mkdir(parents=True, exist_ok=True)
    details_dir = out_dir / "details"
    details_dir.mkdir(parents=True, exist_ok=True)

    with input_path.open(
        encoding="utf-8",
        errors="replace",
    ) as handle:
        source_rows = list(
            csv.DictReader(
                handle,
                delimiter="\t",
            )
        )

    rows = []
    fingerprint_counts = collections.Counter()
    missing_name_counts = collections.Counter()
    fixture_counts = collections.Counter()
    import_counts = collections.Counter()

    for index, source in enumerate(source_rows, start=1):
        model = source["model"]
        sut_name = source["sut_name"]
        repeat = source["repeat"]
        reason = source["evaluator_reason"]
        eval_status = source["eval_status"]

        eval_run = Path(source["eval_run"])
        generated = Path(source["generated_tests"])
        sut_py = sut_root / sut_name / "sut.py"

        logs_dir = eval_run / "logs"

        log_paths = sorted(
            path
            for path in logs_dir.rglob("*.log")
            if path.is_file()
        )

        log_text_parts = []

        for path in log_paths:
            text = read_text(path)

            log_text_parts.append(
                f"\n\n===== {path.name} =====\n{text}"
            )

        combined_logs = "".join(log_text_parts)
        matches = extract_matches(combined_logs)

        sut_symbols = top_level_symbols(sut_py)
        defined_test_names = test_defined_names(generated)

        unresolved_names = sorted(
            name
            for name in matches["name_errors"]
            if name not in defined_test_names
        )

        for name in unresolved_names:
            missing_name_counts[name] += 1

        for fixture in matches["fixture_errors"]:
            fixture_counts[fixture] += 1

        for item in matches["import_errors"]:
            import_counts[item] += 1

        coverage_json_candidates = [
            eval_run / "runner" / "coverage.json",
            eval_run / "metrics" / "coverage.json",
            eval_run / "metrics" / "coverage_metrics.json",
        ]

        coverage_xml_candidates = [
            eval_run / "runner" / "coverage.xml",
            eval_run / "metrics" / "coverage.xml",
        ]

        coverage_json_path = next(
            (
                path
                for path in coverage_json_candidates
                if path.is_file()
            ),
            coverage_json_candidates[0],
        )

        coverage_xml_path = next(
            (
                path
                for path in coverage_xml_candidates
                if path.is_file()
            ),
            coverage_xml_candidates[0],
        )

        coverage_json = read_json(
            coverage_json_path
        )

        coverage_xml = coverage_from_xml(
            coverage_xml_path
        )

        fingerprint_parts = []

        if matches["missing_modules"]:
            fingerprint_parts.append(
                "missing_module:"
                + ",".join(matches["missing_modules"])
            )

        if matches["import_errors"]:
            fingerprint_parts.append(
                "import:"
                + ",".join(matches["import_errors"])
            )

        if unresolved_names:
            fingerprint_parts.append(
                "name:"
                + ",".join(unresolved_names)
            )

        if matches["fixture_errors"]:
            fingerprint_parts.append(
                "fixture:"
                + ",".join(matches["fixture_errors"])
            )

        if matches["attribute_errors"]:
            fingerprint_parts.append(
                "attribute:"
                + ",".join(
                    matches["attribute_errors"][:3]
                )
            )

        if COLLECTION_RE.search(combined_logs):
            fingerprint_parts.append(
                "collection_error"
            )

        if reason == "metrics_exist_but_status_missing":
            fingerprint_parts.append(
                "metrics_overlay"
            )

        if reason == "coverage_xml_exists_despite_fail":
            fingerprint_parts.append(
                "coverage_xml_recovery"
            )

        if reason == "module_level_test_like_code":
            fingerprint_parts.append(
                "module_level_wrapper"
            )

        fingerprint = (
            "|".join(fingerprint_parts)
            or reason
            or "unclassified"
        )

        fingerprint_counts[fingerprint] += 1

        detail_name = (
            f"{index:03d}__{model}__"
            f"{sut_name}__rep_{repeat}.txt"
        )

        detail_path = details_dir / detail_name

        generated_text = read_text(generated)
        sut_text = read_text(sut_py)

        with detail_path.open(
            "w",
            encoding="utf-8",
        ) as detail:
            detail.write(
                f"MODEL={model}\n"
                f"SUT={sut_name}\n"
                f"REPEAT={repeat}\n"
                f"EVAL_STATUS={eval_status}\n"
                f"REASON={reason}\n"
                f"FINGERPRINT={fingerprint}\n"
                f"EVAL_RUN={eval_run}\n"
                f"GENERATED={generated}\n"
                f"SUT_PY={sut_py}\n\n"
            )

            detail.write(
                "===== EXTRACTED ERRORS =====\n"
            )

            detail.write(
                json.dumps(
                    matches,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            detail.write(
                "===== UNRESOLVED NAMES =====\n"
            )

            detail.write(
                json.dumps(
                    unresolved_names,
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            detail.write(
                "===== SUT SYMBOLS =====\n"
            )

            detail.write(
                json.dumps(
                    sut_symbols,
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            detail.write(
                "===== TEST DEFINED NAMES =====\n"
            )

            detail.write(
                json.dumps(
                    defined_test_names,
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            detail.write(
                "===== COVERAGE ARTIFACTS =====\n"
            )

            detail.write(
                json.dumps(
                    {
                        "coverage_json_path": str(
                            coverage_json_path
                        ),
                        "coverage_json": coverage_json,
                        "coverage_xml_path": str(
                            coverage_xml_path
                        ),
                        **coverage_xml,
                    },
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            detail.write(
                "===== GENERATED TEST =====\n"
            )

            detail.write(generated_text)
            detail.write(
                "\n\n===== SUT =====\n"
            )
            detail.write(sut_text)
            detail.write(
                "\n\n===== LOGS =====\n"
            )
            detail.write(combined_logs)

        rows.append({
            "model": model,
            "sut_name": sut_name,
            "repeat": repeat,
            "eval_status": eval_status,
            "reason": reason,
            "fingerprint": fingerprint,
            "missing_modules": json.dumps(
                matches["missing_modules"]
            ),
            "import_errors": json.dumps(
                matches["import_errors"]
            ),
            "name_errors": json.dumps(
                matches["name_errors"]
            ),
            "unresolved_names": json.dumps(
                unresolved_names
            ),
            "fixture_errors": json.dumps(
                matches["fixture_errors"]
            ),
            "attribute_errors": json.dumps(
                matches["attribute_errors"]
            ),
            "sut_symbols": json.dumps(
                sut_symbols
            ),
            "coverage_json_exists": (
                coverage_json_path.is_file()
            ),
            "coverage_json_line": first_nonempty([
                str(
                    coverage_json.get(
                        "line_coverage_pct",
                        "",
                    )
                ),
                str(
                    coverage_json.get(
                        "line_pct",
                        "",
                    )
                ),
            ]),
            "coverage_json_branch": first_nonempty([
                str(
                    coverage_json.get(
                        "branch_coverage_pct",
                        "",
                    )
                ),
                str(
                    coverage_json.get(
                        "branch_pct",
                        "",
                    )
                ),
            ]),
            **coverage_xml,
            "detail_file": str(detail_path),
        })

    fields = list(rows[0].keys())

    diagnostics_path = out_dir / "diagnostics.tsv"

    with diagnostics_path.open(
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

    with (
        out_dir / "fingerprint_counts.tsv"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write("fingerprint\tcount\n")

        for key, value in sorted(
            fingerprint_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            handle.write(f"{key}\t{value}\n")

    with (
        out_dir / "missing_name_counts.tsv"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write("name\tcount\n")

        for key, value in sorted(
            missing_name_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            handle.write(f"{key}\t{value}\n")

    with (
        out_dir / "fixture_counts.tsv"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write("fixture\tcount\n")

        for key, value in sorted(
            fixture_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            handle.write(f"{key}\t{value}\n")

    with (
        out_dir / "import_counts.tsv"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write("import_error\tcount\n")

        for key, value in sorted(
            import_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            handle.write(f"{key}\t{value}\n")

    with (
        out_dir / "summary.txt"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            f"candidate_count={len(rows)}\n"
        )
        handle.write(
            f"fingerprint_count={len(fingerprint_counts)}\n"
        )
        handle.write(
            f"distinct_missing_names={len(missing_name_counts)}\n"
        )
        handle.write(
            f"distinct_fixtures={len(fixture_counts)}\n"
        )
        handle.write(
            f"distinct_import_errors={len(import_counts)}\n"
        )

    print(out_dir / "summary.txt")


if __name__ == "__main__":
    main()
