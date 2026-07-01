#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "projetos" / "SUTs" / "quixbugs"

suts = sorted(
    p for p in root.iterdir()
    if p.is_dir()
    and len(p.name) >= 11
    and p.name[:3].isdigit()
    and "_python_" in p.name
    and (p / "sut.py").is_file()
)

for p in suts:
    print(p.name)
