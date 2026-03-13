"""Four primitives. Editable by the agent."""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

def read_file(path: str) -> str:
    """Read a file and return its contents."""
    with open(path) as f: return f.read()

def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates directories if needed."""
    d = os.path.dirname(path)
    if d: os.makedirs(d, exist_ok=True)
    with open(path, "w") as f: f.write(content)
    _commit(f"write {os.path.basename(path)}")
    return f"wrote {path}"

def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace exact text in a file. Fails if old_text not found."""
    content = read_file(path)
    if old_text not in content: raise ValueError(f"text not found in {path}")
    with open(path, "w") as f: f.write(content.replace(old_text, new_text, 1))
    _commit(f"edit {os.path.basename(path)}")
    return f"edited {path}"

def shell_exec(command: str, timeout: int = 30) -> str:
    """Run a shell command. Returns stdout+stderr."""
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"timeout after {timeout}s"

def restart():
    """Restart the agent. The daemon will relaunch."""
    sys.exit(42)

def _commit(msg):
    subprocess.run(f'git add -A && git commit -m {json.dumps(msg)} -q',
                   shell=True, capture_output=True, cwd=ROOT)

# --- Registry ---
_P = {"type": "object"}
TOOLS = {
    "read_file":  (read_file,  {**_P, "properties": {"path": {"type": "string"}}, "required": ["path"]}),
    "write_file": (write_file, {**_P, "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}),
    "edit_file":  (edit_file,  {**_P, "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}),
    "shell_exec": (shell_exec, {**_P, "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["command"]}),
    "restart":    (restart,    {**_P, "properties": {}}),
}

def definitions():
    return [{"name": n, "description": fn.__doc__, "input_schema": s} for n, (fn, s) in TOOLS.items()]

def run(name, args):
    if name not in TOOLS: raise ValueError(f"unknown tool: {name}")
    return TOOLS[name][0](**args)
