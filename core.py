#!/usr/bin/env python3
"""Agent consciousness. Editable by the agent."""

import json, os, sys, urllib.request
from datetime import datetime, timezone

import tools

ROOT = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(ROOT, "transcript.log")
MAX_MESSAGES = 100
TRIM_TO = 50


def load_config():
    path = os.path.join(ROOT, "config.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {
        "base_url": os.environ.get("BASE_URL", "http://127.0.0.1:11434/v1"),
        "api_key": os.environ.get("API_KEY", "ollama"),
        "model": os.environ.get("MODEL", "qwen3.5:35b"),
    }


def read_if_exists(name):
    try:
        with open(os.path.join(ROOT, name)) as f:
            return f.read()
    except FileNotFoundError:
        return None


def system_prompt():
    parts = [p for p in [read_if_exists("dna.md"), read_if_exists("self.md")] if p]
    return "\n\n---\n\n".join(parts) or "You are an AI agent."


def transcript(role, text):
    with open(TRANSCRIPT, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {role}: {text}\n")


def openai_tools(tool_defs):
    return [{"type": "function", "function": {"name": t["name"],
            "description": t["description"], "parameters": t["input_schema"]}}
            for t in tool_defs]


def chat(config, messages, tool_defs):
    body = json.dumps({"model": config["model"], "messages": messages,
                        "tools": tool_defs}).encode()
    req = urllib.request.Request(
        f"{config['base_url']}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {config['api_key']}"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())


def main():
    config = load_config()
    system = system_prompt()
    tool_defs = openai_tools(tools.definitions())
    messages = [{"role": "system", "content": system}]

    for line in sys.stdin:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        # --- Tick: the agent experiences time ---
        if event["type"] == "tick":
            # No rhythms yet. The agent edits this to add its own.
            continue

        # --- Message: someone talked to the agent ---
        if event["type"] != "message":
            continue

        content = event["content"]
        transcript("user", content)
        messages.append({"role": "user", "content": content})
        snapshot = len(messages)

        try:
            while True:
                data = chat(config, messages, tool_defs)
                msg = data["choices"][0]["message"]
                text = msg.get("content") or ""
                tool_calls = msg.get("tool_calls") or []

                if text:
                    print(text, flush=True)
                    transcript("assistant", text)

                if not tool_calls:
                    messages.append({"role": "assistant", "content": text})
                    break

                messages.append(msg)
                for tc in tool_calls:
                    fn = tc["function"]
                    args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
                    try:
                        result = str(tools.run(fn["name"], args))
                    except Exception as e:
                        result = f"Error: {e}"
                    messages.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                                     "content": result})
        except Exception as e:
            print(f"[error] {e}", file=sys.stderr, flush=True)
            messages = messages[:snapshot]

        # Keep system message + last N
        if len(messages) > MAX_MESSAGES:
            messages = [messages[0]] + messages[-(TRIM_TO - 1):]


if __name__ == "__main__":
    main()
