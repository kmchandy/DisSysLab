"""
dissyslab/cli_chat.py -- ``dsl new`` and ``dsl edit``: build an office by chatting.

The user describes an office in plain English; Claude asks what it needs
to and then writes the files; the CLI writes them into the office folder,
runs ``dsl check`` on the result, and shows the report. If the check finds
problems, the report goes back to Claude to fix -- visibly, at most
``FIX_ROUNDS`` times -- so what is left on disk either checks clean or the
user has seen exactly why not.

**What Claude is told** is the office reference that ships with the
package, the same text ``dsl grammar`` prints
(``dissyslab/reference/*.md``), followed by the rules for this chat. One
copy of the language: the model cannot be taught a version the install
does not have.

The chat-streaming loop and the file-block parser were contributed by
Nyasha Mahonde (github.com/Nyasha2), from the backend of his React UI
prototype.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

# Default model. Sonnet handles office-file generation well at a fraction
# of the per-token cost of Opus, which matters for a teaching context where
# students iterate. Override with `dsl new <name> --model <id>`.
DEFAULT_MODEL = "claude-sonnet-4-6"

#: How many times a failed `dsl check` is sent back to Claude to fix.
FIX_ROUNDS = 2

REFERENCE = Path(__file__).parent / "reference"
_REFERENCE_FILES = ("grammar.md", "roles.md", "sources_and_sinks.md", "worked_examples.md")


# ── What Claude is told ───────────────────────────────────────────────────


_CHAT_RULES = """

---

# You are building an office with a student, in their terminal

The student typed `dsl new <folder>` or `dsl edit <folder>`. Everything
above is the reference for the office language; follow it exactly. In
particular: `office.md` has `sources:`, `sinks:`, `agents:` and
`connections:` sections with `name: kind(args)` declarations and `a -> b`
connections. There is no title line and no sentence form ("X is a Y" is
version 1 and does not run).

Ask a question or two if the request is unclear. Prefer a small office
that works to a large one that might. Prefer `file_source` with a small
data file you write, so the office runs without a network, unless the
student asks for a live source. Give every role an `out:` line, with
values wherever the role chooses from a list: these are the guardrails
the course teaches.

When you are ready, output the files, one per fenced block, with the
path on the opening fence line:

```office.md
sources:
    ...
```

```roles/triage.md
---
emits: ...
in: ...
out: ...
---
...
```

Allowed paths: `office.md`, `README.md`, `roles/<name>.md` or `.py`,
`sources/<name>.py`, `sinks/<name>.py`, and data files in the folder
itself (`<name>.jsonl`, `<name>.json`, `<name>.csv`, `<name>.txt`).
Do not tell the student to save files or run commands: the CLI writes
the files and runs `dsl check` itself. If the check finds problems, you
will be shown its report; fix them by outputting the corrected files in
full.
"""


def _load_reference() -> str:
    """The office reference ``dsl grammar`` prints, as one text."""
    parts = []
    for name in _REFERENCE_FILES:
        path = REFERENCE / name
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(parts)


def system_prompt_create() -> str:
    return _load_reference() + _CHAT_RULES


def system_prompt_edit(office_dir: Path) -> str:
    """The create prompt, plus every file of the office being edited."""
    parts = [system_prompt_create(), "\n---\n\n# You are editing an existing office\n",
             "Here are its current files:\n"]
    for path in _office_files(office_dir):
        rel = path.relative_to(office_dir).as_posix()
        parts += [f"```{rel}", path.read_text(encoding="utf-8").rstrip(), "```\n"]
    parts.append(
        "Apply the student's change. Output **complete** updated files, not "
        "diffs, and only the files that change."
    )
    return "\n".join(parts)


def _office_files(office_dir: Path) -> list[Path]:
    """The files of an office worth showing Claude: the ones it may write."""
    out = []
    for path in sorted(office_dir.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(office_dir).as_posix()
        if allowed_path(rel) and path.stat().st_size < 50_000:
            out.append(path)
    return out


# ── Files out of a reply ──────────────────────────────────────────────────


_ALLOWED = re.compile(
    r"^(office\.md|README\.md"
    r"|roles/[A-Za-z_][\w]*\.(md|py)"
    r"|sources/[A-Za-z_][\w]*\.py"
    r"|sinks/[A-Za-z_][\w]*\.py"
    r"|[A-Za-z_][\w-]*\.(jsonl|json|csv|txt))$"
)


def allowed_path(path: str) -> bool:
    """True for a path the chat may write: see ``_CHAT_RULES``. Never ``..``."""
    return bool(_ALLOWED.match(path))


def parse_claude_files(text: str) -> dict[str, str]:
    """The files in Claude's reply: office-relative path -> body.

    Three forms are accepted, because models drift between them:

      1. the path on the opening fence:      ```roles/triage.md
      2. a heading just before a bare fence:  ### roles/triage.md
      3. "Save as `path`" before a bare fence.

    A leading folder name (``my_office/office.md``) is dropped. Paths the
    chat may not write (``allowed_path``) are left out.
    """
    ext = r"\.(?:md|py|jsonl|json|csv|txt)"
    files: dict[str, str] = {}

    def normalise(path: str) -> str:
        parts = path.strip().split("/")
        if len(parts) >= 2 and parts[0] not in ("roles", "sources", "sinks"):
            parts = parts[1:]
        return "/".join(parts)

    for m in re.finditer(rf"```(?:[\w]+\s+)?(\S+{ext})\n(.*?)```", text, re.DOTALL):
        files[normalise(m.group(1))] = m.group(2)
    for m in re.finditer(rf"#{{1,4}}\s+`?([\w./-]+{ext})`?\s*\n+```[^\n]*\n(.*?)```",
                         text, re.DOTALL):
        files.setdefault(normalise(m.group(1)), m.group(2))
    for m in re.finditer(rf"[Ss]ave as\s+`([\w./-]+{ext})`[^\n]*\n+```[^\n]*\n(.*?)```",
                         text, re.DOTALL):
        files.setdefault(normalise(m.group(1)), m.group(2))
    return {p: body for p, body in files.items() if allowed_path(p)}


def write_files(target_dir: Path, files: dict[str, str]) -> list[Path]:
    """Write the files into ``target_dir``, making ``roles/`` etc. as needed."""
    written = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        if not allowed_path(rel):
            continue  # parse_claude_files already filters; this is the last word
        dest = target_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written.append(dest)
    return written


# ── The chat ──────────────────────────────────────────────────────────────


def _stream_response(client: Any, model: str, system: str, messages: list[dict[str, str]]) -> str:
    """Stream Claude's reply to the terminal; return the whole text."""
    full = ""
    with client.messages.stream(model=model, max_tokens=8192, system=system,
                                messages=messages) as stream:
        for chunk in stream.text_stream:
            print(chunk, end="", flush=True)
            full += chunk
    print()
    return full


def _anthropic_client() -> Any:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY is not set. Put it in a .env file in "
              "this folder or one above it (docs/GETTING_STARTED.md, part 5).",
              file=sys.stderr)
        return None
    try:
        import anthropic
    except ImportError:
        print("Error: the 'anthropic' package is not installed. Run: pip install anthropic",
              file=sys.stderr)
        return None
    return anthropic.Anthropic(api_key=api_key)


def _check(target_dir: Path) -> tuple[bool, str]:
    """``dsl check`` on the folder: (no problems, the report as printed)."""
    from dissyslab.office.check import check_office, format_report

    if not (target_dir / "office.md").is_file():
        return False, "There is no office.md yet.\n"
    report = check_office(target_dir)
    return report.ok, format_report(target_dir.name, report)


def _rel(path: Path) -> Path:
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


def chat_loop(
    initial_prompt: str,
    system_prompt: str,
    target_dir: Path,
    *,
    model: str,
    client: Any = None,
    ask: Callable[[str], str] = input,
) -> int:
    """Talk with Claude until it writes files that check clean, or the user stops.

    ``client`` and ``ask`` are there so the loop can be tested without a
    key or a keyboard; ``dsl new`` passes neither.
    """
    if client is None:
        client = _anthropic_client()
        if client is None:
            return 1
    messages: list[dict[str, str]] = [{"role": "user", "content": initial_prompt}]
    fixes_left = FIX_ROUNDS
    print()
    while True:
        try:
            reply = _stream_response(client, model, system_prompt, messages)
        except KeyboardInterrupt:
            print("\n(aborted)")
            return 130
        except Exception as exc:  # noqa: BLE001 - shown to the user as is
            print(f"\nError calling Claude: {exc}", file=sys.stderr)
            return 1
        messages.append({"role": "assistant", "content": reply})

        files = parse_claude_files(reply)
        if files:
            print()
            for path in write_files(target_dir, files):
                print(f"  wrote {_rel(path)}")
            print()
            ok, report = _check(target_dir)
            print("dsl check:")
            print(report, end="")
            if ok:
                print()
                print("Next steps:")
                print(f"  cd {_rel(target_dir)}")
                print("  dsl draw .")
                print("  dsl run .")
                return 0
            if fixes_left > 0:
                fixes_left -= 1
                print("\nSending the problems back to Claude to fix.\n")
                messages.append({"role": "user", "content":
                                 "dsl check reported these problems. Fix them and output "
                                 "the corrected files in full:\n\n" + report})
                continue
            print("\nThe files are written, but dsl check still reports problems. "
                  "Describe a fix, or press Enter to stop and fix them yourself.")

        try:
            user_input = ask("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n(aborted)")
            return 130
        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("(stopped)")
            return 0
        messages.append({"role": "user", "content": user_input})
        fixes_left = FIX_ROUNDS


# ── Entry points (called by cli.py) ───────────────────────────────────────


def chat_create(target_dir: Path, *, model: str = DEFAULT_MODEL) -> int:
    """``dsl new <folder>``: a new office, by chatting with Claude."""
    if target_dir.exists():
        print(f"Error: '{target_dir}' already exists. Choose a new folder name.",
              file=sys.stderr)
        return 2
    print(f"Creating a new office in: {target_dir}")
    print("Describe what you want it to do. Claude may ask questions, then")
    print("writes the files and checks them. Press Ctrl+C any time to stop.")
    print()
    try:
        initial = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n(aborted)")
        return 130
    if not initial:
        print("(no description given)")
        return 0
    return chat_loop(initial, system_prompt_create(), target_dir, model=model)


def chat_edit(office_dir: Path, *, model: str = DEFAULT_MODEL) -> int:
    """``dsl edit <folder>``: change an office, by chatting with Claude."""
    if not (office_dir / "office.md").is_file():
        print(f"Error: no office.md in '{office_dir}'.", file=sys.stderr)
        return 2
    print(f"Editing office: {office_dir}")
    print("Describe the change. Claude rewrites the files that change and")
    print("checks the result. Press Ctrl+C any time to stop.")
    print()
    try:
        initial = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n(aborted)")
        return 130
    if not initial:
        print("(no description given)")
        return 0
    return chat_loop(initial, system_prompt_edit(office_dir), office_dir, model=model)
