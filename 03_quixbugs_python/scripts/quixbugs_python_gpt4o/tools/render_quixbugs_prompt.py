#!/usr/bin/env python3
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--sut-dir", required=True)
parser.add_argument("--template", required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args()

sut_dir = Path(args.sut_dir).expanduser().resolve()
template = Path(args.template).expanduser().resolve()
out = Path(args.out).expanduser().resolve()

sut_py = sut_dir / "sut.py"
if not sut_py.is_file():
    raise SystemExit(f"missing sut.py: {sut_py}")

source = sut_py.read_text(encoding="utf-8", errors="replace")
text = template.read_text(encoding="utf-8")

text = text.replace("__SUT_NAME__", sut_dir.name)
text = text.replace("__SUT_SOURCE__", source)

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(text, encoding="utf-8")
print(out)
