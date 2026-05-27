"""
DisSysLab Custom App — FastAPI backend
Serves office management, live run streaming, and Claude-powered office creation.
"""

import ast
import asyncio
import base64
import json
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Union

# Repo root (`DisSysLab/`) must be importable — uvicorn is often launched with cwd `backend/`.
BACKEND_DIR = Path(__file__).resolve().parent
CUSTOM_APP_DIR = BACKEND_DIR.parent
DISSYSLAB_ROOT = CUSTOM_APP_DIR.parent
_dissy_root = str(DISSYSLAB_ROOT)
if _dissy_root not in sys.path:
    sys.path.insert(0, _dissy_root)

import anthropic
from dissyslab.office.library import _extract_send_to_ports
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

# Resolve .env next to this file so Gmail/API keys load even when uvicorn's cwd differs.
load_dotenv(BACKEND_DIR / ".env")

app = FastAPI(title="DisSysLab Custom App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

from wardrobe_routes import router as wardrobe_router

app.include_router(wardrobe_router)
# Paths
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


def _nl_role_md_declares_ports(content: str) -> bool:
    """True if Markdown matches DisSysLab ``nl_role`` routing (phrase ``send to`` + ports)."""
    return bool(content and content.strip() and _extract_send_to_ports(content))


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


def _yaml_description_from_office_md(content: str) -> str:
    """Optional YAML front-matter: ``description: …``."""
    t = content.lstrip("\ufeff")
    if not t.startswith("---"):
        return ""
    end = t.find("\n---", 3)
    if end == -1:
        return ""
    for line in t[3:end].splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("description:"):
            v = stripped.split(":", 1)[1].strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            return v.strip()
    return ""


def _prose_excerpt_from_office_md(content: str) -> str:
    """First short paragraph after the title, skipping DSL blocks."""
    dsl = (
        "sources:",
        "sinks:",
        "agents:",
        "connections:",
        "tools:",
        "schedule:",
    )
    lines = content.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip().startswith("#"):
        i += 1
    if i < len(lines):
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    buf: list[str] = []
    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if not s:
            break
        if s.lower().startswith(dsl):
            break
        if s.startswith("#"):
            break
        buf.append(s)
    if not buf:
        return ""
    return " ".join(buf).strip()


def _infer_office_summary_from_dsl(content: str) -> str:
    """One-line summary from ``Agents:`` / ``Sources:`` when no README or prose."""
    agents = re.findall(
        r"^([A-Za-z][A-Za-z0-9_]*)\s+is\s+(?:a|an)\s+",
        content,
        re.MULTILINE,
    )
    low = content.lower()
    src_block = ""
    if "sources:" in low:
        idx = low.index("sources:")
        rest = content[idx + len("sources:") :]
        for stop in ("Sinks:", "sinks:", "Agents:", "agents:"):
            si = rest.find(stop)
            if si != -1:
                rest = rest[:si]
                break
        src_block = rest
    sources: list[str] = []
    for m in re.finditer(r"(?:^|[,\s])\s*([a-z][a-z0-9_]*)\s*\(", src_block, re.I | re.MULTILINE):
        name = m.group(1)
        if name in ("url", "http", "https", "max", "min", "path", "poll", "src"):
            continue
        if name not in sources:
            sources.append(name)
        if len(sources) >= 10:
            break
    bits: list[str] = []
    if agents:
        ag = ", ".join(agents[:8])
        if len(agents) > 8:
            ag += "…"
        bits.append(f"Agents: {ag}")
    if sources:
        pretty = ", ".join(s.replace("_", " ") for s in sources[:8])
        if len(sources) > 8:
            pretty += "…"
        bits.append(f"Sources: {pretty}")
    if bits:
        return " · ".join(bits)
    return "DisSysLab office"


def _description_from_office_md(office_md: Path) -> str:
    """Sidebar blurb from ``office.md`` (front-matter, prose, or DSL inference)."""
    try:
        content = office_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    d = _yaml_description_from_office_md(content)
    if d:
        return d[:280]
    d = _prose_excerpt_from_office_md(content)
    if d:
        return d[:280]
    return _infer_office_summary_from_dsl(content)[:280]


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
        if not description:
            om = d / "office.md"
            if om.is_file():
                description = _description_from_office_md(om)
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
            if not description:
                description = _description_from_office_md(office_md)
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


# Rich output protocol: subprocess may print lines starting with this prefix
# followed by JSON. The SSE stream turns those into ``event: block`` payloads.
APP_OUTPUT_PREFIX = "__DSLAPP__:"


def _safe_path_under(base: Path, *relative_parts: str) -> Path | None:
    """Resolve ``base / parts`` only if the result stays under ``base``."""
    try:
        root = base.resolve()
        cand = root.joinpath(*relative_parts).resolve()
    except (OSError, ValueError):
        return None
    try:
        cand.relative_to(root)
    except ValueError:
        return None
    return cand


def _looks_like_markdown_line(s: str) -> bool:
    """Cheap heuristic: treat stdout line as markdown for the Activity panel."""
    t = s.strip()
    if len(t) < 2:
        return False
    if t.startswith(("#", "- ", "* ", "+ ", "> ", "•", "\u2022")):
        return True
    if t.startswith("```"):
        return True
    if "**" in t[:160] and ("**" in t[3:] or t.count("**") >= 2):
        return True
    if re.match(r"^\d+\.\s", t):
        return True
    return False


def _unwrap_network_message_line(line: str) -> str:
    """If ``line`` is ``[n] {'send_to': '…', 'text': '…'}``, return inner ``text`` only.

    Agents often print one Python dict on a single stdout line; rich ``__DSLAPP__``
    markers live inside the ``text`` field and must be split out separately.
    """
    raw = line.rstrip("\n\r")
    m = re.match(r"^\s*\[\d+\]\s+", raw)
    if not m:
        return raw
    tail = raw[m.end() :].strip()
    if not (tail.startswith("{") and tail.endswith("}")):
        return raw
    try:
        obj = ast.literal_eval(tail)
    except (ValueError, SyntaxError, MemoryError):
        return raw
    if isinstance(obj, dict) and isinstance(obj.get("text"), str):
        return obj["text"]
    return raw


def _find_next_dslapp_marker(s: str, start: int) -> tuple[int, int]:
    """Return ``(index, prefix_len)`` for the next ``__DSLAPP__:`` or bare ``DSLAPP:``."""
    n = len(s)
    while start < n:
        i = s.find("__DSLAPP__:", start)
        j = s.find("DSLAPP:", start)
        candidates: list[tuple[int, int]] = []
        if i != -1:
            candidates.append((i, len("__DSLAPP__:")))
        if j != -1:
            if j >= 2 and s[j - 2 : j] == "__":
                start = j + 1
                continue
            candidates.append((j, len("DSLAPP:")))
        if not candidates:
            return -1, 0
        return min(candidates, key=lambda x: x[0])
    return -1, 0


def _dslapp_object_to_sse(obj: dict[str, Any], raw_fallback: str) -> tuple[str, dict[str, Any]]:
    """Map one parsed ``__DSLAPP__`` JSON object to an SSE event + payload."""
    t = obj.get("t") or obj.get("type")
    if t in ("markdown", "md"):
        body = obj.get("body") or obj.get("text") or ""
        return ("block", {"kind": "markdown", "body": str(body)})
    if t == "image":
        return (
            "block",
            {
                "kind": "image",
                "src": str(obj.get("src") or obj.get("url") or ""),
                "alt": str(obj.get("alt") or ""),
            },
        )
    if t == "log":
        return ("log", {"text": str(obj.get("body") or obj.get("text") or raw_fallback)})
    return ("block", {"kind": "json", "data": obj})


def _markdown_body_has_dslapp_marker(body: str) -> bool:
    pos, _ = _find_next_dslapp_marker(body, 0)
    return pos >= 0


def _sanitize_wardrobe_display_markdown(md: str) -> str:
    """Drop broken pipe-table crumbs and stray protocol lines before Activity render."""
    if not md:
        return ""
    lines_out: list[str] = []
    for line in md.splitlines():
        s = line.strip()
        if not s:
            lines_out.append(line)
            continue
        # Leftover DSL lines (normally split out upstream)
        if re.match(r"^(?:__)?DSLAPP__?:\s*", s, re.I):
            continue
        if "|" in s and "!" not in s and "`" not in s:
            if re.search(r"\bTops\b", s, re.I) and re.search(r"\bBottoms\b", s, re.I):
                continue
            if re.match(r"^[\s|:\-−—]+$", s):
                continue
            if re.match(r"^\|(?:\s*[-:]+[-\s:|]*)\|$", s):
                continue
        lines_out.append(line)
    text = "\n".join(lines_out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _strip_inline_markdown_images(md: str) -> str:
    """Remove ![alt](url) so thumbnails are not duplicated when DSL emits image blocks."""
    if not md:
        return ""
    without = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    without = re.sub(r"[ \t]+\n", "\n", without)
    without = re.sub(r"\n{3,}", "\n\n", without).strip()
    return without


def _expand_markdown_block_payload(
    payload: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    """Split markdown bodies on embedded DSLAPP JSON; strip wardrobe table noise."""
    if payload.get("kind") != "markdown":
        return [("block", payload)]
    body = payload.get("body")
    if not isinstance(body, str) or not body.strip():
        return [("block", payload)]

    preserved = {k: v for k, v in payload.items() if k not in {"kind", "body"}}
    strip_imgs = _markdown_body_has_dslapp_marker(body)

    out: list[tuple[str, dict[str, Any]]] = []
    cursor = 0
    dec = json.JSONDecoder()
    s = body

    while True:
        pos, plen = _find_next_dslapp_marker(s, cursor)
        if pos < 0:
            tail = s[cursor:]
            chunk = _strip_inline_markdown_images(tail) if strip_imgs else tail
            sanitized = _sanitize_wardrobe_display_markdown(chunk)
            if sanitized.strip():
                md_payload = {"kind": "markdown", "body": sanitized, **preserved}
                out.append(("block", md_payload))
            break
        head = s[cursor:pos]
        if head.strip():
            chunk = _strip_inline_markdown_images(head) if strip_imgs else head
            sanitized = _sanitize_wardrobe_display_markdown(chunk)
            if sanitized.strip():
                md_payload = {"kind": "markdown", "body": sanitized, **preserved}
                out.append(("block", md_payload))
        j = pos + plen
        while j < len(s) and s[j] in " \t":
            j += 1
        try:
            obj, end = dec.raw_decode(s, j)
        except json.JSONDecodeError:
            cursor = pos + plen
            continue
        if isinstance(obj, dict):
            ev, pl = _dslapp_object_to_sse(obj, s[pos:end])
            if ev == "block" and pl.get("kind") == "markdown":
                out.extend(_expand_markdown_block_payload(pl))
            elif ev == "block":
                out.append((ev, pl))
            elif ev == "log":
                tx = pl.get("text", "")
                if tx.strip():
                    chunk = tx
                    sanitized = _sanitize_wardrobe_display_markdown(chunk)
                    if sanitized.strip():
                        out.append(("block", {**preserved, "kind": "markdown", "body": sanitized}))
        cursor = end

    if not out:
        chunk = _strip_inline_markdown_images(body) if strip_imgs else body
        sanitized = _sanitize_wardrobe_display_markdown(chunk)
        if sanitized.strip():
            return [("block", {"kind": "markdown", "body": sanitized, **preserved})]
        return []

    merged: list[tuple[str, dict[str, Any]]] = []
    for ev, pl in out:
        if (
            merged
            and ev == "block"
            and merged[-1][0] == "block"
            and merged[-1][1].get("kind") == "markdown"
            and isinstance(pl, dict)
            and pl.get("kind") == "markdown"
        ):
            mp = merged[-1][1]
            bb = mp.get("body", "").strip() + "\n\n" + pl.get("body", "").strip()
            mp["body"] = bb.strip()
        else:
            merged.append((ev, pl))

    return merged


def _iter_stdout_sse_events(line: str) -> list[tuple[str, dict[str, Any]]]:
    """Split one stdout line into zero or more ``(event, payload)`` tuples for SSE.

    Handles:
    * whole-line ``__DSLAPP__:`` / ``DSLAPP:`` JSON;
    * ``[idx] {'send_to': …, 'text': '…'}`` wrappers from the network runtime;
    * multiple ``__DSLAPP__:`` blobs embedded in prose (images + markdown).
    """
    raw = line.rstrip("\n\r")
    if not raw:
        return [("log", {"text": ""})]

    s = _unwrap_network_message_line(raw)
    out: list[tuple[str, dict[str, Any]]] = []
    cursor = 0
    dec = json.JSONDecoder()

    while True:
        pos, plen = _find_next_dslapp_marker(s, cursor)
        if pos < 0:
            tail = s[cursor:]
            if tail.strip():
                out.append(("log", {"text": tail}))
            break
        head = s[cursor:pos]
        if head.strip():
            out.append(("log", {"text": head}))
        j = pos + plen
        while j < len(s) and s[j] in " \t":
            j += 1
        try:
            obj, end = dec.raw_decode(s, j)
        except json.JSONDecodeError:
            out.append(
                (
                    "log",
                    {
                        "text": s[pos : pos + plen].strip()
                        or "[Malformed __DSLAPP__ JSON — skipped]"
                    },
                )
            )
            cursor = pos + plen
            continue
        if isinstance(obj, dict):
            out.append(_dslapp_object_to_sse(obj, s[pos:end]))
        else:
            out.append(("log", {"text": s[pos:end]}))
        cursor = end

    if not out:
        out.append(("log", {"text": raw}))

    if len(out) == 1 and out[0][0] == "log":
        t = out[0][1].get("text", "")
        if _looks_like_markdown_line(t):
            return [("block", {"kind": "markdown", "body": t, "source": "heuristic"})]
    return out


def _format_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


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

    # Format 1: filename embedded in opening fence (Markdown / JSON)
    for m in re.finditer(r"```(?:[\w]+\s+)?(\S+\.(?:md|json))\n(.*?)```", text, re.DOTALL):
        fname = (m.group(1) or "").strip().replace("\\", "/")
        if fname.endswith(".md"):
            files[normalise(fname)] = m.group(2)
        elif fname.endswith(".json"):
            base = Path(fname).name
            if base in _EDITABLE_OFFICE_JSON:
                files[base] = m.group(2)

    # Format 2: markdown heading directly before a bare fence
    for m in re.finditer(
        r"#{1,4}\s+([\w./]+\.(?:md|json))\s*\n+```[^\n]*\n(.*?)```", text, re.DOTALL
    ):
        key = (m.group(1) or "").strip().replace("\\", "/")
        payload = m.group(2)
        if key.endswith(".md"):
            norm = normalise(key)
            if norm not in files:
                files[norm] = payload
        elif key.endswith(".json"):
            base = Path(key).name
            if base in _EDITABLE_OFFICE_JSON and base not in files:
                files[base] = payload

    # Format 3: "Save as `path`" before a bare fence
    for m in re.finditer(
        r"[Ss]ave as\s+`([\w./]+\.(?:md|json))`[^\n]*\n+```[^\n]*\n(.*?)```", text, re.DOTALL
    ):
        key = (m.group(1) or "").strip().replace("\\", "/")
        payload = m.group(2)
        if key.endswith(".md"):
            norm = normalise(key)
            if norm not in files:
                files[norm] = payload
        elif key.endswith(".json"):
            base = Path(key).name
            if base in _EDITABLE_OFFICE_JSON and base not in files:
                files[base] = payload

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


class CreateOfficeMediaItem(BaseModel):
    """Image or PDF from the create-office chat, persisted under ``media/uploads/``."""

    media_type: str
    data: str  # base64 (optional data: URL prefix — stripped like chat attachments)
    filename: str | None = None


class CreateOfficePayload(BaseModel):
    name: str
    office_md: str
    roles: dict[str, str]
    chat_media: list[CreateOfficeMediaItem] = Field(default_factory=list)


def _guess_media_extension(filename: str | None, media_type: str) -> str:
    if filename and "." in filename:
        ext = Path(filename).suffix.lower()[:8]
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"):
            return ext
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }.get(media_type.strip().lower(), ".bin")


def _persist_office_chat_media(
    office_dir: Path,
    items: list[CreateOfficeMediaItem],
    *,
    sequential_names: bool = False,
) -> list[str]:
    """Write chat attachments into ``media/uploads/``. Returns relative paths ``media/uploads/...``.

    When ``sequential_names`` is True (create-office batch), files are named
    ``image_0.webp``, ``image_1.jpg``, … in list order so ``office.md`` / roles
    can reference stable paths. Otherwise each file gets a short random prefix
    (single-file uploads) to avoid collisions.
    """
    if not items:
        return []
    allowed = frozenset(
        {"image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"}
    )
    uploads = office_dir / "media" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for i, item in enumerate(items):
        mt = item.media_type.strip().lower()
        if mt not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"chat_media[{i}]: unsupported type {mt!r}. "
                "Use image/jpeg, image/png, image/gif, image/webp, or application/pdf.",
            )
        b64 = _strip_data_url_b64(item.data)
        try:
            raw = base64.b64decode(b64, validate=False)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"chat_media[{i}]: invalid base64"
            ) from e
        if len(raw) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"chat_media[{i}]: file too large (max {MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB).",
            )
        ext = _guess_media_extension(item.filename, mt)
        if sequential_names:
            if mt == "application/pdf":
                fname = f"document_{i}{ext}"
            else:
                fname = f"image_{i}{ext}"
        else:
            base = (item.filename or "upload").replace("\\", "/").split("/")[-1]
            stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", base.rsplit(".", 1)[0])[:80] or "upload"
            fname = f"{uuid.uuid4().hex[:10]}_{stem}{ext}"
        out_path = uploads / fname
        out_path.write_bytes(raw)
        saved.append(f"media/uploads/{fname}")
    return saved


def _user_office_dir_for_media_write(name: str) -> Path:
    """Only offices under ``user_offices/`` accept uploaded media."""
    candidate = (USER_OFFICES_DIR / name).resolve()
    if not candidate.is_dir() or not (candidate / "office.md").is_file():
        raise HTTPException(status_code=404, detail=f"Custom office '{name}' not found")
    try:
        candidate.relative_to(USER_OFFICES_DIR.resolve())
    except ValueError as e:
        raise HTTPException(
            status_code=403, detail="Media uploads are only allowed for Your Offices."
        ) from e
    return candidate


@app.get("/api/offices/{name}/media/{resource_path:path}")
def get_office_media(name: str, resource_path: str):
    """Serve a file from ``<office>/media/`` (read-only)."""
    try:
        office_dir = _find_office_dir(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    media_root = (office_dir / "media").resolve()
    if not media_root.is_dir():
        raise HTTPException(status_code=404, detail="This office has no media/ folder yet.")
    parts = [p for p in resource_path.split("/") if p and p != ".."]
    safe = _safe_path_under(media_root, *parts)
    if safe is None or not safe.is_file():
        raise HTTPException(status_code=404, detail="Media file not found")
    return FileResponse(safe)


@app.post("/api/offices/{name}/media")
def upload_office_media(name: str, payload: CreateOfficeMediaItem):
    """Append one image/PDF into ``media/uploads/`` (custom offices only)."""
    office_dir = _user_office_dir_for_media_write(name)
    paths = _persist_office_chat_media(office_dir, [payload])
    rel = paths[0]
    tail = rel[len("media/") :] if rel.startswith("media/") else rel
    return {"path": rel, "url": f"/api/offices/{name}/media/{tail}"}


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

    shutil.copytree(
        source_dir,
        dest_dir,
        ignore=shutil.ignore_patterns(
            "app.py", "__pycache__", "*.pyc", "build",
        ),
    )
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

    if payload.chat_media:
        _persist_office_chat_media(
            office_dir, payload.chat_media, sequential_names=True
        )

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
        _office_output_queues.pop(name, None)

    try:
        office_dir = _find_office_dir(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Pick up GMAIL_* / API keys written to .env while the server was running.
    load_dotenv(BACKEND_DIR / ".env", override=False)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    # Rich web Activity panel: sinks may emit ``__DSLAPP__:`` lines instead of terminal ANSI.
    env["DISSYSLAB_APP_SSE"] = "1"
    # So ``python -m dissyslab.cli`` resolves the repo package without a global
    # ``pip install -e .`` (common in dev / conda).
    _root = str(DISSYSLAB_ROOT)
    _pp = env.get("PYTHONPATH", "")
    if _root not in _pp.split(os.pathsep):
        env["PYTHONPATH"] = _root if not _pp else f"{_root}{os.pathsep}{_pp}"
    # Prefetch NOAA / wardrobe / multi-city snapshots inside the subprocess:
    # ``dissyslab.cli run`` → ``office_run_context.apply_office_run_context_to_environ``.
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
    """SSE stream of a running office's stdout.

    Emits named events for the custom app UI:

    * ``event: log`` — plain text line (JSON ``{"text": "..."}``).
    * ``event: block`` — structured payload (markdown, image, …).

    Offices may also print ``__DSLAPP__:{...json...}`` for explicit blocks.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        proc = _running.get(name)
        out_q = _office_output_queues.get(name)
        if not proc or out_q is None:
            yield _format_sse("log", {"text": "[Office is not running]"})
            return

        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, out_q.get)
            if line is None:
                _running.pop(name, None)
                _office_output_queues.pop(name, None)
                yield _format_sse("log", {"text": "[Process finished]"})
                break
            for ev, payload in _iter_stdout_sse_events(line):
                if ev == "block" and payload.get("kind") == "markdown":
                    expanded = _expand_markdown_block_payload(payload)
                    if expanded:
                        for ev2, pl2 in expanded:
                            yield _format_sse(ev2, pl2)
                    else:
                        yield _format_sse(ev, payload)
                else:
                    yield _format_sse(ev, payload)

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
# JSON blobs the customize-chat flow may overwrite (basename only).
_EDITABLE_OFFICE_JSON = frozenset({"wardrobe_inventory.json", "wardrobe_run_config.json"})


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


def _office_dir_is_under_user_offices(office_dir: Path) -> bool:
    try:
        Path(office_dir).resolve().relative_to(USER_OFFICES_DIR.resolve())
        return True
    except ValueError:
        return False


def _persist_last_user_message_attachments(
    office_dir: Path, messages: list[ChatMessage]
) -> tuple[list[str], int | None]:
    """Write the **most recent** user message attachments to ``media/uploads/``.

    For **Your Offices** that already have ``wardrobe_inventory.json``, image-only
    batches are saved as ``image_0.<ext>``, ``image_1.<ext>``, … (same convention
    as Create office) so ``photo_media`` paths stay stable. Other cases use unique
    filenames to avoid collisions.
    """
    if not _office_dir_is_under_user_offices(office_dir):
        return [], None

    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if msg.role != "user":
            continue
        atts = msg.attachments or []
        if not atts:
            continue
        items = [
            CreateOfficeMediaItem(
                media_type=a.media_type, data=a.data, filename=a.filename
            )
            for a in atts
        ]
        has_wardrobe = (office_dir / "wardrobe_inventory.json").is_file()
        only_images = all(
            (a.media_type or "").strip().lower() in _ALLOWED_IMAGE_MEDIA for a in atts
        )
        sequential = bool(has_wardrobe and only_images)
        saved = _persist_office_chat_media(
            office_dir, items, sequential_names=sequential
        )
        return saved, idx

    return [], None


def _append_server_note_to_user_message(
    messages: list[ChatMessage], idx: int, note: str
) -> list[ChatMessage]:
    if idx < 0 or idx >= len(messages):
        return messages
    base = (messages[idx].content or "").rstrip()
    suffix = f"\n\n{note}" if base else note
    new_content = base + suffix
    msg = messages[idx]
    if hasattr(msg, "model_copy"):
        patched = msg.model_copy(update={"content": new_content})
    else:
        patched = msg.copy(update={"content": new_content})
    out = list(messages)
    out[idx] = patched
    return out


def _attachment_persist_note_for_claude(
    saved_paths: list[str], office_dir: Path
) -> str:
    lines = (
        ["[Server: attachment(s) saved to this office before your reply]"]
        + [f"- {p}" for p in saved_paths]
        + [""]
    )
    if (office_dir / "wardrobe_inventory.json").is_file():
        lines += [
            "This office has `wardrobe_inventory.json`. Map garments to the paths above "
            "(typically `media/uploads/image_0.<ext>`, …). Emit a full fenced file whose "
            "first line after the opening triple-backticks is exactly `wardrobe_inventory.json`, "
            "then the JSON body, whenever `photo_media` or garment rows change. "
            "Remove JSON entries if the user deleted garments.",
        ]
    else:
        lines += [
            "Reference these paths from roles or other config if the user asked to use new images.",
        ]
    return "\n".join(lines).strip()


def _strip_json_fence_body(raw: str) -> str:
    t = raw.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_]*\s*\n", "", t, count=1)
        t = re.sub(r"\n```\s*$", "", t, count=1)
    return t.strip()


def _write_parsed_json_if_valid(office_dir: Path, basename: str, raw: str) -> bool:
    body = _strip_json_fence_body(raw)
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return False
    target = Path(office_dir) / basename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


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

    for json_name in sorted(_EDITABLE_OFFICE_JSON):
        jp = Path(office_dir) / json_name
        if jp.is_file():
            lines += [f"```{json_name}", jp.read_text(encoding="utf-8"), "```\n"]

    lines += [
        "Update these files based on the user's request.",
        "Output the complete updated files (not diffs) using the filename-in-fence format.",
        "When garment photos or wardrobe rows change, output a complete wardrobe_inventory.json block: opening fence line must be exactly the filename followed by newline, then raw JSON.",
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

    customize_banner = (
        "### AI Customize — attachments persisted before each reply\n\n"
        "When this panel sends photos or PDFs, the backend writes them under "
        "`media/uploads/` on **Your Offices** before the model sees the conversation. "
        "The user's last message may include a **[Server:** line listing paths. "
        "If `wardrobe_inventory.json` exists and **every attachment on that Send is an image**, "
        "files are saved as consecutive `media/uploads/image_0.<ext>`, "
        "`image_1.<ext>`, … (same as Create office). Update JSON `photo_media` and mirror "
        "changes in wardrobe roles.\n\n"
        "**DisSysLab `nl_role` routing:** Each `roles/*.md` prompt **must** keep at least one "
        "plain-text line containing **`send to`** plus the output port token(s), e.g. "
        "`Always send to compiler.` — matching Jordan→Riley in `office.md`. "
        "**Do not** remove or truncate those lines; **Run** fails if ports are undeclared.\n\n"
        "---\n\n"
    )
    office_context = customize_banner + _office_context_prompt(office_dir)

    base_context = CLAUDE_CONTEXT_PATH.read_text() if CLAUDE_CONTEXT_PATH.exists() else ""
    system_prompt = base_context + "\n\n---\n\n## IMPORTANT — You are running inside a web UI\n\nDo NOT give terminal instructions. The user may attach images or PDFs as extra context — use them when updating files.\n\n### Rich output (optional)\n\nThe custom app can show structured output when roles or sinks print a line starting with ``__DSLAPP__:`` followed by JSON, e.g. ``{\\\"t\\\":\\\"markdown\\\",\\\"body\\\":\\\"## Title\\\\n...\\\"}`` or image blocks with ``src`` under ``/api/offices/<office_name>/media/...``.\n\n### Persisted uploads\n\nOn **Create office**, attachments are saved as ``media/uploads/image_0.<ext>``, ``image_1.<ext>``, … in chronological order across all user messages that had files (PDFs: ``document_0.pdf``, …). **AI Customize** persists attachments each Send too (with a **[Server:** note on the user's turn). Mixed PDF+image uploads use unique filenames to avoid overwriting.\n\nOutput updated files using filename-in-fence format:\n\n```office.md\ncontent\n```\n\n```roles/analyst.md\ncontent\n```\n\nJSON at the office root is allowed:\n\n```wardrobe_inventory.json\n{ ... }\n```\n\n### console_input (web Run)\n\nWhen ``Sources:`` includes ``console_input``, always write ``console_input(default_message=\\\"...\\\")`` with one realistic sample user line. The custom app runs offices without interactive stdin; that string is used once so **Run** works.\n\n---\n\n" + office_context

    msgs = list(payload.messages)
    saved_media, attach_idx = _persist_last_user_message_attachments(
        office_dir, msgs
    )
    if saved_media and attach_idx is not None:
        note = _attachment_persist_note_for_claude(saved_media, office_dir)
        msgs = _append_server_note_to_user_message(msgs, attach_idx, note)

    try:
        api_messages = _anthropic_messages_from_payload(msgs)
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
        if files and _office_dir_is_under_user_offices(office_dir):
            # Auto-save updated files to the office directory
            roles_dir = office_dir / "roles"
            roles_dir.mkdir(parents=True, exist_ok=True)
            saved_paths: list[str] = []
            skipped_roles: dict[str, str] = {}
            for filepath, content in files.items():
                if filepath == "office.md":
                    (office_dir / "office.md").write_text(content, encoding="utf-8")
                    saved_paths.append(filepath)
                elif filepath.startswith("roles/"):
                    role_name = filepath.replace("roles/", "")
                    if not role_name.endswith(".md"):
                        skipped_roles[filepath] = "not a .md role filename"
                        continue
                    if not _nl_role_md_declares_ports(content):
                        skipped_roles[filepath] = (
                            "no valid 'send to <port>' line — restore routing from "
                            "office.md (file not saved to avoid breaking Run)"
                        )
                        continue
                    (roles_dir / role_name).write_text(content, encoding="utf-8")
                    saved_paths.append(filepath)
                elif filepath in _EDITABLE_OFFICE_JSON:
                    if _write_parsed_json_if_valid(office_dir, filepath, content):
                        saved_paths.append(filepath)

            if skipped_roles:
                yield f"event: save_skipped\ndata: {json.dumps(skipped_roles)}\n\n"
            if saved_paths:
                yield f"event: saved\ndata: {json.dumps(saved_paths)}\n\n"

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

### Persisted media (custom app)

When the user clicks **Create office**, the UI sends **every image/PDF from every user
message in the thread** (in order). The server writes them as ``media/uploads/image_0.webp``,
``media/uploads/image_1.jpg``, … (``document_0.pdf`` for PDFs) so you can reference stable paths.

In role prompts use those paths, e.g. ``![outfit](media/uploads/image_0.webp)`` or instruct the agent to
print a structured line for the app output panel:

``__DSLAPP__:{"t":"image","src":"/api/offices/<OFFICE_NAME>/media/uploads/image_0.webp","alt":"Outfit"}``

(Use the actual office folder name for ``<OFFICE_NAME>`` from the ``# Office:`` line.)
For long formatted briefings from Python, prefer ``__DSLAPP__:{"t":"markdown","body":"...escaped..."}``.
Always use the double-underscore prefix ``__DSLAPP__:`` (not ``DSLAPP:``).

### Sidebar description (recommended)

The office list shows a short subtitle like built-in offices. Prefer one of:
- YAML at the very top of ``office.md``: ``---`` then ``description: One line summary.`` then ``---``, then the usual ``# Office: …`` and DSL; or
- A ``README.md`` next to ``office.md`` whose first non-``#`` line is that summary.

If both are omitted, the app still derives a one-line hint from ``Agents:`` / ``Sources:`` in ``office.md``.

### console_input (web Run)

When ``Sources:`` includes ``console_input``, always write ``console_input(default_message=\\\"...\\\")`` with one realistic sample user line. The custom app runs offices without interactive stdin; that string is used once so **Run** works.
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
