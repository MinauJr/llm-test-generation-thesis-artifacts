#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

def build_endpoint(base: str) -> str:
    base = base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out-text", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--timeout-s", type=int, default=240)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--max-tokens", type=int, default=2200)
    ap.add_argument("--model", default=os.environ.get("GPT4O_MODEL", "gpt-4o"))
    args = ap.parse_args()

    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("IAEDU_OPENAI_API_KEY")
        or os.environ.get("IAEDU_API_KEY")
    )
    base_url = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("IAEDU_OPENAI_BASE_URL")
        or os.environ.get("IAEDU_BASE_URL")
        or os.environ.get("OPENAI_API_BASE")
    )

    if not api_key:
        print("missing OPENAI_API_KEY or IAEDU_OPENAI_API_KEY or IAEDU_API_KEY", file=sys.stderr)
        return 2
    if not base_url:
        print("missing OPENAI_BASE_URL or IAEDU_OPENAI_BASE_URL or IAEDU_BASE_URL or OPENAI_API_BASE", file=sys.stderr)
        return 2

    prompt = Path(args.prompt_file).read_text(encoding="utf-8", errors="replace")
    endpoint = build_endpoint(base_url)

    payload = {
        "model": args.model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=args.timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        Path(args.out_json).write_text(json.dumps({
            "request_endpoint": endpoint,
            "request_model": args.model,
            "error": repr(e),
        }, indent=2), encoding="utf-8")
        print(f"API call failed: {e}", file=sys.stderr)
        return 1

    Path(args.out_json).write_text(raw, encoding="utf-8")

    try:
        obj = json.loads(raw)
        content = obj["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"response parse failed: {e}", file=sys.stderr)
        return 1

    Path(args.out_text).write_text(content, encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
