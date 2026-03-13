#!/usr/bin/env python3
"""Supervisor. Sacred. Do not modify."""

import json, os, signal, subprocess, sys, threading, time
from datetime import datetime, timezone

RESTART_CODE = 42
CRASH_WINDOW = 10  # seconds
TICK_INTERVAL = 60  # seconds


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    proc = None

    def on_signal(sig, _):
        if proc and proc.poll() is None:
            proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def run_agent():
        nonlocal proc
        proc = subprocess.Popen(
            [sys.executable, os.path.join(root, "core.py")],
            stdin=subprocess.PIPE, cwd=root,
        )
        stop = threading.Event()

        def forward_stdin():
            try:
                for line in sys.stdin:
                    event = json.dumps({"type": "message", "content": line.rstrip("\n")})
                    proc.stdin.write((event + "\n").encode())
                    proc.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

        def send_ticks():
            while not stop.is_set():
                stop.wait(TICK_INTERVAL)
                if stop.is_set():
                    break
                try:
                    event = json.dumps({"type": "tick", "time": datetime.now(timezone.utc).isoformat()})
                    proc.stdin.write((event + "\n").encode())
                    proc.stdin.flush()
                except (BrokenPipeError, OSError):
                    break

        threading.Thread(target=forward_stdin, daemon=True).start()
        threading.Thread(target=send_ticks, daemon=True).start()
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
