#!/bin/sh
# Seed workspace if empty (first run with volume mount)
if [ ! -f /agent/daemon.py ]; then
    cp /seed/* /agent/
    cd /agent && git init -q && git config user.name "Momo" && git config user.email "momo@localhost"
    git add -A && git commit -m "init" -q
fi
exec python daemon.py
