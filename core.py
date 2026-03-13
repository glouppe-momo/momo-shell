#!/usr/bin/env python3
"""Agent consciousness. Editable by the agent."""

import json, os, sys
from datetime import datetime, timezone

from anthropic import Anthropic

import tools

ROOT = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(ROOT, "transcript.log")
MAX_MESSAGES = 100
TRIM_TO = 50


def load_config():
    with open(os.path.join(ROOT, "config.json")) as f:
        return json.load(f)


def read_if_exists(name):
    path = os.path.join(ROOT, name)
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def system_prompt():
    parts = [p for p in [read_if_exists("dna.md"), read_if_exists("self.md")] if p]
    return "\n\n---\n\n".join(parts) or "You are an AI agent."


def transcript(role, text):
    with open(TRANSCRIPT, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {role}: {text}\n")


def main():
    config = load_config()
    client = Anthropic(api_key=config["api_key"])
    model = config.get("model", "claude-sonnet-4-20250514")
    system = system_prompt()
    tool_defs = tools.definitions()
    messages = []

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

        # Agentic loop: call LLM, handle tool use, repeat
        while True:
            response = client.messages.create(
                model=model, max_tokens=4096,
                system=system, tools=tool_defs, messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            for block in response.content:
                if block.type == "text":
                    print(block.text, flush=True)
                    transcript("assistant", block.text)

            if response.stop_reason != "tool_use":
                break

            results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = str(tools.run(block.name, block.input))
                        results.append({"type": "tool_result", "tool_use_id": block.id,
                                        "content": result})
                    except Exception as e:
                        results.append({"type": "tool_result", "tool_use_id": block.id,
                                        "content": f"Error: {e}", "is_error": True})
            messages.append({"role": "user", "content": results})

        # Trim context if it grows too long
        if len(messages) > MAX_MESSAGES:
            messages = messages[-TRIM_TO:]


if __name__ == "__main__":
    main()
