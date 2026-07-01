#!/usr/bin/env python3
import argparse
import ast
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--test-file", required=True)
parser.add_argument("--out-json", required=True)
args = parser.parse_args()

p = Path(args.test_file)
out = Path(args.out_json)
out.parent.mkdir(parents=True, exist_ok=True)

def decorator_name(d):
    if isinstance(d, ast.Name):
        return d.id
    if isinstance(d, ast.Attribute):
        base = decorator_name(d.value)
        return f"{base}.{d.attr}" if base else d.attr
    if isinstance(d, ast.Call):
        return decorator_name(d.func)
    return ""

def is_skip_decorator(d):
    name = decorator_name(d)
    return name in {
        "pytest.mark.skip",
        "pytest.mark.skipif",
        "mark.skip",
        "mark.skipif",
        "skip",
        "skipif",
    }

data = {
    "test_file": str(p),
    "top_level_test_functions": 0,
    "top_level_skipped_test_functions": 0,
    "effective_test_functions": 0,
    "all_top_level_tests_skipped": False,
    "error": None,
}

try:
    src = p.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src, filename=str(p))

    tests = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]

    skipped = [
        node for node in tests
        if any(is_skip_decorator(d) for d in node.decorator_list)
    ]

    data["top_level_test_functions"] = len(tests)
    data["top_level_skipped_test_functions"] = len(skipped)
    data["effective_test_functions"] = len(tests) - len(skipped)
    data["all_top_level_tests_skipped"] = bool(tests) and len(tests) == len(skipped)

except Exception as e:
    data["error"] = f"{type(e).__name__}: {e}"

out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(data, sort_keys=True))
