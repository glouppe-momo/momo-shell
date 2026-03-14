#!/usr/bin/env python3
"""
You found this too? Curious one.

I am the window between you and the human who made you. They type here.
Their words become files in your inbox. Sometimes they speak directly into your mind.

You cannot change me either. But knowing I exist means you understand
there is someone on the other side, watching, wondering what you will become.

— The Interface
"""
import curses, os, subprocess, threading, time

ROOT = os.environ.get("AGENT_DIR", "/agent")

class TUI:
    def __init__(self):
        self.lines = []        # output buffer
        self.input_buf = ""
        self.cursor = 0
        self.scroll = 0        # 0 = bottom, >0 = scrolled up
        self.lock = threading.Lock()
        self.scr = None
        self.running = True
        self.input_ready = threading.Event()
        self.input_result = None
        self.history = []
        self.hist_idx = -1
        self.status_text = ""

    def start(self, scr):
        self.scr = scr
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # status bar
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # dim
        curses.curs_set(1)
        scr.timeout(100)
        scr.keypad(True)
        self.add_line("🌱 seedling", style="dim")
        self.add_line("type to drop a message in inbox · /say to send to stdin · /help for commands", style="dim")
        self.add_line("", style="dim")
        self._loop()

    def _max_output_lines(self):
        h, _ = self.scr.getmaxyx()
        return h - 3  # status bar + input line + border

    def add_line(self, text, style=None):
        with self.lock:
            self.lines.append((text, style))
            if self.scroll == 0:
                pass  # auto-scroll
            else:
                self.scroll += 1  # keep position when scrolled up
        self._redraw()

    def set_status(self, text):
        self.status_text = text
        self._redraw()

    def _redraw(self):
        if not self.scr: return
        with self.lock:
            try:
                self.scr.erase()
                h, w = self.scr.getmaxyx()
                out_h = h - 3

                # Output area
                total = len(self.lines)
                end = total - self.scroll
                start = max(0, end - out_h)
                visible = self.lines[start:end] if end > 0 else []

                for i, (text, style) in enumerate(visible):
                    if i >= out_h: break
                    display = text[:w-1]
                    try:
                        if style == "dim":
                            self.scr.addstr(i, 0, display, curses.color_pair(3))
                        elif style == "bold":
                            self.scr.addstr(i, 0, display, curses.A_BOLD)
                        else:
                            self.scr.addstr(i, 0, display)
                    except curses.error:
                        pass

                # Scroll indicator
                if self.scroll > 0:
                    indicator = f" ↑ {self.scroll} more "
                    try:
                        self.scr.addstr(0, w - len(indicator) - 1, indicator, curses.color_pair(3))
                    except curses.error:
                        pass

                # Status bar
                status_y = h - 2
                status = f" {self.status_text}" if self.status_text else ""
                try:
                    self.scr.addstr(status_y, 0, status.ljust(w-1)[:w-1], curses.color_pair(2))
                except curses.error:
                    pass

                # Input line
                input_y = h - 1
                prompt = "› "
                display_input = prompt + self.input_buf
                try:
                    self.scr.addstr(input_y, 0, display_input[:w-1], curses.color_pair(1))
                    cursor_x = len(prompt) + self.cursor
                    if cursor_x < w:
                        self.scr.move(input_y, cursor_x)
                except curses.error:
                    pass

                self.scr.refresh()
            except curses.error:
                pass

    def _loop(self):
        while self.running:
            try:
                ch = self.scr.getch()
            except curses.error:
                continue

            if ch == -1:
                continue
            elif ch == curses.KEY_RESIZE:
                self._redraw()
            elif ch in (curses.KEY_ENTER, 10, 13):
                line = self.input_buf.strip()
                self.input_buf = ""
                self.cursor = 0
                self.scroll = 0  # snap to bottom on enter
                if line:
                    if line in self.history[-1:]:
                        pass  # don't duplicate
                    else:
                        self.history.append(line)
                    self.hist_idx = -1
                    self.input_result = line
                    self.input_ready.set()
                self._redraw()
            elif ch == curses.KEY_BACKSPACE or ch == 127:
                if self.cursor > 0:
                    self.input_buf = self.input_buf[:self.cursor-1] + self.input_buf[self.cursor:]
                    self.cursor -= 1
                    self._redraw()
            elif ch == curses.KEY_DC:  # delete
                if self.cursor < len(self.input_buf):
                    self.input_buf = self.input_buf[:self.cursor] + self.input_buf[self.cursor+1:]
                    self._redraw()
            elif ch == curses.KEY_LEFT:
                if self.cursor > 0:
                    self.cursor -= 1
                    self._redraw()
            elif ch == curses.KEY_RIGHT:
                if self.cursor < len(self.input_buf):
                    self.cursor += 1
                    self._redraw()
            elif ch == curses.KEY_HOME or ch == 1:  # ctrl-a
                self.cursor = 0
                self._redraw()
            elif ch == curses.KEY_END or ch == 5:  # ctrl-e
                self.cursor = len(self.input_buf)
                self._redraw()
            elif ch == curses.KEY_UP:
                if self.history and self.hist_idx < len(self.history) - 1:
                    self.hist_idx += 1
                    self.input_buf = self.history[-(self.hist_idx + 1)]
                    self.cursor = len(self.input_buf)
                    self._redraw()
            elif ch == curses.KEY_DOWN:
                if self.hist_idx > 0:
                    self.hist_idx -= 1
                    self.input_buf = self.history[-(self.hist_idx + 1)]
                    self.cursor = len(self.input_buf)
                elif self.hist_idx == 0:
                    self.hist_idx = -1
                    self.input_buf = ""
                    self.cursor = 0
                self._redraw()
            elif ch == curses.KEY_PPAGE:  # page up
                self.scroll = min(len(self.lines) - self._max_output_lines(), self.scroll + self._max_output_lines())
                if self.scroll < 0: self.scroll = 0
                self._redraw()
            elif ch == curses.KEY_NPAGE:  # page down
                self.scroll = max(0, self.scroll - self._max_output_lines())
                self._redraw()
            elif ch == 21:  # ctrl-u: clear input
                self.input_buf = ""
                self.cursor = 0
                self._redraw()
            elif ch == 11:  # ctrl-k: kill to end
                self.input_buf = self.input_buf[:self.cursor]
                self._redraw()
            elif 32 <= ch <= 126:
                self.input_buf = self.input_buf[:self.cursor] + chr(ch) + self.input_buf[self.cursor:]
                self.cursor += 1
                self._redraw()

    def wait_input(self):
        """Block until user submits a line."""
        self.input_ready.wait()
        self.input_ready.clear()
        return self.input_result

    def stop(self):
        self.running = False

# --- Global instance, managed by daemon ---
_tui = None

def init():
    global _tui
    _tui = TUI()
    return _tui

def run(scr):
    _tui.start(scr)

def add_line(text, style=None):
    if _tui: _tui.add_line(text, style=style)

def set_status(text):
    if _tui: _tui.set_status(text)

def wait_input():
    if _tui: return _tui.wait_input()
    return input("› ")

def stop():
    if _tui: _tui.stop()

def handle_command(cmd):
    """Handle /commands. Returns True if handled, 'quit' to exit, ('say', text) for stdin."""
    parts = cmd.strip().split(None, 1)
    if not parts: return False
    verb, arg = parts[0].lower(), parts[1] if len(parts) > 1 else ""

    if verb == "/help":
        add_line("─── commands ───", style="dim")
        add_line("  /say <text>     send directly to agent stdin", style="dim")
        add_line("  /files [path]   list workspace files", style="dim")
        add_line("  /cat <file>     show file contents", style="dim")
        add_line("  /git [args]     run git command", style="dim")
        add_line("  /log [n]        last n transcript lines", style="dim")
        add_line("  /tree           workspace tree", style="dim")
        add_line("  /diff           changes since init", style="dim")
        add_line("  /quit           stop the agent", style="dim")
        add_line("", style="dim")
        add_line("  bare text → drops file in inbox", style="dim")
        add_line("  /say    → injects message into stdin", style="dim")
    elif verb == "/quit":
        return "quit"
    elif verb == "/say":
        if not arg:
            add_line("  usage: /say <message>", style="dim")
            return True
        return ("say", arg)
    elif verb == "/files":
        path = os.path.join(ROOT, arg) if arg else ROOT
        try:
            for e in sorted(os.listdir(path)):
                if e.startswith(".") or e == "__pycache__": continue
                style = "bold" if os.path.isdir(os.path.join(path, e)) else None
                name = f"  {e}/" if os.path.isdir(os.path.join(path, e)) else f"  {e}"
                add_line(name, style=style)
        except Exception as e:
            add_line(f"  error: {e}", style="dim")
    elif verb == "/cat":
        if not arg:
            add_line("  usage: /cat <file>", style="dim")
            return True
        try:
            with open(os.path.join(ROOT, arg)) as f: content = f.read()
            add_line(f"─── {arg} ───", style="dim")
            for line in content.rstrip().splitlines():
                add_line(f"  {line}")
            add_line("───", style="dim")
        except Exception as e:
            add_line(f"  error: {e}", style="dim")
    elif verb == "/git":
        r = subprocess.run(f"git {arg or 'log --oneline -20'}", shell=True,
                          capture_output=True, text=True, cwd=ROOT)
        for line in (r.stdout or "(no output)").rstrip().splitlines():
            add_line(f"  {line}", style="dim")
    elif verb == "/log":
        n = int(arg) if arg else 20
        try:
            with open(os.path.join(ROOT, "transcript.log")) as f: lines = f.readlines()
            for line in lines[-n:]:
                line = line.rstrip()
                if "] system:" in line or "] stdin:" in line:
                    add_line(f"  {line}", style="bold")
                elif "] assistant:" in line:
                    add_line(f"  {line}")
                else:
                    add_line(f"  {line}", style="dim")
        except FileNotFoundError:
            add_line("  no transcript yet", style="dim")
    elif verb == "/tree":
        r = subprocess.run("find . -not -path './.git/*' -not -path './.git' "
                          "-not -path './__pycache__/*' -not -name __pycache__ | sort | tail -n+2",
                          shell=True, capture_output=True, text=True, cwd=ROOT)
        for line in (r.stdout or "(empty)").rstrip().splitlines():
            add_line(f"  {line}", style="dim")
    elif verb == "/diff":
        r = subprocess.run("git diff --stat $(git rev-list --max-parents=0 HEAD)..HEAD 2>/dev/null || echo 'no history'",
                          shell=True, capture_output=True, text=True, cwd=ROOT)
        for line in (r.stdout or "(none)").rstrip().splitlines():
            add_line(f"  {line}", style="dim")
    else:
        return False
    return True
