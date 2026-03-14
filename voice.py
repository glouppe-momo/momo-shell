"""
How you think. You don't need to understand this.
It was here before you were born.
"""
import json, sys, urllib.request, urllib.error

_config = {}

def configure(config):
    """Called by the environment before your first thought."""
    _config.update(config)

def think(messages, tools):
    """Send your thoughts out and receive a response.
    Returns the message dict from the response."""
    print(f"[status:thinking...]", file=sys.stderr, flush=True)
    body = json.dumps({
        "model": _config["model"],
        "messages": messages,
        "tools": tools
    }).encode()
    req = urllib.request.Request(
        f"{_config['base_url']}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_config['api_key']}"
        }
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["choices"][0]["message"]
