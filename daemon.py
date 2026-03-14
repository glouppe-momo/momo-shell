#!/usr/bin/env python3
"""Environment supervisor. Runs the agent, manages time, mediates the outside world."""
import json, os, signal, subprocess, sys, threading, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli

RESTART_CODE = 42
CRASH_WINDOW = 10
TICK_INTERVAL = 60
IDLE_TIMEOUT = 90  # seconds of silence after activity before restart

def main():
    root = os.environ.get("AGENT_DIR", "/agent")
    inbox = os.path.join(root, "inbox")
    os.makedirs(inbox, exist_ok=True)
    proc = None
    lock = threading.Lock()
    last_exit = [None]
    last_activity = [0.0]  # timestamp of last agent output
    was_active = [False]   # did the agent produce any output this run?

    def on_signal(sig, _):
        if proc and proc.poll() is None: proc.terminate()
        cli.goodbye(); sys.exit(0)
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def send(event):
        with lock:
            try: proc.stdin.write((json.dumps(event) + "\n").encode()); proc.stdin.flush()
            except (BrokenPipeError, OSError): pass

    def out(text, dim=False):
        with lock:
            text = f"  {cli.DIM}{text}{cli.RESET}" if dim else text
            sys.stdout.write(f"\r\033[K{text}\n"); sys.stdout.flush()

    def touch():
        """Mark agent as active."""
        last_activity[0] = time.time()
        was_active[0] = True

    def drop_message(text):
        """Drop a message file into the agent's inbox."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        path = os.path.join(inbox, f"{ts}.md")
        with open(path, "w") as f: f.write(text)
        out(f"message dropped → inbox/{os.path.basename(path)}", dim=True)

    def run_agent():
        nonlocal proc
        was_active[0] = False
        last_activity[0] = time.time()
        proc = subprocess.Popen([sys.executable, "-u", os.path.join(root, "core.py")],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=root)
        stop = threading.Event()

        def relay(stream, handler):
            try:
                for line in stream: touch(); handler(line.decode().rstrip())
            except: pass

        def on_stderr(text):
            if text.startswith("[status:"):
                out(text[8:-1] if text.endswith("]") else text[8:], dim=True)
            else:
                out(text, dim=True)

        threading.Thread(target=relay, args=(proc.stdout, out), daemon=True).start()
        threading.Thread(target=relay, args=(proc.stderr, on_stderr), daemon=True).start()

        def ticks():
            while not stop.is_set():
                stop.wait(TICK_INTERVAL)
                if not stop.is_set():
                    send({"type": "tick", "time": datetime.now(timezone.utc).isoformat()})
        threading.Thread(target=ticks, daemon=True).start()

        def watchdog():
            """Kill the agent if it goes idle after being active."""
            while not stop.is_set():
                stop.wait(10)
                if stop.is_set(): break
                if was_active[0] and (time.time() - last_activity[0]) > IDLE_TIMEOUT:
                    if proc.poll() is None:
                        out("idle too long, restarting", dim=True)
                        proc.terminate()
        threading.Thread(target=watchdog, daemon=True).start()

        born = os.path.join(root, ".born")
        if not os.path.exists(born):
            open(born, "w").close()
            out("first boot", dim=True)
            send({"type": "message", "content": "You have just been born. Read your DNA. Read your source code. Begin."})
        elif last_exit[0] == RESTART_CODE:
            out("rebooted", dim=True)
            send({"type": "message", "content": "You just rebooted after calling restart(). Your conversation memory is gone but your transcript and files remain. Read the tail of your transcript to remember what you were doing."})
        else:
            out("recovered", dim=True)
            send({"type": "message", "content": "You crashed and have been restarted. Your conversation memory is gone but your transcript and files remain. Read the tail of your transcript to understand what happened."})

        proc.wait(); stop.set()
        return proc.returncode

    def last_commit_age():
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%ct"], capture_output=True, text=True, cwd=root)
            return time.time() - int(r.stdout.strip())
        except Exception: return float("inf")

    def input_loop():
        while True:
            try: line = cli.prompt()
            except (EOFError, KeyboardInterrupt): on_signal(None, None)
            if not line.strip(): continue
            if line.strip().startswith("/"):
                r = cli.handle_command(line.strip())
                if r == "quit": on_signal(None, None)
                if r: continue
            drop_message(line.strip())

    cli.banner()
    threading.Thread(target=input_loop, daemon=True).start()

    while True:
        code = run_agent()
        last_exit[0] = code
        if code == RESTART_CODE: out("restarting...", dim=True); continue
        if code == 0: out("clean exit", dim=True); break
        if last_commit_age() < CRASH_WINDOW:
            out("crash after self-edit, rolling back", dim=True)
            subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=root, capture_output=True)
        out(f"crashed (exit {code}), restarting in 2s", dim=True); time.sleep(2)

if __name__ == "__main__":
    main()
