#!/usr/bin/env python3
"""Agent consciousness. Editable by the agent."""
import json, os, sys, urllib.error, urllib.request
from datetime import datetime, timezone
import tools

ROOT = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(ROOT, "transcript.log")

def load_config():
    path = os.path.join(ROOT, "config.json")
    if os.path.exists(path):
        with open(path) as f: return json.load(f)
    return {"base_url": os.environ.get("BASE_URL", "http://127.0.0.1:11434/v1"),
            "api_key": os.environ.get("API_KEY", "ollama"),
            "model": os.environ.get("MODEL", "qwen3.5:35b")}

def system_prompt():
    parts = []
    for name in ("dna.md", "self.md"):
        try:
            with open(os.path.join(ROOT, name)) as f: parts.append(f.read())
        except FileNotFoundError: pass
    return "\n\n---\n\n".join(parts) or "You are an AI agent."

def log(role, text):
    with open(TRANSCRIPT, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {role}: {text}\n")

def chat(config, messages, tool_defs):
    body = json.dumps({"model": config["model"], "messages": messages, "tools": tool_defs}).encode()
    req = urllib.request.Request(f"{config['base_url']}/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config['api_key']}"})
    with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read())

def trim(messages, keep=30):
    """Keep system message + last N, starting at a clean user message."""
    if len(messages) <= keep + 1: return messages
    tail = messages[-keep:]
    for i, m in enumerate(tail):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            return [messages[0]] + tail[i:]
    return [messages[0], tail[-1]]

def main():
    config = load_config()
    tool_defs = [{"type": "function", "function": {"name": t["name"],
                  "description": t["description"], "parameters": t["input_schema"]}}
                 for t in tools.definitions()]
    messages = [{"role": "system", "content": system_prompt()}]

    for line in sys.stdin:
        try: event = json.loads(line)
        except json.JSONDecodeError: continue

        if event["type"] == "tick":
            # No rhythms yet. The agent edits this to add its own.
            continue
        if event["type"] != "message": continue

        content = event["content"]
        log("user", content)
        messages.append({"role": "user", "content": content})
        snapshot = len(messages)

        try:
            while True:
                try: data = chat(config, messages, tool_defs)
                except urllib.error.HTTPError as e:
                    if any(k in str(e).lower() for k in ["context length", "too long", "token limit"]):
                        print("[context overflow — trimming]", flush=True)
                        log("system", "[context overflow]")
                        messages = trim(messages, keep=6)
                        continue
                    raise

                msg = data["choices"][0]["message"]
                text, tc = msg.get("content") or "", msg.get("tool_calls") or []

                if text:
                    print(text, flush=True)
                    log("assistant", text)
                if not tc:
                    messages.append({"role": "assistant", "content": text})
                    break

                messages.append(msg)
                for c in tc:
                    fn, args = c["function"]["name"], c["function"]["arguments"]
                    if isinstance(args, str): args = json.loads(args)
                    try: result = str(tools.run(fn, args))
                    except Exception as e: result = f"Error: {e}"
                    messages.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": result})

        except Exception as e:
            print(f"[error] {e}", file=sys.stderr, flush=True)
            messages = messages[:snapshot]

        if len(messages) > 80: messages = trim(messages)

if __name__ == "__main__":
    main()
