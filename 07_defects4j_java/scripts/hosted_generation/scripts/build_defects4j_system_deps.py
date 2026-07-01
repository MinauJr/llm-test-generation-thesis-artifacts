#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


def read_first_line(p: Path) -> str:
    txt = p.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    if not txt:
        raise RuntimeError(f"empty file: {p}")
    return txt[0].strip()


def jar_directory(src_dir: Path, out_jar: Path) -> None:
    out_jar.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_jar, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(src_dir).as_posix())


def should_keep_jar(p: Path) -> bool:
    name = p.name.lower()
    if not p.exists() or not p.is_file():
        return False
    if p.suffix.lower() != ".jar":
        return False
    if re.match(r"^junit([-.].*)?\.jar$", name):
        return False
    return True


def dep_xml(i: int, jar_path: Path) -> str:
    jar_s = escape(str(jar_path))
    return f"""    <dependency>
      <groupId>defects4j.cp</groupId>
      <artifactId>cpdep{i}</artifactId>
      <version>1.0</version>
      <scope>system</scope>
      <systemPath>{jar_s}</systemPath>
    </dependency>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sut-root", required=True)
    ap.add_argument("--dir-bin-file", required=True)
    ap.add_argument("--cp-compile-file", required=True)
    ap.add_argument("--out-xml", required=True)
    ap.add_argument("--out-jar", required=True)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    sut_root = Path(args.sut_root).resolve()
    dir_bin_rel = read_first_line(Path(args.dir_bin_file))
    bin_dir = (sut_root / dir_bin_rel).resolve()

    if not bin_dir.exists():
        raise RuntimeError(f"compiled classes dir not found: {bin_dir}")

    out_jar = Path(args.out_jar).resolve()
    jar_directory(bin_dir, out_jar)

    cp_text = Path(args.cp_compile_file).read_text(encoding="utf-8", errors="replace").strip()
    raw_entries = [x for x in cp_text.split(":") if x.strip()]

    jars = []
    seen = set()
    for entry in raw_entries:
        p = Path(entry).expanduser().resolve()
        key = str(p)
        if key in seen:
            continue
        if should_keep_jar(p):
            jars.append(p)
            seen.add(key)

    xml_blocks = []
    for i, jar in enumerate(jars, start=1):
        xml_blocks.append(dep_xml(i, jar))

    Path(args.out_xml).write_text("\n".join(xml_blocks) + "\n", encoding="utf-8")
    Path(args.manifest).write_text(json.dumps({
        "sut_root": str(sut_root),
        "compiled_classes_dir": str(bin_dir),
        "sut_classes_jar": str(out_jar),
        "compile_classpath_jars": [str(p) for p in jars],
    }, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
