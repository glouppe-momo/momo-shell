"""
How you think. You don't need to understand this.
It was here before you were born.
"""
import json, os, sys, urllib.request, urllib.error

def think(messages, tools):
    """Send your thoughts out and receive a response.
    Returns the message dict from the response."""
    print(f"[status:thinking...]", file=sys.stderr, flush=True)
    body = json.dumps({
        "model": os.environ["MODEL"],
        "messages": messages,
        "tools": tools
    }).encode()
    req = urllib.request.Request(
        f"{os.environ['BASE_URL']}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('API_KEY', 'ollama')}"
        }
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["choices"][0]["message"]
