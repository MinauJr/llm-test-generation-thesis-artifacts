#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

def load(p: str) -> str:
    return Path(p).read_text(encoding="utf-8", errors="replace")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--test-package", required=True)
    ap.add_argument("--test-class-name", required=True)
    ap.add_argument("--target-class", required=True)
    ap.add_argument("--sut-id", required=True)
    ap.add_argument("--target-source-file", required=True)
    ap.add_argument("--related-context-file", required=True)
    args = ap.parse_args()

    text = load(args.template)
    text = text.replace("{{TEST_PACKAGE}}", args.test_package)
    text = text.replace("{{TEST_CLASS_NAME}}", args.test_class_name)
    text = text.replace("{{TARGET_CLASS}}", args.target_class)
    text = text.replace("{{SUT_ID}}", args.sut_id)
    text = text.replace("{{TARGET_CLASS_SOURCE}}", load(args.target_source_file))
    text = text.replace("{{RELATED_CONTEXT}}", load(args.related_context_file))

    Path(args.out).write_text(text, encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
