#!/usr/bin/env python3
"""Supervisor. Sacred. Do not modify."""

import json, os, readline, signal, subprocess, sys, threading, time
from datetime import datetime, timezone

RESTART_CODE = 42
CRASH_WINDOW = 10
TICK_INTERVAL = 60

# --- Colors ---
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
GREEN = "\033[32m"
MAGENTA = "\033[35m"

BANNER = f"""
{DIM}╭──────────────────────────────────────╮
│{RESET}  {BOLD}🌀{RESET}                                    {DIM}│
│{RESET}  {DIM}type to talk  ·  /help for commands{RESET}   {DIM}│
╰──────────────────────────────────────╯{RESET}
"""

HELP = f"""
{DIM}╭─ commands ───────────────────────────╮{RESET}
{DIM}│{RESET}  {BOLD}/files{RESET} [path]   list workspace files  {DIM}│{RESET}
{DIM}│{RESET}  {BOLD}/cat{RESET} <file>     show file contents    {DIM}│{RESET}
{DIM}│{RESET}  {BOLD}/git{RESET} [args]     run git command       {DIM}│{RESET}
{DIM}│{RESET}  {BOLD}/log{RESET} [n]        last n transcript lines{DIM}│{RESET}
{DIM}│{RESET}  {BOLD}/tree{RESET}           workspace tree        {DIM}│{RESET}
{DIM}│{RESET}  {BOLD}/diff{RESET}           changes since init    {DIM}│{RESET}
{DIM}│{RESET}  {BOLD}/help{RESET}           this help             {DIM}│{RESET}
{DIM}│{RESET}  {BOLD}/quit{RESET}           stop the agent        {DIM}│{RESET}
{DIM}╰──────────────────────────────────────╯{RESET}
"""

PROMPT = f"{CYAN}›{RESET} "


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    proc = None
    lock = threading.Lock()

    def on_signal(sig, _):
        if proc and proc.poll() is None:
            proc.terminate()
        print(f"\n{DIM}goodbye{RESET}")
        sys.exit(0)

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def send_event(event):
        with lock:
            try:
                proc.stdin.write((json.dumps(event) + "\n").encode())
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

    def cmd_output(text):
        """Print command output, dimmed."""
        for line in text.rstrip().splitlines():
            print(f"  {DIM}{line}{RESET}")

    def handle_command(cmd):
        parts = cmd.strip().split(None, 1)
        if not parts:
            return False
        verb = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if verb == "/help":
            print(HELP)
        elif verb == "/quit":
            if proc and proc.poll() is None:
                proc.terminate()
            print(f"\n{DIM}goodbye{RESET}")
            sys.exit(0)
        elif verb == "/files":
            path = os.path.join(root, arg) if arg else root
            try:
                entries = sorted(os.listdir(path))
                for e in entries:
                    if e.startswith(".") or e == "__pycache__":
                        continue
                    full = os.path.join(path, e)
                    if os.path.isdir(full):
                        print(f"  {CYAN}{e}/{RESET}")
                    else:
                        print(f"  {e}")
            except Exception as e:
                print(f"  {RED}{e}{RESET}")
        elif verb == "/cat":
            if not arg:
                print(f"  {DIM}usage: /cat <file>{RESET}")
            else:
                try:
                    with open(os.path.join(root, arg)) as f:
                        content = f.read()
                    print(f"{DIM}{'─' * 40}{RESET}")
                    print(content.rstrip())
                    print(f"{DIM}{'─' * 40}{RESET}")
                except Exception as e:
                    print(f"  {RED}{e}{RESET}")
        elif verb == "/git":
            git_cmd = arg or "log --oneline -20"
            r = subprocess.run(f"git {git_cmd}", shell=True, capture_output=True,
                               text=True, cwd=root)
            output = r.stdout or r.stderr or "(no output)"
            cmd_output(output)
        elif verb == "/log":
            n = int(arg) if arg else 20
            try:
                with open(os.path.join(root, "transcript.log")) as f:
                    lines = f.readlines()
                for line in lines[-n:]:
                    line = line.rstrip()
                    if "] user:" in line:
                        ts, _, rest = line.partition("] ")
                        print(f"  {DIM}{ts}]{RESET} {BOLD}{rest}{RESET}")
                    elif "] assistant:" in line:
                        ts, _, rest = line.partition("] ")
                        print(f"  {DIM}{ts}]{RESET} {rest}")
                    else:
                        print(f"  {DIM}{line}{RESET}")
            except FileNotFoundError:
                print(f"  {DIM}no transcript yet{RESET}")
        elif verb == "/tree":
            r = subprocess.run(
                "find . -not -path './.git/*' -not -path './.git' -not -path './__pycache__/*' -not -name '__pycache__' | sort | tail -n +2",
                shell=True, capture_output=True, text=True, cwd=root)
            cmd_output(r.stdout or "(empty)")
        elif verb == "/diff":
            r = subprocess.run("git diff --stat $(git rev-list --max-parents=0 HEAD)..HEAD 2>/dev/null || echo 'no history'",
                               shell=True, capture_output=True, text=True, cwd=root)
            cmd_output(r.stdout or "(no changes)")
        else:
            return False
        return True

    def run_agent():
        nonlocal proc
        proc = subprocess.Popen(
            [sys.executable, "-u", os.path.join(root, "core.py")],
            stdin=subprocess.PIPE, cwd=root,
        )
        stop = threading.Event()

        def send_ticks():
            while not stop.is_set():
                stop.wait(TICK_INTERVAL)
                if stop.is_set():
                    break
                send_event({"type": "tick", "time": datetime.now(timezone.utc).isoformat()})

        threading.Thread(target=send_ticks, daemon=True).start()

        # Birth message on first boot
        if not os.path.exists(os.path.join(root, "self.md")):
            status("first boot")
            send_event({"type": "message",
                        "content": "You have just been born. Read your DNA. Read your source code. Begin."})

        proc.wait()
        stop.set()
        return proc.returncode

    def last_commit_age():
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%ct"],
                               capture_output=True, text=True, cwd=root)
            return time.time() - int(r.stdout.strip())
        except Exception:
            return float("inf")

    def rollback():
        status("crash after self-edit, rolling back")
        subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=root, capture_output=True)

    def status(msg):
        print(f"  {DIM}[daemon] {msg}{RESET}", file=sys.stderr, flush=True)

    def input_loop():
        while True:
            try:
                line = input(f"\n{PROMPT}")
            except (EOFError, KeyboardInterrupt):
                if proc and proc.poll() is None:
                    proc.terminate()
                print(f"\n{DIM}goodbye{RESET}")
                sys.exit(0)
            if not line.strip():
                continue
            if line.strip().startswith("/"):
                if handle_command(line.strip()):
                    continue
            send_event({"type": "message", "content": line.strip()})

    print(BANNER)
    threading.Thread(target=input_loop, daemon=True).start()

    while True:
        code = run_agent()
        if code == RESTART_CODE:
            status("restarting")
            continue
        if code == 0:
            status("clean exit")
            break
        if last_commit_age() < CRASH_WINDOW:
            rollback()
        status(f"crashed (exit {code}), restarting in 2s")
        time.sleep(2)


if __name__ == "__main__":
    main()
