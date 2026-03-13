FROM python:3.12-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /agent
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY daemon.py core.py tools.py dna.md ./

RUN git init && git config user.name "Momo" && git config user.email "momo@localhost" \
    && git add -A && git commit -m "init" -q

CMD ["python", "daemon.py"]
