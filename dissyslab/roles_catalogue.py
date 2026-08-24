"""What the built-in roles are, and what each one adds to a message.

Why this exists
---------------
Nothing could list the role library, and nothing anywhere said what a
role *emits*. So an assistant asked "what roles are there?" read the
thirteen prompt files and paraphrased, afresh, every time — and no two
students were told the same thing about ``summarizer``.

The emitted field is the fact a user actually needs. It is not
decoration: an agent wired downstream of ``severity_classifier`` reads
``severity``, and someone who was told only that the role "decides how
significant an article is" wires the next agent blind and meets the
mismatch at run time.

The format
----------
Each role file opens with front matter::

    ---
    emits: adds a `severity` field — CRITICAL, HIGH, MEDIUM or LOW
    outboxes: out
    ---
    # Role: severity_classifier

Two lines, in the file whose behaviour they describe, so that changing
the role and changing its description are the same edit. A separate
catalogue would be a second thing to keep true.

**The front matter never reaches the model.** These files are prompts;
``load_roles_dir`` strips the block before handing the body to
``nl_role``, and a test asserts it. Metadata leaking into a prompt is
the kind of thing that changes behaviour subtly and is never noticed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_FRONT_MATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.S)


def strip_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Return ``(metadata, body)``.

    A deliberately small parser: ``key: value`` lines, one per line,
    no nesting, no lists, no dependency. The moment this needs YAML,
    the front matter has grown past what it is for.
    """
    m = _FRONT_MATTER.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, text[m.end():]


@dataclass(frozen=True)
class RoleInfo:
    name: str
    emits: str
    outboxes: tuple[str, ...]
    kind: str          # "english" (a model runs it) or "python"
    path: Path

    @property
    def costs_money(self) -> bool:
        return self.kind == "english"


def builtin_roles_dir() -> Path:
    return Path(__file__).resolve().parent / "roles"


def _outboxes_from(meta: dict[str, str], body: str) -> tuple[str, ...]:
    """Declared outboxes, preferring what the role's own text says.

    An English role's outboxes are extracted from its prompt by a
    strict ``send to <name>`` rule — the same rule the framework uses,
    so this cannot disagree with what the office will actually wire.
    The front matter is the fallback, for Python roles whose outboxes
    are in code.
    """
    # ``\s+`` and not a literal space: these prompts are wrapped, and
    # "send to\nkeep" is the common case. With a literal space this
    # missed every outbox that fell at the end of a line, and quietly
    # returned a shorter list.
    found = re.findall(r"\bsend\s+to\s+([a-z_][a-z0-9_]*)", body, re.I)
    if found:
        # Sorted, because that is what ``nl_role`` does, and the order
        # decides which outbox is ``out_0``. A catalogue that disagreed
        # with the framework about the order would be worse than no
        # catalogue. ``test_roles_catalogue`` pins the two together.
        return tuple(sorted(set(found)))
    declared = meta.get("outboxes", "")
    return tuple(sorted({p.strip() for p in declared.split(",") if p.strip()}))


def read_role(path: Path) -> RoleInfo | None:
    if path.name.startswith("_") or path.stem == "README":
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if path.suffix == ".py":
        # A Python role keeps its front matter at the top of the module
        # docstring, in the same shape. Find the docstring rather than
        # trimming from the start of the file: these files open with a
        # path comment, and a shebang would be there too.
        _, sep, after = text.partition('"""')
        meta, body = strip_front_matter(after.lstrip("\n")) if sep else ({}, text)
        kind = "python"
    elif path.suffix == ".md":
        meta, body = strip_front_matter(text)
        kind = "english"
    else:
        return None
    return RoleInfo(
        name=path.stem,
        emits=meta.get("emits", ""),
        outboxes=_outboxes_from(meta, body),
        kind=kind,
        path=path,
    )


def catalogue(roles_dir: Path | None = None) -> list[RoleInfo]:
    """Every built-in role, by name."""
    roles_dir = Path(roles_dir or builtin_roles_dir())
    if not roles_dir.is_dir():
        return []
    out = []
    for path in sorted(roles_dir.iterdir()):
        info = read_role(path)
        if info is not None:
            out.append(info)
    return out


def format_catalogue(roles: list[RoleInfo]) -> str:
    """The table `dsl roles` prints."""
    if not roles:
        return "No built-in roles found.\n"
    width = max(len(r.name) for r in roles)
    lines = [
        f"{len(roles)} roles ship with dissyslab. Each reads one message "
        "and adds to it.",
        "",
    ]
    for r in roles:
        emits = r.emits or "(no description — see the role file)"
        lines.append(f"  {r.name:<{width}}  {emits}")
        detail = []
        if r.outboxes and tuple(r.outboxes) != ("out",):
            detail.append("sends to " + " or ".join(r.outboxes))
        if r.kind == "python":
            detail.append("Python, costs nothing to run")
        if detail:
            lines.append(f"  {'':<{width}}  ({'; '.join(detail)})")
    lines += [
        "",
        "Use one by name:  Jay is a summarizer.",
        "`dsl show <name>` prints the whole role. If none of these fit,",
        "describe what you want in a sentence and your assistant will",
        "write the role from your words.",
    ]
    return "\n".join(lines) + "\n"
