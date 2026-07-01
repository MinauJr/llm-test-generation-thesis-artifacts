#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


IMPORT_RE = re.compile(r'(?m)^\s*import\s+([A-Za-z_][\w.]*?)\s*;\s*$')
PACKAGE_RE = re.compile(r'(?m)^\s*package\s+([A-Za-z_][\w.]*)\s*;\s*$')
CLASS_RE = re.compile(r'\b(?:class|interface|enum)\s+([A-Za-z_]\w*)\b')
TOKEN_RE = re.compile(r'\b([A-Z][A-Za-z0-9_]*)\b')


def read_text(p: str) -> str:
    return Path(p).read_text(encoding="utf-8", errors="replace")


def collect_candidate_imports(*texts: str) -> dict[str, str]:
    by_simple: dict[str, set[str]] = {}
    for text in texts:
        for full in IMPORT_RE.findall(text):
            if full.startswith("static "):
                continue
            simple = full.split(".")[-1]
            by_simple.setdefault(simple, set()).add(full)

    resolved: dict[str, str] = {}
    for simple, fulls in by_simple.items():
        if len(fulls) == 1:
            resolved[simple] = next(iter(fulls))
    return resolved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--java-file", required=True)
    ap.add_argument("--target-source-file", required=True)
    ap.add_argument("--related-context-file", required=True)
    args = ap.parse_args()

    java_path = Path(args.java_file)
    java_text = java_path.read_text(encoding="utf-8", errors="replace")
    target_text = read_text(args.target_source_file)
    related_text = read_text(args.related_context_file)

    package_match = PACKAGE_RE.search(java_text)
    current_package = package_match.group(1) if package_match else ""

    existing_imports = set(IMPORT_RE.findall(java_text))
    existing_simple = {x.split(".")[-1] for x in existing_imports}
    declared_classes = set(CLASS_RE.findall(java_text))
    referenced_tokens = set(TOKEN_RE.findall(java_text))

    candidates = collect_candidate_imports(target_text, related_text)

    to_add: list[str] = []
    for simple in sorted(referenced_tokens):
        if simple in existing_simple:
            continue
        if simple in declared_classes:
            continue
        full = candidates.get(simple)
        if not full:
            continue
        full_pkg = ".".join(full.split(".")[:-1])
        if full_pkg == current_package:
            continue
        if full.startswith("java.lang."):
            continue
        to_add.append(full)

    if not to_add:
        print("NO_IMPORTS_ADDED")
        return 0

    lines = java_text.splitlines()
    package_idx = None
    last_import_idx = None
    for i, line in enumerate(lines):
        if package_idx is None and re.match(r'^\s*package\s+[A-Za-z_][\w.]*\s*;\s*$', line):
            package_idx = i
        if re.match(r'^\s*import\s+[A-Za-z_][\w.]*\s*;\s*$', line):
            last_import_idx = i

    insert_lines = [f"import {full};" for full in to_add]

    if last_import_idx is not None:
        insert_at = last_import_idx + 1
    elif package_idx is not None:
        insert_at = package_idx + 1
    else:
        insert_at = 0

    new_lines = lines[:insert_at] + insert_lines + lines[insert_at:]
    java_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    print("ADDED_IMPORTS")
    for full in to_add:
        print(full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
