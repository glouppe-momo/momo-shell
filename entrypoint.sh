#!/bin/sh
git config --global --add safe.directory /agent

# Seed workspace if empty (first run with volume mount)
if [ ! -f /agent/core.py ]; then
    cp /seed/core.py /seed/tools.py /seed/dna.md /agent/
fi

# Init git if needed
if [ ! -d /agent/.git ]; then
    cd /agent && git init -q && git config user.name "agent" && git config user.email "agent@localhost"
    git add -A && git commit -m "init" -q
fi

export PYTHONPATH="/app:$PYTHONPATH"
exec python /app/daemon.py
