#!/usr/bin/env python3
import ast
import csv
import json
import os
import pathlib
import random
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter

COV_ROOT = pathlib.Path(os.environ["COV_ROOT"])
PLAN = pathlib.Path(os.environ["PLAN"])
MUT_ROOT = pathlib.Path(os.environ["MUT_ROOT"])

SUMMARY_TSV = MUT_ROOT / "mutation_status.tsv"
SUMMARY_JSON = MUT_ROOT / "mutation_status.json"
NOTES = MUT_ROOT / "mutation_method_notes.txt"

PER_SUT_BUDGET_S = 180
PER_MUTANT_TIMEOUT_S = 25
MAX_MUTANTS_PER_SUT = 500

ORDER = [
    "PySnooper_2f",
    "PySnooper_3f",
    "ansible_14f",
    "ansible_17f",
    "black_2f",
    "black_5f",
    "cookiecutter_1f",
    "cookiecutter_3f",
    "httpie_1f",
    "httpie_2f",
    "matplotlib_16f",
    "matplotlib_9f",
    "thefuck_25f",
    "tornado_14f",
    "tornado_4f",
    "youtube-dl_35f",
]

FIELDNAMES = [
    "sut_id",
    "status",
    "generated_mutants",
    "executed_mutants",
    "killed",
    "survived",
    "timeout",
    "incompetent",
    "not_run_budget_or_cap",
    "mutation_score",
    "baseline_exit",
    "patch_files",
    "repo_copy",
    "notes",
]

def write_outputs(results):
    with SUMMARY_TSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter="\t")
        w.writeheader()
        w.writerows(results)

    SUMMARY_JSON.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

def copy_repo(src, dst):
    src = pathlib.Path(src)
    dst = pathlib.Path(dst)

    if dst.exists():
        shutil.rmtree(dst)

    def ignore(dirpath, names):
        blocked = {
            ".git",
            "env",
            ".tox",
            ".pytest_cache",
            ".mypy_cache",
            "__pycache__",
            ".mutmut-cache",
            "mutmut-cache",
            "mutants",
            "htmlcov",
            ".coverage",
            "mutmut.sqlite3",
        }
        return {n for n in names if n in blocked or n.endswith(".pyc")}

    shutil.copytree(
        src,
        dst,
        symlinks=False,
        ignore=ignore,
        ignore_dangling_symlinks=True,
    )

def run_cmd(cmd, cwd, env, out_path, err_path, timeout):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    err_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", errors="replace") as out, err_path.open("w", encoding="utf-8", errors="replace") as err:
        try:
            p = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=out,
                stderr=err,
                preexec_fn=os.setsid,
                text=True,
            )

            try:
                p.wait(timeout=timeout)
                return p.returncode
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                    time.sleep(2)
                    if p.poll() is None:
                        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                except Exception:
                    pass
                return 124

        except Exception as exc:
            err.write(f"\nRUN_CMD_EXCEPTION: {exc}\n")
            return 125

def make_httpie_compat_shim(sut):
    shim = MUT_ROOT / "shims" / sut / "py310_compat"
    shim.mkdir(parents=True, exist_ok=True)

    (shim / "sitecustomize.py").write_text(
        """
import sys
import types
import collections
import collections.abc

for name in [
    "Mapping", "MutableMapping", "Sequence", "MutableSequence",
    "Set", "MutableSet", "Iterable", "Iterator", "Callable"
]:
    if not hasattr(collections, name) and hasattr(collections.abc, name):
        setattr(collections, name, getattr(collections.abc, name))

if "UserDict" not in sys.modules:
    m = types.ModuleType("UserDict")
    m.DictMixin = collections.abc.MutableMapping
    sys.modules["UserDict"] = m
""".lstrip(),
        encoding="utf-8",
    )

    return shim

def build_env(sut, repo_copy):
    env = os.environ.copy()

    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    env["PIP_NO_INPUT"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["MPLBACKEND"] = "Agg"
    env["MPLCONFIGDIR"] = str(MUT_ROOT / "mplconfig" / sut)
    env["PYTHONWARNINGS"] = "ignore"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    pathlib.Path(env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

    paths = []

    if sut.startswith("httpie_"):
        paths.append(str(make_httpie_compat_shim(sut)))

    if sut.startswith("matplotlib_"):
        mat_shim = COV_ROOT / "metrics" / sut / "force_mplot3d_sitecustomize_v13"
        if mat_shim.exists():
            paths.append(str(mat_shim))
        paths.append(str(repo_copy / "lib"))

    for helper in COV_ROOT.rglob("_black_version.py"):
        paths.append(str(helper.parent))

    for p in [
        repo_copy / "build" / "lib",
        repo_copy,
        repo_copy / "tests",
        repo_copy / "test",
    ]:
        if p.exists():
            paths.append(str(p))

    clean = []
    seen = set()

    for p in paths:
        if p not in seen:
            clean.append(p)
            seen.add(p)

    env["PYTHONPATH"] = ":".join(clean) + ":" + env.get("PYTHONPATH", "")

    if sut == "httpie_2f":
        env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)

    return env

def assign_ids(tree):
    for i, node in enumerate(ast.walk(tree)):
        setattr(node, "_mut_id", i)

def candidate_kinds_for_node(node):
    kinds = []

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            kinds.append("boolop_and_to_or")
        elif isinstance(node.op, ast.Or):
            kinds.append("boolop_or_to_and")

    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Add):
            kinds.append("binop_add_to_sub")
        elif isinstance(node.op, ast.Sub):
            kinds.append("binop_sub_to_add")
        elif isinstance(node.op, ast.Mult):
            kinds.append("binop_mult_to_add")
        elif isinstance(node.op, ast.Div):
            kinds.append("binop_div_to_mult")
        elif isinstance(node.op, ast.FloorDiv):
            kinds.append("binop_floordiv_to_div")
        elif isinstance(node.op, ast.Mod):
            kinds.append("binop_mod_to_add")

    if isinstance(node, ast.Compare) and node.ops:
        op = node.ops[0]
        if isinstance(op, ast.Eq):
            kinds.append("cmp_eq_to_noteq")
        elif isinstance(op, ast.NotEq):
            kinds.append("cmp_noteq_to_eq")
        elif isinstance(op, ast.Lt):
            kinds.append("cmp_lt_to_lte")
        elif isinstance(op, ast.LtE):
            kinds.append("cmp_lte_to_lt")
        elif isinstance(op, ast.Gt):
            kinds.append("cmp_gt_to_gte")
        elif isinstance(op, ast.GtE):
            kinds.append("cmp_gte_to_gt")
        elif isinstance(op, ast.Is):
            kinds.append("cmp_is_to_isnot")
        elif isinstance(op, ast.IsNot):
            kinds.append("cmp_isnot_to_is")
        elif isinstance(op, ast.In):
            kinds.append("cmp_in_to_notin")
        elif isinstance(op, ast.NotIn):
            kinds.append("cmp_notin_to_in")

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            kinds.append("unary_not_remove")
        elif isinstance(node.op, ast.USub):
            kinds.append("unary_usub_to_uadd")

    if isinstance(node, ast.Constant):
        v = node.value
        if isinstance(v, bool):
            kinds.append("const_bool_flip")
        elif isinstance(v, int) and not isinstance(v, bool):
            kinds.append("const_int_plus_one")
            kinds.append("const_int_minus_one")
        elif isinstance(v, float):
            kinds.append("const_float_plus_one")
            kinds.append("const_float_minus_one")
        elif v is None:
            kinds.append("const_none_to_false")

    if isinstance(node, ast.If):
        kinds.append("if_test_negate")

    if isinstance(node, ast.While):
        kinds.append("while_test_negate")

    if isinstance(node, ast.Assert):
        kinds.append("assert_test_negate")

    return kinds

def collect_candidates(source_text, file_rel):
    try:
        tree = ast.parse(source_text, filename=str(file_rel), type_comments=True)
    except SyntaxError as exc:
        return [], f"parse_error: {exc}"

    assign_ids(tree)
    cands = []

    for node in ast.walk(tree):
        if not hasattr(node, "lineno"):
            continue

        for kind in candidate_kinds_for_node(node):
            cands.append({
                "mut_id": getattr(node, "_mut_id"),
                "kind": kind,
                "lineno": getattr(node, "lineno", -1),
                "col": getattr(node, "col_offset", -1),
                "file": str(file_rel),
            })

    cands.sort(key=lambda c: (c["file"], c["lineno"], c["col"], c["kind"], c["mut_id"]))
    return cands, ""

class ApplyMutation(ast.NodeTransformer):
    def __init__(self, target_id, kind):
        self.target_id = target_id
        self.kind = kind
        self.changed = False

    def _is_target(self, node):
        return getattr(node, "_mut_id", None) == self.target_id

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if self._is_target(node):
            if self.kind == "boolop_and_to_or" and isinstance(node.op, ast.And):
                node.op = ast.Or()
                self.changed = True
            elif self.kind == "boolop_or_to_and" and isinstance(node.op, ast.Or):
                node.op = ast.And()
                self.changed = True
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if self._is_target(node):
            mapping = {
                "binop_add_to_sub": (ast.Add, ast.Sub),
                "binop_sub_to_add": (ast.Sub, ast.Add),
                "binop_mult_to_add": (ast.Mult, ast.Add),
                "binop_div_to_mult": (ast.Div, ast.Mult),
                "binop_floordiv_to_div": (ast.FloorDiv, ast.Div),
                "binop_mod_to_add": (ast.Mod, ast.Add),
            }
            if self.kind in mapping:
                src, dst = mapping[self.kind]
                if isinstance(node.op, src):
                    node.op = dst()
                    self.changed = True
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        if self._is_target(node) and node.ops:
            mapping = {
                "cmp_eq_to_noteq": (ast.Eq, ast.NotEq),
                "cmp_noteq_to_eq": (ast.NotEq, ast.Eq),
                "cmp_lt_to_lte": (ast.Lt, ast.LtE),
                "cmp_lte_to_lt": (ast.LtE, ast.Lt),
                "cmp_gt_to_gte": (ast.Gt, ast.GtE),
                "cmp_gte_to_gt": (ast.GtE, ast.Gt),
                "cmp_is_to_isnot": (ast.Is, ast.IsNot),
                "cmp_isnot_to_is": (ast.IsNot, ast.Is),
                "cmp_in_to_notin": (ast.In, ast.NotIn),
                "cmp_notin_to_in": (ast.NotIn, ast.In),
            }
            if self.kind in mapping:
                src, dst = mapping[self.kind]
                if isinstance(node.ops[0], src):
                    node.ops[0] = dst()
                    self.changed = True
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if self._is_target(node):
            if self.kind == "unary_not_remove" and isinstance(node.op, ast.Not):
                self.changed = True
                return node.operand
            elif self.kind == "unary_usub_to_uadd" and isinstance(node.op, ast.USub):
                node.op = ast.UAdd()
                self.changed = True
        return node

    def visit_Constant(self, node):
        if self._is_target(node):
            v = node.value

            if self.kind == "const_bool_flip" and isinstance(v, bool):
                self.changed = True
                return ast.copy_location(ast.Constant(value=not v), node)

            if self.kind == "const_int_plus_one" and isinstance(v, int) and not isinstance(v, bool):
                self.changed = True
                return ast.copy_location(ast.Constant(value=v + 1), node)

            if self.kind == "const_int_minus_one" and isinstance(v, int) and not isinstance(v, bool):
                self.changed = True
                return ast.copy_location(ast.Constant(value=v - 1), node)

            if self.kind == "const_float_plus_one" and isinstance(v, float):
                self.changed = True
                return ast.copy_location(ast.Constant(value=v + 1.0), node)

            if self.kind == "const_float_minus_one" and isinstance(v, float):
                self.changed = True
                return ast.copy_location(ast.Constant(value=v - 1.0), node)

            if self.kind == "const_none_to_false" and v is None:
                self.changed = True
                return ast.copy_location(ast.Constant(value=False), node)

        return node

    def visit_If(self, node):
        self.generic_visit(node)
        if self._is_target(node) and self.kind == "if_test_negate":
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            self.changed = True
        return node

    def visit_While(self, node):
        self.generic_visit(node)
        if self._is_target(node) and self.kind == "while_test_negate":
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            self.changed = True
        return node

    def visit_Assert(self, node):
        self.generic_visit(node)
        if self._is_target(node) and self.kind == "assert_test_negate":
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            self.changed = True
        return node

def create_mutated_source(original_text, file_rel, cand):
    tree = ast.parse(original_text, filename=str(file_rel), type_comments=True)
    assign_ids(tree)

    mutator = ApplyMutation(cand["mut_id"], cand["kind"])
    tree = mutator.visit(tree)
    ast.fix_missing_locations(tree)

    if not mutator.changed:
        return None, "unchanged"

    try:
        mutated = ast.unparse(tree) + "\n"
        compile(mutated, str(file_rel), "exec")
    except Exception as exc:
        return None, f"incompetent_compile_or_unparse: {exc}"

    if mutated.strip() == original_text.strip():
        return None, "unchanged_text"

    return mutated, ""

def score(killed, survived, timeout):
    denom = killed + survived + timeout
    if denom <= 0:
        return ""
    return f"{100.0 * (killed + timeout) / denom:.6f}"

def main():
    print("===== BUGSINPY OFFICIAL DATASET CUSTOM EXACT MUTATION V8 =====", flush=True)
    print(f"date_start={time.strftime('%Y-%m-%dT%H:%M:%S%z')}", flush=True)
    print(f"COV_ROOT={COV_ROOT}", flush=True)
    print(f"PLAN={PLAN}", flush=True)
    print(f"MUT_ROOT={MUT_ROOT}", flush=True)
    print(f"PER_SUT_BUDGET_S={PER_SUT_BUDGET_S}", flush=True)
    print(f"PER_MUTANT_TIMEOUT_S={PER_MUTANT_TIMEOUT_S}", flush=True)
    print(f"MAX_MUTANTS_PER_SUT={MAX_MUTANTS_PER_SUT}", flush=True)
    print("", flush=True)

    NOTES.write_text(
        "\n".join([
            "BUGSINPY OFFICIAL DATASET TESTS — MUTATION V8",
            "Mutation is computed with a controlled AST mutant runner.",
            "Only patch_files from the validated V3 exact-runner plan are mutated.",
            "Each mutant is evaluated with the exact official dataset runner previously validated for that SUT.",
            "Timeout mutants are counted as killed for the mutation score numerator.",
            "Incompetent mutants are excluded from the mutation-score denominator.",
            f"Per-SUT budget: {PER_SUT_BUDGET_S}s.",
            f"Per-mutant timeout: {PER_MUTANT_TIMEOUT_S}s.",
            f"Max mutants per SUT: {MAX_MUTANTS_PER_SUT}.",
            "",
        ]),
        encoding="utf-8",
    )

    rows = list(csv.DictReader(PLAN.open(encoding="utf-8"), delimiter="\t"))
    by_sut = {r["sut_id"]: r for r in rows}
    rows = [by_sut[s] for s in ORDER if s in by_sut]

    results = []

    for idx, row in enumerate(rows, start=1):
        sut = row["sut_id"]
        src_repo = pathlib.Path(row["repo_dir"])
        repo_copy = MUT_ROOT / "workspaces" / sut / "repo"
        log_dir = MUT_ROOT / "logs" / sut
        log_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 100, flush=True)
        print(f"[{idx}/{len(rows)}] {sut}", flush=True)
        print("=" * 100, flush=True)
        print(f"source_repo={src_repo}", flush=True)
        print(f"repo_copy={repo_copy}", flush=True)
        print(f"patch_files={row['patch_files']}", flush=True)
        print(f"runner={row['runner']}", flush=True)

        try:
            copy_repo(src_repo, repo_copy)
        except Exception as exc:
            res = {
                "sut_id": sut,
                "status": "copy_fail",
                "generated_mutants": "0",
                "executed_mutants": "0",
                "killed": "0",
                "survived": "0",
                "timeout": "0",
                "incompetent": "0",
                "not_run_budget_or_cap": "0",
                "mutation_score": "",
                "baseline_exit": "",
                "patch_files": row["patch_files"],
                "repo_copy": str(repo_copy),
                "notes": str(exc),
            }
            results.append(res)
            write_outputs(results)
            continue

        env = build_env(sut, repo_copy)
        runner = shlex.split(row["runner"])

        baseline_exit = run_cmd(
            runner,
            repo_copy,
            env,
            log_dir / "baseline.stdout.log",
            log_dir / "baseline.stderr.log",
            timeout=180,
        )

        print(f"baseline_exit={baseline_exit}", flush=True)

        if baseline_exit != 0:
            res = {
                "sut_id": sut,
                "status": "baseline_fail_on_copy",
                "generated_mutants": "0",
                "executed_mutants": "0",
                "killed": "0",
                "survived": "0",
                "timeout": "0",
                "incompetent": "0",
                "not_run_budget_or_cap": "0",
                "mutation_score": "",
                "baseline_exit": str(baseline_exit),
                "patch_files": row["patch_files"],
                "repo_copy": str(repo_copy),
                "notes": "Exact runner failed before mutation.",
            }
            results.append(res)
            write_outputs(results)
            continue

        all_candidates = []
        originals = {}

        for file_rel_s in [p.strip() for p in row["patch_files"].split(",") if p.strip()]:
            file_rel = pathlib.Path(file_rel_s)
            file_path = repo_copy / file_rel

            if not file_path.exists():
                print(f"missing_patch_file={file_rel}", flush=True)
                continue

            text = file_path.read_text(encoding="utf-8", errors="replace")
            originals[str(file_rel)] = text

            cands, err = collect_candidates(text, file_rel)

            if err:
                print(f"candidate_error {file_rel}: {err}", flush=True)
                continue

            all_candidates.extend(cands)

        generated = len(all_candidates)

        # deterministic order, capped only after full candidate collection
        selected = all_candidates[:MAX_MUTANTS_PER_SUT]

        killed = 0
        survived = 0
        timeout_n = 0
        incompetent = 0
        executed = 0
        start = time.time()
        details_path = log_dir / "mutation_details.tsv"

        with details_path.open("w", encoding="utf-8", newline="") as df:
            dw = csv.DictWriter(
                df,
                fieldnames=[
                    "mutant_index",
                    "file",
                    "line",
                    "kind",
                    "exit_code",
                    "result",
                    "error",
                ],
                delimiter="\t",
            )
            dw.writeheader()

            for m_idx, cand in enumerate(selected, start=1):
                elapsed = time.time() - start

                if elapsed >= PER_SUT_BUDGET_S:
                    break

                file_rel = cand["file"]
                file_path = repo_copy / file_rel
                original_text = originals[file_rel]

                mutated_text, err = create_mutated_source(original_text, file_rel, cand)

                if mutated_text is None:
                    incompetent += 1
                    dw.writerow({
                        "mutant_index": m_idx,
                        "file": file_rel,
                        "line": cand["lineno"],
                        "kind": cand["kind"],
                        "exit_code": "",
                        "result": "incompetent",
                        "error": err,
                    })
                    continue

                file_path.write_text(mutated_text, encoding="utf-8")

                rc = run_cmd(
                    runner,
                    repo_copy,
                    env,
                    log_dir / "mutant_stdout" / f"mutant_{m_idx:05d}.stdout.log",
                    log_dir / "mutant_stderr" / f"mutant_{m_idx:05d}.stderr.log",
                    timeout=PER_MUTANT_TIMEOUT_S,
                )

                file_path.write_text(original_text, encoding="utf-8")

                executed += 1

                if rc == 0:
                    survived += 1
                    result = "survived"
                elif rc == 124:
                    timeout_n += 1
                    result = "timeout"
                else:
                    killed += 1
                    result = "killed"

                dw.writerow({
                    "mutant_index": m_idx,
                    "file": file_rel,
                    "line": cand["lineno"],
                    "kind": cand["kind"],
                    "exit_code": rc,
                    "result": result,
                    "error": "",
                })

                if m_idx % 25 == 0:
                    print(
                        f"{sut}: progress selected={m_idx}/{len(selected)} "
                        f"executed={executed} killed={killed} survived={survived} timeout={timeout_n} incompetent={incompetent}",
                        flush=True,
                    )

        # restore originals defensively
        for file_rel, text in originals.items():
            (repo_copy / file_rel).write_text(text, encoding="utf-8")

        not_run = max(0, generated - executed - incompetent)

        if generated == 0:
            status = "no_mutants"
        elif executed == 0:
            status = "no_executed_mutants"
        elif not_run > 0:
            status = "partial_budget_or_cap"
        else:
            status = "ok"

        mut_score = score(killed, survived, timeout_n)

        res = {
            "sut_id": sut,
            "status": status,
            "generated_mutants": str(generated),
            "executed_mutants": str(executed),
            "killed": str(killed),
            "survived": str(survived),
            "timeout": str(timeout_n),
            "incompetent": str(incompetent),
            "not_run_budget_or_cap": str(not_run),
            "mutation_score": mut_score,
            "baseline_exit": str(baseline_exit),
            "patch_files": row["patch_files"],
            "repo_copy": str(repo_copy),
            "notes": "",
        }

        print(
            f"RESULT {sut}: status={status} generated={generated} executed={executed} "
            f"killed={killed} survived={survived} timeout={timeout_n} incompetent={incompetent} "
            f"not_run={not_run} score={mut_score}",
            flush=True,
        )
        print("", flush=True)

        results.append(res)
        write_outputs(results)

    scores = [float(r["mutation_score"]) for r in results if r["mutation_score"]]
    status_counts = Counter(r["status"] for r in results)

    print("=" * 100, flush=True)
    print("FINAL V8 CUSTOM MUTATION SUMMARY", flush=True)
    print("=" * 100, flush=True)
    print(f"suts={len(results)}", flush=True)
    print(f"status_counts={dict(status_counts)}", flush=True)
    print(f"scores_available={len(scores)}", flush=True)

    if scores:
        print(f"mean_mutation_score={sum(scores)/len(scores):.6f}", flush=True)
    else:
        print("mean_mutation_score=NA", flush=True)

    print("", flush=True)
    print(f"{'SUT':<20}{'STATUS':<24}{'GEN':>8}{'EXEC':>8}{'KILL':>8}{'SURV':>8}{'TO':>8}{'MUT%':>12}", flush=True)
    print("-" * 104, flush=True)

    for r in results:
        print(
            f"{r['sut_id']:<20}"
            f"{r['status']:<24}"
            f"{r['generated_mutants']:>8}"
            f"{r['executed_mutants']:>8}"
            f"{r['killed']:>8}"
            f"{r['survived']:>8}"
            f"{r['timeout']:>8}"
            f"{r['mutation_score']:>12}",
            flush=True,
        )

    print("", flush=True)
    print(f"SUMMARY_TSV={SUMMARY_TSV}", flush=True)
    print(f"SUMMARY_JSON={SUMMARY_JSON}", flush=True)
    print(f"NOTES={NOTES}", flush=True)
    print(f"date_end={time.strftime('%Y-%m-%dT%H:%M:%S%z')}", flush=True)
    print("official_mutation_v8_status=completed", flush=True)

if __name__ == "__main__":
    main()
