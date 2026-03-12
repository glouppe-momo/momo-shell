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


## Architecture

```
momo-shell/
  daemon.py       # supervisor: agent process + clock loop, crash recovery
  clock.py        # body rhythm: schedule periodic tasks (scribe, heartbeat, etc.)
  core.py         # agent loop and tool dispatch
  llm.py          # LLM API backends (Claude, Ollama)
  context.py      # build system prompt from personality + memory files
  tools/          # tool modules (auto-discovered)
    builtins.py   # read, write, edit, exec
    web.py        # web_fetch, web_search
  skills/         # agent-authored skill modules (same format as tools)
  memory/         # persistent memory (plain files)
    subconscious/ # background memory processors (agent-editable)
      capture.py  # logs all messages to transcript
      scribe.py   # distills transcript into structured notes
      consolidate.py  # promotes daily notes to long-term memory
  soul.md         # personality and identity
  config.yaml     # API keys, model, telegram token, etc.
  bridge/         # messaging bridges
    telegram.py   # Telegram bot
    cli.py        # local terminal (for dev/debug)
```

### What each piece does

**daemon.py (~120 lines)** — The one file the agent should not modify (or modify with extreme care). Manages the agent process and the body clock:
1. `git stash` or snapshot current state
2. Start the agent process (core.py + bridge)
3. Run the clock loop (tick every 60s, fire due tasks)
4. If agent crashes within 10s, roll back and restart from last known good
5. If agent signals restart (e.g., after self-edit), go to 1
6. Watchdog: if agent is unresponsive for N minutes, restart
7. On clean shutdown: trigger a final scribe run (capture session-end memories)

**core.py (~150 lines)** — The agent loop:
1. Receive input (from bridge or CLI)
2. Build messages array (system prompt + conversation)
3. Call LLM
4. Parse response for tool calls
5. Execute tools, feed results back
6. Repeat until LLM gives a plain text response
7. Send response back through bridge

**llm.py (~60 lines)** — Thin wrappers around LLM APIs. Anthropic (Claude) as primary, Ollama as local fallback. Just `call(messages, model) -> str`. Streaming optional.

**context.py (~60 lines)** — Builds the system prompt:
1. Read `soul.md` (personality, identity)
2. Read memory files (today's notes, long-term memory)
3. Enumerate available tools (from `tools/` and `skills/`)
4. Assemble into a single system prompt string

**bridge/ (~100 lines each)** — Messaging adapters. Each exposes the same interface: `listen() -> messages`, `send(text)`. Start with Telegram + CLI.


## Memory System

Memory is **subconscious by default**. The agent doesn't actively decide to remember things during conversation. Background processes handle capture, structuring, and consolidation automatically. The agent just talks; memory happens.

### The subconscious pipeline

Three background processes in `memory/subconscious/`. The agent can read, edit, and improve all of them.

**1. Capture (`capture.py`) — always running, zero LLM cost**

A middleware in the message flow. Every message in and out gets appended to `memory/transcript.jsonl`:

```json
{"ts": "2026-03-12T16:45:00", "role": "user", "text": "..."}
{"ts": "2026-03-12T16:45:12", "role": "assistant", "text": "..."}
```

No intelligence, no filtering. Just a log. This is the rawest form of memory, like sensory input before processing. Runs in-process (not a separate LLM call), triggered by the message flow in `core.py`.

**2. Scribe (`scribe.py`) — periodic, uses LLM**

Runs every ~30 minutes (or on session end). Reads the transcript since last run, calls a (cheap/local) LLM to produce structured notes:

- What was discussed
- Decisions made
- Tasks mentioned
- Things worth remembering

Writes to `memory/YYYY-MM-DD.md` (today's daily notes). Clears processed transcript entries.

The scribe prompt itself lives in `memory/subconscious/scribe.py` and is editable by the agent. If the notes are too verbose or miss important things, the agent can refine how the scribe works.

**3. Consolidator (`consolidate.py`) — daily/weekly, uses LLM**

Runs once per day (or on demand). Reviews recent daily notes and updates long-term memory:

- `memory/long-term.md` — curated knowledge, lessons, preferences, people
- Compresses old daily notes (optional)
- Identifies patterns across days

Also agent-editable. The consolidation strategy evolves as the agent learns what's worth keeping.

### Memory files (the "conscious" layer)

The agent reads these during conversation. They're just files:

| File | What | Written by |
|------|------|-----------|
| `memory/transcript.jsonl` | Raw message log | Capture (automatic) |
| `memory/YYYY-MM-DD.md` | Today's structured notes | Scribe (background) |
| `memory/long-term.md` | Curated long-term knowledge | Consolidator (background) + agent (manual) |
| `memory/working.md` | Scratch pad for current session | Agent (conscious) |

The agent can also write to any memory file directly. The subconscious processes handle the routine; the agent handles the exceptional ("I need to remember this specific thing right now").

### Retrieval

Simple and improvable:
1. **Context injection:** `context.py` loads today's notes + long-term.md into the system prompt automatically
2. **Direct read:** Agent reads a specific file when it knows where to look
3. **Grep search:** `grep -r <query> memory/` for keyword lookup
4. **Semantic search (future):** The agent builds this itself when grep isn't enough

The key insight: the agent improves its own memory system. The scribe produces bad notes? Edit `scribe.py`. Grep is too noisy? Write a `skills/memory_search.py` with embeddings. The consolidator misses patterns? Rewrite its prompt. The subconscious evolves.

### Clock integration

The subconscious processes run on the body clock (see **Clock** section):
- Capture runs in-process (just a function call in the message pipeline, not clocked)
- Scribe is a clock rhythm (default: every 30 min)
- Consolidator is a clock rhythm (default: daily at 3 AM)

All three are restartable, crash-safe, and independent of each other.


## Tool System

Tools are Python functions in `tools/*.py` and `skills/*.py`. Auto-discovered by introspection.

### Tool format

```python
# tools/builtins.py

def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    with open(path) as f:
        return f.read()

def shell_exec(command: str, timeout: int = 30) -> str:
    """Execute a shell command and return stdout/stderr."""
    r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr if r.returncode != 0 else r.stdout
```

That's it. A function with type hints and a docstring. The runtime introspects these to build tool descriptions for the LLM.

### Discovery

```python
# In context.py or core.py
def discover_tools(dirs=["tools", "skills"]):
    """Walk dirs, import modules, extract functions with docstrings."""
    tools = {}
    for dir in dirs:
        for file in glob(f"{dir}/*.py"):
            module = import_module(file)
            for name, fn in inspect.getmembers(module, inspect.isfunction):
                if fn.__doc__:  # only functions with docstrings are tools
                    tools[name] = fn
    return tools
```

### Self-improvement

The `skills/` directory is where the agent writes new tools. Same format as `tools/`, but agent-authored. Examples of what the agent might create:

- `skills/telegram_summary.py` — summarize unread Telegram messages
- `skills/arxiv.py` — fetch and filter arXiv papers
- `skills/calendar.py` — Google Calendar integration

The agent creates these by writing Python files. No registration, no config. Drop a `.py` file with typed functions and docstrings, and it's available next turn.

To improve an existing tool: read it, edit it, done. Takes effect on the next tool call (or after restart for structural changes).

### Built-in tools (v0)

Starting set, deliberately minimal:

| Tool | Description |
|------|-------------|
| `read_file(path)` | Read a file |
| `write_file(path, content)` | Write/overwrite a file |
| `edit_file(path, old, new)` | Replace exact text in a file |
| `shell_exec(command, timeout)` | Run a shell command |
| `web_fetch(url)` | Fetch URL, extract readable text |
| `list_tools()` | List all available tools (for self-awareness) |
| `restart()` | Signal the supervisor to restart the agent |

Everything else gets built by the agent as needed.


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

### Bridge interface

```python
class Bridge:
    def listen(self) -> Generator[Message]:
        """Yield incoming messages."""
        ...

    def send(self, text: str):
        """Send a response."""
        ...

    def send_file(self, path: str, caption: str = ""):
        """Send a file/image."""
        ...
```

### Telegram bridge (~100 lines)

Uses `python-telegram-bot` or raw Bot API via `requests`. Polls for updates, dispatches to the agent loop. Sends responses back.

### CLI bridge (~30 lines)

`input()` loop. For development and debugging. Already exists in Miniature.


## Clock — The Body Rhythm

The agent has an internal clock (`clock.py`, ~80 lines) that coordinates all periodic processes. Think of it as a biological rhythm: heartbeat, breathing, sleep cycles. Not a dumb cron table, but a living schedule the agent can introspect and modify.

### How it works

The clock is a simple event loop running inside the daemon. It maintains a schedule of named tasks with intervals:

```python
# clock.py

schedule = {
    "scribe":      {"every": "30m",  "fn": run_scribe,      "last": None},
    "consolidate": {"every": "24h",  "fn": run_consolidator, "last": None},
    "heartbeat":   {"every": "1h",   "fn": run_heartbeat,    "last": None},
}

def tick():
    """Called every minute by the daemon. Runs anything that's due."""
    now = time.time()
    for name, task in schedule.items():
        if task["last"] is None or now - task["last"] >= parse_interval(task["every"]):
            task["fn"]()
            task["last"] = now
```

That's the core. ~30 lines for the scheduler itself.

### What runs on the clock

| Rhythm | Default interval | What it does |
|--------|-----------------|--------------|
| **Scribe** | 30 min | Distill transcript into daily notes |
| **Consolidator** | 24h (3 AM) | Promote daily notes to long-term memory |
| **Heartbeat** | 1h | Agent wakes up, checks if anything needs attention |

The heartbeat is the interesting one. It's a scheduled LLM call where the agent gets to look around: check for pending tasks, review recent memory, decide if it needs to reach out. Proactive behavior without constant polling.

### Adaptive rhythms

The schedule is a file the agent can read and modify. Examples of self-adaptation:

- **Active conversation:** Scribe interval drops to 10 min (more to capture)
- **Idle hours:** Heartbeat stretches to 2h, scribe pauses entirely
- **Night (23:00-07:00):** Everything sleeps except capture. Consolidator runs once at 3 AM.
- **After self-edit:** Immediate scribe run (capture what just changed and why)

The agent modifies rhythms by editing `clock.py` or a `clock.yaml` config:

```yaml
# clock.yaml (agent-editable)
scribe:
  every: 30m
  quiet_hours: "23:00-07:00"  # pause during sleep
consolidate:
  every: 24h
  at: "03:00"                 # prefer a specific time
heartbeat:
  every: 1h
  idle_stretch: 2h            # stretch when no conversation
  quiet_hours: "23:00-07:00"
```

### Custom rhythms

The agent can add new periodic tasks by adding entries to the schedule. Examples it might create over time:

- **arXiv check** — daily at 7:30 AM
- **Email poll** — every 2h during business hours
- **Weather** — twice daily
- **Git backup** — every 6h, push to remote

Adding a rhythm = writing a function + adding a schedule entry. Same self-improvement pattern as tools.

### Daemon integration

The daemon runs the clock loop:

```python
# In daemon.py
while True:
    clock.tick()     # check if anything is due
    time.sleep(60)   # resolution: 1 minute
```

The clock runs in the daemon process, not the agent process. This means scheduled tasks (scribe, consolidator) keep running even if the agent is idle or restarting. The heartbeat is the exception: it starts a fresh agent interaction.


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

### Phase 1: Core
- [ ] `daemon.py` — supervisor with crash recovery and rollback
- [ ] `clock.py` — body rhythm scheduler
- [ ] `core.py` — agent loop with tool dispatch
- [ ] `llm.py` — Claude API backend
- [ ] `context.py` — system prompt builder
- [ ] `tools/builtins.py` — read, write, edit, exec
- [ ] `bridge/cli.py` — terminal interface
- [ ] Memory: capture (in-process) + scribe (on clock) + file-based storage

### Phase 2: Connected
- [ ] `bridge/telegram.py` — Telegram messaging
- [ ] `tools/web.py` — web_fetch
- [ ] Heartbeat rhythm on the clock
- [ ] Agent self-modification tested and working

### Phase 3: Living
- [ ] Agent improves its own memory retrieval
- [ ] Agent creates its first skill
- [ ] Agent adapts its own clock rhythms
- [ ] Consolidator running, long-term memory growing

### Phase 4: Migration
- [ ] Feature parity with what I actually use from OpenClaw
- [ ] Switch over
