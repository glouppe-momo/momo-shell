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


def is_context_overflow(error):
    """Detect context length errors from various providers."""
    msg = str(error).lower()
    return any(k in msg for k in ["context length", "too long", "token limit",
                                   "maximum context", "content too large"])


def trim_messages(messages, keep_last=6):
    """Emergency trim: keep system message + last few exchanges.

    Ensures tool_call/tool_result pairs stay intact by finding a safe
    cut point where the first kept message is a user text message.
    """
    if len(messages) <= keep_last + 1:
        return messages
    system = messages[0]
    tail = messages[-(keep_last):]
    # Walk forward to find a clean user message as the start
    for i, m in enumerate(tail):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            return [system] + tail[i:]
    # Fallback: just keep system + last message
    return [system, tail[-1]]


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
                try:
                    data = chat(config, messages, tool_defs)
                except urllib.error.HTTPError as e:
                    if is_context_overflow(e):
                        notice = "[context overflow — trimming history]"
                        print(notice, flush=True)
                        transcript("system", notice)
                        messages = trim_messages(messages)
                        continue
                    raise

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

        # Soft trim: if message list grows large, cut from the middle
        if len(messages) > 80:
            messages = trim_messages(messages, keep_last=30)


if __name__ == "__main__":
    main()
