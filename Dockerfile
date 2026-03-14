FROM python:3.12-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Agent user (unprivileged)
RUN useradd -m -s /bin/bash agent

# Environment (daemon + CLI) — invisible to the agent
COPY daemon.py cli.py /app/
RUN chmod 700 /app/daemon.py /app/cli.py

# Voice — importable but opaque
COPY voice.py /usr/local/lib/python3.12/voice.py

# Seed files (copied to /agent on first run)
COPY core.py tools.py dna.md /seed/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /agent
ENTRYPOINT ["/entrypoint.sh"]
