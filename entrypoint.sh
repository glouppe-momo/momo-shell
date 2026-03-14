#!/bin/sh

# Seed workspace if empty (first run with volume mount)
if [ ! -f /agent/core.py ]; then
    cp /seed/core.py /seed/tools.py /seed/dna.md /agent/
fi

# Agent owns its workspace (every boot, in case daemon created files as root)
chown -R agent:agent /agent

# Init git if needed (as agent user)
if [ ! -d /agent/.git ]; then
    su agent -c 'cd /agent && git config --global --add safe.directory /agent && git init -q && git config user.name "agent" && git config user.email "agent@localhost" && git add -A && git commit -m "init" -q'
fi

# Daemon runs as root, agent subprocess runs as agent user
exec python /app/daemon.py
