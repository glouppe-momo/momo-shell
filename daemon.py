#!/usr/bin/env python3
"""Supervisor. Sacred. Do not modify."""
import json, os, signal, subprocess, sys, threading, time
from datetime import datetime, timezone
import cli

RESTART_CODE = 42
CRASH_WINDOW = 10
TICK_INTERVAL = 60

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    proc = None
    lock = threading.Lock()
    last_exit = [None]  # track last exit code

    def on_signal(sig, _):
        if proc and proc.poll() is None: proc.terminate()
        cli.goodbye(); sys.exit(0)
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def send(event):
        with lock:
            try: proc.stdin.write((json.dumps(event) + "\n").encode()); proc.stdin.flush()
            except (BrokenPipeError, OSError): pass

    def run_agent():
        nonlocal proc
        proc = subprocess.Popen([sys.executable, "-u", os.path.join(root, "core.py")],
                                stdin=subprocess.PIPE, cwd=root)
        stop = threading.Event()
        def ticks():
            while not stop.is_set():
                stop.wait(TICK_INTERVAL)
                if not stop.is_set():
                    send({"type": "tick", "time": datetime.now(timezone.utc).isoformat()})
        threading.Thread(target=ticks, daemon=True).start()

        if not os.path.exists(os.path.join(root, "self.md")):
            status("first boot")
            send({"type": "message", "content": "You have just been born. Read your DNA. Read your source code. Begin."})
        elif last_exit[0] == RESTART_CODE:
            status("rebooted")
            send({"type": "message", "content": "You just rebooted. Your conversation memory is gone but your transcript and files remain. Read your transcript to remember what you were doing."})

        proc.wait(); stop.set()
        return proc.returncode

    def last_commit_age():
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%ct"], capture_output=True, text=True, cwd=root)
            return time.time() - int(r.stdout.strip())
        except Exception: return float("inf")

    def rollback():
        status("crash after self-edit, rolling back")
        subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=root, capture_output=True)

    def status(msg):
        print(f"  {cli.DIM}[daemon] {msg}{cli.RESET}", file=sys.stderr, flush=True)

    def input_loop():
        while True:
            try: line = cli.prompt()
            except (EOFError, KeyboardInterrupt): on_signal(None, None)
            if not line.strip(): continue
            if line.strip().startswith("/"):
                r = cli.handle_command(line.strip())
                if r == "quit": on_signal(None, None)
                if r: continue
            send({"type": "message", "content": line.strip()})

    cli.banner()
    threading.Thread(target=input_loop, daemon=True).start()

    while True:
        code = run_agent()
        last_exit[0] = code
        if code == RESTART_CODE: status("restarting"); continue
        if code == 0: status("clean exit"); break
        if last_commit_age() < CRASH_WINDOW: rollback()
        status(f"crashed (exit {code}), restarting in 2s"); time.sleep(2)

if __name__ == "__main__":
    main()
