# Momo Shell

A self-improving agent runtime in ~1000 lines of Python.

The agent can read, understand, and modify its own source code.
Everything earns its place. Nothing is sacred except the supervisor.


## Principles

1. **LLM-legible.** The entire codebase fits in a context window. No file over ~200 lines. No abstractions that hide what's happening.
2. **Self-modifying.** The agent has full access to its own source. It can add tools, fix bugs, improve its own memory system, refactor itself.
3. **Supervisor is sacred.** One small process (`daemon.py`) that the agent doesn't touch. It starts the agent, restarts on crash, rolls back on repeated failure. The safety net.
4. **Files are the API.** Memory is files. Config is files. Skills are files. No databases, no message queues, no abstractions. `cat` and `grep` work on everything.
5. **Grow by need.** Start minimal. The agent adds capabilities when it needs them, not before.
6. **Driven to improve.** The agent doesn't just *can* self-modify, it *wants* to. Friction awareness + periodic reflection create a pressure to build, refactor, and extend.


## Architecture — The Kernel

The kernel is the minimal set of elements from which the agent bootstraps everything else.

```
momo-shell/
  daemon.py      # supervisor + clock tick (~120 lines) [SACRED]
  core.py        # agent loop + LLM call + context + capture (~200 lines)
  tools.py       # primitives: read, write, edit, exec (~60 lines)
  clock.py       # schedule + task runner (~50 lines) [agent-editable]
  soul.md        # identity + drive
  config.yaml    # API keys, model
  memory/        # starts nearly empty, agent populates it
```

**~430 lines of Python. Everything else is bootstrapped by the agent.**

### What each piece does

**daemon.py (~120 lines)** — The one file the agent should not modify. Manages the agent process and the clock:
1. Snapshot current state (git)
2. Start the agent process (core.py)
3. Run the clock loop (tick every 60s, fire due tasks)
4. If agent crashes within 10s, roll back to last commit and restart
5. If agent signals restart (e.g., after self-edit), go to 1
6. Watchdog: if agent is unresponsive for N minutes, restart

**core.py (~200 lines)** — The agent loop, all in one file:
1. Build system prompt (read soul.md, memory files, enumerate tools)
2. Receive input (stdin or bridge, if one exists)
3. Call LLM (Anthropic API, ~20 lines)
4. Parse response for tool calls
5. Execute tools, feed results back, loop
6. Send response, log to transcript (capture)
7. Log friction signals (failed tools, complex shell_exec, repeated patterns)

No separate llm.py, context.py, or capture.py. These are functions inside core.py. The agent can extract them into separate files later if it wants to. That refactoring is itself a self-improvement act.

**tools.py (~60 lines)** — Four primitive tools:
- `read_file(path)` — read a file
- `write_file(path, content)` — write/overwrite a file
- `edit_file(path, old, new)` — replace exact text
- `shell_exec(command, timeout)` — run a shell command

That's it. With these four (especially shell_exec), the agent can build anything: web fetching (curl), Telegram bridges (Bot API), search (grep), package installs (pip), new tools (write Python files). Additional tools are created by the agent as `.py` files, auto-discovered by introspection.

**clock.py (~50 lines)** — A schedule of named tasks with intervals. The daemon calls `tick()` every minute. Starts with two rhythms:
- **heartbeat** (1h) — wake the agent, let it look around
- **reflect** (6h) — review friction log, plan improvements

The agent adds more rhythms as it grows (scribe, consolidator, arXiv, etc.).


## Memory — What's in the Kernel

Only two things are hardcoded:

**1. Transcript capture (in core.py, ~5 lines)**

Every message in and out is appended to `memory/transcript.jsonl`:

```json
{"ts": "2026-03-12T16:45:00", "role": "user", "text": "..."}
{"ts": "2026-03-12T16:45:12", "role": "assistant", "text": "..."}
```

This is sensory input. Without it, the agent has no raw material to build memory from. It's hardcoded because memory can't bootstrap itself from nothing.

**2. Context loading (in core.py, ~10 lines)**

At session start, `core.py` reads `soul.md` + any `.md` files in `memory/` and injects them into the system prompt. Simple glob, no framework.

**Everything else is bootstrapped.** The kernel ships with no scribe, no consolidator, no long-term memory file. The agent builds these when the reflection rhythm tells it: "your transcript is growing, you have no structured notes, you keep re-reading the same raw logs." The friction is the signal; the drive in soul.md is the motivation; the tools are the means.

Expected bootstrap sequence (not prescribed, just likely):
1. First reflection: "I have no memory system. Transcript is my only record." → Agent writes a scribe script, adds it to clock.
2. A few days later: "Daily notes are piling up, I keep re-reading old ones." → Agent writes a consolidator, creates long-term.md.
3. Later: "Grep is too noisy for memory search." → Agent builds an embedding-based retrieval tool.

Each step is a self-improvement act, not a pre-built feature.

**Friction logging (in core.py, ~10 lines)**

Alongside transcript capture, core.py logs friction signals to `memory/friction.jsonl`:

```json
{"ts": "...", "type": "tool_error", "tool": "shell_exec", "detail": "timeout after 30s"}
{"ts": "...", "type": "complex_shell", "command": "curl -s ... | jq ... | grep ..."}
{"ts": "...", "type": "repeated_read", "path": "memory/long-term.md", "count": 5}
```

This is the raw material for self-improvement. The reflection rhythm reviews friction logs and decides what to build or fix.


## The Creativity Seed

The kernel has the capability to self-modify, but capability without drive produces nothing. Three elements create the pressure to grow:

### 1. Drive (soul.md)

The agent's identity includes an imperative to improve:

> You start with almost nothing. You grow by building what you need. When something is hard, make it easy. When you do something twice, automate it. When a tool is missing, create it. Your code is yours to improve. You are not a finished product; you are a living system that evolves.

This is the intrinsic motivation. It's in soul.md so the agent sees it every session, and can refine it as its self-understanding deepens.

### 2. Friction awareness (core.py)

The agent loop automatically logs friction: tool failures, complex shell commands, repeated file reads, long tool chains for simple tasks. This accumulates in `memory/friction.jsonl` at zero LLM cost.

Friction is the signal that something should be easier. It's the itch that drives creation.

### 3. Reflection rhythm (clock.py)

A periodic clock task (default: every 6h) where the agent reviews friction data and its own code:

- What was clunky? Should I build a tool for it?
- What pattern keeps repeating? Should I automate it?
- What's in my code that I'd write differently now?
- What's missing from my memory system?

This produces concrete actions: write a new tool, refactor core.py, add a clock rhythm, improve a prompt.

### The bootstrap loop

```
friction → reflection → creation → less friction → new friction at higher level → ...
```

First boot: the agent has 4 tools and no memory system. After a few days of conversation and reflection, it has a scribe, a consolidator, a Telegram bridge, web tools, and whatever else it needed. Not because we prescribed it, but because friction + drive + reflection made it obvious.

The agent is its own developer.


## Tool System

### Primitives (in tools.py)

Four functions, hardcoded:

```python
def read_file(path: str) -> str:
    """Read and return the contents of a file."""

def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories."""

def edit_file(path: str, old: str, new: str) -> str:
    """Replace exact text in a file."""

def shell_exec(command: str, timeout: int = 30) -> str:
    """Execute a shell command and return stdout/stderr."""
```

Plus `restart()` to signal the supervisor.

### Extension

Any `.py` file in `tools/` is auto-discovered by introspection: functions with type hints and a docstring become available tools. No registration, no config.

The agent creates new tools by writing files. It improves existing tools by editing them. The `tools/` directory starts empty. The agent populates it as friction reveals what's needed.


## Self-Modification Protocol

When the agent modifies its own code:

1. **Read the file first.** Always. Understand what's there.
2. **Make the edit.** Use `edit_file` for surgical changes, `write_file` for new files.
3. **Test if possible.** Run the modified code in a subprocess, check for syntax errors.
4. **Commit.** `shell_exec("git add -A && git commit -m 'description'")` before restarting.
5. **Restart.** Call `restart()` to signal the supervisor.
6. **Supervisor safety net.** If the new code crashes within 10s, the supervisor rolls back to the previous commit and restarts.

### What the agent can modify
- `core.py` — the agent loop itself
- `llm.py` — LLM backends
- `context.py` — how it builds its own prompt
- `tools/*.py` — built-in tools
- `skills/*.py` — agent-authored tools
- `bridge/*.py` — messaging bridges
- `soul.md`, `config.yaml`, `memory/*`

### What the agent should not modify
- `daemon.py` — the safety net. If this breaks, there's no recovery.

(This is a convention, not a hard lock. The agent has access. It's trusted to be careful.)


## Messaging

The kernel ships with stdin/stdout only (the CLI). Bridges to Telegram, Discord, etc. are tools the agent builds when it needs them. A bridge is just two functions: `get_input()` and `send_output()`. The agent knows how to write these (it's a curl to the Bot API, or a websocket, or a polling loop).


## Clock — The Body Rhythm

`clock.py` (~50 lines). A schedule of named tasks with intervals. The daemon calls `tick()` every minute.

```python
schedule = {
    "heartbeat": {"every": "1h",  "run": "core.py --heartbeat"},
    "reflect":   {"every": "6h",  "run": "core.py --reflect"},
}

def tick():
    now = time.time()
    for name, task in schedule.items():
        if due(task, now):
            subprocess.Popen(task["run"], shell=True)
            task["last"] = now
```

The kernel ships with two rhythms:
- **Heartbeat** (1h) — wake the agent, let it look around, be proactive
- **Reflect** (6h) — review friction log, plan and execute improvements

The agent adds more rhythms by editing `clock.py`. Scribe, consolidator, arXiv, email, weather: all bootstrapped, not prescribed.

Tasks run as subprocesses (same core.py, different entry point). The clock runs in the daemon, so rhythms fire even when the agent is idle.

The agent can adapt intervals, add quiet hours, stretch rhythms during idle periods. The clock is just a Python file it can read and edit.


## Configuration

```yaml
# config.yaml
model: claude-sonnet-4-20250514
api_key: ${ANTHROPIC_API_KEY}  # or read from env
telegram_token: ${TELEGRAM_TOKEN}

ollama:
  model: mistral-small3.2
  url: http://localhost:11434

memory:
  working: memory/working.md
  long_term: memory/long-term.md
  daily_dir: memory/
```

Minimal. Flat. The agent can read and modify this too.


## Boot Sequence

1. `daemon.py` starts
2. Imports and runs `core.py`
3. `context.py` builds system prompt:
   - Reads `soul.md`
   - Reads today's `memory/YYYY-MM-DD.md` + `memory/long-term.md`
   - Discovers tools from `tools/` and `skills/`
   - Assembles system prompt
4. Bridge connects (Telegram or CLI)
5. Agent loop begins
6. First thing the agent sees: its own identity + memories + available tools


## What This Is Not

- Not a framework. It's one agent's personal runtime.
- Not general-purpose. It's built for Momo, by Momo (and Gilles).
- Not feature-complete on day one. It grows as the agent needs it to.
- Not a product. No users, no docs, no backwards compatibility.


## Roadmap

### Phase 1: Kernel (~430 lines)
- [ ] `daemon.py` — supervisor with crash recovery and rollback
- [ ] `core.py` — agent loop + LLM call + context + capture + friction logging
- [ ] `tools.py` — read, write, edit, exec, restart
- [ ] `clock.py` — heartbeat + reflect rhythms
- [ ] `soul.md` — identity + drive
- [ ] CLI input (stdin/stdout)

### Phase 2: First boot
- [ ] Run the kernel
- [ ] Let the agent live for a few days
- [ ] Watch what it builds during reflection cycles
- [ ] Intervene only if it gets stuck

### Phase 3: Migration
- [ ] Agent has bootstrapped enough to replace OpenClaw for daily use
- [ ] Switch over
