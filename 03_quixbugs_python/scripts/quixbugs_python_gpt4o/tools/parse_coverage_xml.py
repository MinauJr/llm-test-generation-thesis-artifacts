#!/usr/bin/env python3
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--xml", required=True)
parser.add_argument("--out-json", required=True)
args = parser.parse_args()

xml_path = Path(args.xml)
out = Path(args.out_json)
out.parent.mkdir(parents=True, exist_ok=True)

if not xml_path.is_file():
    data = {
        "line_coverage_pct": None,
        "branch_coverage_pct": None,
        "error": f"missing coverage xml: {xml_path}",
    }
else:
    root = ET.parse(xml_path).getroot()
    line_rate = root.attrib.get("line-rate")
    branch_rate = root.attrib.get("branch-rate")
    data = {
        "line_coverage_pct": round(float(line_rate) * 100.0, 4) if line_rate is not None else None,
        "branch_coverage_pct": round(float(branch_rate) * 100.0, 4) if branch_rate is not None else None,
        "error": None,
    }

out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(data, sort_keys=True))
