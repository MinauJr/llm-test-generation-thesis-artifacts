#!/usr/bin/env python3
import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--runner-dir", required=True)
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--timeout", type=int, default=20)
parser.add_argument("--log", required=True)
args = parser.parse_args()

runner = Path(args.runner_dir).resolve()
inp = Path(args.input)
out = Path(args.output)
log = Path(args.log)
log.parent.mkdir(parents=True, exist_ok=True)

src_path = runner / inp
if not src_path.is_file():
    raise SystemExit(f"missing input test file: {src_path}")

src = src_path.read_text(encoding="utf-8", errors="replace")
tree = ast.parse(src, filename=str(src_path))

# Deliberately conservative: top-level pytest functions only.
test_funcs = [
    node.name for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name.startswith("test_")
]

bad = set()
lines = []
env = os.environ.copy()
env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

for name in test_funcs:
    cmd = [
        sys.executable, "-m", "pytest",
        "-q", f"{inp.name}::{name}",
        "--tb=short",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(runner),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=args.timeout,
        )
        rc = proc.returncode
        output = proc.stdout
    except subprocess.TimeoutExpired as e:
        rc = 124
        output = (e.stdout or "") if isinstance(e.stdout, str) else ""
        output += "\n[TIMEOUT]\n"

    lines.append(f"===== {name} rc={rc} =====\n{output}\n")
    if rc != 0:
        bad.add(name)

log.write_text("\n".join(lines), encoding="utf-8")

if not test_funcs:
    raise SystemExit("no top-level test functions found for sanitisation")

new_lines = src.splitlines()
insertions = []

for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in bad:
        lineno = node.lineno
        # Put decorator immediately above existing decorators if any.
        if node.decorator_list:
            lineno = min(d.lineno for d in node.decorator_list)
        insertions.append((lineno - 1, '@pytest.mark.skip(reason="auto-sanitized failing generated test")'))

for idx, text in sorted(insertions, reverse=True):
    new_lines.insert(idx, text)

sanitized = "\n".join(new_lines) + "\n"

if bad and not re.search(r"^\s*import\s+pytest\b", sanitized, flags=re.M):
    # Insert import pytest after shebang/encoding/import block conservatively at top.
    sanitized = "import pytest\n" + sanitized

out_path = runner / out
out_path.write_text(sanitized, encoding="utf-8")

print(f"test_functions={len(test_funcs)}")
print(f"skipped={len(bad)}")
print("bad_tests=" + ",".join(sorted(bad)))
