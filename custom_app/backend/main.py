"""
DisSysLab Custom App — FastAPI backend
Serves office management, live run streaming, and Claude-powered office creation.
"""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import AsyncGenerator

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="DisSysLab Custom App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BACKEND_DIR = Path(__file__).parent
CUSTOM_APP_DIR = BACKEND_DIR.parent
DISSYSLAB_ROOT = CUSTOM_APP_DIR.parent
GALLERY_DIR = DISSYSLAB_ROOT / "dissyslab" / "gallery"
USER_OFFICES_DIR = CUSTOM_APP_DIR / "user_offices"
CLAUDE_CONTEXT_PATH = DISSYSLAB_ROOT / "CLAUDE_CONTEXT_OFFICE.md"

USER_OFFICES_DIR.mkdir(exist_ok=True)

# In-memory registry of running office subprocesses: {office_name: subprocess.Popen}
_running: dict[str, subprocess.Popen] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _office_dirs() -> list[dict]:
    """Return list of office metadata dicts from gallery + user_offices."""
    offices = []

    for source, is_builtin in [(GALLERY_DIR, True), (USER_OFFICES_DIR, False)]:
        if not source.exists():
            continue
        for d in sorted(source.iterdir()):
            if not d.is_dir() or d.name.startswith("_") or d.name == "__pycache__":
                continue
            office_md = d / "office.md"
            if not office_md.exists():
                continue
            readme = d / "README.md"
            description = ""
            if readme.exists():
                first_lines = readme.read_text().splitlines()
                for line in first_lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        description = line
                        break
            offices.append({
                "name": d.name,
                "builtin": is_builtin,
                "description": description,
                "path": str(d),
            })

    return offices


def _read_office(office_dir: Path) -> dict:
    """Read office.md and all role files from an office directory."""
    office_md = office_dir / "office.md"
    if not office_md.exists():
        raise FileNotFoundError(f"office.md not found in {office_dir}")

    roles = {}
    roles_dir = office_dir / "roles"
    if roles_dir.exists():
        for role_file in sorted(roles_dir.glob("*.md")):
            roles[role_file.stem] = role_file.read_text()

    return {
        "name": office_dir.name,
        "office_md": office_md.read_text(),
        "roles": roles,
    }


def _find_office_dir(name: str) -> Path:
    """Return the Path to the office dir, searching gallery then user_offices."""
    for base in [GALLERY_DIR, USER_OFFICES_DIR]:
        candidate = base / name
        if candidate.exists() and (candidate / "office.md").exists():
            return candidate
    raise FileNotFoundError(f"Office '{name}' not found")


def _parse_claude_files(text: str) -> dict[str, str]:
    """
    Parse Claude's response for file blocks. Handles multiple formats Claude uses:

    Format 1 — filename inside the opening fence:
        ```roles/analyst.md
        content
        ```

    Format 2 — filename as a markdown heading before a bare fence:
        ### roles/analyst.md
        ```
        content
        ```

    Format 3 — "Save as `path`" instruction before a bare fence:
        Save as `my_office/roles/analyst.md`
        ```
        content
        ```

    Strips any leading directory prefix (e.g. my_office/) from paths so all
    files are stored relative to the office root.
    """
    import re
    files = {}

    def normalise(path: str) -> str:
        """Strip leading directory so paths are office-relative."""
        parts = path.strip().split('/')
        # Keep only roles/x.md or office.md (drop leading folder name)
        if len(parts) >= 2 and parts[0] not in ('roles',):
            parts = parts[1:]
        return '/'.join(parts)

    # Format 1: filename embedded in opening fence
    for m in re.finditer(r"```(?:[\w]+\s+)?(\S+\.md)\n(.*?)```", text, re.DOTALL):
        files[normalise(m.group(1))] = m.group(2)

    # Format 2: markdown heading directly before a bare fence
    for m in re.finditer(r"#{1,4}\s+([\w./]+\.md)\s*\n+```[^\n]*\n(.*?)```", text, re.DOTALL):
        key = normalise(m.group(1))
        if key not in files:
            files[key] = m.group(2)

    # Format 3: "Save as `path`" before a bare fence
    for m in re.finditer(r"[Ss]ave as\s+`([\w./]+\.md)`[^\n]*\n+```[^\n]*\n(.*?)```", text, re.DOTALL):
        key = normalise(m.group(1))
        if key not in files:
            files[key] = m.group(2)

    return files


# ---------------------------------------------------------------------------
# Routes — Office listing and file management
# ---------------------------------------------------------------------------

@app.get("/api/offices")
def list_offices():
    return {"offices": _office_dirs()}


@app.get("/api/offices/{name}")
def get_office(name: str):
    try:
        office_dir = _find_office_dir(name)
        return _read_office(office_dir)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


class SaveOfficePayload(BaseModel):
    office_md: str
    roles: dict[str, str]


@app.put("/api/offices/{name}")
def save_office(name: str, payload: SaveOfficePayload):
    try:
        office_dir = _find_office_dir(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    (office_dir / "office.md").write_text(payload.office_md)
    roles_dir = office_dir / "roles"
    roles_dir.mkdir(exist_ok=True)
    for role_name, content in payload.roles.items():
        (roles_dir / f"{role_name}.md").write_text(content)

    return {"status": "saved"}


class CreateOfficePayload(BaseModel):
    name: str
    office_md: str
    roles: dict[str, str]


@app.delete("/api/offices/{name}")
def delete_office(name: str):
    """Delete a custom office. Built-in offices cannot be deleted."""
    import shutil
    candidate = USER_OFFICES_DIR / name
    if not candidate.exists():
        raise HTTPException(status_code=404, detail=f"Custom office '{name}' not found")
    shutil.rmtree(candidate)
    return {"status": "deleted"}


class ClonePayload(BaseModel):
    new_name: str = ""


@app.post("/api/offices/{name}/clone")
def clone_office(name: str, payload: ClonePayload):
    """Copy a built-in office into user_offices/ so the user can edit it."""
    import re
    import shutil
    try:
        source_dir = _find_office_dir(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Sanitise the requested name or fall back to a default
    requested = re.sub(r"[^a-z0-9_]", "_", payload.new_name.strip().lower()) if payload.new_name.strip() else ""
    dest_name = requested or f"{name}_custom"

    # Avoid collisions
    dest_dir = USER_OFFICES_DIR / dest_name
    counter = 1
    while dest_dir.exists():
        dest_dir = USER_OFFICES_DIR / f"{dest_name}_{counter}"
        dest_name = dest_dir.name
        counter += 1

    shutil.copytree(source_dir, dest_dir,
                    ignore=shutil.ignore_patterns("app.py", "__pycache__", "*.pyc"))
    return {"status": "cloned", "name": dest_name}


@app.post("/api/offices")
def create_office(payload: CreateOfficePayload):
    office_dir = USER_OFFICES_DIR / payload.name
    if office_dir.exists():
        raise HTTPException(status_code=409, detail=f"Office '{payload.name}' already exists")

    office_dir.mkdir(parents=True)
    (office_dir / "office.md").write_text(payload.office_md)
    roles_dir = office_dir / "roles"
    roles_dir.mkdir()
    for role_name, content in payload.roles.items():
        (roles_dir / f"{role_name}.md").write_text(content)

    return {"status": "created", "name": payload.name}


# ---------------------------------------------------------------------------
# Routes — Run / Stop / Stream output
# ---------------------------------------------------------------------------

@app.post("/api/offices/{name}/run")
def run_office(name: str):
    if name in _running:
        proc = _running[name]
        if proc.poll() is None:
            raise HTTPException(status_code=409, detail=f"Office '{name}' is already running")
        del _running[name]

    try:
        office_dir = _find_office_dir(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "dissyslab.office.office_compiler", str(office_dir)],
        cwd=str(DISSYSLAB_ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
        start_new_session=True,  # isolate process group so stop() doesn't kill the backend
    )
    # Auto-answer the "Does this look right?" prompt
    try:
        proc.stdin.write("yes\n")
        proc.stdin.flush()
        proc.stdin.close()
    except Exception:
        pass
    _running[name] = proc
    return {"status": "started", "pid": proc.pid}


@app.post("/api/offices/{name}/stop")
def stop_office(name: str):
    proc = _running.get(name)
    if not proc or proc.poll() is not None:
        _running.pop(name, None)
        raise HTTPException(status_code=404, detail=f"Office '{name}' is not running")
    try:
        os.killpg(proc.pid, signal.SIGTERM)  # proc.pid == pgid since start_new_session=True
    except Exception:
        proc.terminate()
    _running.pop(name, None)
    return {"status": "stopped"}


@app.get("/api/offices/{name}/output")
async def stream_output(name: str):
    """SSE stream of a running office's stdout."""

    async def event_generator() -> AsyncGenerator[str, None]:
        proc = _running.get(name)
        if not proc:
            yield "data: [Office is not running]\n\n"
            return

        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, proc.stdout.readline)
            if line:
                safe = line.rstrip("\n").replace("\n", " ")
                yield f"data: {safe}\n\n"
            else:
                if proc.poll() is not None:
                    _running.pop(name, None)
                    yield "data: [Process finished]\n\n"
                    break
                await asyncio.sleep(0.05)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/offices/{name}/status")
def office_status(name: str):
    proc = _running.get(name)
    if proc and proc.poll() is None:
        return {"running": True, "pid": proc.pid}
    _running.pop(name, None)
    return {"running": False}


# ---------------------------------------------------------------------------
# Routes — Claude chat for office creation
# ---------------------------------------------------------------------------

class EnvVarsPayload(BaseModel):
    vars: dict[str, str]


ENV_FILE = Path(__file__).parent / ".env"


def _write_env_file():
    """Persist watched env vars to .env so they survive backend restarts."""
    watched = ["ANTHROPIC_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD"]
    lines = []
    for key in watched:
        val = os.environ.get(key)
        if val:
            lines.append(f'{key}={val}\n')
    ENV_FILE.write_text("".join(lines))


@app.post("/api/env")
def set_env_vars(payload: EnvVarsPayload):
    """Set environment variables for the current process (inherited by subprocesses)."""
    for key, value in payload.vars.items():
        os.environ[key] = value
    _write_env_file()
    return {"status": "set", "keys": list(payload.vars.keys())}


@app.get("/api/env")
def get_env_keys():
    """Return which credential keys are currently set (not their values)."""
    watched = ["ANTHROPIC_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD"]
    return {"set": {k: bool(os.environ.get(k)) for k in watched}}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatPayload(BaseModel):
    messages: list[ChatMessage]


def _office_context_prompt(office_dir: Path) -> str:
    """Build a prompt prefix showing Claude the current office files."""
    try:
        data = _read_office(office_dir)
    except FileNotFoundError:
        return ""

    lines = [
        "The user wants to modify an existing DisSysLab office.",
        "Here are the current files:\n",
        "```office.md",
        data["office_md"],
        "```\n",
    ]
    for role_name, content in data["roles"].items():
        lines += [f"```roles/{role_name}.md", content, "```\n"]

    lines += [
        "Update these files based on the user's request.",
        "Output the complete updated files (not diffs) using the filename-in-fence format.",
        "Only output files that need to change.",
        "Do not give terminal instructions — the UI handles saving automatically.",
    ]
    return "\n".join(lines)


@app.post("/api/offices/{name}/chat")
async def office_chat(name: str, payload: ChatPayload):
    """
    Chat endpoint scoped to an existing office.
    Injects current office files as context so Claude can edit them intelligently.
    When Claude produces updated files they are auto-saved to disk.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")

    try:
        office_dir = _find_office_dir(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    base_context = CLAUDE_CONTEXT_PATH.read_text() if CLAUDE_CONTEXT_PATH.exists() else ""
    office_context = _office_context_prompt(office_dir)
    system_prompt = base_context + "\n\n---\n\n## IMPORTANT — You are running inside a web UI\n\nDo NOT give terminal instructions. Output updated files using filename-in-fence format:\n\n```office.md\ncontent\n```\n\n```roles/analyst.md\ncontent\n```\n\n---\n\n" + office_context

    client = anthropic.Anthropic(api_key=api_key)

    async def generate():
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-5",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": m.role, "content": m.content} for m in payload.messages],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    safe = text.replace("\n", "\\n")
                    yield f"event: text\ndata: {safe}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"
            return

        files = _parse_claude_files(full_response)
        if files:
            # Auto-save updated files to the office directory
            roles_dir = office_dir / "roles"
            roles_dir.mkdir(exist_ok=True)
            for filepath, content in files.items():
                if filepath == "office.md":
                    (office_dir / "office.md").write_text(content)
                elif filepath.startswith("roles/"):
                    role_name = filepath.replace("roles/", "")
                    (roles_dir / role_name).write_text(content)

            import json
            yield f"event: saved\ndata: {json.dumps(list(files.keys()))}\n\n"

        yield "event: done\ndata: \n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/chat")
async def chat(payload: ChatPayload):
    """
    Stream a Claude response. The system prompt is CLAUDE_CONTEXT_OFFICE.md.
    Returns SSE with text deltas, then a final 'files' event if office files
    were detected in the response.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")

    base_context = CLAUDE_CONTEXT_PATH.read_text() if CLAUDE_CONTEXT_PATH.exists() else ""
    system_prompt = base_context + """

---

## IMPORTANT — You are running inside a web UI

The user does NOT need terminal instructions. Do NOT tell them to save files manually,
run commands, or open a terminal. The UI will handle all of that automatically.

When you are ready to output files, output ONLY the file contents in this exact format
(filename in the opening code fence):

```office.md
# Office: name_here
...
```

```roles/analyst.md
# Role: analyst
...
```

Use this format for EVERY file. Do not add "Save as" instructions, folder structures,
or run commands. Just output the files in the format above and the UI will create them.
"""

    client = anthropic.Anthropic(api_key=api_key)

    async def generate() -> AsyncGenerator[str, None]:
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-5",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": m.role, "content": m.content} for m in payload.messages],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    safe = text.replace("\n", "\\n")
                    yield f"event: text\ndata: {safe}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"
            return

        # After streaming, check if office files are embedded in the response
        files = _parse_claude_files(full_response)
        if files:
            import json
            yield f"event: files\ndata: {json.dumps(files)}\n\n"

        yield "event: done\ndata: \n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
