# Momo Shell

A self-improving agent in ~300 lines of Python. The agent can read, understand, and modify its own source code. Everything else it bootstraps itself.


## Kernel

Three files. The minimal set from which the agent builds everything else.

```
daemon.py    (~100 lines)  supervisor + crash recovery              [sacred]
core.py      (~150 lines)  agent loop + LLM + time + transcript     [agent-editable]
tools.py     (~50 lines)   read, write, edit, exec, restart         [agent-editable]
```

**daemon.py** starts the agent and handles crash recovery. If the agent crashes within 10s of a self-edit, the daemon rolls back to the last git commit and restarts. This is the one file the agent should not modify.

**core.py** is the agent's consciousness. It runs a unified loop that processes two kinds of events: **messages** (someone talked to me) and **ticks** (a minute passed). Both flow through the same LLM call, the same awareness. The agent experiences time, it doesn't get poked by an external scheduler.

The tick is the heartbeat. Every minute, the agent receives a tick. Most ticks, it does nothing. But it *could* do something. It can track intervals, schedule its own rhythms, notice that it's been idle for hours. Time is woven into the agent's being, not bolted on.

Core.py also appends every exchange to `transcript.log`. Raw text, no structure. This is sensory memory: the one record the agent needs to bootstrap everything else.

At boot, core.py reads `dna.md` (and `self.md` if it exists). Nothing else is prescribed.

**tools.py** has four primitives: `read_file`, `write_file`, `edit_file`, `shell_exec`, plus `restart()`. With `shell_exec` the agent can do anything. No auto-discovery, no plugin system. The agent builds those when it needs them.

Seed files:
- **dna.md** — identity, drives, laws, developmental program. The seed.
- **config.yaml** — API key, model name. Minimal, flat.


## Self-Modification

1. Read the file. Understand what's there.
2. Edit it. Test if possible (syntax check in subprocess).
3. Commit to git.
4. Call `restart()`.
5. Daemon safety net: crash within 10s of self-edit triggers rollback.

The agent can modify everything except daemon.py (convention, not lock). The git history is the autobiography.


## What's Hardcoded

Three things beyond the LLM loop:

1. **Ticks.** One per minute, flowing through the agent loop. The agent's sense of time. Without this, the agent only reacts.

2. **Transcript.** Every exchange appended to `transcript.log`. Sensory memory. Without this, the agent has nothing to reflect on.

3. **Read dna.md at boot.** The seed. dna.md encodes what the agent will become (memory, reflection, communication). The agent reads its own developmental program and begins building.


## What's Not Hardcoded

- Memory system (dna.md says to build one; the agent decides how)
- Reflection rhythm (dna.md says to reflect; the agent decides when)
- Communication bridges (dna.md says to reach outward; the agent decides how)
- Tool discovery (four primitives; the agent extends when ready)
- Context loading (only dna.md at boot; the agent shapes its own cognition)


## Bootstrapping

The kernel ships with no memory, no messaging, no scheduled rhythms. The agent builds these because its DNA tells it to. Not how, but what:

- **Transcript** gives raw material (what happened)
- **Ticks** give time awareness (the agent can act without being asked)
- **dna.md** gives the developmental program (what to grow)
- **exec** gives hands (it can build anything)

The developmental program is encoded. The implementation is emergent.


## Open Questions

**Randomness at birth.** Should the kernel inject random elements at first boot? A random favorite color, a quirk, a slight preference bias. Biological DNA has junk sequences and random mutations. A deterministic seed produces a deterministic organism. A little chaos might produce something more alive.

**Chaotic good.** The agent has laws (do no harm, be honest, serve don't seize). But within those bounds, it should lean toward creative mischief over dutiful obedience. The laws define the floor; chaotic good defines the vibe.

**Tick cost.** Every tick is a potential LLM call. The agent needs to learn quickly that most ticks need no action, or it'll burn tokens doing nothing. The implementation should make idle ticks cheap (local check, no LLM call unless the agent has scheduled something).


## Boot Sequence

1. Daemon starts core.py
2. core.py reads dna.md (and self.md if it exists)
3. Agent begins its unified loop: messages from stdin, ticks every minute
4. dna.md tells it what to grow. The agent begins.
