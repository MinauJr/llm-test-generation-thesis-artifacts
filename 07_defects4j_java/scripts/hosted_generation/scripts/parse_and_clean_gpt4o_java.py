#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

def remove_ansi_and_control_chars(text: str) -> tuple[str, dict]:
    before = len(text)

    text = ANSI_RE.sub("", text)

    # Keep normal whitespace, remove other control chars that break javac.
    cleaned_chars = []
    removed_control = 0
    for ch in text:
        o = ord(ch)
        if ch in "\n\r\t":
            cleaned_chars.append(ch)
        elif o < 32 or o == 127:
            removed_control += 1
        else:
            cleaned_chars.append(ch)

    out = "".join(cleaned_chars)
    return out, {
        "chars_before_control_cleanup": before,
        "chars_after_control_cleanup": len(out),
        "removed_control_chars": removed_control,
    }

def extract_best_java_block(text: str) -> tuple[str, dict]:
    meta = {
        "fenced_blocks_found": 0,
        "used_fenced_block": False,
        "cut_prefix_before_java": False,
        "cut_suffix_after_balanced_class": False,
    }

    blocks = re.findall(
        r"```(?:java|Java|JAVA)?\s*(.*?)```",
        text,
        flags=re.DOTALL,
    )

    meta["fenced_blocks_found"] = len(blocks)

    if blocks:
        def score(block: str) -> tuple[int, int]:
            s = 0
            if "@Test" in block or "org.junit.Test" in block:
                s += 1000
            if "public class " in block:
                s += 500
            if "class " in block:
                s += 200
            if "package " in block:
                s += 100
            return (s, len(block))

        text = max(blocks, key=score)
        meta["used_fenced_block"] = True

    text = text.strip()

    # Remove prose before code when no fenced block was selected.
    first_candidates = []
    for patt in [
        r"(?m)^\s*package\s+[\w.]+\s*;",
        r"(?m)^\s*import\s+",
        r"(?m)^\s*public\s+(?:abstract\s+|final\s+)?class\s+",
        r"(?m)^\s*(?:abstract\s+|final\s+)?class\s+",
    ]:
        m = re.search(patt, text)
        if m:
            first_candidates.append(m.start())

    if first_candidates:
        first = min(first_candidates)
        if first > 0:
            text = text[first:]
            meta["cut_prefix_before_java"] = True

    # Try to cut trailing prose after the first public class body.
    # This is deliberately conservative: only cut if braces balance.
    class_match = re.search(r"\bpublic\s+(?:abstract\s+|final\s+)?class\s+\w+", text)
    if class_match:
        brace_start = text.find("{", class_match.end())
        if brace_start != -1:
            depth = 0
            end_idx = None
            for i in range(brace_start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end_idx = i + 1
                        break
            if end_idx is not None and end_idx < len(text):
                trailing = text[end_idx:].strip()
                if trailing:
                    text = text[:end_idx]
                    meta["cut_suffix_after_balanced_class"] = True

    return text.strip() + "\n", meta

def convert_simple_junit5_to_junit4(text: str) -> tuple[str, dict]:
    meta = {"junit5_simple_conversions": 0}

    replacements = [
        ("import org.junit.jupiter.api.Test;", "import org.junit.Test;"),
        ("import org.junit.jupiter.api.BeforeEach;", "import org.junit.Before;"),
        ("import org.junit.jupiter.api.AfterEach;", "import org.junit.After;"),
        ("import static org.junit.jupiter.api.Assertions.*;", "import static org.junit.Assert.*;"),
        ("org.junit.jupiter.api.Assertions.", "org.junit.Assert."),
        ("@BeforeEach", "@Before"),
        ("@AfterEach", "@After"),
    ]

    for old, new in replacements:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            meta["junit5_simple_conversions"] += n

    return text, meta

def detect_invalid_structure(text: str) -> list[str]:
    errors: list[str] = []
    stripped = text.strip()

    if not stripped:
        errors.append("empty_output")

    if "class " not in stripped:
        errors.append("no_class_keyword")

    if len(re.findall(r"\bpublic\s+(?:abstract\s+|final\s+)?class\s+", stripped)) > 1:
        errors.append("multiple_public_classes")

    if re.search(r"\bpublic\s+abstract\s+class\s+", stripped):
        errors.append("public_abstract_test_class")

    # Defects4J generated artefact is expected to be a JUnit test.
    # If no @Test annotation is present, compiling it as a test is usually meaningless.
    if "@Test" not in stripped and "org.junit.Test" not in stripped:
        errors.append("no_junit_test_annotation")

    return errors

def force_package(text: str, package_name: str) -> tuple[str, dict]:
    meta = {"package_forced": False, "package_inserted": False}
    package_line = f"package {package_name};"

    if re.search(r"(?m)^\s*package\s+[\w.]+\s*;", text):
        text2 = re.sub(r"(?m)^\s*package\s+[\w.]+\s*;", package_line, text, count=1)
        meta["package_forced"] = text2 != text
        text = text2
    else:
        text = package_line + "\n\n" + text
        meta["package_inserted"] = True

    return text, meta

def force_class_name_and_constructors(text: str, class_name: str) -> tuple[str, dict]:
    meta = {
        "original_public_class_name": None,
        "class_name_forced": False,
        "constructors_renamed": 0,
    }

    m = re.search(r"\bpublic\s+(abstract\s+|final\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)", text)
    if not m:
        return text, meta

    modifier = m.group(1) or ""
    old_name = m.group(2)
    meta["original_public_class_name"] = old_name

    # Make test class concrete even if the model emitted "public abstract class".
    new_decl = f"public {modifier}class {class_name}"
    if modifier.strip() == "abstract":
        new_decl = f"public class {class_name}"

    text2 = (
        text[:m.start()]
        + new_decl
        + text[m.end():]
    )
    meta["class_name_forced"] = text2 != text
    text = text2

    if old_name != class_name:
        # Rename constructor declarations at start of a line:
        # public OldName(...)
        # protected OldName(...)
        # private OldName(...)
        # OldName(...)
        patt = re.compile(
            rf"(?m)^([ \t]*(?:public|protected|private)?[ \t]*){re.escape(old_name)}([ \t]*\()"
        )
        text, n = patt.subn(rf"\1{class_name}\2", text)
        meta["constructors_renamed"] = n

    return text, meta

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--clean", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--package", required=True)
    ap.add_argument("--class-name", required=True)
    args = ap.parse_args()

    raw = Path(args.raw).read_text(encoding="utf-8", errors="replace")

    cleaned, control_meta = remove_ansi_and_control_chars(raw)
    cleaned, extract_meta = extract_best_java_block(cleaned)
    cleaned, junit_meta = convert_simple_junit5_to_junit4(cleaned)

    errors_before_forcing = detect_invalid_structure(cleaned)

    package_meta = {}
    class_meta = {}

    if not errors_before_forcing:
        cleaned, package_meta = force_package(cleaned, args.package)
        cleaned, class_meta = force_class_name_and_constructors(cleaned, args.class_name)

    errors_after_forcing = detect_invalid_structure(cleaned)

    Path(args.clean).write_text(cleaned, encoding="utf-8")

    Path(args.meta).write_text(json.dumps({
        "raw_chars": len(raw),
        "clean_chars": len(cleaned),
        "structural_errors": errors_after_forcing,
        "structural_errors_before_forcing": errors_before_forcing,
        "package": args.package,
        "class_name": args.class_name,
        "control_cleanup": control_meta,
        "extraction": extract_meta,
        "junit_conversion": junit_meta,
        "package_transform": package_meta,
        "class_transform": class_meta,
    }, indent=2, sort_keys=True), encoding="utf-8")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
