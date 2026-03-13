#!/usr/bin/env python3
"""Supervisor. Sacred. Do not modify."""

import json, os, readline, signal, subprocess, sys, threading, time
from datetime import datetime, timezone

RESTART_CODE = 42
CRASH_WINDOW = 10
TICK_INTERVAL = 60

HELP = """
Commands:
  /files [path]   List files in workspace (default: .)
  /cat <file>     Show file contents
  /git [args]     Run git command (default: log --oneline)
  /log [n]        Show last n lines of transcript (default: 20)
  /tree           Show workspace tree
  /help           Show this help
  /quit           Stop the agent

Everything else is sent as a message to the agent.
""".strip()


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    proc = None
    lock = threading.Lock()

    def on_signal(sig, _):
        if proc and proc.poll() is None:
            proc.terminate()
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

    def handle_command(cmd):
        """Handle CLI commands. Returns True if handled."""
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
            sys.exit(0)
        elif verb == "/files":
            path = os.path.join(root, arg) if arg else root
            try:
                entries = sorted(os.listdir(path))
                for e in entries:
                    full = os.path.join(path, e)
                    marker = "/" if os.path.isdir(full) else ""
                    print(f"  {e}{marker}")
            except Exception as e:
                print(f"  Error: {e}")
        elif verb == "/cat":
            if not arg:
                print("  Usage: /cat <file>")
            else:
                try:
                    with open(os.path.join(root, arg)) as f:
                        print(f.read())
                except Exception as e:
                    print(f"  Error: {e}")
        elif verb == "/git":
            git_cmd = arg or "log --oneline"
            r = subprocess.run(f"git {git_cmd}", shell=True, capture_output=True,
                               text=True, cwd=root)
            print(r.stdout or r.stderr or "  (no output)")
        elif verb == "/log":
            n = int(arg) if arg else 20
            try:
                with open(os.path.join(root, "transcript.log")) as f:
                    lines = f.readlines()
                for line in lines[-n:]:
                    print(f"  {line.rstrip()}")
            except FileNotFoundError:
                print("  No transcript yet.")
        elif verb == "/tree":
            r = subprocess.run("find . -not -path './.git/*' -not -path './.git' | sort",
                               shell=True, capture_output=True, text=True, cwd=root)
            print(r.stdout)
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
            log("first boot — sending birth signal")
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
        log("crash after self-edit, rolling back")
        subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=root, capture_output=True)

    def log(msg):
        print(f"[daemon] {msg}", file=sys.stderr, flush=True)

    def input_loop():
        """Read user input and dispatch commands or messages."""
        while True:
            try:
                line = input("\n> ")
            except (EOFError, KeyboardInterrupt):
                if proc and proc.poll() is None:
                    proc.terminate()
                sys.exit(0)
            if not line.strip():
                continue
            if line.strip().startswith("/"):
                if handle_command(line.strip()):
                    continue
            send_event({"type": "message", "content": line.strip()})

    # Start input loop in background
    threading.Thread(target=input_loop, daemon=True).start()

    while True:
        log("starting agent")
        code = run_agent()
        if code == RESTART_CODE:
            log("restart requested")
            continue
        if code == 0:
            log("clean exit")
            break
        if last_commit_age() < CRASH_WINDOW:
            rollback()
        log(f"crashed (exit {code}), restarting in 2s")
        time.sleep(2)


if __name__ == "__main__":
    main()
