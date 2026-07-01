#!/usr/bin/env python3
import argparse
import importlib.util
import csv
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter, defaultdict


IGNORE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    ".tox",
    ".venv",
    "venv",
}


def safe_int_from_sut(s: str) -> int:
    try:
        return int(s.split("_", 1)[1])
    except Exception:
        return 10**12


def rep_int(rep_name: str) -> int:
    m = re.search(r"(\d+)$", rep_name)
    return int(m.group(1)) if m else 10**12


def copy_sut_tree(src: Path, dst: Path) -> None:
    def ignore(dir_path, names):
        return [n for n in names if n in IGNORE_DIRS or n.endswith(".pyc")]
    shutil.copytree(src, dst, ignore=ignore)


def run_cmd(cmd, cwd: Path, env: dict, timeout_s: int, stdout_path: Path, stderr_path: Path):
    start = time.time()
    timed_out = False
    exit_code = -1

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_s,
        )
        exit_code = proc.returncode
        stdout_path.write_text(proc.stdout or "", encoding="utf-8", errors="replace")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as e:
        timed_out = True
        exit_code = 124
        timeout_stdout = e.stdout or ""
        timeout_stderr = e.stderr or ""

        if isinstance(timeout_stdout, (bytes, bytearray)):
            timeout_stdout = timeout_stdout.decode("utf-8", errors="replace")
        if isinstance(timeout_stderr, (bytes, bytearray)):
            timeout_stderr = timeout_stderr.decode("utf-8", errors="replace")

        stdout_path.write_text(timeout_stdout, encoding="utf-8", errors="replace")
        stderr_path.write_text(timeout_stderr, encoding="utf-8", errors="replace")
    except Exception as e:
        exit_code = 125
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(f"{type(e).__name__}: {e}\n", encoding="utf-8", errors="replace")

    duration = time.time() - start
    return exit_code, timed_out, duration


def parse_failed_test_names(text: str):
    names = set()

    # Typical pytest lines:
    # FAILED tests/test_cluster_generated.py::test_x - AssertionError
    # FAILED tests/test_cluster_generated.py::TestSomething::test_x - ...
    for m in re.finditer(r"(?:FAILED|ERROR)\s+tests/test_cluster_generated\.py::(?:[A-Za-z_][A-Za-z0-9_]*::)?(test_[A-Za-z0-9_]+)", text):
        names.add(m.group(1))

    # Short traceback lines can also include:
    # tests/test_cluster_generated.py::test_x
    for m in re.finditer(r"tests/test_cluster_generated\.py::(?:[A-Za-z_][A-Za-z0-9_]*::)?(test_[A-Za-z0-9_]+)", text):
        names.add(m.group(1))

    return sorted(names)


def ensure_pytest_import(lines):
    if any(re.match(r"\s*import\s+pytest\b", line) or re.match(r"\s*from\s+pytest\s+import\b", line) for line in lines):
        return lines

    insert_at = 0
    # skip shebang/encoding/comments/blank lines
    while insert_at < len(lines):
        stripped = lines[insert_at].strip()
        if stripped == "" or stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            insert_at += 1
        else:
            break

    return lines[:insert_at] + ["import pytest\n"] + lines[insert_at:]


def sanitize_tests(raw_test: Path, sanitized_test: Path, failing_names):
    original = raw_test.read_text(encoding="utf-8", errors="replace").splitlines(True)
    if not failing_names:
        sanitized_test.write_text("".join(original), encoding="utf-8")
        return 0

    failing = set(failing_names)
    lines = ensure_pytest_import(original)
    out = []
    inserted = 0

    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)def\s+(test_[A-Za-z0-9_]+)\s*\(", line)
        if m and m.group(2) in failing:
            indent = m.group(1)
            prev = "".join(out[-3:])
            if "@pytest.mark.skip" not in prev:
                out.append(f'{indent}@pytest.mark.skip(reason="auto: failing generated cluster test")\n')
                inserted += 1
        out.append(line)

    sanitized_test.write_text("".join(out), encoding="utf-8")
    return inserted


def parse_coverage_xml(xml_path: Path):
    if not xml_path.exists():
        return None, None

    try:
        root = ET.parse(xml_path).getroot()
        line_rate = float(root.attrib.get("line-rate", "0")) * 100.0
        branch_rate = float(root.attrib.get("branch-rate", "0")) * 100.0
        return line_rate, branch_rate
    except Exception:
        return None, None


def parse_mutmut_results(text: str):
    lower = text.lower()

    def find_count(name):
        patterns = [
            rf"(\d+)\s+{re.escape(name)}",
            rf"{re.escape(name)}\s*[:=]\s*(\d+)",
        ]
        for pat in patterns:
            m = re.search(pat, lower)
            if m:
                return int(m.group(1))
        return 0

    killed = find_count("killed")
    survived = find_count("survived")
    timeout = find_count("timeout")
    suspicious = find_count("suspicious")
    skipped = find_count("skipped")

    denom = killed + survived + timeout + suspicious
    score = (100.0 * killed / denom) if denom > 0 else None

    return {
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "suspicious": suspicious,
        "skipped": skipped,
        "score_pct": score,
        "denominator": denom,
    }



def create_patched_mutmut_override(base_dir: Path) -> Path:
    """
    Create a local patched copy of the installed mutmut package.

    Reason:
    Some mutmut versions call multiprocessing.set_start_method('fork')
    unconditionally from mutmut.__main__.py. During mutmut execution, the
    generated mutant imports mutmut.__main__.record_trampoline_hit, which can
    re-import __main__.py after multiprocessing has already been configured,
    causing:

        RuntimeError: context has already been set

    This local override keeps the installed mutmut code unchanged and patches
    only the temporary evaluation workspace.
    """
    spec = importlib.util.find_spec("mutmut")
    if spec is None or spec.submodule_search_locations is None:
        raise RuntimeError("Could not locate installed mutmut package")

    src_pkg = Path(list(spec.submodule_search_locations)[0]).resolve()
    override_root = base_dir / "_py_overrides"
    dst_pkg = override_root / "mutmut"

    if dst_pkg.exists():
        shutil.rmtree(dst_pkg)

    shutil.copytree(src_pkg, dst_pkg)

    main_py = dst_pkg / "__main__.py"
    if not main_py.exists():
        raise RuntimeError(f"Could not find mutmut __main__.py in patched copy: {main_py}")

    txt = main_py.read_text(encoding="utf-8", errors="replace")

    old = "set_start_method('fork')"
    new = (
        "try:\n"
        "    set_start_method('fork')\n"
        "except RuntimeError as _mutmut_start_method_error:\n"
        "    if 'context has already been set' not in str(_mutmut_start_method_error):\n"
        "        raise"
    )

    if old not in txt and "_mutmut_start_method_error" not in txt:
        raise RuntimeError("Could not find set_start_method('fork') in mutmut __main__.py")

    if "_mutmut_start_method_error" not in txt:
        txt = txt.replace(old, new, 1)
        main_py.write_text(txt, encoding="utf-8")

    return override_root

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def evaluate_one(args, model_root: Path, sut_id: str, rep_dir: Path, out_root: Path):
    rep_tag = rep_dir.name
    sut_src = args.sut_root / sut_id
    generated_src = rep_dir / "generated_tests.py"
    cluster_status = load_json(rep_dir / "status.json")

    rel_out = Path(args.model_name) / sut_id / rep_tag
    out_dir = out_root / rel_out
    metrics_dir = out_dir / "metrics"
    logs_dir = out_dir / "logs"
    work_dir = out_dir / "work"
    sut_work = work_dir / "sut_project"
    tests_dir = work_dir / "tests"

    status_json = metrics_dir / "status.json"

    if status_json.exists() and not args.force:
        existing = load_json(status_json)
        existing["skipped_existing"] = True
        return existing

    if out_dir.exists() and args.force:
        shutil.rmtree(out_dir)

    metrics_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "dataset": "MBPP+",
        "phase": "cluster_generated_local_eval",
        "model": args.model_name,
        "sut_id": sut_id,
        "repeat_tag": rep_tag,
        "repeat": rep_int(rep_tag),
        "cluster_rep_dir": str(rep_dir),
        "sut_root": str(sut_src),
        "out_dir": str(out_dir),
        "cluster_generation_status": cluster_status.get("status"),
        "cluster_structure_ok": cluster_status.get("structure_ok"),
        "cluster_total_test_count": cluster_status.get("total_test_count"),
        "pytest_raw_exit_code": None,
        "pytest_final_exit_code": None,
        "sanitized": False,
        "sanitized_skipped_tests": 0,
        "coverage_exit_code": None,
        "line_coverage_pct": 0.0,
        "branch_coverage_pct": 0.0,
        "mutation_exit_code": None,
        "mutation_score_pct": 0.0,
        "mutation_killed": None,
        "mutation_survived": None,
        "mutation_timeout": None,
        "mutation_suspicious": None,
        "mutation_denominator": None,
        "status": "unknown",
        "note": "",
    }

    if not sut_src.is_dir():
        result["status"] = "missing_sut"
        result["note"] = f"Missing local SUT dir: {sut_src}"
        write_json(status_json, result)
        return result

    if not generated_src.is_file():
        result["status"] = "missing_generated_tests"
        result["note"] = f"Missing generated_tests.py: {generated_src}"
        write_json(status_json, result)
        return result

    # Strict-zero policy for cluster generation failures:
    # if the cluster generation phase did not produce status=ok, do not
    # evaluate the generated file locally. Keep pytest/coverage/mutation at 0.
    if cluster_status.get("status") != "ok":
        result["status"] = "cluster_generation_non_ok"
        result["cluster_generation_failure_status"] = cluster_status.get("status")
        result["note"] = (
            "Cluster generation status was non-ok; local pytest, coverage and "
            "mutation were skipped and strict-zero metrics were kept."
        )
        write_json(status_json, result)
        return result

    copy_sut_tree(sut_src, sut_work)
    tests_dir.mkdir(parents=True, exist_ok=True)

    raw_test = tests_dir / "test_cluster_generated.py"
    shutil.copy2(generated_src, raw_test)
    shutil.copy2(generated_src, out_dir / "generated_tests_original.py")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(sut_work) + os.pathsep + str(work_dir)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = args.disable_pytest_plugin_autoload

    pytest_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--import-mode=importlib",
        "tests",
    ]

    raw_out = logs_dir / "pytest_raw_stdout.txt"
    raw_err = logs_dir / "pytest_raw_stderr.txt"
    raw_exit, raw_timeout, raw_dur = run_cmd(
        pytest_cmd,
        cwd=work_dir,
        env=env,
        timeout_s=args.pytest_timeout_s,
        stdout_path=raw_out,
        stderr_path=raw_err,
    )

    result["pytest_raw_exit_code"] = raw_exit
    result["pytest_raw_timed_out"] = raw_timeout
    result["pytest_raw_duration_s"] = raw_dur

    final_test = raw_test

    if raw_exit != 0:
        combined = ""
        if raw_out.exists():
            combined += raw_out.read_text(encoding="utf-8", errors="replace")
        if raw_err.exists():
            combined += "\n" + raw_err.read_text(encoding="utf-8", errors="replace")

        failing_names = parse_failed_test_names(combined)
        (metrics_dir / "failing_test_names.txt").write_text("\n".join(failing_names) + ("\n" if failing_names else ""), encoding="utf-8")

        if failing_names:
            sanitized_test = tests_dir / "test_cluster_generated_sanitized.py"
            raw_test.rename(tests_dir / "_raw_test_cluster_generated.py.disabled")
            skipped = sanitize_tests(tests_dir / "_raw_test_cluster_generated.py.disabled", sanitized_test, failing_names)
            final_test = sanitized_test
            result["sanitized"] = True
            result["sanitized_skipped_tests"] = skipped
        else:
            result["note"] += "Raw pytest failed but no failing test names were parsed; "

    final_out = logs_dir / "pytest_final_stdout.txt"
    final_err = logs_dir / "pytest_final_stderr.txt"
    final_exit, final_timeout, final_dur = run_cmd(
        pytest_cmd,
        cwd=work_dir,
        env=env,
        timeout_s=args.pytest_timeout_s,
        stdout_path=final_out,
        stderr_path=final_err,
    )

    result["pytest_final_exit_code"] = final_exit
    result["pytest_final_timed_out"] = final_timeout
    result["pytest_final_duration_s"] = final_dur

    if final_exit != 0:
        result["status"] = "pytest_final_failed"
        result["note"] += "Final pytest failed; coverage and mutation set to strict zero."
        write_json(status_json, result)
        return result

    # Coverage
    cov_xml = metrics_dir / "coverage.xml"
    cov_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "pytest_cov",
        "-q",
        "--import-mode=importlib",
        "tests",
        "--cov=sut",
        "--cov-branch",
        f"--cov-report=xml:{cov_xml}",
        "--cov-report=term-missing",
    ]

    cov_out = logs_dir / "coverage_stdout.txt"
    cov_err = logs_dir / "coverage_stderr.txt"
    cov_exit, cov_timeout, cov_dur = run_cmd(
        cov_cmd,
        cwd=work_dir,
        env=env,
        timeout_s=args.pytest_timeout_s,
        stdout_path=cov_out,
        stderr_path=cov_err,
    )

    result["coverage_exit_code"] = cov_exit
    result["coverage_timed_out"] = cov_timeout
    result["coverage_duration_s"] = cov_dur

    line_pct, branch_pct = parse_coverage_xml(cov_xml)
    if cov_exit == 0 and line_pct is not None:
        result["line_coverage_pct"] = line_pct
        result["branch_coverage_pct"] = branch_pct if branch_pct is not None else 0.0
    else:
        result["note"] += "Coverage failed or coverage.xml unavailable; strict-zero coverage kept. "

    # Mutation
    if args.run_mutation:
        mut_dir = work_dir / "mutmut_work"
        mut_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(sut_work / "sut.py", mut_dir / "sut.py")
        shutil.copytree(tests_dir, mut_dir / "tests")

        (mut_dir / "setup.cfg").write_text(
            "[mutmut]\n"
            "paths_to_mutate=sut.py\n"
            "runner=python -m pytest -q --import-mode=importlib tests\n"
            "tests_dir=tests\n",
            encoding="utf-8",
        )

        override_root = create_patched_mutmut_override(mut_dir)

        mut_env = os.environ.copy()
        mut_env["PYTHONPATH"] = str(override_root) + os.pathsep + str(mut_dir)
        mut_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = args.disable_pytest_plugin_autoload

        mut_out = logs_dir / "mutmut_run_stdout.txt"
        mut_err = logs_dir / "mutmut_run_stderr.txt"
        mut_exit, mut_timeout, mut_dur = run_cmd(
            [sys.executable, "-m", "mutmut", "run"],
            cwd=mut_dir,
            env=mut_env,
            timeout_s=args.mutation_timeout_s,
            stdout_path=mut_out,
            stderr_path=mut_err,
        )

        result["mutation_exit_code"] = mut_exit
        result["mutation_timed_out"] = mut_timeout
        result["mutation_duration_s"] = mut_dur

        res_out = logs_dir / "mutmut_results_stdout.txt"
        res_err = logs_dir / "mutmut_results_stderr.txt"
        res_exit, res_timeout, res_dur = run_cmd(
            [sys.executable, "-m", "mutmut", "results"],
            cwd=mut_dir,
            env=mut_env,
            timeout_s=60,
            stdout_path=res_out,
            stderr_path=res_err,
        )

        result["mutation_results_exit_code"] = res_exit
        result["mutation_results_timed_out"] = res_timeout
        result["mutation_results_duration_s"] = res_dur

        mut_text = ""
        for p in [mut_out, mut_err, res_out, res_err]:
            if p.exists():
                mut_text += "\n" + p.read_text(encoding="utf-8", errors="replace")

        parsed = parse_mutmut_results(mut_text)
        result["mutation_killed"] = parsed["killed"]
        result["mutation_survived"] = parsed["survived"]
        result["mutation_timeout"] = parsed["timeout"]
        result["mutation_suspicious"] = parsed["suspicious"]
        result["mutation_skipped"] = parsed["skipped"]
        result["mutation_denominator"] = parsed["denominator"]

        if parsed["score_pct"] is not None:
            result["mutation_score_pct"] = parsed["score_pct"]
        else:
            result["note"] += "Could not parse mutmut score; strict-zero mutation kept. "
    else:
        result["note"] += "Mutation disabled for this evaluation run. "

    if result["coverage_exit_code"] == 0:
        if args.run_mutation:
            if result["mutation_score_pct"] is not None:
                result["status"] = "ok"
            else:
                result["status"] = "ok_no_mutation_score"
        else:
            result["status"] = "ok_no_mutation"
    else:
        result["status"] = "coverage_failed"

    write_json(status_json, result)
    return result


def discover_runs(generated_root: Path):
    runs = []
    for sut_dir in sorted([p for p in generated_root.iterdir() if p.is_dir() and p.name.startswith("Mbpp_")], key=lambda p: safe_int_from_sut(p.name)):
        for rep_dir in sorted([p for p in sut_dir.iterdir() if p.is_dir() and p.name.startswith("rep_")], key=lambda p: rep_int(p.name)):
            runs.append((sut_dir.name, rep_dir))
    return runs


def aggregate(out_root: Path, model_name: str):
    rows = []
    for p in sorted((out_root / model_name).rglob("metrics/status.json")):
        data = load_json(p)
        rows.append(data)

    index_tsv = out_root / "dataset_runs_index.tsv"
    with index_tsv.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "model", "sut_id", "repeat_tag", "status",
            "cluster_generation_status",
            "pytest_raw_exit_code", "pytest_final_exit_code",
            "sanitized", "sanitized_skipped_tests",
            "coverage_exit_code", "line_coverage_pct", "branch_coverage_pct",
            "mutation_exit_code", "mutation_score_pct",
            "mutation_killed", "mutation_survived", "mutation_timeout", "mutation_suspicious",
            "out_dir",
        ]
        w = csv.DictWriter(f, fields, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})

    def fnum(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    status_counts = Counter(r.get("status", "<missing>") for r in rows)
    cluster_status_counts = Counter(r.get("cluster_generation_status", "<missing>") for r in rows)

    line_vals = [fnum(r.get("line_coverage_pct")) for r in rows]
    branch_vals = [fnum(r.get("branch_coverage_pct")) for r in rows]
    mut_vals = [fnum(r.get("mutation_score_pct")) for r in rows]

    summary = {
        "model": model_name,
        "evaluated_repetitions": len(rows),
        "distinct_suts": len(set(r.get("sut_id") for r in rows)),
        "status_counts": dict(status_counts),
        "cluster_generation_status_counts": dict(cluster_status_counts),
        "sanitized_repetitions": sum(1 for r in rows if r.get("sanitized")),
        "pytest_final_failed": sum(1 for r in rows if r.get("pytest_final_exit_code") not in (0, "0")),
        "coverage_failed": sum(1 for r in rows if r.get("coverage_exit_code") not in (0, "0")),
        "line_coverage_mean_pct_strict0": statistics.mean(line_vals) if line_vals else 0.0,
        "branch_coverage_mean_pct_strict0": statistics.mean(branch_vals) if branch_vals else 0.0,
        "mutation_score_mean_pct_strict0": statistics.mean(mut_vals) if mut_vals else 0.0,
        "out_root": str(out_root),
        "dataset_runs_index": str(index_tsv),
    }

    write_json(out_root / "dataset_summary.json", summary)

    with (out_root / "dataset_summary.txt").open("w", encoding="utf-8") as f:
        f.write("===== MBPP+ CLUSTER-GENERATED LOCAL EVALUATION SUMMARY =====\n")
        for k, v in summary.items():
            f.write(f"{k}: {v}\n")

    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated-root", required=True, type=Path)
    ap.add_argument("--sut-root", required=True, type=Path)
    ap.add_argument("--out-root", required=True, type=Path)
    ap.add_argument("--model-name", required=True)
    ap.add_argument("--max-runs", type=int, default=0)
    ap.add_argument("--only-suts", default="")
    ap.add_argument("--run-mutation", type=int, default=1)
    ap.add_argument("--pytest-timeout-s", type=int, default=60)
    ap.add_argument("--mutation-timeout-s", type=int, default=120)
    ap.add_argument("--disable-pytest-plugin-autoload", default="1")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    args.generated_root = args.generated_root.expanduser().resolve()
    args.sut_root = args.sut_root.expanduser().resolve()
    args.out_root = args.out_root.expanduser().resolve()
    args.run_mutation = bool(args.run_mutation)

    if not args.generated_root.is_dir():
        raise SystemExit(f"generated root not found: {args.generated_root}")
    if not args.sut_root.is_dir():
        raise SystemExit(f"SUT root not found: {args.sut_root}")

    args.out_root.mkdir(parents=True, exist_ok=True)

    all_runs = discover_runs(args.generated_root)

    if args.only_suts.strip():
        wanted = {x.strip() for x in args.only_suts.split(",") if x.strip()}
        all_runs = [(sut, rep) for sut, rep in all_runs if sut in wanted]

    if args.max_runs > 0:
        all_runs = all_runs[:args.max_runs]

    master_log = args.out_root / "master_eval.log"

    with master_log.open("a", encoding="utf-8") as log:
        log.write("============================================================\n")
        log.write(f"START={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"generated_root={args.generated_root}\n")
        log.write(f"sut_root={args.sut_root}\n")
        log.write(f"out_root={args.out_root}\n")
        log.write(f"model={args.model_name}\n")
        log.write(f"runs={len(all_runs)}\n")
        log.write(f"run_mutation={args.run_mutation}\n")
        log.write("============================================================\n")

    print("===== MBPP+ CLUSTER-GENERATED LOCAL EVALUATION =====")
    print(f"generated_root={args.generated_root}")
    print(f"sut_root={args.sut_root}")
    print(f"out_root={args.out_root}")
    print(f"model={args.model_name}")
    print(f"runs={len(all_runs)}")
    print(f"run_mutation={args.run_mutation}")

    for i, (sut_id, rep_dir) in enumerate(all_runs, start=1):
        print(f"[{i}/{len(all_runs)}] {sut_id} {rep_dir.name}")
        res = evaluate_one(args, args.generated_root, sut_id, rep_dir, args.out_root)
        line = (
            f"[DONE] {sut_id} {rep_dir.name} "
            f"status={res.get('status')} "
            f"raw={res.get('pytest_raw_exit_code')} "
            f"final={res.get('pytest_final_exit_code')} "
            f"line={res.get('line_coverage_pct')} "
            f"branch={res.get('branch_coverage_pct')} "
            f"mut={res.get('mutation_score_pct')}\n"
        )
        with master_log.open("a", encoding="utf-8") as log:
            log.write(line)

    summary = aggregate(args.out_root, args.model_name)

    print("\n===== SUMMARY =====")
    for k, v in summary.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
