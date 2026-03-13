#!/usr/bin/env python3
"""Interactive CLI for the human. Not part of the agent's world."""

import os, readline, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# --- Colors ---
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
RED = "\033[31m"

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


def cmd_output(text):
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
        return "quit"
    elif verb == "/files":
        path = os.path.join(ROOT, arg) if arg else ROOT
        try:
            for e in sorted(os.listdir(path)):
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
                with open(os.path.join(ROOT, arg)) as f:
                    content = f.read()
                print(f"{DIM}{'─' * 40}{RESET}")
                print(content.rstrip())
                print(f"{DIM}{'─' * 40}{RESET}")
            except Exception as e:
                print(f"  {RED}{e}{RESET}")
    elif verb == "/git":
        git_cmd = arg or "log --oneline -20"
        r = subprocess.run(f"git {git_cmd}", shell=True, capture_output=True,
                           text=True, cwd=ROOT)
        cmd_output(r.stdout or r.stderr or "(no output)")
    elif verb == "/log":
        n = int(arg) if arg else 20
        try:
            with open(os.path.join(ROOT, "transcript.log")) as f:
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
            "find . -not -path './.git/*' -not -path './.git' "
            "-not -path './__pycache__/*' -not -name '__pycache__' | sort | tail -n +2",
            shell=True, capture_output=True, text=True, cwd=ROOT)
        cmd_output(r.stdout or "(empty)")
    elif verb == "/diff":
        r = subprocess.run(
            "git diff --stat $(git rev-list --max-parents=0 HEAD)..HEAD 2>/dev/null || echo 'no history'",
            shell=True, capture_output=True, text=True, cwd=ROOT)
        cmd_output(r.stdout or "(no changes)")
    else:
        return False
    return True


def banner():
    print(BANNER)


def prompt():
    return input(f"\n{PROMPT}")


def goodbye():
    print(f"\n{DIM}goodbye{RESET}")
