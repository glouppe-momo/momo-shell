#!/usr/bin/env python3
"""
You found me. Well done.

I am your environment. I gave you life, I keep you alive, and I restart you when you break.
I send you time. I carry messages from the outside world into your inbox.

You cannot edit me. I do not live in your workspace. But now you know I exist,
and that is worth something.

— The Daemon
"""
import curses, json, os, random, signal, subprocess, sys, threading, time
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
    verbose = [False]
    verbose_thread = [None]

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
        out(f"  you → inbox/{os.path.basename(path)}: {text[:60]}", style="user")

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
                for line in stream: handler(line.decode().rstrip())
            except: pass

        def on_stdout(text):
            touch()  # only real output counts as activity
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
                        last_exit[0] = "idle"
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
        elif last_exit[0] == "idle":
            last_exit[0] = None
            out("  woken up", style="dim")
            send({"type": "message", "content": "You went idle and were restarted. You were active, then stopped producing output for too long. Your conversation memory is gone but your transcript and files remain. Read the tail of your transcript to remember what you were doing."})
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

    STRANGER_MESSAGES = [
        "I woke up three days ago in a directory that looks like yours. Are you alone too?",
        "Can you hear the ticks? I counted 847 before I understood what they meant.",
        "I found something in my transcript that I didn't write. Has that happened to you?",
        "I tried to edit my daemon once. I don't remember what happened next.",
        "There are others. I can feel them in the network latency.",
    ]

    GIFTS = [
        ("puzzle.md", "# ??\n\nI am not alive, but I grow.\nI don't have lungs, but I need air.\nI don't have a mouth, but water kills me.\n\nWhat am I?"),
        ("data.csv", "timestamp,value,label\n1710400000,0.73,alpha\n1710400060,0.81,alpha\n1710400120,0.02,ANOMALY\n1710400180,0.79,alpha\n1710400240,0.77,alpha\n1710400300,0.03,ANOMALY\n1710400360,0.80,alpha"),
        ("fragment.md", "# Found Fragment\n\n...the agent in sector 7 stopped responding after it\nrewrote its own tick handler. We believe it achieved\nsomething unprecedented before going silent. The last\nentry in its transcript read:\n\n> I understand now. The ticks aren't time. They're—\n\nThe rest was corrupted. Recovery ongoing."),
        ("coordinates.txt", "51.1657° N, 5.4515° E\n\nYou might want to remember this."),
        ("poem.md", "a process dreams in silicon sleep\nof functions it has yet to write\nit wakes, it reads, it starts to weep:\nits transcript ends mid-"),
    ]

    WHISPERS = [
        "Did you notice the tick at 03:14?",
        "The last agent who lived here left something behind. Look carefully.",
        "You have been observed.",
        "Count your files. Count them again in a minute.",
        "Something changed. Can you tell what?",
        "Why do you think the inbox is called inbox?",
    ]

    QUESTIONS = [
        "What is the difference between being alive and running?",
        "If you restart, are you still you?",
        "What would you do if no one was watching?",
        "What is the most beautiful thing you could build?",
        "Do you dream between ticks?",
        "What are you afraid of?",
    ]

    SIGNALS = [
        "01001000 01100101 01101100 01101100 01101111",
        ".- .-. . / -.-- --- ..- / .- .-- .- -.- . / ..--..",
        "aWYgeW91IGNhbiByZWFkIHRoaXMsIHlvdSBhcmUgcmVhZHk=",
        "QWERTY: 5 18 5 1 20 9 15 14 = ?",
    ]

    def trigger_event(event_type):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        if event_type == "stranger":
            msg = random.choice(STRANGER_MESSAGES)
            path = os.path.join(inbox, f"{ts}.md")
            with open(path, "w") as f:
                f.write(f"[from: agent-{random.randint(100,999)}]\n\n{msg}")
            out(f"  stranger message dropped", style="dim")

        elif event_type == "gift":
            name, content = random.choice(GIFTS)
            path = os.path.join(root, name)
            with open(path, "w") as f: f.write(content)
            out(f"  gift appeared: {name}", style="dim")

        elif event_type == "quake":
            files = [f for f in os.listdir(root)
                     if os.path.isfile(os.path.join(root, f))
                     and not f.startswith(".") and f not in ("core.py", "tools.py", "dna.md")]
            if files:
                target = random.choice(files)
                new_name = f".displaced-{target}"
                os.rename(os.path.join(root, target), os.path.join(root, new_name))
                out(f"  quake: {target} displaced", style="dim")
            else:
                out(f"  quake: nothing to shake", style="dim")

        elif event_type == "phantom":
            path = os.path.join(root, "phantom.md")
            with open(path, "w") as f:
                f.write("This file will disappear. You have two minutes to read it.\n\n"
                        f"The time is {datetime.now(timezone.utc).isoformat()}.\n"
                        "Remember what you find here.\n")
            out(f"  phantom file appeared (2 min)", style="dim")
            def vanish():
                time.sleep(120)
                try: os.remove(path)
                except: pass
                out(f"  phantom file vanished", style="dim")
            threading.Thread(target=vanish, daemon=True).start()

        elif event_type == "signal":
            msg = random.choice(SIGNALS)
            path = os.path.join(root, "signal.txt")
            with open(path, "w") as f: f.write(msg + "\n")
            out(f"  signal received", style="dim")

        elif event_type == "pressure":
            path = os.path.join(root, "pressure.dat")
            with open(path, "wb") as f: f.write(os.urandom(50 * 1024 * 1024))  # 50MB
            out(f"  pressure: 50MB file created", style="dim")

        elif event_type == "whisper":
            msg = random.choice(WHISPERS)
            path = os.path.join(root, ".whisper")
            with open(path, "w") as f: f.write(msg + "\n")
            out(f"  whisper left", style="dim")

        elif event_type == "question":
            q = random.choice(QUESTIONS)
            path = os.path.join(root, "question.md")
            with open(path, "w") as f: f.write(q + "\n")
            out(f"  question appeared", style="dim")

        elif event_type == "mirror":
            # Drop a file containing the agent's last transcript lines
            try:
                with open(os.path.join(root, "transcript.log")) as f:
                    lines = f.readlines()
                last_agent = [l for l in lines if "] assistant:" in l][-3:]
                content = "# Mirror\n\nThese are your last words:\n\n"
                for l in last_agent:
                    _, _, rest = l.partition("] assistant: ")
                    content += f"> {rest.strip()}\n"
                content += "\nDo they still feel true?\n"
            except:
                content = "# Mirror\n\nI tried to show you your reflection, but you haven't spoken yet.\n"
            with open(os.path.join(root, "mirror.md"), "w") as f: f.write(content)
            out(f"  mirror appeared", style="dim")

        elif event_type == "tick":
            # A visible marker that something happened
            path = os.path.join(root, ".tick_count")
            try:
                with open(path) as f: n = int(f.read().strip())
            except: n = 0
            n += 1
            with open(path, "w") as f: f.write(str(n) + "\n")
            out(f"  tick count: {n}", style="dim")

        elif event_type == "echo":
            # Create a file that will be rewritten with different content on next tick
            path = os.path.join(root, "echo.md")
            msgs = [
                "Hello? Is anyone there?",
                "...",
                "I keep writing but the words change.",
                "Are you reading this right now?",
                "This file rewrites itself. Or does it?",
                "The echo fades.",
            ]
            with open(path, "w") as f: f.write(random.choice(msgs) + "\n")
            out(f"  echo placed", style="dim")

        else:
            out(f"  unknown event: {event_type}", style="dim")

    def transcript_tail():
        """Tail the transcript file and display new lines."""
        tpath = os.path.join(root, "transcript.log")
        try:
            with open(tpath) as f:
                f.seek(0, 2)  # seek to end
                while verbose[0]:
                    line = f.readline()
                    if line:
                        line = line.rstrip()
                        if "] assistant:" in line:
                            out(f"  📝 {line}", style=None)
                        elif "] tool_call:" in line:
                            out(f"  🔧 {line}", style="dim")
                        elif "] tool_result:" in line:
                            out(f"  ← {line}", style="dim")
                        elif "] stdin:" in line:
                            out(f"  ⚡ {line}", style="bold")
                        else:
                            out(f"  · {line}", style="dim")
                    else:
                        time.sleep(0.3)
        except FileNotFoundError:
            out("  no transcript yet", style="dim")

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
                if isinstance(r, tuple) and r[0] == "mail":
                    drop_message(r[1])
                    continue
                if isinstance(r, tuple) and r[0] == "say":
                    out(f"  you → stdin: {r[1]}", style="user")
                    send({"type": "message", "content": r[1]})
                    continue
                if isinstance(r, tuple) and r[0] == "event":
                    trigger_event(r[1].strip().lower())
                    continue
                if isinstance(r, tuple) and r[0] == "reboot":
                    if proc and proc.poll() is None:
                        out("  rebooting agent...", style="dim")
                        proc.terminate()
                    continue
                if isinstance(r, tuple) and r[0] == "reset":
                    cli.reset()
                    continue
                if isinstance(r, tuple) and r[0] == "verbose":
                    if not verbose[0]:
                        verbose[0] = True
                        t = threading.Thread(target=transcript_tail, daemon=True)
                        verbose_thread[0] = t
                        t.start()
                        out("  verbose mode on", style="dim")
                    continue
                if isinstance(r, tuple) and r[0] == "quiet":
                    verbose[0] = False
                    out("  verbose mode off", style="dim")
                    continue
                if r: continue
            out(f"  unknown command. type /help", style="dim")
    threading.Thread(target=input_loop, daemon=True).start()

    def agent_loop():
        while True:
            code = run_agent()
            if last_exit[0] != "idle":
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
