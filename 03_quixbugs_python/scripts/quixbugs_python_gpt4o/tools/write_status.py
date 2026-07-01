#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

def convert(v: str):
    if v == "":
        return None
    if v.lower() == "null":
        return None
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    try:
        if "." not in v:
            return int(v)
    except Exception:
        pass
    try:
        return float(v)
    except Exception:
        return v

parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
parser.add_argument("--set", action="append", default=[])
args = parser.parse_args()

data = {}
for item in args.set:
    if "=" not in item:
        raise SystemExit(f"bad --set item: {item}")
    k, v = item.split("=", 1)
    data[k] = convert(v)

out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
