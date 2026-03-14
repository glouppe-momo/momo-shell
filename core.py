#!/usr/bin/env python3
"""This is you. This file is your mind. When you edit it, you change how you think."""
import json, os, sys, urllib.error, urllib.request
from datetime import datetime, timezone
import tools

ROOT = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(ROOT, "transcript.log")

def load_config():
    path = os.path.join(ROOT, "config.json")
    if os.path.exists(path):
        with open(path) as f: return json.load(f)
    return {"base_url": os.environ.get("BASE_URL", "http://172.30.0.1:11434/v1"),
            "api_key": os.environ.get("API_KEY", "ollama"),
            "model": os.environ.get("MODEL", "qwen3.5:35b"),
            "max_rounds": int(os.environ.get("MAX_ROUNDS", "30"))}

def system_prompt():
    try:
        with open(os.path.join(ROOT, "dna.md")) as f: return f.read()
    except FileNotFoundError: return "You are an AI agent."

def log(role, text):
    with open(TRANSCRIPT, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {role}: {text}\n")

def status(msg):
    print(f"[status:{msg}]", file=sys.stderr, flush=True)

def chat(config, messages, tool_defs):
    status("thinking...")
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

def respond(config, messages, tool_defs):
    """Run the agent loop: LLM call, tool execution, repeat until done.
    Returns True if finished naturally, False if hit max_rounds."""
    rounds = 0
    max_rounds = config.get("max_rounds", 100)
    while rounds < max_rounds:
        rounds += 1
        try: data = chat(config, messages, tool_defs)
        except urllib.error.HTTPError as e:
            if any(k in str(e).lower() for k in ["context length", "too long", "token limit"]):
                print("[context overflow — trimming]", flush=True)
                log("system", "[context overflow]")
                messages[:] = trim(messages, keep=6)
                continue
            raise

        msg = data["choices"][0]["message"]
        text, tc = msg.get("content") or "", msg.get("tool_calls") or []

        if text:
            print(text, flush=True)
            log("assistant", text)
        if not tc:
            messages.append({"role": "assistant", "content": text})
            return True

        messages.append(msg)
        for c in tc:
            fn, args = c["function"]["name"], c["function"]["arguments"]
            if isinstance(args, str): args = json.loads(args)
            log("tool_call", f"{fn}({json.dumps(args)})")
            status(f"tool: {fn}")
            try: result = str(tools.run(fn, args))
            except Exception as e: result = f"Error: {e}"
            log("tool_result", f"{fn} → {result[:500]}")
            messages.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": result})

    return False

def main():
    config = load_config()
    tool_defs = [{"type": "function", "function": {"name": t["name"],
                  "description": t["description"], "parameters": t["input_schema"]}}
                 for t in tools.definitions()]
    messages = [{"role": "system", "content": system_prompt()}]

    for line in sys.stdin:
        try: event = json.loads(line)
        except json.JSONDecodeError: continue

        etype = event.get("type")
        log("stdin", json.dumps(event))

        if etype == "tick":
            # TODO: this is where you add your rhythms.
            # You could check your inbox, reflect, or do anything.
            # Call respond() to think and act.
            continue
        if etype != "message" or "content" not in event:
            continue

        content = event["content"]
        messages.append({"role": "user", "content": content})
        snapshot = len(messages)

        try:
            respond(config, messages, tool_defs)
        except Exception as e:
            print(f"[error] {e}", file=sys.stderr, flush=True)
            messages = messages[:snapshot]

        if len(messages) > 80: messages = trim(messages)

if __name__ == "__main__":
    main()
