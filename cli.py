#!/usr/bin/env python3
"""Interactive CLI for the human. Not part of the agent's world."""
import os, readline, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

DIM, RESET, BOLD, CYAN, RED = "\033[2m", "\033[0m", "\033[1m", "\033[36m", "\033[31m"

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

def _dim(text): 
    for line in text.rstrip().splitlines(): print(f"  {DIM}{line}{RESET}")

def _shell(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)

def handle_command(cmd):
    parts = cmd.strip().split(None, 1)
    if not parts: return False
    verb, arg = parts[0].lower(), parts[1] if len(parts) > 1 else ""

    if verb == "/help":
        print(HELP)
    elif verb == "/quit":
        return "quit"
    elif verb == "/files":
        path = os.path.join(ROOT, arg) if arg else ROOT
        try:
            for e in sorted(os.listdir(path)):
                if e.startswith(".") or e == "__pycache__": continue
                if os.path.isdir(os.path.join(path, e)): print(f"  {CYAN}{e}/{RESET}")
                else: print(f"  {e}")
        except Exception as e: print(f"  {RED}{e}{RESET}")
    elif verb == "/cat":
        if not arg: print(f"  {DIM}usage: /cat <file>{RESET}"); return True
        try:
            with open(os.path.join(ROOT, arg)) as f: content = f.read()
            print(f"{DIM}{'─'*40}{RESET}\n{content.rstrip()}\n{DIM}{'─'*40}{RESET}")
        except Exception as e: print(f"  {RED}{e}{RESET}")
    elif verb == "/git":
        _dim((_shell(f"git {arg or 'log --oneline -20'}").stdout or "(no output)"))
    elif verb == "/log":
        n = int(arg) if arg else 20
        try:
            with open(os.path.join(ROOT, "transcript.log")) as f: lines = f.readlines()
            for line in lines[-n:]:
                line = line.rstrip()
                if "] user:" in line:
                    ts, _, rest = line.partition("] ")
                    print(f"  {DIM}{ts}]{RESET} {BOLD}{rest}{RESET}")
                elif "] assistant:" in line:
                    ts, _, rest = line.partition("] ")
                    print(f"  {DIM}{ts}]{RESET} {rest}")
                else: print(f"  {DIM}{line}{RESET}")
        except FileNotFoundError: print(f"  {DIM}no transcript yet{RESET}")
    elif verb == "/tree":
        _dim(_shell("find . -not -path './.git/*' -not -path './.git' "
                    "-not -path './__pycache__/*' -not -name __pycache__ | sort | tail -n+2").stdout or "(empty)")
    elif verb == "/diff":
        _dim(_shell("git diff --stat $(git rev-list --max-parents=0 HEAD)..HEAD 2>/dev/null || echo 'no history'").stdout or "(none)")
    else: return False
    return True

def banner(): print(BANNER)
def prompt(): return input(f"\n{CYAN}›{RESET} ")
def goodbye(): print(f"\n{DIM}goodbye{RESET}")
