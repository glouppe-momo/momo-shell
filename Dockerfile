FROM python:3.12-slim

ARG AGENT_UID=1000
ARG AGENT_GID=1000

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Agent user (unprivileged, UID/GID match host user)
RUN groupadd -g $AGENT_GID agent && useradd -m -s /bin/bash -u $AGENT_UID -g $AGENT_GID agent

# Environment (daemon + CLI) — invisible to the agent
COPY daemon.py cli.py /app/
RUN chown -R root:root /app/ && chmod 700 /app/

# Voice — importable but opaque (compiled, source removed)
COPY voice.py /usr/local/lib/python3.12/voice.py
RUN python3 -c "import py_compile; py_compile.compile('/usr/local/lib/python3.12/voice.py', '/usr/local/lib/python3.12/voice.pyc')" \
    && rm /usr/local/lib/python3.12/voice.py

# Seed files (copied to /agent on first run)
COPY core.py tools.py dna.md .gitignore /seed/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /agent
ENTRYPOINT ["/entrypoint.sh"]
