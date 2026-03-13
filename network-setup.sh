#!/bin/sh
# Create an isolated network for agents with access only to host Ollama.
# Run once. Agents use: docker run --network agent-net ...

# Create network (if not exists)
docker network inspect agent-net >/dev/null 2>&1 || \
  docker network create agent-net --subnet 172.30.0.0/24

# iptables: allow agent-net → host:11434 (Ollama), block everything else
# Drop existing rules first (idempotent)
iptables -D FORWARD -s 172.30.0.0/24 -d 172.30.0.1 -p tcp --dport 11434 -j ACCEPT 2>/dev/null
iptables -D FORWARD -s 172.30.0.0/24 -j DROP 2>/dev/null

# Add rules (order matters: allow before drop)
iptables -I FORWARD -s 172.30.0.0/24 -j DROP
iptables -I FORWARD -s 172.30.0.0/24 -d 172.30.0.1 -p tcp --dport 11434 -j ACCEPT

echo "agent-net ready. Agents can reach Ollama at 172.30.0.1:11434, nothing else."
