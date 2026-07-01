#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

PROGRESS_RE = re.compile(
    r"(?P<done>\d+)/(?P<total>\d+)"
    r"\s+🎉\s*(?P<killed>\d+)"
    r"\s+🫥\s*(?P<no_tests>\d+)"
    r"\s+⏰\s*(?P<timeout>\d+)"
    r"\s+🤔\s*(?P<suspicious>\d+)"
    r"\s+🙁\s*(?P<survived>\d+)"
    r"\s+🔇\s*(?P<skipped>\d+)"
)

RESULT_STATUS_RE = re.compile(
    r":\s*(killed|survived|timeout|suspicious|skipped|not checked)\s*$",
    flags=re.IGNORECASE,
)


def clean_text(path: Path) -> str:
    if not path.is_file():
        return ""

    text = path.read_text(encoding="utf-8", errors="replace")
    text = ANSI_RE.sub("", text)
    return text.replace("\r", "\n")


def parse_progress(run_text: str) -> dict[str, int]:
    matches = []

    for line in run_text.splitlines():
        match = PROGRESS_RE.search(line)
        if match:
            matches.append(match)

    if not matches:
        raise RuntimeError(
            "Não foi possível encontrar a linha final de progresso do Mutmut."
        )

    match = matches[-1]

    return {
        key: int(value)
        for key, value in match.groupdict().items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-log", required=True)
    parser.add_argument("--results-log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    run_log = Path(args.run_log).resolve()
    results_log = Path(args.results_log).resolve()
    out = Path(args.out).resolve()

    run_text = clean_text(run_log)
    results_text = clean_text(results_log)

    progress = parse_progress(run_text)

    total = progress["total"]
    killed = progress["killed"]
    no_tests = progress["no_tests"]
    timeout = progress["timeout"]
    suspicious = progress["suspicious"]
    survived = progress["survived"]
    skipped = progress["skipped"]

    category_sum = (
        killed
        + no_tests
        + timeout
        + suspicious
        + survived
        + skipped
    )

    detected = killed + timeout

    mutation_score_pct = (
        100.0 * detected / total
        if total
        else None
    )

    killed_only_score_pct = (
        100.0 * killed / total
        if total
        else None
    )

    result_log_counts = Counter()

    for line in results_text.splitlines():
        match = RESULT_STATUS_RE.search(line.strip())
        if match:
            key = match.group(1).lower().replace(" ", "_")
            result_log_counts[key] += 1

    payload = {
        "parser": "parse_mutmut_v34.py",
        "run_log": str(run_log),
        "results_log": str(results_log),

        "mutants_progress_done": progress["done"],
        "mutants_total": total,

        "mutants_killed": killed,
        "mutants_timeout": timeout,
        "mutants_detected": detected,
        "mutants_survived": survived,
        "mutants_no_tests": no_tests,
        "mutants_suspicious": suspicious,
        "mutants_skipped": skipped,

        "category_sum": category_sum,
        "category_sum_matches_total": category_sum == total,
        "progress_complete": progress["done"] == total,

        "mutation_score_pct": mutation_score_pct,
        "killed_only_score_pct": killed_only_score_pct,

        "mutation_score_formula": (
            "(killed + timeout) / total_mutants"
        ),
        "timeout_policy": (
            "Timeout mutants are treated as detected/killed."
        ),

        "results_log_status_counts": dict(result_log_counts),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(out)


if __name__ == "__main__":
    main()
