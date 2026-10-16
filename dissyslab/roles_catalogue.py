"""``dsl roles``: the built-in roles, and what each one adds or sends.

Read from each role's front matter (spec section 4.4), never by running
it: ``emits:`` for the sentence, ``kind:`` for annotator or author, and
``out:`` for the fields. The fields are the fact a person wiring the
next agent needs -- the key they will read downstream -- and ``emits:``
is prose written by hand, so both are shown.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dissyslab.office.frontmatter import FrontMatterError, read_front_matter


@dataclass(frozen=True)
class RoleInfo:
    """One built-in role, as its front matter describes it."""

    name: str
    language: str  # "english" | "python"
    kind: str  # "annotator" | "author"
    emits: str
    out: tuple[str, ...]


def builtin_roles_dir() -> Path:
    from dissyslab.office.resolve import BUILTIN_ROLES

    return BUILTIN_ROLES


def read_role(path: Path) -> RoleInfo | None:
    """The role in ``path``, or None if it is not a role file."""
    if path.suffix not in (".md", ".py") or path.name.startswith("_"):
        return None
    if path.stem.upper() == "README":
        return None
    try:
        fm = read_front_matter(path)
    except FrontMatterError:
        return None
    if fm.same_as_in:
        out: tuple[str, ...] = ("same as in",)
    else:
        out = tuple(f.name for f in fm.outputs or ())
    return RoleInfo(
        name=path.stem,
        language="english" if path.suffix == ".md" else "python",
        kind=fm.kind,
        emits=fm.emits or "",
        out=out,
    )


def catalogue(roles_dir: Path | None = None) -> list[RoleInfo]:
    """Every built-in role, by name."""
    roles_dir = Path(roles_dir or builtin_roles_dir())
    if not roles_dir.is_dir():
        return []
    roles = (read_role(p) for p in sorted(roles_dir.iterdir()))
    return [r for r in roles if r is not None]


def format_catalogue(roles: list[RoleInfo]) -> str:
    """The table ``dsl roles`` prints."""
    if not roles:
        return "No built-in roles found.\n"
    width = max(len(r.name) for r in roles)
    lines = [f"{len(roles)} roles ship with dissyslab.", ""]
    for r in roles:
        lines.append(f"  {r.name:<{width}}  {r.emits or '(no emits: line)'}")
        verb = "adds" if r.kind == "annotator" else "sends"
        detail = f"{verb} {', '.join(r.out)}" if r.out else f"{r.kind}, declares no out:"
        if r.language == "python":
            detail += "; Python, no model"
        lines.append(f"  {'':<{width}}  ({detail})")
    lines += [
        "",
        "Use one by name in office.md:  Sam: summarizer",
        "`dsl show <name>` prints the whole role. To change one, copy it into",
        "your office's roles/ folder under a new name and edit it there.",
    ]
    return "\n".join(lines) + "\n"
