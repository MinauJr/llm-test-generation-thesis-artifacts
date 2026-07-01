#!/usr/bin/env python3
import os
import sys
import json
import uuid
import requests

ENDPOINT = "https://api.iaedu.pt/agent-chat//api/v1/agent/cmamvd3n40000c801qeacoad2/stream"
CHANNEL_ID = "cmissxs8l08jgmh010ggu70rc"

API_KEY = os.getenv("IAEDU_API_KEY")
if API_KEY is None:
    raise RuntimeError("IAEDU_API_KEY não está definida. Verifica o ~/.bashrc ou faz export IAEDU_API_KEY=...")


def ask_iaedu(message: str) -> str:
    thread_id = str(uuid.uuid4())

    files = {
        "channel_id": (None, CHANNEL_ID),
        "thread_id": (None, thread_id),
        "user_info": (None, "{}"),
        "message": (None, message),
    }

    headers = {
        "x-api-key": API_KEY,
    }

    resp = requests.post(ENDPOINT, headers=headers, files=files, stream=True)
    resp.raise_for_status()

    full_text = ""
    final_message = None

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        t = data.get("type")
        if t == "token":
            full_text += data.get("content", "")
        elif t == "message":
            content_obj = data.get("content", {})
            if isinstance(content_obj, dict):
                final_message = content_obj.get("content")

    return (final_message or full_text).strip()


def main():
    if len(sys.argv) != 2:
        print("Uso: iaedu_from_prompt.py PROMPT_FILE", file=sys.stderr)
        sys.exit(1)

    prompt_file = sys.argv[1]
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_text = f.read()

    answer = ask_iaedu(prompt_text)
    # Muito importante: imprimir só o texto para stdout,
    # porque o run_all_llms redireciona isto para o ficheiro de output
    print(answer)


if __name__ == "__main__":
    main()
