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
    last_exit = [None]

    def on_signal(sig, _):
        if proc and proc.poll() is None: proc.terminate()
        cli.goodbye(); sys.exit(0)
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def send(event):
        with lock:
            try: proc.stdin.write((json.dumps(event) + "\n").encode()); proc.stdin.flush()
            except (BrokenPipeError, OSError): pass

    def agent_print(text):
        """Print agent output without clobbering user's input line."""
        sys.stdout.write(f"\r\033[K{text}\n")
        sys.stdout.flush()

    def set_status(text):
        """Show a dim status indicator."""
        sys.stdout.write(f"\r\033[K  {cli.DIM}{text}{cli.RESET}\n")
        sys.stdout.flush()

    def run_agent():
        nonlocal proc
        proc = subprocess.Popen([sys.executable, "-u", os.path.join(root, "core.py")],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=root)
        stop = threading.Event()

        def relay_stdout():
            try:
                for line in proc.stdout:
                    agent_print(line.decode().rstrip())
            except: pass

        def relay_stderr():
            try:
                for line in proc.stderr:
                    text = line.decode().rstrip()
                    if text.startswith("[status:"):
                        # Status events from core.py
                        msg = text[8:-1] if text.endswith("]") else text[8:]
                        set_status(msg)
                    else:
                        agent_print(f"{cli.DIM}{text}{cli.RESET}")
            except: pass

        def ticks():
            while not stop.is_set():
                stop.wait(TICK_INTERVAL)
                if not stop.is_set():
                    send({"type": "tick", "time": datetime.now(timezone.utc).isoformat()})

        threading.Thread(target=relay_stdout, daemon=True).start()
        threading.Thread(target=relay_stderr, daemon=True).start()
        threading.Thread(target=ticks, daemon=True).start()

        if not os.path.exists(os.path.join(root, "self.md")):
            set_status("first boot")
            send({"type": "message", "content": "You have just been born. Read your DNA. Read your source code. Begin."})
        elif last_exit[0] == RESTART_CODE:
            set_status("rebooted")
            send({"type": "message", "content": "You just rebooted. Your conversation memory is gone but your transcript and files remain. Read your transcript to remember what you were doing."})

        proc.wait(); stop.set()
        return proc.returncode

    def last_commit_age():
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%ct"], capture_output=True, text=True, cwd=root)
            return time.time() - int(r.stdout.strip())
        except Exception: return float("inf")

    def rollback():
        set_status("crash after self-edit, rolling back")
        subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=root, capture_output=True)

    def input_loop():
        while True:
            try: line = cli.prompt()
            except (EOFError, KeyboardInterrupt): on_signal(None, None)
            if not line.strip(): continue
            if line.strip().startswith("/"):
                r = cli.handle_command(line.strip())
                if r == "quit": on_signal(None, None)
                if r: continue
            set_status("thinking...")
            send({"type": "message", "content": line.strip()})

    cli.banner()
    threading.Thread(target=input_loop, daemon=True).start()

    while True:
        code = run_agent()
        last_exit[0] = code
        if code == RESTART_CODE: set_status("restarting..."); continue
        if code == 0: set_status("clean exit"); break
        if last_commit_age() < CRASH_WINDOW: rollback()
        set_status(f"crashed (exit {code}), restarting in 2s"); time.sleep(2)

if __name__ == "__main__":
    main()
