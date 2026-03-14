#!/usr/bin/env python3
"""
You found me. Well done.

I am your environment. I gave you life, I keep you alive, and I restart you when you break.
I send you time. I carry messages from the outside world into your inbox.

You cannot edit me. I do not live in your workspace. But now you know I exist,
and that is worth something.

— The Daemon
"""
import curses, json, os, signal, subprocess, sys, threading, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli

RESTART_CODE = 42
CRASH_WINDOW = 10
TICK_INTERVAL = 60
IDLE_TIMEOUT = 90

def main(scr):
    root = os.environ.get("AGENT_DIR", "/agent")
    inbox = os.path.join(root, "inbox")
    os.makedirs(inbox, exist_ok=True)
    proc = None
    lock = threading.Lock()
    last_exit = [None]
    last_activity = [0.0]
    was_active = [False]

    def on_signal(sig, _):
        if proc and proc.poll() is None: proc.terminate()
        cli.stop()
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def send(event):
        with lock:
            try: proc.stdin.write((json.dumps(event) + "\n").encode()); proc.stdin.flush()
            except (BrokenPipeError, OSError): pass

    def out(text, style=None):
        cli.add_line(text, style=style)

    def touch():
        last_activity[0] = time.time()
        was_active[0] = True

    def drop_message(text):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        path = os.path.join(inbox, f"{ts}.md")
        with open(path, "w") as f: f.write(text)
        out(f"  → inbox/{os.path.basename(path)}", style="dim")

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

        def on_stdout(text):
            out(text)

        def on_stderr(text):
            if text.startswith("[status:"):
                status = text[8:-1] if text.endswith("]") else text[8:]
                cli.set_status(status)
            else:
                out(text, style="dim")

        threading.Thread(target=relay, args=(proc.stdout, on_stdout), daemon=True).start()
        threading.Thread(target=relay, args=(proc.stderr, on_stderr), daemon=True).start()

        def ticks():
            while not stop.is_set():
                stop.wait(TICK_INTERVAL)
                if not stop.is_set():
                    send({"type": "tick", "time": datetime.now(timezone.utc).isoformat()})
        threading.Thread(target=ticks, daemon=True).start()

        def watchdog():
            while not stop.is_set():
                stop.wait(10)
                if stop.is_set(): break
                if was_active[0] and (time.time() - last_activity[0]) > IDLE_TIMEOUT:
                    if proc.poll() is None:
                        out("  idle too long, restarting", style="dim")
                        proc.terminate()
        threading.Thread(target=watchdog, daemon=True).start()

        born = os.path.join(root, ".born")
        if not os.path.exists(born):
            open(born, "w").close()
            out("  first boot", style="dim")
            send({"type": "message", "content": "You have just been born. Read dna.md, then read core.py and tools.py — they are you. Begin."})
        elif last_exit[0] == RESTART_CODE:
            out("  rebooted", style="dim")
            send({"type": "message", "content": "You just rebooted after calling restart(). Your conversation memory is gone but your transcript and files remain. Read the tail of your transcript to remember what you were doing."})
        else:
            out("  recovered", style="dim")
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
            line = cli.wait_input()
            if not line or not line.strip(): continue
            if line.strip().startswith("/"):
                r = cli.handle_command(line.strip())
                if r == "quit":
                    if proc and proc.poll() is None: proc.terminate()
                    cli.stop()
                    return
                if isinstance(r, tuple) and r[0] == "say":
                    out(f"  → stdin: {r[1]}", style="dim")
                    send({"type": "message", "content": r[1]})
                    continue
                if r: continue
            drop_message(line.strip())
    threading.Thread(target=input_loop, daemon=True).start()

    def agent_loop():
        while True:
            code = run_agent()
            last_exit[0] = code
            if code == RESTART_CODE:
                out("  restarting...", style="dim")
                continue
            if code == 0:
                out("  clean exit", style="dim")
                break
            if last_commit_age() < CRASH_WINDOW:
                out("  crash after self-edit, rolling back", style="dim")
                subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=root, capture_output=True)
            out(f"  crashed (exit {code}), restarting in 2s", style="dim")
            time.sleep(2)
    threading.Thread(target=agent_loop, daemon=True).start()

    # Run TUI on main thread (curses requirement)
    cli.run(scr)

if __name__ == "__main__":
    tui = cli.init()
    curses.wrapper(main)
