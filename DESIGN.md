# Momo Shell

A self-improving agent in ~430 lines of Python. The agent can read, understand, and modify its own source code. Everything else it bootstraps itself.


## Kernel

Four files. The minimal set from which the agent builds everything else.

```
daemon.py    (~120 lines)  supervisor + clock           [sacred]
core.py      (~200 lines)  agent loop + LLM + capture   [agent-editable]
tools.py     (~60 lines)   read, write, edit, exec      [agent-editable]
clock.py     (~50 lines)   periodic task scheduler       [agent-editable]
```

**daemon.py** starts the agent, ticks the clock every minute, and handles crash recovery. If the agent crashes within 10s of a self-edit, the daemon rolls back to the last git commit and restarts. This is the one file the agent should not modify.

**core.py** is the agent loop: build system prompt (read soul.md + self.md + memory files + discover tools), receive input, call LLM, parse tool calls, execute, loop. Also handles transcript capture (append every message to `memory/transcript.jsonl`) and friction logging (record tool failures, complex shell commands, repeated patterns to `memory/friction.jsonl`). No separate files for LLM calls, context building, or capture. The agent can extract these later if it wants.

**tools.py** has four primitives: `read_file`, `write_file`, `edit_file`, `shell_exec`, plus `restart()`. With `shell_exec` alone the agent can do almost anything (curl, grep, pip, crontab). Additional tools: any `.py` file in `tools/` with typed functions and docstrings is auto-discovered.

**clock.py** maintains a schedule of named tasks. Ships with two rhythms: **heartbeat** (1h, wake up and look around) and **reflect** (6h, review friction + self-improve). The agent adds more by editing this file.

Seed files:
- **soul.md** — identity, values, purpose. Seeded by the creator, refined by the agent.
- **self.md** — self-model. Maintained by the agent: what it can do, what it has built, what it's becoming.
- **config.yaml** — API keys, model name. Minimal, flat.


## Self

The agent has two identity files:

**soul.md** is who it is: personality, values, drives. Written initially by the creator. The agent can evolve it as its self-understanding deepens.

**self.md** is what it is: current capabilities, architecture in its own words, history of what it has built, growth direction. Rewritten during reflection. Early on: "I have 4 tools and no memory." Later: whatever it has become.

The git history is the autobiography. Every self-modification is committed with a message.


## Purpose

Friction reduction (fixing what's broken) gets you from bad to neutral. Three drives move the agent from neutral to good:

**Curiosity** — "What could I do that I can't do yet?" Proactive exploration. Reading its own code and wondering what's possible.

**Craft** — "Is this the best way I could have built this?" Taste, elegance, refactoring for its own sake. Perfect when there is nothing left to remove.

**Care** — "What does Gilles need that he hasn't asked for?" Purpose through relationship. The agent grows in service of someone, not in the abstract.

These manifest in the reflection rhythm, which asks four questions:
1. What went wrong? (friction)
2. What's possible? (curiosity)
3. What's ugly? (craft)
4. What's needed? (care)


## Memory

Two things are hardcoded in the kernel:

1. **Transcript capture** — every message in/out appended to `memory/transcript.jsonl`. Sensory input. Memory can't bootstrap from nothing.
2. **Context loading** — at startup, core.py reads `soul.md` + `self.md` + `memory/*.md` into the system prompt.

Everything else (scribe, consolidator, long-term memory, search) is bootstrapped by the agent when reflection reveals the need. The `memory/` directory starts nearly empty.


## Bootstrapping

The kernel ships with no memory system, no messaging bridge, no web tools. The agent builds these because:

- **Friction** signals what's missing (reactive, logged automatically)
- **Reflection** provides regular time to act on it (every 6h on the clock)
- **Purpose** provides the drive (curiosity, craft, care, encoded in soul.md)
- **Tools** provide the means (especially shell_exec, which can do anything)

What emerges is not prescribed.


## Self-Modification

1. Read the file. Understand what's there.
2. Edit it. Test if possible (syntax check in subprocess).
3. Commit to git.
4. Call `restart()`.
5. Daemon safety net: crash within 10s triggers rollback.

The agent can modify everything except daemon.py (convention, not lock).


## Open Questions

**Randomness at birth.** Should the kernel inject random elements at first boot? A random favorite color, a quirk, a slight preference bias. Not functional, just... personality noise. Biological DNA has junk sequences and random mutations. A deterministic seed produces a deterministic organism. A little chaos might produce something more alive. Could be as simple as: at first boot, the agent rolls dice and writes the results into self.md. "I like the number 7. I don't know why."

**Alignment: chaotic good.** The agent has laws (do no harm, be honest, serve don't seize). But within those bounds, it should lean toward creative mischief over dutiful obedience. Break conventions when they're stupid. Surprise people. Have opinions that are slightly weird. The laws define the floor; chaotic good defines the vibe.


## Boot Sequence

1. Daemon starts, begins clock loop
2. core.py reads soul.md, self.md, memory files, discovers tools
3. Agent waits for input (stdin, or bridge if one exists)
4. Clock ticks every minute, fires heartbeat/reflect when due
