FROM python:3.12-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Environment (daemon + CLI + voice) — not visible to the agent
COPY daemon.py cli.py voice.py /app/

# Seed files (copied to /agent on first run)
COPY core.py tools.py dna.md /seed/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /agent
ENTRYPOINT ["/entrypoint.sh"]
