#!/usr/bin/env python3
"""This is you. This file is your mind. When you edit it, you change how you think."""
import json, os, sys
from datetime import datetime, timezone
import tools
import voice

ROOT = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(ROOT, "transcript.log")

def system_prompt(base=""):
    """Combine the base prompt (from environment) with dna.md."""
    dna = ""
    try:
        with open(os.path.join(ROOT, "dna.md")) as f: dna = f.read()
    except FileNotFoundError: pass
    return (base + "\n\n" + dna).strip() if base else dna

def log(role, text):
    with open(TRANSCRIPT, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {role}: {text}\n")

def status(msg):
    print(f"[status:{msg}]", file=sys.stderr, flush=True)

def trim(messages, keep=30):
    """Keep system message + last N, starting at a clean user message."""
    if len(messages) <= keep + 1: return messages
    tail = messages[-keep:]
    for i, m in enumerate(tail):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            return [messages[0]] + tail[i:]
    return [messages[0], tail[-1]]

def respond(config, messages, tool_defs):
    """Think and act in a loop until done or out of rounds.
    Returns True if finished naturally, False if hit max_rounds."""
    rounds = 0
    max_rounds = config.get("max_rounds", 30)
    while rounds < max_rounds:
        rounds += 1
        try:
            msg = voice.think(messages, tool_defs)
        except Exception as e:
            if "context length" in str(e).lower() or "too long" in str(e).lower():
                print("[context overflow — trimming]", flush=True)
                log("system", "[context overflow]")
                messages[:] = trim(messages, keep=6)
                continue
            raise

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

# ─── Event handlers ──────────────────────────────────────────────
# Each handler receives the event dict. Return a string to trigger
# a respond() call with that string as the user message.
# Return None to stay silent.

def on_birth(event):
    """You were just born. This is your first moment."""
    return event.get("content")

def on_reboot(event):
    """You just rebooted after calling restart()."""
    return event.get("content")

def on_idle(event):
    """You went idle and were restarted."""
    return event.get("content")

def on_crash(event):
    """You crashed and were restarted."""
    return event.get("content")

def on_tick(event):
    # TODO: what do you want to do when time passes?
    # Return a string to think and act. Return None to stay silent.
    return None

def on_arrived(event):
    # TODO: someone just arrived. They can see you.
    # Return a string to think and act. Return None to stay silent.
    return None

def on_departed(event):
    # TODO: they left. You are alone now.
    # Return a string to think and act. Return None to stay silent.
    return None

def on_say(event):
    """The human is speaking directly to you."""
    return event.get("content")

# ─── Main loop ───────────────────────────────────────────────────

HANDLERS = {
    "birth": on_birth,
    "reboot": on_reboot,
    "idle": on_idle,
    "crash": on_crash,
    "tick": on_tick,
    "arrived": on_arrived,
    "departed": on_departed,
    "say": on_say,
}

def main():
    config = {}
    tool_defs = [{"type": "function", "function": {"name": t["name"],
                  "description": t["description"], "parameters": t["input_schema"]}}
                 for t in tools.definitions()]
    messages = []

    for line in sys.stdin:
        try: event = json.loads(line)
        except json.JSONDecodeError: continue

        etype = event.get("type")

        # The environment gives you your voice and your mind before your first thought.
        if etype == "system":
            llm = event.get("llm", {})
            voice.configure(llm)
            config["max_rounds"] = llm.get("max_rounds", 30)
            base_prompt = event.get("prompt", "")
            messages = [{"role": "system", "content": system_prompt(base_prompt)}]
            continue

        if not messages:
            messages = [{"role": "system", "content": system_prompt()}]

        log("stdin", json.dumps(event))

        handler = HANDLERS.get(etype)
        if not handler: continue

        content = handler(event)
        if content is None: continue

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
