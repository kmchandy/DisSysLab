"""How the kind after the colon is found (spec section 3.2).

For each declaration in an office file, this says what its kind refers
to, or why it refers to nothing:

1. ``router``, ``synchronizer``, ``gate``, ``office`` and
   ``unassigned`` are reserved words, built in. They are agents.
2. Any other kind is searched for first in the office's own folder --
   ``roles/`` for an agent, ``sources/`` for a source, ``sinks/`` for a
   sink -- and then among the built-ins.
3. A file whose name starts with ``_`` is a helper module, never a role
   or component, so ``_signal_common`` cannot be a kind.
4. A local file may not reuse a built-in name or a reserved word: that is
   an error, not an override.

Problems are collected, not raised, so ``dsl check`` can report them all
with their lines. Nothing here imports or runs a role or component.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from dissyslab.office.model import Declaration, OfficeFile

#: Kinds built into the language; they are always agents.
RESERVED = ("router", "synchronizer", "gate", "office", "unassigned")

#: The office subfolder searched for each section's kinds.
LOCAL_FOLDER = {"agents": "roles", "sources": "sources", "sinks": "sinks"}

#: The built-in roles (spec 4).
BUILTIN_ROLES = Path(__file__).resolve().parent.parent / "roles"


@dataclass(frozen=True)
class Found:
    """What a declaration's kind refers to.

    ``origin`` is ``"reserved"``, ``"local"`` or ``"builtin"``. ``path`` is
    the file for a role or a local component; None for a reserved word or
    a built-in source or sink (those live in the component registry).
    """

    name: str
    kind: str
    origin: str
    path: Path | None = None

    @property
    def language(self) -> str | None:
        """``"english"`` for a .md role, ``"python"`` for a .py file."""
        if self.path is None:
            return None
        return "english" if self.path.suffix == ".md" else "python"


@dataclass(frozen=True)
class Problem:
    """A declaration whose kind cannot be found, with its line."""

    line: int
    name: str
    message: str


def _files(folder: Path) -> dict[str, list[Path]]:
    """kind -> files in ``folder`` (.md and .py), helper modules left out."""
    found: dict[str, list[Path]] = {}
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.suffix in (".md", ".py") and not path.name.startswith("_"):
                if path.stem.upper() == "README":
                    continue
                found.setdefault(path.stem, []).append(path)
    return found


def _builtin_components(section: str) -> set[str]:
    from dissyslab.office.utils import SINK_REGISTRY, SOURCE_REGISTRY

    return set(SOURCE_REGISTRY if section == "sources" else SINK_REGISTRY)


def _near(word: str, choices: set[str] | list[str]) -> str:
    near = difflib.get_close_matches(word, sorted(choices), n=1)
    return f" Did you mean {near[0]!r}?" if near else ""


def resolve_declaration(decl: Declaration, office_dir: Path) -> Found | Problem:
    """What ``decl.kind`` refers to, or the problem that prevents it."""
    kind, section = decl.kind, decl.section

    def problem(message: str) -> Problem:
        return Problem(decl.line, decl.name, message)

    if kind.startswith("_"):
        return problem(f"{kind!r} names a helper module (a leading _), not a {section[:-1]}.")

    local = _files(office_dir / LOCAL_FOLDER[section])

    if kind in RESERVED:
        if section != "agents":
            return problem(f"{kind!r} is an agent; declare it under agents:, not {section}:.")
        if kind in local:
            return problem(
                f"roles/{local[kind][0].name} reuses the reserved word {kind!r}; rename the file."
            )
        return Found(decl.name, kind, "reserved")

    if section == "agents":
        builtin = _files(BUILTIN_ROLES)
        other: set[str] = set()
    else:
        builtin_names = _builtin_components(section)
        builtin = {k: [] for k in builtin_names}
        opposite = "sinks" if section == "sources" else "sources"
        other = _builtin_components(opposite)

    if kind in local:
        files = local[kind]
        if len(files) > 1:
            return problem(
                f"{LOCAL_FOLDER[section]}/ has both {files[0].name} and {files[1].name}; "
                "keep one."
            )
        if kind in builtin:
            return problem(
                f"{LOCAL_FOLDER[section]}/{files[0].name} reuses the built-in name {kind!r}; "
                "copy it under a new name instead (`dsl grammar roles`)."
            )
        return Found(decl.name, kind, "local", files[0])

    if kind in builtin:
        paths = builtin[kind]
        return Found(decl.name, kind, "builtin", paths[0] if paths else None)

    if kind in other:
        where = "sinks" if section == "sources" else "sources"
        return problem(f"{kind!r} is a {where[:-1]}; declare it under {where}:, not {section}:.")

    known = set(local) | set(builtin) | (set(RESERVED) if section == "agents" else set())
    return problem(
        f"no {section[:-1]} called {kind!r} in {LOCAL_FOLDER[section]}/ or the built-ins."
        f"{_near(kind, known)}"
    )


def resolve_office(office: OfficeFile, office_dir: Path) -> tuple[dict[str, Found], list[Problem]]:
    """Resolve every declaration. Returns (name -> Found, problems)."""
    found: dict[str, Found] = {}
    problems: list[Problem] = []
    for decl in office.declarations:
        result = resolve_declaration(decl, office_dir)
        if isinstance(result, Found):
            found[decl.name] = result
        else:
            problems.append(result)
    return found, problems
