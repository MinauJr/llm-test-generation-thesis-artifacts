#!/usr/bin/env python3
import os
import sys
import json
import uuid
import requests

ENDPOINT = os.getenv("IAEDU_ENDPOINT")
CHANNEL_ID = os.getenv("IAEDU_CHANNEL_ID")
API_KEY = os.getenv("IAEDU_API_KEY")
THREAD_PREFIX = os.getenv("IAEDU_THREAD_PREFIX", "")

if not ENDPOINT:
    raise RuntimeError("IAEDU_ENDPOINT não está definida.")
if not CHANNEL_ID:
    raise RuntimeError("IAEDU_CHANNEL_ID não está definida.")
if not API_KEY:
    raise RuntimeError("IAEDU_API_KEY não está definida.")

def ask_iaedu(message: str) -> str:
    thread_id = f"{THREAD_PREFIX}{uuid.uuid4()}"

    files = {
        "channel_id": (None, CHANNEL_ID),
        "thread_id": (None, thread_id),
        "user_info": (None, "{}"),
        "message": (None, message),
    }

    headers = {
        "x-api-key": API_KEY,
    }

    resp = requests.post(
        ENDPOINT,
        headers=headers,
        files=files,
        stream=True,
        timeout=(30, 600),
    )

    try:
        resp.raise_for_status()
    except Exception as e:
        body = ""
        try:
            body = resp.text[:2000]
        except Exception:
            pass
        raise RuntimeError(f"IAEdu request failed: {e}\nBODY_HEAD:\n{body}") from e

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
            full_text += data.get("content", "") or ""

        elif t == "message":
            content_obj = data.get("content", {})
            if isinstance(content_obj, dict):
                msg = content_obj.get("content")
                if isinstance(msg, str):
                    final_message = msg.strip()
                    if final_message:
                        return final_message
            elif isinstance(content_obj, str):
                final_message = content_obj.strip()
                if final_message:
                    return final_message

        elif t == "done":
            if final_message:
                return final_message.strip()
            if full_text.strip():
                return full_text.strip()
            break

        elif t == "error":
            # Alguns agentes parecem mandar erro/timeout depois de já terem enviado a resposta.
            # Só tratamos como erro fatal se ainda não houver resposta útil.
            if final_message:
                return final_message.strip()
            if full_text.strip():
                return full_text.strip()
            # caso não haja nada útil, continuamos até ao fim e falharemos por vazio

    return (final_message or full_text).strip()

def main():
    if len(sys.argv) != 2:
        print("Uso: iaedu_from_prompt.py PROMPT_FILE", file=sys.stderr)
        sys.exit(1)

    prompt_file = sys.argv[1]
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_text = f.read()

    answer = ask_iaedu(prompt_text)
    print(answer)

if __name__ == "__main__":
    main()
