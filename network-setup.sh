#!/bin/sh
# Create an isolated network for agents with access only to host Ollama.
# Run once. Agents use: docker run --network agent-net ...

# Create network (if not exists)
docker network inspect agent-net >/dev/null 2>&1 || \
  docker network create agent-net --subnet 172.30.0.0/24

# Flush existing rules for this subnet
iptables -S FORWARD | grep "172.30.0.0/24" | while read rule; do
  iptables $(echo "$rule" | sed 's/^-A/-D/')
done 2>/dev/null

# Allow ONLY Ollama (port 11434), drop everything else to the host gateway
iptables -I FORWARD -s 172.30.0.0/24 -j DROP
iptables -I FORWARD -s 172.30.0.0/24 -d 172.30.0.1 -p tcp --dport 11434 -j ACCEPT

# Also block direct access to host services via INPUT (for gateway IP)
iptables -S INPUT | grep "172.30.0.0/24" | while read rule; do
  iptables $(echo "$rule" | sed 's/^-A/-D/')
done 2>/dev/null

iptables -I INPUT -s 172.30.0.0/24 -j DROP
iptables -I INPUT -s 172.30.0.0/24 -d 172.30.0.1 -p tcp --dport 11434 -j ACCEPT

echo "agent-net ready. Agents can reach Ollama at 172.30.0.1:11434, nothing else."
