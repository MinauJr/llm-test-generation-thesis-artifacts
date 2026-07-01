#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
from pathlib import Path

def read_first_line(p: Path) -> str:
    txt = p.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    if not txt:
        raise RuntimeError(f"empty file: {p}")
    return txt[0].strip()

def build_target_path(src_root: Path, target_class: str) -> Path:
    rel = Path(*target_class.split("."))
    return src_root / f"{rel}.java"

def extract_signatures(java_text: str) -> list[str]:
    out = []
    for line in java_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("package ") or s.startswith("import "):
            out.append(s)
            continue
        if re.search(r"\b(class|interface|enum)\b", s) and ("public " in s or "protected " in s or "abstract " in s or "final " in s):
            out.append(s)
            continue
        if "(" in s and ")" in s and ("public " in s or "protected " in s):
            out.append(s)
            continue
    return out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sut-root", required=True)
    ap.add_argument("--dir-src-file", required=True)
    ap.add_argument("--target-class", required=True)
    ap.add_argument("--out-source", required=True)
    ap.add_argument("--out-related", required=True)
    ap.add_argument("--max-source-lines", type=int, default=1200)
    ap.add_argument("--max-related-files", type=int, default=3)
    ap.add_argument("--max-related-lines", type=int, default=250)
    args = ap.parse_args()

    sut_root = Path(args.sut_root).resolve()
    dir_src_rel = read_first_line(Path(args.dir_src_file))
    src_root = (sut_root / dir_src_rel).resolve()

    if not src_root.exists():
        raise RuntimeError(f"src root not found: {src_root}")

    target_path = build_target_path(src_root, args.target_class)
    if not target_path.exists():
        raise RuntimeError(f"target source not found: {target_path}")

    target_text = target_path.read_text(encoding="utf-8", errors="replace")
    target_lines = target_text.splitlines()
    target_trimmed = "\n".join(target_lines[:args.max_source_lines])

    target_pkg = ".".join(args.target_class.split(".")[:-1])
    package_dir = target_path.parent

    related_chunks = []
    count = 0
    for cand in sorted(package_dir.glob("*.java")):
        if cand == target_path:
            continue
        try:
            txt = cand.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        sigs = extract_signatures(txt)
        if not sigs:
            continue
        block = [f"// FILE: {cand.name}"]
        block.extend(sigs[:args.max_related_lines])
        related_chunks.append("\n".join(block))
        count += 1
        if count >= args.max_related_files:
            break

    related_text = f"// TARGET PACKAGE: {target_pkg}\n\n"
    if related_chunks:
        related_text += "\n\n".join(related_chunks)
    else:
        related_text += "// No extra related package context extracted."

    Path(args.out_source).write_text(target_trimmed, encoding="utf-8")
    Path(args.out_related).write_text(related_text, encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
