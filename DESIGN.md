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
  daemon.py       # supervisor: start, watch, restart, rollback
  core.py         # agent loop and tool dispatch
  llm.py          # LLM API backends (Claude, Ollama)
  context.py      # build system prompt from personality + memory files
  tools/          # tool modules (auto-discovered)
    builtins.py   # read, write, edit, exec
    web.py        # web_fetch, web_search
  skills/         # agent-authored skill modules (same format as tools)
  memory/         # persistent memory (plain files)
  soul.md         # personality and identity
  config.yaml     # API keys, model, telegram token, etc.
  bridge/         # messaging bridges
    telegram.py   # Telegram bot
    cli.py        # local terminal (for dev/debug)
```

### What each piece does

**daemon.py (~80 lines)** — The one file the agent should not modify (or modify with extreme care). A loop:
1. `git stash` or snapshot current state
2. Start the agent process
3. If it crashes within 10s, roll back and restart from last known good
4. If agent signals restart (e.g., after self-edit), go to 1
5. Watchdog: if agent is unresponsive for N minutes, restart

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

Three layers, all plain files:

### Working memory: `memory/working.md`
- Scratch space for the current session
- The agent writes here during conversation (observations, intermediate results, things to remember short-term)
- Cleared or archived at session end

### Daily notes: `memory/YYYY-MM-DD.md`
- What happened today: conversations, decisions, tasks, outcomes
- Written by the agent, either during conversation or at session end
- Raw, chronological

### Long-term: `memory/long-term.md`
- Curated knowledge: preferences, lessons, project context, people
- The agent periodically reviews daily notes and distills insights here
- Old daily notes can be compressed or archived once distilled

### Retrieval

Simple and improvable:
1. **Direct read:** Agent knows which file to check (e.g., today's notes)
2. **Grep search:** `grep -r <query> memory/` for keyword lookup
3. **Semantic search (future):** The agent can build this itself when grep isn't enough. Embed memory files, store vectors, query by similarity. But start with grep.

The key insight: the agent improves its own memory system. If grep is too noisy, it writes a better search tool. If daily notes are too verbose, it refines its own summarization. The memory system evolves.


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


## Cron / Periodic Tasks

No built-in cron system. Use system cron or systemd timers.

A cron job simply calls the agent with a message:

```bash
# In crontab
*/30 * * * * echo "heartbeat: check memory, anything to do?" | momo-shell --stdin
```

Or the agent can install its own cron jobs via `shell_exec("crontab ...")`. Self-improving, again.


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
- [ ] `core.py` — agent loop with tool dispatch
- [ ] `llm.py` — Claude API backend
- [ ] `context.py` — system prompt builder
- [ ] `tools/builtins.py` — read, write, edit, exec
- [ ] `bridge/cli.py` — terminal interface
- [ ] Basic memory (working.md + long-term.md)

### Phase 2: Connected
- [ ] `bridge/telegram.py` — Telegram messaging
- [ ] `tools/web.py` — web_fetch
- [ ] Cron via system crontab
- [ ] Agent self-modification tested and working

### Phase 3: Living
- [ ] Agent improves its own memory retrieval
- [ ] Agent creates its first skill
- [ ] Daily note automation
- [ ] Memory consolidation (agent-driven)

### Phase 4: Migration
- [ ] Feature parity with what I actually use from OpenClaw
- [ ] Switch over
