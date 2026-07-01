#!/usr/bin/env python3
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

DETECTED = {
    "KILLED",
    "TIMED_OUT",
    "MEMORY_ERROR",
    "NON_VIABLE",
    "RUN_ERROR",
}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--score-out", required=True)
    args = ap.parse_args()

    xml_path = Path(args.xml)
    if not xml_path.exists():
        raise SystemExit(f"pit xml not found: {xml_path}")

    root = ET.parse(xml_path).getroot()
    muts = root.findall("mutation")

    total = len(muts)
    detected = 0
    survived = 0

    for m in muts:
        status = (m.attrib.get("status") or "").strip().upper()
        if status in DETECTED:
            detected += 1
        elif status == "SURVIVED":
            survived += 1

    score = 0.0 if total == 0 else round((detected / total) * 100.0, 6)

    Path(args.score_out).write_text(f"{score}\n", encoding="utf-8")
    print(f"TOTAL={total}")
    print(f"DETECTED={detected}")
    print(f"SURVIVED={survived}")
    print(f"SCORE={score}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
