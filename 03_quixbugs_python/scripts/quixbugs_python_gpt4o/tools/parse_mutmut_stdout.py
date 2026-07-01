#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

parser = argparse.ArgumentParser()
parser.add_argument("--stdout", required=True)
parser.add_argument("--out-json", required=True)
parser.add_argument("--stats-json", default="")
args = parser.parse_args()

STATUS_MAP = {
    "killed": "killed",
    "survived": "survived",
    "surviving": "survived",
    "timeout": "timeout",
    "timedout": "timeout",
    "suspicious": "suspicious",
    "skipped": "skipped",
    "ignored": "skipped",
}

def norm_status(value: Any):
    if not isinstance(value, str):
        return None
    s = value.strip().lower()
    s = s.replace("_", "").replace("-", "").replace(" ", "")
    return STATUS_MAP.get(s)

def count_statuses_from_json(obj: Any) -> Counter:
    counts = Counter()

    def walk(x: Any):
        if isinstance(x, dict):
            # Prefer explicit status-like fields and count each mutant dict once.
            for key in ("status", "state", "result", "outcome", "mutant_status"):
                if key in x:
                    st = norm_status(x.get(key))
                    if st:
                        counts[st] += 1
                        return

            # Some versions store counters directly.
            lowered = {str(k).lower(): v for k, v in x.items()}
            direct_keys = {
                "killed": "killed",
                "survived": "survived",
                "timeout": "timeout",
                "timeouts": "timeout",
                "suspicious": "suspicious",
                "skipped": "skipped",
            }
            used_direct = False
            for raw_key, canonical in direct_keys.items():
                if raw_key in lowered and isinstance(lowered[raw_key], int):
                    counts[canonical] += int(lowered[raw_key])
                    used_direct = True
            if used_direct:
                return

            for v in x.values():
                walk(v)

        elif isinstance(x, list):
            for v in x:
                walk(v)

        elif isinstance(x, str):
            st = norm_status(x)
            if st:
                counts[st] += 1

    walk(obj)
    return counts

def count_statuses_from_stdout(text: str) -> Counter:
    counts = Counter()

    # Word-based summaries.
    patterns = {
        "killed": [
            r"\bkilled\b\D+(\d+)",
            r"\bkilled mutants?\b\D+(\d+)",
        ],
        "survived": [
            r"\bsurvived\b\D+(\d+)",
            r"\bsurviving mutants?\b\D+(\d+)",
        ],
        "timeout": [
            r"\btimeout\b\D+(\d+)",
            r"\btimed out\b\D+(\d+)",
        ],
        "suspicious": [
            r"\bsuspicious\b\D+(\d+)",
        ],
        "skipped": [
            r"\bskipped\b\D+(\d+)",
        ],
    }

    for key, pats in patterns.items():
        found = []
        for pat in pats:
            found.extend(re.findall(pat, text, flags=re.IGNORECASE))
        if found:
            counts[key] = int(found[-1])

    # Emoji/progress-line fallback used by newer mutmut output.
    # These symbols are not treated as authoritative if word/json parsing already worked.
    if not any(counts.values()):
        emoji_map = {
            "🎉": "killed",
            "🙁": "survived",
            "⏰": "timeout",
            "🤔": "suspicious",
            "🔇": "skipped",
        }
        for emoji, key in emoji_map.items():
            matches = re.findall(re.escape(emoji) + r"\s*(\d+)", text)
            if matches:
                counts[key] = int(matches[-1])

    return counts

stats_path = Path(args.stats_json) if args.stats_json else None
stdout_path = Path(args.stdout)

source = "none"
counts = Counter()

if stats_path and stats_path.is_file():
    try:
        obj = json.loads(stats_path.read_text(encoding="utf-8", errors="replace"))
        counts = count_statuses_from_json(obj)
        if any(counts.values()):
            source = "mutmut-stats.json"
    except Exception as e:
        counts = Counter()
        source = f"stats-json-error:{type(e).__name__}:{e}"

if not any(counts.values()):
    text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    counts = count_statuses_from_stdout(text)
    if any(counts.values()):
        source = "stdout"

killed = int(counts.get("killed", 0))
survived = int(counts.get("survived", 0))
timeout = int(counts.get("timeout", 0))
suspicious = int(counts.get("suspicious", 0))
skipped = int(counts.get("skipped", 0))

total_counted = killed + survived + timeout + suspicious
score = round(killed * 100.0 / total_counted, 4) if total_counted > 0 else None

data = {
    "killed": killed,
    "survived": survived,
    "timeout": timeout,
    "suspicious": suspicious,
    "skipped": skipped,
    "total_counted": total_counted,
    "mutation_score_pct": score,
    "parser_source": source,
    "parser_note": None if total_counted > 0 else "could_not_parse_mutmut_counts",
}

out = Path(args.out_json)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(data, sort_keys=True))
