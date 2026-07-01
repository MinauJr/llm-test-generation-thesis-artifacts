#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path
from collections import Counter


COLUMNS = [
    "model",
    "sut_id",
    "repeat_tag",
    "status",
    "cluster_generation_status",
    "pytest_raw_exit_code",
    "pytest_final_exit_code",
    "sanitized",
    "sanitized_skipped_tests",
    "coverage_exit_code",
    "line_coverage_pct",
    "branch_coverage_pct",
    "mutation_exit_code",
    "mutation_score_pct",
    "mutation_killed",
    "mutation_survived",
    "mutation_timeout",
    "mutation_suspicious",
    "out_dir",
]


def parse_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes"}


def as_int(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(v)
    except Exception:
        return default


def as_float(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def strip_ansi_and_controls(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", text)
    text = text.replace("\r", "\n")
    return text


def parse_mutmut_run_stdout(text: str):
    """
    Parse mutmut v3-style progress summary, e.g.:

        4/4  🎉 4 🫥 0  ⏰ 0  🤔 0  🙁 0  🔇 0

    Meaning:
      checked/total, killed, no_tests, timeout, suspicious, survived, skipped
    """
    text = strip_ansi_and_controls(text)

    patterns = [
        r"(?P<checked>\d+)\s*/\s*(?P<total>\d+)\s*"
        r"🎉\s*(?P<killed>\d+)\s*"
        r"🫥\s*(?P<no_tests>\d+)\s*"
        r"⏰\s*(?P<timeout>\d+)\s*"
        r"🤔\s*(?P<suspicious>\d+)\s*"
        r"🙁\s*(?P<survived>\d+)\s*"
        r"🔇\s*(?P<skipped>\d+)",

        # Fallback mais permissivo: útil se houver caracteres invisíveis/spinner.
        r"(?P<checked>\d+)\s*/\s*(?P<total>\d+).*?"
        r"🎉\s*(?P<killed>\d+).*?"
        r"🫥\s*(?P<no_tests>\d+).*?"
        r"⏰\s*(?P<timeout>\d+).*?"
        r"🤔\s*(?P<suspicious>\d+).*?"
        r"🙁\s*(?P<survived>\d+).*?"
        r"🔇\s*(?P<skipped>\d+)",
    ]

    matches = []
    for pat in patterns:
        matches = list(re.finditer(pat, text, flags=re.DOTALL))
        if matches:
            break

    if not matches:
        return None

    # Usar o último resumo, porque o mutmut imprime progresso incremental.
    m = matches[-1]
    d = {k: int(v) for k, v in m.groupdict().items()}

    denominator = d["killed"] + d["survived"] + d["timeout"] + d["suspicious"]
    score = 100.0 * d["killed"] / denominator if denominator > 0 else 0.0

    d["mutation_score_pct"] = round(score, 6)
    return d


def get_status_jsons(out_root: Path):
    return sorted(out_root.rglob("metrics/status.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", required=True)
    args = ap.parse_args()

    out_root = Path(args.out_root).resolve()
    if not out_root.is_dir():
        raise SystemExit(f"out_root not found: {out_root}")

    status_files = get_status_jsons(out_root)
    rows = []
    parse_counts = Counter()
    status_counts = Counter()
    cluster_counts = Counter()

    for sf in status_files:
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] cannot read {sf}: {type(e).__name__}: {e}")
            continue

        rep_dir = sf.parent.parent
        logs_dir = rep_dir / "logs"
        mut_stdout = logs_dir / "mutmut_run_stdout.txt"

        parsed = None
        if mut_stdout.is_file():
            parsed = parse_mutmut_run_stdout(mut_stdout.read_text(encoding="utf-8", errors="replace"))

        if parsed is not None:
            data["mutation_parse_source"] = "mutmut_run_stdout"
            data["mutation_checked"] = parsed["checked"]
            data["mutation_total"] = parsed["total"]
            data["mutation_killed"] = parsed["killed"]
            data["mutation_survived"] = parsed["survived"]
            data["mutation_timeout"] = parsed["timeout"]
            data["mutation_suspicious"] = parsed["suspicious"]
            data["mutation_skipped"] = parsed["skipped"]
            data["mutation_no_tests"] = parsed["no_tests"]
            data["mutation_score_pct"] = parsed["mutation_score_pct"]
            parse_counts["parsed_mutmut_run_stdout"] += 1
        else:
            data.setdefault("mutation_parse_source", "not_parsed")
            data.setdefault("mutation_checked", 0)
            data.setdefault("mutation_total", 0)
            data.setdefault("mutation_killed", 0)
            data.setdefault("mutation_survived", 0)
            data.setdefault("mutation_timeout", 0)
            data.setdefault("mutation_suspicious", 0)
            data.setdefault("mutation_skipped", 0)
            data.setdefault("mutation_no_tests", 0)
            data.setdefault("mutation_score_pct", 0.0)
            parse_counts["not_parsed"] += 1

        sf.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

        model = str(data.get("model", ""))
        sut_id = str(data.get("sut_id", ""))
        repeat_tag = str(data.get("repeat_tag", data.get("repeat", "")))
        if repeat_tag.isdigit():
            repeat_tag = f"rep_{int(repeat_tag):02d}"

        status = str(data.get("status", ""))
        cluster_status = str(data.get("cluster_generation_status", data.get("generation_status", "")))

        row = {
            "model": model,
            "sut_id": sut_id,
            "repeat_tag": repeat_tag,
            "status": status,
            "cluster_generation_status": cluster_status,
            "pytest_raw_exit_code": as_int(data.get("pytest_raw_exit_code")),
            "pytest_final_exit_code": as_int(data.get("pytest_final_exit_code")),
            "sanitized": parse_bool(data.get("sanitized", False)),
            "sanitized_skipped_tests": as_int(data.get("sanitized_skipped_tests", data.get("skipped_tests", 0))),
            "coverage_exit_code": as_int(data.get("coverage_exit_code")),
            "line_coverage_pct": as_float(data.get("line_coverage_pct")),
            "branch_coverage_pct": as_float(data.get("branch_coverage_pct")),
            "mutation_exit_code": as_int(data.get("mutation_exit_code")),
            "mutation_score_pct": as_float(data.get("mutation_score_pct")),
            "mutation_killed": as_int(data.get("mutation_killed")),
            "mutation_survived": as_int(data.get("mutation_survived")),
            "mutation_timeout": as_int(data.get("mutation_timeout")),
            "mutation_suspicious": as_int(data.get("mutation_suspicious")),
            "out_dir": str(rep_dir),
        }

        rows.append(row)
        status_counts[status] += 1
        cluster_counts[cluster_status] += 1

    def sut_key(s):
        try:
            return int(str(s).split("_", 1)[1])
        except Exception:
            return 10**12

    def rep_key(r):
        m = re.search(r"(\d+)$", str(r))
        return int(m.group(1)) if m else 10**12

    rows.sort(key=lambda r: (r["model"], sut_key(r["sut_id"]), rep_key(r["repeat_tag"])))

    index_path = out_root / "dataset_runs_index.tsv"
    with index_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    n = len(rows)

    def mean(field):
        if not rows:
            return 0.0
        return sum(as_float(r.get(field)) for r in rows) / len(rows)

    distinct_suts = len({r["sut_id"] for r in rows})
    models = sorted({r["model"] for r in rows})

    summary = {
        "out_root": str(out_root),
        "dataset_runs_index": str(index_path),
        "models": models,
        "model_count": len(models),
        "evaluated_repetitions": n,
        "distinct_suts": distinct_suts,
        "status_counts": dict(status_counts),
        "cluster_generation_status_counts": dict(cluster_counts),
        "mutation_parse_counts": dict(parse_counts),
        "sanitized_repetitions": sum(1 for r in rows if parse_bool(r["sanitized"])),
        "pytest_final_failed": sum(1 for r in rows if as_int(r["pytest_final_exit_code"]) != 0),
        "coverage_failed": sum(1 for r in rows if as_int(r["coverage_exit_code"]) != 0),
        "mutation_run_failed": sum(1 for r in rows if as_int(r["mutation_exit_code"]) != 0),
        "line_coverage_mean_pct_strict0": round(mean("line_coverage_pct"), 6),
        "branch_coverage_mean_pct_strict0": round(mean("branch_coverage_pct"), 6),
        "mutation_score_mean_pct_strict0": round(mean("mutation_score_pct"), 6),
    }

    (out_root / "dataset_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    with (out_root / "dataset_summary.txt").open("w", encoding="utf-8") as f:
        f.write("===== MBPP+ CLUSTER-GENERATED LOCAL EVALUATION SUMMARY — MUTMUT FIXED =====\n")
        for k, v in summary.items():
            f.write(f"{k}: {v}\n")

    print("===== MUTMUT METRICS FIX SUMMARY =====")
    for k, v in summary.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
