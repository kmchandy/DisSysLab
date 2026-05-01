"""
dissyslab/cli_chat.py — Claude-powered "create / edit office" CLI commands.

Powers `dsl new <name>` and `dsl edit <office_dir>`, which let users build
or modify offices by chatting with Claude in plain English. The CLI streams
Claude's response to the terminal, parses out the file blocks Claude
produces, and writes them to disk automatically — no copy-paste.

Lifted from the React UI prototype contributed by Nyasha Mahonde
(github.com/Nyasha2). The chat-streaming flow and the `parse_claude_files`
parser come from his FastAPI backend; here they're packaged as a stdlib +
anthropic chat loop with no JavaScript stack required.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Default model. Sonnet handles office-file generation well at ~1/5 the
# per-token cost of Opus, which matters for a teaching context where
# students iterate. Override with `dsl new <name> --model <id>`.
DEFAULT_MODEL = "claude-sonnet-4-6"

_CLAUDE_CONTEXT: str | None = None


def _load_claude_context() -> str:
    """Read the bundled CLAUDE_CONTEXT_OFFICE.md, or return a minimal fallback."""
    global _CLAUDE_CONTEXT
    if _CLAUDE_CONTEXT is not None:
        return _CLAUDE_CONTEXT

    here = Path(__file__).parent
    candidates = [
        here.parent / "CLAUDE_CONTEXT_OFFICE.md",  # development install
        here / "CLAUDE_CONTEXT_OFFICE.md",          # if ever shipped inside pkg
    ]
    for path in candidates:
        if path.exists():
            _CLAUDE_CONTEXT = path.read_text()
            return _CLAUDE_CONTEXT

    _CLAUDE_CONTEXT = (
        "You are helping a user build a DisSysLab office in plain English.\n"
        "Output an `office.md` file and one or more `roles/<name>.md` files.\n"
    )
    return _CLAUDE_CONTEXT


# ── File parsing (lifted from Nyasha's custom_app backend) ────────────────

def parse_claude_files(text: str) -> dict[str, str]:
    """
    Parse Claude's response for office.md and roles/*.md file blocks.

    Handles three formats Claude tends to use:

      Format 1 — filename inside the opening fence:
          ```roles/analyst.md
          content
          ```

      Format 2 — markdown heading directly before a bare fence:
          ### roles/analyst.md
          ```
          content
          ```

      Format 3 — "Save as `path`" instruction before a bare fence:
          Save as `roles/analyst.md`
          ```
          content
          ```

    Returns a dict mapping office-relative path -> file body. Strips any
    leading directory prefix (e.g. `my_office/`) so paths are uniformly
    `office.md` or `roles/<name>.md`.
    """
    files: dict[str, str] = {}

    def normalise(path: str) -> str:
        parts = path.strip().split("/")
        # Drop any leading directory unless it's the literal `roles/` prefix.
        if len(parts) >= 2 and parts[0] != "roles":
            parts = parts[1:]
        return "/".join(parts)

    # Format 1: filename embedded in opening fence
    for m in re.finditer(r"```(?:[\w]+\s+)?(\S+\.md)\n(.*?)```", text, re.DOTALL):
        files[normalise(m.group(1))] = m.group(2)
    # Format 2: heading immediately before a bare fence
    for m in re.finditer(
        r"#{1,4}\s+([\w./]+\.md)\s*\n+```[^\n]*\n(.*?)```", text, re.DOTALL
    ):
        files.setdefault(normalise(m.group(1)), m.group(2))
    # Format 3: "Save as `path`" before a bare fence
    for m in re.finditer(
        r"[Ss]ave as\s+`([\w./]+\.md)`[^\n]*\n+```[^\n]*\n(.*?)```", text, re.DOTALL
    ):
        files.setdefault(normalise(m.group(1)), m.group(2))

    return files


def _write_files(target_dir: Path, files: dict[str, str]) -> list[Path]:
    """Write parsed files into target_dir; create roles/ as needed."""
    written: list[Path] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    roles_dir = target_dir / "roles"

    for filepath, content in files.items():
        if filepath == "office.md":
            dest = target_dir / "office.md"
        elif filepath.startswith("roles/"):
            roles_dir.mkdir(exist_ok=True)
            dest = roles_dir / filepath[len("roles/"):]
        else:
            # Unexpected path — skip silently rather than risk a write
            # outside target_dir.
            continue
        dest.write_text(content)
        written.append(dest)

    return written


# ── System prompts ────────────────────────────────────────────────────────

_CHAT_MODE_NOTE = """

---

## You are running in a CLI chat session

The user typed `dsl new <name>` or `dsl edit <office>` and is talking to
you in their terminal. Do NOT give "save this file" or "run this command"
instructions — when you produce final files, the CLI parses them out and
writes them to disk automatically.

When you are ready to output files, use this exact format:

```office.md
# Office: name_here
...
```

```roles/analyst.md
# Role: analyst
...
```

The filename goes **on the opening fence line** (not as a heading or a
"Save as" comment). One file per fenced block.

Before you are ready to produce files, you may ask the user clarifying
questions; they will reply and the conversation continues. When the
design is clear, output the files.
"""


def _system_prompt_create() -> str:
    return _load_claude_context() + _CHAT_MODE_NOTE


def _system_prompt_edit(office_dir: Path) -> str:
    """System prompt for editing — includes the current office's files."""
    base = _load_claude_context() + _CHAT_MODE_NOTE

    office_md = office_dir / "office.md"
    if not office_md.exists():
        return base

    parts = [
        base,
        "\n---\n\n## You are editing an existing office",
        "\nHere are the current files:\n",
        "```office.md",
        office_md.read_text().rstrip(),
        "```\n",
    ]

    roles_dir = office_dir / "roles"
    if roles_dir.exists():
        for role_file in sorted(roles_dir.glob("*.md")):
            parts.extend([
                f"```roles/{role_file.name}",
                role_file.read_text().rstrip(),
                "```\n",
            ])

    parts.append(
        "Apply the user's requested changes. Output **complete** updated "
        "files (not diffs). Output ONLY the files that need to change."
    )

    return "\n".join(parts)


# ── Chat loop ─────────────────────────────────────────────────────────────

def _stream_response(client, model: str, system: str, messages: list) -> str:
    """Stream Claude's response to stdout; return the accumulated text."""
    full = ""
    with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=system,
        messages=messages,
    ) as stream:
        for chunk in stream.text_stream:
            print(chunk, end="", flush=True)
            full += chunk
    print()  # final newline
    return full


def _chat_loop(
    initial_prompt: str,
    system_prompt: str,
    target_dir: Path,
    *,
    model: str,
) -> int:
    """
    Multi-turn chat with Claude. Exits when Claude produces files (which
    are written to target_dir) or the user types empty input / quit.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        print("Set it in your shell or in a .env file in this folder.",
              file=sys.stderr)
        return 1

    try:
        import anthropic
    except ImportError:
        print("Error: the 'anthropic' package is not installed.", file=sys.stderr)
        print("Run: pip install anthropic", file=sys.stderr)
        return 1

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = [{"role": "user", "content": initial_prompt}]

    print()
    while True:
        try:
            response = _stream_response(client, model, system_prompt, messages)
        except KeyboardInterrupt:
            print("\n(aborted)")
            return 130
        except Exception as exc:
            print(f"\nError calling Claude: {exc}", file=sys.stderr)
            return 1

        files = parse_claude_files(response)
        if files:
            written = _write_files(target_dir, files)
            print()
            cwd = Path.cwd()
            for path in written:
                try:
                    rel = path.relative_to(cwd)
                except ValueError:
                    rel = path
                print(f"  ✓ wrote {rel}")
            print()
            print("Next steps:")
            try:
                rel_dir = target_dir.relative_to(cwd)
            except ValueError:
                rel_dir = target_dir
            print(f"  cd {rel_dir}")
            print("  dsl run .")
            return 0

        # No files yet — continue the conversation.
        messages.append({"role": "assistant", "content": response})
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n(aborted)")
            return 130
        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("(aborted)")
            return 0
        messages.append({"role": "user", "content": user_input})


# ── Public entry points (called by cli.py) ────────────────────────────────

def chat_create(target_dir: Path, *, model: str = DEFAULT_MODEL) -> int:
    """Create a new office in target_dir by chatting with Claude."""
    if target_dir.exists():
        print(f"Error: target folder '{target_dir}' already exists.",
              file=sys.stderr)
        print("Refusing to overwrite. Choose a different folder name.",
              file=sys.stderr)
        return 2

    print(f"Creating a new office in: {target_dir}")
    print("Describe what you want it to do. Claude may ask follow-ups,")
    print("then write the office files. Press Ctrl+C any time to abort.")
    print()

    try:
        initial = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n(aborted)")
        return 130
    if not initial:
        print("(no description provided)")
        return 0

    return _chat_loop(
        initial_prompt=initial,
        system_prompt=_system_prompt_create(),
        target_dir=target_dir,
        model=model,
    )


def chat_edit(office_dir: Path, *, model: str = DEFAULT_MODEL) -> int:
    """Modify an existing office by chatting with Claude."""
    if not office_dir.is_dir():
        print(f"Error: '{office_dir}' is not a directory.", file=sys.stderr)
        return 2
    if not (office_dir / "office.md").exists():
        print(f"Error: no office.md in '{office_dir}'.", file=sys.stderr)
        return 2

    print(f"Editing office: {office_dir}")
    print("Describe the change you want. Claude will rewrite the files")
    print("in place. Press Ctrl+C any time to abort.")
    print()

    try:
        initial = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n(aborted)")
        return 130
    if not initial:
        print("(no description provided)")
        return 0

    return _chat_loop(
        initial_prompt=initial,
        system_prompt=_system_prompt_edit(office_dir),
        target_dir=office_dir,
        model=model,
    )
