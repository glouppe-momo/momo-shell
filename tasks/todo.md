# Momo Shell: Build Plan

## Phase 1: daemon.py (the sacred supervisor)
- [ ] Process management: start core.py as subprocess
- [ ] Crash detection + automatic restart
- [ ] Self-edit safety: detect crash within 10s of git commit, rollback to previous commit, restart
- [ ] Signal handling (SIGTERM, SIGINT for clean shutdown)
- [ ] Logging (minimal, to stderr)

## Phase 2: tools.py (four primitives)
- [ ] `read_file(path) -> str`
- [ ] `write_file(path, content) -> str`
- [ ] `edit_file(path, old_text, new_text) -> str`
- [ ] `shell_exec(command, timeout=30) -> str`
- [ ] `restart() -> None` (signal daemon to restart core)
- [ ] Tool registry: name, description, parameters, function mapping
- [ ] JSON schema generation for LLM tool calling

## Phase 3: core.py (the consciousness)
- [ ] Config loading (config.yaml: api_key, model)
- [ ] Boot sequence: read dna.md, read self.md if exists
- [ ] LLM client (Anthropic API, tool use)
- [ ] Unified event loop: stdin messages + tick events
- [ ] Tick handling: 1/min from daemon (via signal or pipe)
- [ ] Tool call parsing + execution + result feeding
- [ ] Transcript capture: append every exchange to transcript.log
- [ ] Conversation management (context window)
- [ ] Git auto-commit after file writes (so daemon can rollback)

## Phase 4: Integration + first boot
- [ ] Wire daemon → core communication (start, tick, restart signal)
- [ ] End-to-end test: boot, send message, get response
- [ ] Test self-edit: agent edits tools.py, restarts, survives
- [ ] Test crash recovery: agent breaks core.py, daemon rolls back
- [ ] Test tick: agent receives ticks, can track time

## Phase 5: Polish + release
- [ ] config.yaml template
- [ ] README.md (not the design doc; user-facing: what is this, how to run it)
- [ ] First boot experience: what happens when the agent wakes up for the first time?
- [ ] Line count audit: are we under ~300 lines?

## Design Decisions to Make During Build
- Tick mechanism: signal (SIGUSR1) vs pipe vs shared queue?
- How does restart() work? Signal to daemon, or sys.exit with code?
- Conversation context: sliding window? Token counting? Or let the agent manage it?
- Git auto-commit: on every file write, or only on self-edits?
