from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


IGNORE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".git",
    ".hg",
    ".svn",
    ".coverage",
    "htmlcov",
    "mutants",
    "mutation_project",
    "freetype-2.6.1",
}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--mutation-timeout-s", type=int, default=180)
    return ap.parse_args()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def update_status(run_dir: Path, **kwargs):
    p = run_dir / "metrics" / "status.json"
    d = read_json(p)
    d.update(kwargs)
    write_json(p, d)
    return d


def copy_contents(src: Path, dst: Path):
    if not src.exists():
        return

    dst.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        if item.name in IGNORE_NAMES:
            continue

        target = dst / item.name

        if item.is_dir():
            shutil.copytree(
                item,
                target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(*IGNORE_NAMES),
            )
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def rel_if_under(path: Path, root: Path):
    try:
        return path.resolve().relative_to(root.resolve())
    except Exception:
        return None


def resolve_target(run_dir: Path, work_sut_dir: Path, target_module: str):
    prep = read_json(run_dir / "raw" / "work_sut_prepare.json")

    import_roots = []
    for r in prep.get("import_roots") or []:
        rr = Path(r).resolve()
        if rr not in import_roots:
            import_roots.append(rr)

    for r in [
        work_sut_dir,
        work_sut_dir / "src",
        work_sut_dir / "lib",
        work_sut_dir / "build" / "lib",
    ]:
        rr = r.resolve()
        if rr not in import_roots:
            import_roots.append(rr)

    target_file = None

    target_relpath = prep.get("target_relpath")
    if target_relpath:
        candidate = (work_sut_dir / target_relpath).resolve()
        if candidate.exists() and candidate.is_file():
            target_file = candidate

    if target_file is None:
        base = Path(*target_module.split("."))
        candidates = []

        for root in import_roots:
            candidates.append(root / (base.as_posix() + ".py"))
            candidates.append(root / base / "__init__.py")

        for c in candidates:
            if c.exists() and c.is_file():
                target_file = c.resolve()
                break

    if target_file is None:
        raise FileNotFoundError(f"cannot resolve target module {target_module} under {work_sut_dir}")

    # Prefer the most specific import root. This is critical for lib/ and src/ layouts:
    # work/sut/lib/ansible/utils/unicode.py -> ansible/utils/unicode.py, not lib/ansible/utils/unicode.py.
    chosen_import_root = None
    target_rel = None

    for root in sorted(import_roots, key=lambda x: len(str(x.resolve())), reverse=True):
        rel = rel_if_under(target_file, root)
        if rel is not None:
            chosen_import_root = root
            target_rel = rel
            break

    if chosen_import_root is None or target_rel is None:
        chosen_import_root = work_sut_dir
        target_rel = target_file.relative_to(work_sut_dir)

    # Package-aware mutation targeting v2.
    # When importlib resolves a package to __init__.py, mutate
    # the package directory rather than only the facade file.
    if target_file.name == "__init__.py":
        package_dir = target_file.parent
        package_rel = None

        for package_base in (chosen_import_root, work_sut_dir):
            if package_base is None:
                continue

            try:
                candidate_rel = package_dir.relative_to(package_base)
            except ValueError:
                continue

            if candidate_rel.as_posix() in ("", "."):
                continue

            package_rel = candidate_rel
            break

        if package_rel is None:
            try:
                package_rel = package_dir.relative_to(work_sut_dir)
            except ValueError:
                package_rel = None

        if package_rel is not None:
            target_rel = package_rel

    return {
        "target_file": target_file,
        "target_rel": target_rel,
        "chosen_import_root": chosen_import_root,
        "import_roots": import_roots,
        "prep": prep,
    }


def mutation_import_shim(target_module: str) -> str:
    return (
        "# --- BugsInPy mutmut import shim start ---\n"
        "from pathlib import Path as _bugsinpy_Path\n"
        "import importlib as _bugsinpy_importlib\n"
        "import sys as _bugsinpy_sys\n"
        f"_bugsinpy_target_module = {target_module!r}\n"
        "_bugsinpy_this_file = _bugsinpy_Path(__file__).resolve()\n"
        "_bugsinpy_in_mutants = (\n"
        "    len(_bugsinpy_this_file.parents) > 2\n"
        "    and _bugsinpy_this_file.parents[1].name == 'mutants'\n"
        ")\n"
        "if _bugsinpy_in_mutants:\n"
        "    _bugsinpy_project_root = _bugsinpy_this_file.parents[2]\n"
        "    _bugsinpy_mutants_root = _bugsinpy_this_file.parents[1]\n"
        "else:\n"
        "    _bugsinpy_project_root = _bugsinpy_this_file.parents[1]\n"
        "    _bugsinpy_mutants_root = _bugsinpy_project_root / 'mutants'\n"
        "for _bugsinpy_p in [_bugsinpy_project_root, _bugsinpy_mutants_root]:\n"
        "    _bugsinpy_s = str(_bugsinpy_p)\n"
        "    if _bugsinpy_s in _bugsinpy_sys.path:\n"
        "        _bugsinpy_sys.path.remove(_bugsinpy_s)\n"
        "if _bugsinpy_in_mutants:\n"
        "    _bugsinpy_sys.path.insert(0, str(_bugsinpy_project_root))\n"
        "    _bugsinpy_sys.path.insert(0, str(_bugsinpy_mutants_root))\n"
        "else:\n"
        "    _bugsinpy_sys.path.insert(0, str(_bugsinpy_project_root))\n"
        "\n"
        "def _bugsinpy_force_package_path(_pkg_name):\n"
        "    _parts = _pkg_name.split('.')\n"
        "    _rel = _bugsinpy_Path(*_parts)\n"
        "    _mutant_pkg_dir = _bugsinpy_mutants_root / _rel\n"
        "    _original_pkg_dir = _bugsinpy_project_root / _rel\n"
        "    try:\n"
        "        _pkg = _bugsinpy_importlib.import_module(_pkg_name)\n"
        "    except Exception:\n"
        "        return\n"
        "    _pkg_path = getattr(_pkg, '__path__', None)\n"
        "    if _pkg_path is None:\n"
        "        return\n"
        "    _new_path = []\n"
        "    if _bugsinpy_in_mutants and _mutant_pkg_dir.exists():\n"
        "        _new_path.append(str(_mutant_pkg_dir))\n"
        "    if _original_pkg_dir.exists():\n"
        "        _new_path.append(str(_original_pkg_dir))\n"
        "    for _old in list(_pkg_path):\n"
        "        if _old not in _new_path:\n"
        "            _new_path.append(_old)\n"
        "    try:\n"
        "        _pkg.__path__ = _new_path\n"
        "    except Exception:\n"
        "        pass\n"
        "\n"
        "_bugsinpy_pkg_parts = _bugsinpy_target_module.split('.')\n"
        "for _bugsinpy_i in range(1, len(_bugsinpy_pkg_parts) + 1):\n"
        "    _bugsinpy_force_package_path('.'.join(_bugsinpy_pkg_parts[:_bugsinpy_i]))\n"
        "\n"
        "def _bugsinpy_restore_top_level_metadata():\n"
        "    try:\n"
        "        import ast as _bugsinpy_ast\n"
        "        _top_package = _bugsinpy_target_module.split('.', 1)[0]\n"
        "        _pkg = _bugsinpy_importlib.import_module(_top_package)\n"
        "        _original_init = _bugsinpy_project_root / _top_package / '__init__.py'\n"
        "        if not _original_init.exists():\n"
        "            return\n"
        "        _text = _original_init.read_text(encoding='utf-8', errors='replace')\n"
        "        _tree = _bugsinpy_ast.parse(_text, filename=str(_original_init))\n"
        "        for _node in _tree.body:\n"
        "            if isinstance(_node, _bugsinpy_ast.Assign):\n"
        "                _targets = list(_node.targets)\n"
        "                _value = _node.value\n"
        "            elif isinstance(_node, _bugsinpy_ast.AnnAssign):\n"
        "                _targets = [_node.target]\n"
        "                _value = _node.value\n"
        "            else:\n"
        "                continue\n"
        "            if not isinstance(_value, _bugsinpy_ast.Constant):\n"
        "                continue\n"
        "            for _target in _targets:\n"
        "                if not isinstance(_target, _bugsinpy_ast.Name):\n"
        "                    continue\n"
        "                _name = _target.id\n"
        "                if _name.startswith('__') and _name.endswith('__') and not hasattr(_pkg, _name):\n"
        "                    setattr(_pkg, _name, _value.value)\n"
        "        if not getattr(_pkg, '__file__', None):\n"
        "            try:\n"
        "                _pkg.__file__ = str(_original_init)\n"
        "            except Exception:\n"
        "                pass\n"
        "    except Exception:\n"
        "        pass\n"
        "\n"
        "_bugsinpy_restore_top_level_metadata()\n"
        "# --- BugsInPy mutmut import shim end ---\n"
        "\n"
    )


def prepare_tests(run_dir: Path, mutation_project: Path, target_module: str):
    status = read_json(run_dir / "metrics" / "status.json")

    test_file = (
        status.get("canonical_test_file")
        or status.get("sanitized_test_file")
        or status.get("generated_test_file")
    )

    if test_file:
        test_file = Path(test_file)
    else:
        test_file = run_dir / "work" / "tests" / "test_gpt_iaedu.py"

    if not test_file.exists():
        raise FileNotFoundError(f"canonical/generated test not found: {test_file}")

    tests_dir = mutation_project / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    dst = tests_dir / "test_gpt_iaedu.py"
    text = test_file.read_text(encoding="utf-8", errors="replace")

    if "BugsInPy mutmut import shim start" not in text:
        text = mutation_import_shim(target_module) + text

    dst.write_text(text, encoding="utf-8")
    return dst


def build_mutation_project(run_dir: Path, work_sut_dir: Path, resolved: dict):
    mutation_project = run_dir / "work" / "mutation_project"

    if mutation_project.exists():
        shutil.rmtree(mutation_project)

    mutation_project.mkdir(parents=True, exist_ok=True)

    # Copy full SUT, then overlay import roots into mutation_project root.
    copy_contents(work_sut_dir, mutation_project)

    for root in resolved["import_roots"]:
        if root.exists():
            copy_contents(root, mutation_project)

    # Isolate mutation testing from dataset-provided tests and pytest
    # configuration. Only the generated/canonical test is added later.
    removed_test_artifacts = []

    for name in ("tests", "test"):
        candidate = mutation_project / name

        if candidate.is_dir():
            shutil.rmtree(candidate)
            removed_test_artifacts.append(str(candidate))
        elif candidate.exists():
            candidate.unlink()
            removed_test_artifacts.append(str(candidate))

    for name in ("pytest.ini", "tox.ini"):
        candidate = mutation_project / name

        if candidate.exists():
            if candidate.is_dir():
                shutil.rmtree(candidate)
            else:
                candidate.unlink()

            removed_test_artifacts.append(str(candidate))

    for candidate in sorted(mutation_project.rglob("conftest.py")):
        try:
            candidate.unlink()
            removed_test_artifacts.append(str(candidate))
        except FileNotFoundError:
            pass

    write_json(
        run_dir / "metrics" / "mutation_isolation.json",
        {
            "policy": "generated_test_only",
            "removed_test_artifacts": removed_test_artifacts,
        },
    )

    target_file = resolved["target_file"]
    target_rel = resolved["target_rel"]

    flat_target = mutation_project / target_rel
    if not flat_target.exists():
        flat_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_file, flat_target)

    return mutation_project, flat_target


def write_mutmut_config(mutation_project: Path, target_rel: Path):
    runner = "env PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS= python -m pytest -c /dev/null -q --disable-warnings --import-mode=importlib tests/test_gpt_iaedu.py"

    pyproject = mutation_project / "pyproject.toml"
    pyproject.write_text(
        "\n".join(
            [
                "[tool.mutmut]",
                f'paths_to_mutate = ["{target_rel.as_posix()}"]',
                'tests_dir = ["tests"]',
                f'runner = "{runner}"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    setup_cfg = mutation_project / "setup.cfg"
    setup_cfg.write_text(
        "\n".join(
            [
                "[mutmut]",
                f"paths_to_mutate={target_rel.as_posix()}",
                "tests_dir=tests",
                f"runner={runner}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_contextsafe_sitecustomize(mutation_project: Path):
    sitecustomize = mutation_project / "sitecustomize.py"
    sitecustomize.write_text(
        """# Auto-generated BugsInPy mutmut multiprocessing context patch.
# This file is created inside the temporary mutation_project only.
# It does not modify the generated tests or the SUT source tree.

import multiprocessing as _mp

_orig_set_start_method = _mp.set_start_method

def _safe_set_start_method(method=None, force=False):
    try:
        return _orig_set_start_method(method, force=force)
    except RuntimeError as e:
        msg = str(e)
        if "context has already been set" in msg:
            current = _mp.get_start_method(allow_none=True)
            if current == method or method == "fork":
                return None
        raise

_mp.set_start_method = _safe_set_start_method
""",
        encoding="utf-8",
    )


def run_cmd(cmd, cwd: Path, env: dict, timeout_s: int):
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        cp = subprocess.CompletedProcess(cmd, 124)
        cp.stdout = e.stdout or ""
        cp.stderr = e.stderr or ""
        return cp


def parse_results(text: str):
    counts = {
        "killed": 0,
        "survived": 0,
        "timeout": 0,
        "suspicious": 0,
        "skipped": 0,
        "not_checked": 0,
        "no_tests": 0,
        "total": 0,
        "score_pct": None,
        "parse_source": "mutmut_results_lines",
    }

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue

        status = stripped.rsplit(":", 1)[-1].strip().lower()
        counts["total"] += 1

        if status == "killed":
            counts["killed"] += 1
        elif status == "survived":
            counts["survived"] += 1
        elif status == "timeout":
            counts["timeout"] += 1
        elif status == "suspicious":
            counts["suspicious"] += 1
        elif status == "skipped":
            counts["skipped"] += 1
        elif status == "no tests":
            counts["no_tests"] += 1
        elif status == "not checked":
            counts["not_checked"] += 1

    denominator = counts["killed"] + counts["survived"] + counts["timeout"] + counts["suspicious"]

    if denominator > 0:
        counts["score_pct"] = counts["killed"] / denominator * 100.0

    return counts


def parse_mutmut_stdout_summary(text: str):
    """Fallback parser for mutmut 3.x progress summary lines.

    Example final line:
    3/3  🎉 3 🫥 0  ⏰ 0  🤔 0  🙁 0  🔇 0
    """
    counts = {
        "killed": 0,
        "survived": 0,
        "timeout": 0,
        "suspicious": 0,
        "skipped": 0,
        "not_checked": 0,
        "no_tests": 0,
        "total": 0,
        "score_pct": None,
        "parse_source": "mutmut_stdout_summary",
    }

    candidate = None
    for line in text.splitlines():
        if "/" in line and "🎉" in line:
            m = re.search(
                r"(\d+)/(\d+).*?🎉\s*(\d+).*?🫥\s*(\d+).*?⏰\s*(\d+).*?🤔\s*(\d+).*?🙁\s*(\d+).*?🔇\s*(\d+)",
                line,
            )
            if m:
                candidate = m

    if not candidate:
        return counts

    done, total, killed, unknown, timeout, suspicious, survived, skipped = map(int, candidate.groups())

    counts["total"] = total
    counts["killed"] = killed
    counts["survived"] = survived
    counts["timeout"] = timeout
    counts["suspicious"] = suspicious
    counts["skipped"] = skipped
    counts["not_checked"] = unknown

    denominator = killed + survived + timeout + suspicious
    if denominator > 0:
        counts["score_pct"] = killed / denominator * 100.0

    counts["done"] = done
    return counts


def main() -> int:
    ns = parse_args()

    run_dir = Path(ns.run_dir).resolve()
    metrics_dir = run_dir / "metrics"
    logs_dir = run_dir / "logs"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    status = read_json(metrics_dir / "status.json")

    target_module = status.get("target_module")
    if not target_module:
        update_status(
            run_dir,
            status="mutation_missing_target_module",
            mutation_available=False,
            mutation_score_pct=None,
        )
        print("status=mutation_missing_target_module")
        return 0

    work_sut_dir = Path(status.get("work_sut_dir") or run_dir / "work" / "sut").resolve()
    if not work_sut_dir.exists():
        update_status(
            run_dir,
            status="mutation_missing_work_sut_dir",
            mutation_available=False,
            mutation_score_pct=None,
        )
        print("status=mutation_missing_work_sut_dir")
        return 0

    try:
        resolved = resolve_target(run_dir, work_sut_dir, target_module)
        mutation_project, flat_target = build_mutation_project(run_dir, work_sut_dir, resolved)
        prepare_tests(run_dir, mutation_project, target_module)
        write_mutmut_config(mutation_project, resolved["target_rel"])
        write_contextsafe_sitecustomize(mutation_project)
    except Exception as e:
        update_status(
            run_dir,
            status="mutation_prepare_fail",
            mutation_available=False,
            mutation_score_pct=None,
            mutation_error=repr(e),
        )
        print("status=mutation_prepare_fail")
        print(repr(e))
        return 0

    update_status(
        run_dir,
        mutation_project_dir=str(mutation_project),
        mutation_target_relpath=str(resolved["target_rel"]),
        mutation_flat_target=str(flat_target),
        mutation_import_root=str(resolved["chosen_import_root"]),
    )

    if not flat_target.exists():
        update_status(
            run_dir,
            status="mutation_flat_target_missing",
            mutation_available=False,
            mutation_score_pct=None,
        )
        print("status=mutation_flat_target_missing")
        print(f"target not found in flat project: {flat_target}")
        return 0

    repo = Path.cwd().resolve()
    root_repo = repo.parent.resolve()
    py_overrides = root_repo / "_py_overrides"

    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTEST_ADDOPTS"] = ""
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("MUTANT_UNDER_TEST", "")

    pythonpath_parts = []
    if py_overrides.exists():
        pythonpath_parts.append(str(py_overrides))
    pythonpath_parts.append(str(mutation_project))
    pythonpath_parts.append(".")

    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])

    env["PYTHONPATH"] = ":".join(pythonpath_parts)

    update_status(run_dir, mutation_runner_pythonpath=env["PYTHONPATH"])

    print("[A] Checking mutmut availability...")
    avail = run_cmd(
        [sys.executable, "-m", "mutmut", "--version"],
        cwd=mutation_project,
        env=env,
        timeout_s=30,
    )
    (logs_dir / "mutmut.version.stdout.log").write_text(avail.stdout or "", encoding="utf-8")
    (logs_dir / "mutmut.version.stderr.log").write_text(avail.stderr or "", encoding="utf-8")

    print("[B] Running mutmut in flat mutation_project...")
    run = run_cmd(
        [sys.executable, "-m", "mutmut", "run"],
        cwd=mutation_project,
        env=env,
        timeout_s=ns.mutation_timeout_s,
    )

    (logs_dir / "mutmut.stdout.log").write_text(run.stdout or "", encoding="utf-8")
    (logs_dir / "mutmut.stderr.log").write_text(run.stderr or "", encoding="utf-8")

    print("[C] Running mutmut results...")
    results = run_cmd(
        [sys.executable, "-m", "mutmut", "results"],
        cwd=mutation_project,
        env=env,
        timeout_s=60,
    )

    (logs_dir / "mutmut_results.stdout.log").write_text(results.stdout or "", encoding="utf-8")
    (logs_dir / "mutmut_results.stderr.log").write_text(results.stderr or "", encoding="utf-8")
    (metrics_dir / "mutation_results.txt").write_text(results.stdout or "", encoding="utf-8")

    counts = parse_results(results.stdout or "")
    if counts.get("total", 0) == 0 and (run.stdout or ""):
        stdout_counts = parse_mutmut_stdout_summary(run.stdout or "")
        if stdout_counts.get("total", 0) > 0:
            counts = stdout_counts
    write_json(metrics_dir / "mutmut_counts.json", counts)

    if counts["score_pct"] is not None:
        final_status = "ok"
        mutation_available = True
        mutation_score = counts["score_pct"]
    elif counts["total"] > 0:
        final_status = "mutation_no_checked_mutants"
        mutation_available = False
        mutation_score = None
    elif run.returncode == 124:
        final_status = "mutation_timeout"
        mutation_available = False
        mutation_score = None
    else:
        final_status = "mutation_results_empty"
        mutation_available = False
        mutation_score = None

    update_status(
        run_dir,
        status=final_status,
        mutation_available=mutation_available,
        mutation_score_pct=mutation_score,
        mutmut_exit_code=run.returncode,
        mutmut_results_exit_code=results.returncode,
        mutmut_counts=counts,
        mutation_project_dir=str(mutation_project),
        mutation_target_relpath=str(resolved["target_rel"]),
        mutation_flat_target=str(flat_target),
        mutation_import_root=str(resolved["chosen_import_root"]),
        mutation_runner_pythonpath=env["PYTHONPATH"],
    )

    print(f"status={final_status}")
    print(f"mutmut_exit_code={run.returncode}")
    print(f"mutmut_results_exit_code={results.returncode}")
    print(f"mutation_available={mutation_available}")
    print(f"mutation_score_pct={mutation_score}")
    print(f"counts={json.dumps(counts, sort_keys=True)}")
    print(f"mutation_project={mutation_project}")
    print(f"target_rel={resolved['target_rel']}")
    print(f"flat_target={flat_target}")
    print(f"chosen_import_root={resolved['chosen_import_root']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
