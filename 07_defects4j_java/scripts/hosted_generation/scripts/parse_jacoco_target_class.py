#!/usr/bin/env python3
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

def pct(covered: int, missed: int) -> float:
    total = covered + missed
    return 0.0 if total == 0 else round((covered / total) * 100.0, 6)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--target-class", required=True)
    ap.add_argument("--line-out", required=True)
    ap.add_argument("--branch-out", required=True)
    args = ap.parse_args()

    xml_path = Path(args.xml)
    if not xml_path.exists():
        raise SystemExit(f"jacoco xml not found: {xml_path}")

    target_internal = args.target_class.replace(".", "/")
    root = ET.parse(xml_path).getroot()

    found = None
    for pkg in root.findall("package"):
        for cls in pkg.findall("class"):
            if cls.attrib.get("name") == target_internal:
                found = cls
                break
        if found is not None:
            break

    if found is None:
        raise SystemExit(f"target class not found in jacoco xml: {args.target_class}")

    line_cov = 0.0
    branch_cov = 0.0

    for c in found.findall("counter"):
        typ = c.attrib.get("type")
        missed = int(c.attrib.get("missed", "0"))
        covered = int(c.attrib.get("covered", "0"))
        if typ == "LINE":
            line_cov = pct(covered, missed)
        elif typ == "BRANCH":
            branch_cov = pct(covered, missed)

    Path(args.line_out).write_text(f"{line_cov}\n", encoding="utf-8")
    Path(args.branch_out).write_text(f"{branch_cov}\n", encoding="utf-8")
    print(f"TARGET={args.target_class}")
    print(f"LINE={line_cov}")
    print(f"BRANCH={branch_cov}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
