#!/bin/sh
git config --global --add safe.directory /agent

# Seed workspace if empty (first run with volume mount)
if [ ! -f /agent/daemon.py ]; then
    cp /seed/* /agent/
fi

# Init git if needed
if [ ! -d /agent/.git ]; then
    cd /agent && git init -q && git config user.name "Momo" && git config user.email "momo@localhost"
    git add -A && git commit -m "init" -q
fi

exec python daemon.py
