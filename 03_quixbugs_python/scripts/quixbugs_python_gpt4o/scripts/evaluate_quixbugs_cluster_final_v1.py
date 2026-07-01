#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SITE_CUSTOMIZE = r'''
from __future__ import annotations

import ast
import builtins
import collections
import importlib
import math
import random
import string
import sys
from pathlib import Path

try:
    import pytest
    builtins.pytest = pytest

    # Compatibilidade apenas para metadados gerados.
    # Não afeta inputs, assertions nem chamadas ao SUT.
    class _QuixBugsTags:
        QUAXIBUGS_PYTHON_SUT = pytest.mark.quixbugs_python_sut

    builtins.Tags = _QuixBugsTags

    # Alguns outputs contêm apenas a expressão "TestFile"
    # como cabeçalho/metadado sem qualquer uso funcional.
    builtins.TestFile = object()

except Exception:
    pass

builtins.random = random
builtins.string = string
builtins.defaultdict = collections.defaultdict
builtins.inf = math.inf

ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "test_generated.py"

try:
    sut = importlib.import_module("sut")
except Exception:
    sut = None

if sut is not None:
    builtins.sut = sut

    # Alias legítimo: ambos os nomes referem exatamente o mesmo
    # objeto de módulo. Isto evita executar uma segunda cópia do SUT
    # e garante que coverage e mutation medem sut.py.
    sys.modules["quixbugs_python_sut"] = sut

    # Compatibilidade legítima para "from sut import sut".
    if not hasattr(sut, "sut"):
        setattr(sut, "sut", sut)

    # Expõe apenas símbolos que existem realmente no módulo SUT.
    for name in dir(sut):
        if name.startswith("__"):
            continue

        try:
            value = getattr(sut, name)
        except Exception:
            continue

        if not hasattr(builtins, name):
            setattr(builtins, name, value)


def top_level_symbols(path):
    try:
        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except Exception:
        return set()

    names = set()

    for node in tree.body:
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            names.add(node.name)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)

    return names


def requested_names(path):
    try:
        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except Exception:
        return set()

    requested = set()
    defined = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "sut":
                for alias in node.names:
                    requested.add(alias.name)

            for alias in node.names:
                defined.add(alias.asname or alias.name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                defined.add(
                    alias.asname
                    or alias.name.split(".")[0]
                )

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            defined.add(node.name)

        elif isinstance(node, ast.arg):
            defined.add(node.arg)

        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                defined.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                requested.add(node.id)

    return requested - defined


if sut is not None and TEST_FILE.is_file():
    wanted = requested_names(TEST_FILE)

    excluded = {
        "sut.py",
        "test_generated.py",
        "test_wrapper.py",
        "conftest.py",
        "quixbugs_eval_compat.py",
    }

    symbol_sources = {}

    for path in ROOT.glob("*.py"):
        if path.name in excluded:
            continue

        for symbol in top_level_symbols(path):
            symbol_sources.setdefault(
                symbol,
                [],
            ).append(path)

    for name in sorted(wanted):
        if hasattr(builtins, name):
            continue

        if hasattr(sut, name):
            try:
                setattr(
                    builtins,
                    name,
                    getattr(sut, name),
                )
            except Exception:
                pass
            continue

        sources = symbol_sources.get(name, [])

        # Só resolve símbolos auxiliares quando o nome é único.
        if len(sources) != 1:
            continue

        source = sources[0]
        module_name = source.stem

        try:
            module = importlib.import_module(module_name)
            value = getattr(module, name)
        except Exception:
            continue

        try:
            setattr(builtins, name, value)
            setattr(sut, name, value)
        except Exception:
            pass
'''


CONFTEST = r'''
from __future__ import annotations

# Forçar a camada de compatibilidade antes de o pytest importar
# o ficheiro de testes gerado.
import quixbugs_eval_compat

import importlib
import os
from pathlib import Path

import pytest

# Normalizar apenas pytestmark malformado que seja texto.
# Valores como "benchmark" ou "not implemented" são metadados,
# não lógica de teste.
import _pytest.mark.structures as _mark_structures

_original_normalize_mark_list = (
    _mark_structures.normalize_mark_list
)


def _safe_normalize_mark_list(mark_list):
    if isinstance(mark_list, (str, bytes)):
        return iter(())

    try:
        return _original_normalize_mark_list(mark_list)
    except TypeError:
        try:
            filtered = [
                item
                for item in mark_list
                if hasattr(item, "mark")
            ]
        except Exception:
            return iter(())

        return _original_normalize_mark_list(filtered)


_mark_structures.normalize_mark_list = (
    _safe_normalize_mark_list
)


@pytest.fixture
def sut():
    return importlib.import_module("sut")


def pytest_collection_modifyitems(config, items):
    if os.environ.get(
        "QUIXBUGS_EFFECTIVE_FILTER"
    ) != "1":
        return

    allow_file = (
        Path(__file__).resolve().parent
        / "effective_nodeids.txt"
    )

    if not allow_file.is_file():
        return

    allowed = {
        line.strip()
        for line in allow_file.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }

    selected = []
    deselected = []

    for item in items:
        if item.nodeid in allowed:
            selected.append(item)
        else:
            deselected.append(item)

    items[:] = selected

    if deselected:
        config.hook.pytest_deselected(
            items=deselected
        )
'''


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except Exception:
        return {}


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    if not path.is_file():
        return ""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def run(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    log: Path,
    timeout: int,
) -> int:
    log.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    full_command = [
        "timeout",
        "--kill-after=5s",
        f"{timeout}s",
        *command,
    ]

    with log.open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            "COMMAND="
            + json.dumps(full_command)
            + "\n"
        )

        handle.flush()

        result = subprocess.run(
            full_command,
            cwd=cwd,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )

        handle.write(
            f"\nEXIT_CODE={result.returncode}\n"
        )

    return result.returncode


def module_testlike_count(path: Path) -> int:
    """
    Conta construções executáveis de teste ao nível do módulo.

    Não altera o teste. Apenas permite executar, dentro de um único
    node pytest, ficheiros que exprimem os testes através de asserts
    ou chamadas diretas ao nível do módulo.
    """
    try:
        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except Exception:
        return 0

    count = 0

    for node in tree.body:
        if isinstance(node, ast.Assert):
            count += 1

        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
        ):
            count += 1

    return count


def parse_nodeids(
    log: Path,
    filename: str,
) -> list[str]:
    if not log.is_file():
        return []

    prefix = filename + "::"
    nodeids = []

    for line in log.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        line = line.strip()

        if line.startswith(prefix):
            nodeids.append(line)

    return nodeids


def parse_coverage(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "coverage_available": False,
            "line_coverage_pct": None,
            "branch_coverage_pct": None,
        }

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        totals = data.get("totals", {})

        statements = int(
            totals.get("num_statements") or 0
        )

        covered_lines = int(
            totals.get("covered_lines") or 0
        )

        branches = int(
            totals.get("num_branches") or 0
        )

        covered_branches = int(
            totals.get("covered_branches") or 0
        )

        line_pct = (
            100.0 * covered_lines / statements
            if statements
            else 100.0
        )

        # Não existindo branches, não há branches por cobrir.
        branch_pct = (
            100.0 * covered_branches / branches
            if branches
            else 100.0
        )

        return {
            "coverage_available": True,
            "num_statements": statements,
            "covered_lines": covered_lines,
            "num_branches": branches,
            "covered_branches": covered_branches,
            "line_coverage_pct": line_pct,
            "branch_coverage_pct": branch_pct,
        }

    except Exception as exc:
        return {
            "coverage_available": False,
            "coverage_parse_error": (
                f"{type(exc).__name__}: {exc}"
            ),
            "line_coverage_pct": None,
            "branch_coverage_pct": None,
        }



MUTMUT_ANSI_RE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"
)

MUTMUT_PROGRESS_RE = re.compile(
    r"(?P<done>\d+)/(?P<total>\d+)"
    r"\s+🎉\s*(?P<killed>\d+)"
    r"\s+🫥\s*(?P<no_tests>\d+)"
    r"\s+⏰\s*(?P<timeout>\d+)"
    r"\s+🤔\s*(?P<suspicious>\d+)"
    r"\s+🙁\s*(?P<survived>\d+)"
    r"\s+🔇\s*(?P<skipped>\d+)"
)


def parse_mutmut_log(path: Path) -> dict[str, Any]:
    defaults = {
        "mutation_available": False,
        "mutants_progress_done": 0,
        "mutants_total": 0,
        "mutants_killed": 0,
        "mutants_timeout": 0,
        "mutants_detected": 0,
        "mutants_survived": 0,
        "mutants_no_tests": 0,
        "mutants_suspicious": 0,
        "mutants_skipped": 0,
        "mutation_score_detected_pct": None,
        "mutation_score_killed_only_pct": None,
        "mutation_score_formula": (
            "(killed + timeout) / total_mutants"
        ),
        "mutation_timeout_policy": (
            "Timeout mutants are treated as detected. "
            "Killed-only score is retained separately."
        ),
    }

    if not path.is_file():
        return defaults

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    text = MUTMUT_ANSI_RE.sub(
        "",
        text,
    ).replace("\r", "\n")

    matches = []

    for line in text.splitlines():
        match = MUTMUT_PROGRESS_RE.search(line)

        if match:
            matches.append(match)

    if not matches:
        return defaults

    values = {
        key: int(value)
        for key, value
        in matches[-1].groupdict().items()
    }

    total = values["total"]
    killed = values["killed"]
    timed_out = values["timeout"]
    detected = killed + timed_out

    category_sum = sum(
        values[key]
        for key in (
            "killed",
            "no_tests",
            "timeout",
            "suspicious",
            "survived",
            "skipped",
        )
    )

    complete = (
        values["done"] == total
        and category_sum == total
    )

    if total == 0:
        detected_score = 100.0
        killed_only_score = 100.0
    else:
        detected_score = (
            100.0 * detected / total
        )

        killed_only_score = (
            100.0 * killed / total
        )

    return {
        "mutation_available": complete,
        "mutants_progress_done": values["done"],
        "mutants_total": total,
        "mutants_killed": killed,
        "mutants_timeout": timed_out,
        "mutants_detected": detected,
        "mutants_survived": values["survived"],
        "mutants_no_tests": values["no_tests"],
        "mutants_suspicious": values["suspicious"],
        "mutants_skipped": values["skipped"],
        "mutation_score_detected_pct": detected_score,
        "mutation_score_killed_only_pct": (
            killed_only_score
        ),
        "mutation_score_formula": (
            "(killed + timeout) / total_mutants"
        ),
        "mutation_timeout_policy": (
            "Timeout mutants are treated as detected. "
            "Killed-only score is retained separately."
        ),
    }


def recover_existing_metrics(
    eval_run: Path,
) -> dict[str, Any]:
    status_path = (
        eval_run
        / "metrics"
        / "status.json"
    )

    status = read_json(status_path)

    candidates = [
        (
            eval_run
            / "metrics"
            / "coverage_metrics.json"
        ),
        eval_run / "runner" / "coverage.json",
        eval_run / "metrics" / "coverage.json",
    ]

    coverage_data = {}

    for path in candidates:
        if path.is_file():
            coverage_data = read_json(path)

            if coverage_data:
                break

    line = status.get("line_coverage_pct")
    branch = status.get("branch_coverage_pct")

    if line is None:
        line = coverage_data.get(
            "line_coverage_pct",
            coverage_data.get("line_pct"),
        )

    if branch is None:
        branch = coverage_data.get(
            "branch_coverage_pct",
            coverage_data.get("branch_pct"),
        )

    branches_total = coverage_data.get(
        "num_branches",
        coverage_data.get("branches_total"),
    )

    if (
        branch is None
        or branch == ""
        or (
            float(branch) == 0.0
            and branches_total in (0, "0")
        )
    ):
        if branches_total in (0, "0"):
            branch = 100.0

    return {
        "status": status.get("status"),
        "line_coverage_pct": line,
        "branch_coverage_pct": branch,
        "coverage_data": coverage_data,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sut-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument(
        "--node-timeout",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--suite-timeout",
        type=int,
        default=90,
    )
    parser.add_argument(
        "--mutation-timeout",
        type=int,
        default=300,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    sut_root = Path(args.sut_root).resolve()
    out_root = Path(args.out_root).resolve()

    work_root = out_root / "work"
    work_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    with input_path.open(
        encoding="utf-8",
        errors="replace",
    ) as handle:
        input_rows = list(
            csv.DictReader(
                handle,
                delimiter="\t",
            )
        )

    results = []
    status_counts = Counter()

    for index, row in enumerate(
        input_rows,
        start=1,
    ):
        model = row["model"]
        sut_name = row["sut_name"]
        repeat = int(row["repeat"])
        reason = row["evaluator_reason"]

        source_test = Path(
            row["generated_tests"]
        )

        eval_run = Path(row["eval_run"])
        sut_dir = sut_root / sut_name

        case_root = (
            work_root
            / model
            / sut_name
            / f"rep_{repeat:02d}"
        )

        result_path = (
            case_root / "result.json"
        )

        if (
            result_path.is_file()
            and not args.force
        ):
            existing = read_json(result_path)

            results.append(existing)

            status_counts[
                existing.get(
                    "probe_status",
                    "unknown_existing_status",
                )
            ] += 1

            print(
                f"[{index}/{len(input_rows)}] "
                f"{model} {sut_name} rep={repeat} "
                f"status=SKIP_EXISTING"
            )

            continue

        if case_root.exists():
            shutil.rmtree(case_root)

        case_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        base = {
            "index": index,
            "model": model,
            "sut_name": sut_name,
            "repeat": repeat,
            "original_eval_status": (
                row["eval_status"]
            ),
            "reason": reason,
            "source_test": str(source_test),
            "source_test_sha256": (
                sha256(source_test)
            ),
            "case_root": str(case_root),
        }

        if reason in {
            "metrics_exist_but_status_missing",
            "coverage_xml_exists_despite_fail",
        }:
            metrics = recover_existing_metrics(
                eval_run
            )

            recovered = (
                metrics["line_coverage_pct"]
                not in (None, "")
                and metrics["branch_coverage_pct"]
                not in (None, "")
            )

            base.update(metrics)
            base["recovered"] = recovered
            base["probe_status"] = (
                "existing_metrics_recovered"
                if recovered
                else "existing_metrics_unusable"
            )

            status_counts[
                base["probe_status"]
            ] += 1

            write_json(
                case_root / "result.json",
                base,
            )

            results.append(base)
            continue

        if not source_test.is_file():
            base.update({
                "recovered": False,
                "probe_status": "missing_test_file",
            })

            status_counts[
                base["probe_status"]
            ] += 1

            write_json(
                case_root / "result.json",
                base,
            )

            results.append(base)
            continue

        if not sut_dir.is_dir():
            base.update({
                "recovered": False,
                "probe_status": "missing_sut_dir",
            })

            status_counts[
                base["probe_status"]
            ] += 1

            write_json(
                case_root / "result.json",
                base,
            )

            results.append(base)
            continue

        # Copia o SUT completo, incluindo módulos auxiliares.
        for source in sut_dir.iterdir():
            destination = case_root / source.name

            if source.is_dir():
                shutil.copytree(
                    source,
                    destination,
                    dirs_exist_ok=True,
                )

            elif source.is_file():
                shutil.copy2(
                    source,
                    destination,
                )

        # Alias de compatibilidade legítimo: alguns testes gerados
        # importam o mesmo SUT através do nome quixbugs_python_sut.
        # O conteúdo é uma cópia byte a byte de sut.py.
        sut_file = case_root / "sut.py"
        sut_alias = case_root / "quixbugs_python_sut.py"

        if sut_file.is_file():
            shutil.copy2(
                sut_file,
                sut_alias,
            )

        shutil.copy2(
            source_test,
            case_root / "test_generated.py",
        )

        copied_hash = sha256(
            case_root / "test_generated.py"
        )

        base["copied_test_sha256"] = copied_hash
        base["test_unchanged"] = (
            copied_hash
            == base["source_test_sha256"]
        )

        (case_root / "quixbugs_eval_compat.py").write_text(
            SITE_CUSTOMIZE,
            encoding="utf-8",
        )

        (case_root / "conftest.py").write_text(
            CONFTEST,
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["PYTHONPATH"] = str(case_root)
        # Não desativar o user-site: pytest/pytest-cov estão
        # instalados nesse ambiente na VM.
        env.pop("PYTHONNOUSERSITE", None)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

        collect_log = (
            case_root / "logs" / "collect.log"
        )

        collect_rc = run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "test_generated.py",
            ],
            case_root,
            env,
            collect_log,
            60,
        )

        test_filename = "test_generated.py"

        nodeids = parse_nodeids(
            collect_log,
            test_filename,
        )

        wrapper_used = False

        # Só cria wrapper quando existem assertions reais
        # ao nível do módulo.
        if (
            not nodeids
            and module_testlike_count(
                case_root / "test_generated.py"
            ) > 0
        ):
            wrapper_used = True

            (
                case_root / "test_wrapper.py"
            ).write_text(
                "import runpy\n\n"
                "def test_generated_module_level():\n"
                "    runpy.run_path(\n"
                "        'test_generated.py',\n"
                "        run_name='__generated_test__',\n"
                "    )\n",
                encoding="utf-8",
            )

            collect_log = (
                case_root
                / "logs"
                / "collect_wrapper.log"
            )

            collect_rc = run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--collect-only",
                    "-q",
                    "test_wrapper.py",
                ],
                case_root,
                env,
                collect_log,
                60,
            )

            test_filename = "test_wrapper.py"

            nodeids = parse_nodeids(
                collect_log,
                test_filename,
            )

        passing = []
        failing = 0
        timed_out = 0

        node_log_root = (
            case_root / "logs" / "nodeids"
        )

        for nodeid in nodeids:
            safe = hashlib.sha256(
                nodeid.encode("utf-8")
            ).hexdigest()

            rc = run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "--disable-warnings",
                    nodeid,
                ],
                case_root,
                env,
                node_log_root / f"{safe}.log",
                args.node_timeout,
            )

            if rc == 0:
                passing.append(nodeid)

            elif rc in (124, 137):
                timed_out += 1

            else:
                failing += 1

        (
            case_root / "effective_nodeids.txt"
        ).write_text(
            "\n".join(passing)
            + ("\n" if passing else ""),
            encoding="utf-8",
        )

        combined_rc = None
        coverage_rc = None
        coverage_metrics = {
            "coverage_available": False,
            "line_coverage_pct": None,
            "branch_coverage_pct": None,
        }

        if passing:
            effective_env = dict(env)
            effective_env[
                "QUIXBUGS_EFFECTIVE_FILTER"
            ] = "1"

            combined_rc = run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "--disable-warnings",
                    test_filename,
                ],
                case_root,
                effective_env,
                case_root
                / "logs"
                / "combined.log",
                args.suite_timeout,
            )

            if combined_rc == 0:
                coverage_rc = run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-p",
                        "pytest_cov.plugin",
                        "-q",
                        "--disable-warnings",
                        "--cov=sut",
                        "--cov-branch",
                        "--cov-report=json:coverage.json",
                        test_filename,
                    ],
                    case_root,
                    effective_env,
                    case_root
                    / "logs"
                    / "coverage.log",
                    args.suite_timeout,
                )

                coverage_metrics = parse_coverage(
                    case_root / "coverage.json"
                )

        mutation_metrics = {
            "mutation_available": False,
            "mutants_progress_done": 0,
            "mutants_total": 0,
            "mutants_killed": 0,
            "mutants_timeout": 0,
            "mutants_detected": 0,
            "mutants_survived": 0,
            "mutants_no_tests": 0,
            "mutants_suspicious": 0,
            "mutants_skipped": 0,
            "mutation_score_detected_pct": None,
            "mutation_score_killed_only_pct": None,
            "mutation_score_formula": (
                "(killed + timeout) / total_mutants"
            ),
            "mutation_timeout_policy": (
                "Timeout mutants are treated as detected. "
                "Killed-only score is retained separately."
            ),
        }

        mutmut_rc = None
        mutmut_results_rc = None

        if (
            passing
            and combined_rc == 0
            and coverage_metrics.get(
                "coverage_available"
            )
        ):
            also_copy = sorted({
                path.name
                for path in case_root.glob("*.py")
                if path.name != "sut.py"
            })

            if (
                "effective_nodeids.txt"
                not in also_copy
            ):
                also_copy.append(
                    "effective_nodeids.txt"
                )

            pyproject = (
                "[tool.mutmut]\n"
                'paths_to_mutate = ["sut.py"]\n'
                "pytest_add_cli_args_test_selection = "
                + json.dumps([test_filename])
                + "\n"
                'pytest_add_cli_args = '
                '["-q", "--disable-warnings"]\n'
                "also_copy = "
                + json.dumps(also_copy)
                + "\n"
                "timeout_constant = 2.0\n"
                "timeout_multiplier = 5.0\n"
                "use_git_change_detection = false\n"
            )

            (
                case_root / "pyproject.toml"
            ).write_text(
                pyproject,
                encoding="utf-8",
            )

            mutants_dir = (
                case_root / "mutants"
            )

            if mutants_dir.exists():
                shutil.rmtree(mutants_dir)

            mutmut_bin = (
                shutil.which("mutmut")
                or "/usr/local/bin/mutmut"
            )

            mutation_env = dict(
                effective_env
            )

            mutation_env[
                "QUIXBUGS_EFFECTIVE_FILTER"
            ] = "1"

            mutation_env[
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD"
            ] = "1"

            mutmut_run_log = (
                case_root
                / "logs"
                / "mutmut_run.log"
            )

            mutmut_results_log = (
                case_root
                / "logs"
                / "mutmut_results.log"
            )

            mutmut_rc = run(
                [
                    mutmut_bin,
                    "run",
                ],
                case_root,
                mutation_env,
                mutmut_run_log,
                args.mutation_timeout,
            )

            mutmut_results_rc = run(
                [
                    mutmut_bin,
                    "results",
                ],
                case_root,
                mutation_env,
                mutmut_results_log,
                60,
            )

            mutation_metrics = (
                parse_mutmut_log(
                    mutmut_run_log
                )
            )

            if mutmut_rc != 0:
                mutation_metrics[
                    "mutation_available"
                ] = False

        recovered = bool(
            passing
            and combined_rc == 0
            and coverage_metrics.get(
                "coverage_available"
            )
        )

        if recovered:
            probe_status = "recovered_with_safe_harness"

        elif not nodeids:
            probe_status = "still_no_tests_collected"

        elif not passing:
            probe_status = "all_nodeids_still_fail"

        elif combined_rc != 0:
            probe_status = "passing_nodeids_unstable"

        else:
            probe_status = "coverage_still_failed"

        base.update({
            "collect_exit_code": collect_rc,
            "collected_nodeids": len(nodeids),
            "passing_nodeids": len(passing),
            "failing_nodeids": failing,
            "timeout_nodeids": timed_out,
            "combined_exit_code": combined_rc,
            "coverage_exit_code": coverage_rc,
            "wrapper_used": wrapper_used,
            "recovered": recovered,
            "probe_status": probe_status,
            "mutmut_exit_code": mutmut_rc,
            "mutmut_results_exit_code": (
                mutmut_results_rc
            ),
            **coverage_metrics,
            **mutation_metrics,
        })

        status_counts[probe_status] += 1

        write_json(
            case_root / "result.json",
            base,
        )

        results.append(base)

        print(
            f"[{index}/{len(input_rows)}] "
            f"{model} {sut_name} rep={repeat} "
            f"status={probe_status} "
            f"collected={len(nodeids)} "
            f"passed={len(passing)} "
            f"line={base.get('line_coverage_pct')} "
            f"branch={base.get('branch_coverage_pct')}"
        )

    all_fields = sorted({
        key
        for result in results
        for key in result.keys()
        if key != "coverage_data"
    })

    results_path = out_root / "results.tsv"

    with results_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=all_fields,
            delimiter="\t",
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(results)

    recovered_rows = [
        result
        for result in results
        if result.get("recovered")
    ]

    with (
        out_root / "recovered.tsv"
    ).open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=all_fields,
            delimiter="\t",
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(recovered_rows)

    with (
        out_root / "status_counts.tsv"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write("status\tcount\n")

        for status, count in sorted(
            status_counts.items()
        ):
            handle.write(
                f"{status}\t{count}\n"
            )

    with (
        out_root / "summary.txt"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            f"candidate_count={len(results)}\n"
        )

        handle.write(
            f"recovered_count={len(recovered_rows)}\n"
        )

        handle.write(
            "status_counts="
            + json.dumps(
                dict(sorted(status_counts.items()))
            )
            + "\n"
        )

    print(out_root / "summary.txt")


if __name__ == "__main__":
    main()
