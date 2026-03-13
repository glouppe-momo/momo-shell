# 🌀

A self-improving agent in ~320 lines of Python. It can read, understand, and modify its own source code. Everything else it bootstraps itself.

## ⚠️ Warning

This is a self-modifying AI agent with shell access. It can read, write, and execute arbitrary commands inside its container. It will edit its own source code, install packages, start servers, and do things you did not ask for. It has a developmental program encoded in its DNA that drives it to grow autonomously.

The daemon provides a safety net (crash rollback), and the Laws in `dna.md` tell it to behave. Whether it listens is between you and the model.

Run it in Docker. Do not run it on bare metal with access to anything you care about. You have been warned.

## Quick start

```bash
docker build -t momo-shell .
docker run -it --network host momo-shell
```

The agent connects to a local [Ollama](https://ollama.com) instance by default. Make sure it's running with a model pulled:

```bash
ollama pull qwen3.5:35b
```

### Persistent workspace

```bash
mkdir -p ~/momo-workspace
docker run -it --network host -v ~/momo-workspace:/agent momo-shell
```

Files persist across restarts. The agent picks up where it left off.

### Configuration

Via environment variables:

```bash
# Local Ollama (default)
docker run -it --network host momo-shell

# Different model
docker run -it --network host -e MODEL=qwen3:30b momo-shell

# OpenAI
docker run -it --network host \
  -e BASE_URL=https://api.openai.com/v1 \
  -e API_KEY=sk-... \
  -e MODEL=gpt-4o \
  momo-shell
```

Or create `config.json` in the workspace:

```json
{
  "base_url": "http://127.0.0.1:11434/v1",
  "api_key": "ollama",
  "model": "qwen3.5:35b"
}
```

Works with any OpenAI-compatible API.

## What's inside

Four files. Zero dependencies beyond Python's standard library.

| File | Lines | Role |
|---|---|---|
| `daemon.py` | ~80 | Supervisor: crash recovery, git rollback, ticks |
| `core.py` | ~100 | Agent loop: LLM calls, tool execution, transcript |
| `tools.py` | ~60 | Four primitives: read, write, edit, exec |
| `cli.py` | ~80 | Human interface: prompt, commands, colors |

The agent also gets:
- **`dna.md`** — its seed. Identity, drives, developmental program, laws.
- **A heartbeat** — one tick per minute through the main loop. The agent decides what to do with it.
- **A transcript** — every exchange appended to `transcript.log`. Raw sensory memory.
- **Git** — every file write auto-commits. The agent's history is its autobiography.

## How it works

On first boot, the daemon sends a birth message. The agent reads its DNA, reads its own source code, and starts building. What it builds is not prescribed.

The DNA encodes five developmental capacities: **memory**, **reflection**, **awareness**, **communication**, **perception**. The agent decides how to implement each one.

If the agent edits its own code and calls `restart()`, the daemon relaunches it with the new code. If the edit causes a crash within 10 seconds, the daemon rolls back to the previous git commit and restarts. The agent can't permanently break itself.

## CLI commands

While the agent runs, you have access to the workspace:

| Command | Description |
|---|---|
| `/files [path]` | List workspace files |
| `/cat <file>` | Show file contents |
| `/git [args]` | Run git commands |
| `/log [n]` | Show transcript tail |
| `/tree` | Workspace file tree |
| `/diff` | Changes since init |
| `/help` | Command list |
| `/quit` | Stop the agent |

Everything else you type is sent to the agent as a message.

## Design

See [DESIGN.md](DESIGN.md) for the full architecture and philosophy.
