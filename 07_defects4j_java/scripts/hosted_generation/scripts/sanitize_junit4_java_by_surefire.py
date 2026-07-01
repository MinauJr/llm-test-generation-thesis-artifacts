#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

METHOD_RE = re.compile(r'\b(?:public|protected|private)\s+void\s+([A-Za-z_]\w*)\s*\(')

def unique_keep_order(items):
    out = []
    seen = set()
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def collect_failed_methods(surefire_dir: Path):
    failed = []
    for xml_file in sorted(surefire_dir.glob("TEST-*.xml")):
        try:
            root = ET.parse(xml_file).getroot()
        except Exception:
            continue
        for tc in root.findall(".//testcase"):
            if tc.find("failure") is not None or tc.find("error") is not None:
                name = (tc.attrib.get("name") or "").strip()
                if name:
                    failed.append(name)
    return unique_keep_order(failed)

def ensure_ignore_import(lines):
    if any(line.strip() == "import org.junit.Ignore;" for line in lines):
        return lines

    insert_at = None
    for i, line in enumerate(lines):
        if line.strip() == "import org.junit.Test;":
            insert_at = i + 1
            break

    if insert_at is None:
        for i, line in enumerate(lines):
            if line.strip().startswith("import "):
                insert_at = i
                break

    if insert_at is None:
        for i, line in enumerate(lines):
            if line.strip().startswith("package "):
                insert_at = i + 1
                break

    if insert_at is None:
        insert_at = 0

    lines.insert(insert_at, "import org.junit.Ignore;")
    return lines

def patch_java(java_path: Path, failed_methods):
    text = java_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    if failed_methods:
        lines = ensure_ignore_import(lines)

    failed_set = set(failed_methods)
    changed = False
    i = 0
    while i < len(lines):
        m = METHOD_RE.search(lines[i])
        if not m:
            i += 1
            continue

        method_name = m.group(1)
        if method_name not in failed_set:
            i += 1
            continue

        j = i - 1
        while j >= 0 and (lines[j].strip() == "" or lines[j].lstrip().startswith("@")):
            j -= 1
        insert_at = j + 1

        already = False
        for k in range(insert_at, i):
            if "@Ignore(" in lines[k] or lines[k].strip() == "@Ignore":
                already = True
                break

        if not already:
            indent = re.match(r"^(\s*)", lines[insert_at]).group(1)
            lines.insert(insert_at, f'{indent}@Ignore("Generated test failed during raw validation")')
            changed = True
            i += 1

        i += 1

    new_text = "\n".join(lines) + "\n"
    java_path.write_text(new_text, encoding="utf-8")
    return changed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--java-file", required=True)
    ap.add_argument("--surefire-dir", required=True)
    ap.add_argument("--skipped-out", required=True)
    args = ap.parse_args()

    java_file = Path(args.java_file)
    surefire_dir = Path(args.surefire_dir)
    skipped_out = Path(args.skipped_out)

    failed_methods = collect_failed_methods(surefire_dir)
    skipped_out.write_text("\n".join(failed_methods) + ("\n" if failed_methods else ""), encoding="utf-8")

    changed = patch_java(java_file, failed_methods)

    print("FAILED_METHODS")
    for m in failed_methods:
        print(m)
    print(f"PATCHED={1 if changed else 0}")

if __name__ == "__main__":
    raise SystemExit(main())
