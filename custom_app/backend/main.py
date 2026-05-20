"""
DisSysLab Custom App — FastAPI backend
Serves office management, live run streaming, and Claude-powered office creation.
"""

import asyncio
import base64
import os
import queue
import re
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, AsyncGenerator, Union

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Resolve .env next to this file so Gmail/API keys load even when uvicorn's cwd differs.
BACKEND_DIR = Path(__file__).parent
load_dotenv(BACKEND_DIR / ".env")

app = FastAPI(title="DisSysLab Custom App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
CUSTOM_APP_DIR = BACKEND_DIR.parent
DISSYSLAB_ROOT = CUSTOM_APP_DIR.parent
GALLERY_DIR = DISSYSLAB_ROOT / "dissyslab" / "gallery"
USER_OFFICES_DIR = CUSTOM_APP_DIR / "user_offices"
CLAUDE_CONTEXT_PATH = DISSYSLAB_ROOT / "CLAUDE_CONTEXT_OFFICE.md"

# Match ``dissyslab.cli`` gallery layout: Pat-facing apps, Builder examples,
# and legacy offices directly under ``gallery/`` (see ``_GALLERY_SUBSECTIONS`` there).
_GALLERY_SUBSECTIONS: tuple[str, ...] = ("apps", "examples", "")

USER_OFFICES_DIR.mkdir(exist_ok=True)

# In-memory registry of running office subprocesses: {office_name: subprocess.Popen}
_running: dict[str, subprocess.Popen] = {}

# One Queue per running office: a daemon thread drains child stdout here; SSE reads the same queue.
_office_output_queues: dict[str, queue.Queue[str | None]] = {}


def _office_stdout_bridge(name: str, proc: subprocess.Popen, out_q: queue.Queue[str | None]) -> None:
    """Sole reader of proc.stdout: enqueue each line, mirror to stderr, then sentinel."""
    try:
        if proc.stdout is None:
            return
        while True:
            raw = proc.stdout.readline()
            if raw == "":
                break
            line = raw.rstrip("\n")
            print(f"[office:{name}] {line}", file=sys.stderr, flush=True)
            out_q.put(line)
    finally:
        out_q.put(None)


def _start_office_stdout_bridge(name: str, proc: subprocess.Popen) -> None:
    """Start (or replace) the stdout bridge for this office. Only the bridge reads proc.stdout."""
    _office_output_queues.pop(name, None)
    out_q: queue.Queue[str | None] = queue.Queue()
    _office_output_queues[name] = out_q
    threading.Thread(
        target=_office_stdout_bridge,
        args=(name, proc, out_q),
        name=f"office-stdout-{name}",
        daemon=True,
    ).start()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iter_gallery_office_dirs() -> list[Path]:
    """Office directories under the packaged gallery (each has ``office.md``).

    Mirrors ``dissyslab.cli._walk_packaged_offices`` resolution: ``apps/``,
    ``examples/``, then legacy children of ``gallery/`` itself. Skips
    ``apps`` / ``examples`` folder names when scanning the legacy root.
    """
    found: list[Path] = []
    if not GALLERY_DIR.is_dir():
        return found
    for sub in _GALLERY_SUBSECTIONS:
        root = GALLERY_DIR / sub if sub else GALLERY_DIR
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith((".", "_")):
                continue
            if not sub and child.name in ("apps", "examples"):
                continue
            if (child / "office.md").is_file():
                found.append(child)
    return found


def _find_gallery_office_dir(name: str) -> Path | None:
    """Resolve ``name`` under the gallery (apps → examples → legacy root)."""
    for sub in _GALLERY_SUBSECTIONS:
        candidate = GALLERY_DIR / sub / name if sub else GALLERY_DIR / name
        if candidate.is_dir() and (candidate / "office.md").is_file():
            return candidate
    return None


def _office_dirs() -> list[dict]:
    """Return list of office metadata dicts from gallery + user_offices."""
    offices = []

    for d in _iter_gallery_office_dirs():
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
            "builtin": True,
            "description": description,
            "path": str(d),
        })

    if USER_OFFICES_DIR.exists():
        for d in sorted(USER_OFFICES_DIR.iterdir()):
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
                "builtin": False,
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
    gallery_hit = _find_gallery_office_dir(name)
    if gallery_hit is not None:
        return gallery_hit
    candidate = USER_OFFICES_DIR / name
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


def _nws_mapclick_forecast_digest(page_url: str) -> str:
    """
    Scrape NOAA 7-day tombstones from a MapClick forecast URL.
    """
    from urllib.request import Request, urlopen

    from bs4 import BeautifulSoup

    req = Request(
        page_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; DisSysLabCustomApp/1.0; "
                "+https://github.com/kmchandy/DisSysLab)"
            )
        },
    )
    try:
        with urlopen(req, timeout=25) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[tuple[str, str]] = []
    for li in soup.select("li.forecast-tombstone")[:14]:
        pn = li.select_one("p.period-name")
        tc = li.select_one("div.tombstone-container")
        period = pn.get_text(strip=True) if pn else ""
        body = tc.get_text(" ", strip=True) if tc else ""
        if period or body:
            safe = body.replace("|", "/")[:220]
            rows.append((period, safe))
    if not rows:
        return ""
    lines = [
        "**NOAA weather.gov** (MapClick scrape for Pasadena area). "
        "If the system prompt footer mentions another provider, **ignore that** — "
        "use **only** this table for quantitative forecast.",
        "",
        "| period | conditions |",
        "|--------|--------------|",
    ]
    for period, safe in rows:
        lines.append(f"| {period} | {safe} |")
    return "\n".join(lines)


def _forecast_digest_for_subprocess(office_dir: Path) -> str:
    """
    Prefetch NOAA HTML when office.md uses web_scraper on forecast.weather.gov.
    The office_v2 pipeline can surface this via env for role prompts when running
    under ``dsl run`` / the custom app. Skips when office uses weatherapi (compiler
    builds digest from JSON API).
    """
    md_path = office_dir / "office.md"
    if not md_path.is_file():
        return ""
    raw = md_path.read_text()
    if "weatherapi(" in raw:
        return ""
    if "web_scraper(" not in raw or "forecast.weather.gov" not in raw:
        return ""
    m = re.search(r'web_scraper\s*\(\s*url\s*=\s*"([^"]+)"', raw)
    page_url = m.group(1) if m else ""
    if not page_url or "forecast.weather.gov" not in page_url:
        return ""
    return _nws_mapclick_forecast_digest(page_url)


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
        _office_output_queues.pop(name, None)

    try:
        office_dir = _find_office_dir(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Pick up GMAIL_* / API keys written to .env while the server was running.
    load_dotenv(BACKEND_DIR / ".env", override=False)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    # So ``python -m dissyslab.cli`` resolves the repo package without a global
    # ``pip install -e .`` (common in dev / conda).
    _root = str(DISSYSLAB_ROOT)
    _pp = env.get("PYTHONPATH", "")
    if _root not in _pp.split(os.pathsep):
        env["PYTHONPATH"] = _root if not _pp else f"{_root}{os.pathsep}{_pp}"
    digest = _forecast_digest_for_subprocess(office_dir)
    if digest:
        env["OFFICE_WEATHERAPI_DIGEST"] = digest
    else:
        env.pop("OFFICE_WEATHERAPI_DIGEST", None)
    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "dissyslab.cli", "run", str(office_dir)],
        cwd=str(DISSYSLAB_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
        start_new_session=True,  # isolate process group so stop() doesn't kill the backend
    )
    _running[name] = proc
    _start_office_stdout_bridge(name, proc)
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
    """SSE stream of a running office's stdout (fed by a single stdout-draining thread)."""

    async def event_generator() -> AsyncGenerator[str, None]:
        proc = _running.get(name)
        out_q = _office_output_queues.get(name)
        if not proc or out_q is None:
            yield "data: [Office is not running]\n\n"
            return

        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, out_q.get)
            if line is None:
                _running.pop(name, None)
                _office_output_queues.pop(name, None)
                yield "data: [Process finished]\n\n"
                break
            safe = line.replace("\n", " ")
            yield f"data: {safe}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/offices/{name}/status")
def office_status(name: str):
    proc = _running.get(name)
    if proc and proc.poll() is None:
        return {"running": True, "pid": proc.pid}
    _running.pop(name, None)
    _office_output_queues.pop(name, None)
    return {"running": False}


# ---------------------------------------------------------------------------
# Routes — Claude chat for office creation
# ---------------------------------------------------------------------------

class EnvVarsPayload(BaseModel):
    vars: dict[str, str]


ENV_FILE = Path(__file__).parent / ".env"


def _write_env_file():
    """Persist watched env vars to .env so they survive backend restarts."""
    watched = ["ANTHROPIC_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD", "WEATHERAPI_KEY"]
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
    watched = ["ANTHROPIC_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD", "WEATHERAPI_KEY"]
    return {"set": {k: bool(os.environ.get(k)) for k in watched}}


MAX_ATTACHMENT_BYTES = 28 * 1024 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 12
_ALLOWED_IMAGE_MEDIA = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})


class ChatAttachment(BaseModel):
    """Single file from the UI: raw base64 (no data: URL prefix)."""

    media_type: str
    data: str
    filename: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str = ""
    attachments: list[ChatAttachment] = Field(default_factory=list)


class ChatPayload(BaseModel):
    messages: list[ChatMessage]


def _strip_data_url_b64(data: str) -> str:
    s = (data or "").strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            s = s[comma + 1 :]
    return "".join(s.split())


def _user_content_for_api(msg: ChatMessage) -> Union[str, list[dict[str, Any]]]:
    """Anthropic `content`: string or list of content blocks (text, image, document)."""
    text = (msg.content or "").strip()
    atts = msg.attachments or []
    if not atts:
        return text if text else ""

    if len(atts) > MAX_ATTACHMENTS_PER_MESSAGE:
        raise HTTPException(
            status_code=400,
            detail=f"Too many attachments (max {MAX_ATTACHMENTS_PER_MESSAGE} per message).",
        )

    blocks: list[dict[str, Any]] = []
    if text:
        blocks.append({"type": "text", "text": text})
    else:
        blocks.append(
            {
                "type": "text",
                "text": (
                    "The user attached images and/or PDFs with no separate text message. "
                    "Use these files as context for their request."
                ),
            }
        )

    for i, a in enumerate(atts):
        b64_clean = _strip_data_url_b64(a.data)
        try:
            raw = base64.b64decode(b64_clean, validate=False)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Attachment {i + 1}: invalid base64.") from e
        if len(raw) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Attachment {i + 1}: too large (max {MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB).",
            )

        mt = (a.media_type or "").strip().lower()
        if mt in _ALLOWED_IMAGE_MEDIA:
            blocks.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mt, "data": b64_clean},
                }
            )
        elif mt == "application/pdf":
            doc: dict[str, Any] = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": b64_clean,
                },
            }
            if a.filename:
                doc["title"] = a.filename[:256]
            blocks.append(doc)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Attachment {i + 1}: unsupported type {mt!r}. "
                "Use image/jpeg, image/png, image/gif, image/webp, or application/pdf.",
            )

    return blocks


def _anthropic_messages_from_payload(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "assistant":
            out.append({"role": "assistant", "content": m.content or ""})
        elif m.role == "user":
            out.append({"role": "user", "content": _user_content_for_api(m)})
        else:
            raise HTTPException(status_code=400, detail=f"Invalid message role: {m.role!r}")
    return out


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
    system_prompt = base_context + "\n\n---\n\n## IMPORTANT — You are running inside a web UI\n\nDo NOT give terminal instructions. The user may attach images or PDFs as extra context — use them when updating files.\n\nOutput updated files using filename-in-fence format:\n\n```office.md\ncontent\n```\n\n```roles/analyst.md\ncontent\n```\n\n---\n\n" + office_context

    try:
        api_messages = _anthropic_messages_from_payload(payload.messages)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    client = anthropic.Anthropic(api_key=api_key)

    async def generate():
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-5",
                max_tokens=4096,
                system=system_prompt,
                messages=api_messages,
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

The user may attach images (e.g. wardrobe or outfit photos) and/or PDF files as extra
context in their messages. When present, use that visual and document context to infer
requirements (sources, agent behavior, sinks) even if the user does not repeat those
details in plain text.
"""

    try:
        api_messages = _anthropic_messages_from_payload(payload.messages)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    client = anthropic.Anthropic(api_key=api_key)

    async def generate() -> AsyncGenerator[str, None]:
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-5",
                max_tokens=4096,
                system=system_prompt,
                messages=api_messages,
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
