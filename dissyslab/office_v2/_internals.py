"""
Shared internals — used by both the compiler (Layer 5) and codegen
(Layer 6).

These helpers describe *how* an office tree turns into runtime
decisions:

* ``CompileError`` / ``CompileWarning`` — the error / warning types
  both layers raise.
* ``_BlockTable`` — per-office bookkeeping the connection translator
  needs to know whether a block is a source, sink, leaf agent, or
  sub-office.
* ``_runtime_outport`` / ``_runtime_inport`` — translate user-written
  semantic port names into runtime port names (``out_0`` / ``in_``).
* ``_resolve_subpath`` — turn an inline ``office at <path>`` string
  into a real directory path.
* ``_load_office_library`` — read ``<office>/roles/`` plus the
  framework's built-in ``dissyslab/roles/`` into a ``Library`` mapping.

Why a private module
====================

Compiler and codegen share these primitives word-for-word. Putting
them in one place keeps the two layers honest: a refactor cannot
silently update one and not the other. The leading-underscore module
name signals "don't import this from outside ``office_v2``" — public
API still flows through ``compiler.py`` and the package
``__init__``.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from dissyslab.office_v2.library import load_roles_dir
from dissyslab.office_v2.office_spec_constants import EXTERNAL


# ── "Did you mean?" helper ────────────────────────────────────────────


def _suggest(
    name: str,
    candidates: Iterable[str],
    *,
    cutoff: float = 0.6,
) -> str:
    """Return a 'Did you mean X?' fragment, or '' if no close match.

    Used to soften "unknown source/sink/role/section" errors so a Pat
    typo like ``hackr_news`` produces ``Did you mean 'hacker_news'?``
    next to the bare "unknown" complaint, rather than a wall-of-list
    of every name in the registry.

    The returned fragment has no leading space, no trailing punctuation,
    and is safe to concatenate into a larger message — callers control
    spacing.
    """
    matches = difflib.get_close_matches(
        name, list(candidates), n=1, cutoff=cutoff
    )
    if not matches:
        return ""
    return f"Did you mean {matches[0]!r}?"


# ── Errors and warnings ───────────────────────────────────────────────


class CompileError(Exception):
    """Raised when ``compile_office`` cannot produce a runtime Network.

    Errors are fatal — the compiler aborts. Use ``CompileWarning`` for
    non-fatal observations the caller may want to surface.
    """


@dataclass(frozen=True)
class CompileWarning:
    """A non-fatal issue encountered during compilation.

    Parameters
    ----------
    message
        Human-readable explanation of the issue.
    location
        Optional path or office name where the issue surfaced.
    """

    message: str
    location: str = ""

    def __str__(self) -> str:  # convenient for printing
        if self.location:
            return f"[{self.location}] {self.message}"
        return self.message


# ── Path resolution for sub-offices ───────────────────────────────────


def _resolve_subpath(office_dir: Path, ref_path: str) -> Path:
    """Resolve a sub-office path string against an office directory.

    Two conventions are accepted, in order:

    1. **Relative to the parent office.** ``office_dir / ref_path``
       — the v2 idiom; recommended for new work.
    2. **Absolute or relative to CWD.** v1's gallery wrote sub-office
       paths from the project root (``"gallery/org/news_monitor"``);
       we accept that as a fallback so the gallery keeps working.

    Raises ``CompileError`` if neither resolves to a directory.
    """
    primary = (office_dir / ref_path).resolve()
    if primary.is_dir():
        return primary
    fallback = Path(ref_path).resolve()
    if fallback.is_dir():
        return fallback
    raise CompileError(
        f"sub-office path {ref_path!r} could not be resolved — "
        f"tried {primary} and {fallback}"
    )


# ── Library loading ───────────────────────────────────────────────────


def _builtin_roles_dir() -> Path:
    """Return the framework's built-in role library directory.

    The directory ships inside the installed package at
    ``dissyslab/roles/``. Resolved once per call (cheap) so test
    harnesses can monkeypatch the package layout without us caching
    a stale path.
    """
    # _internals.py lives at dissyslab/office_v2/_internals.py;
    # the built-in role library is two levels up + "roles".
    return Path(__file__).resolve().parent.parent / "roles"


def _load_office_library(office_dir: Path) -> Dict[str, Any]:
    """Load roles for an office from local ``roles/`` then framework.

    Two locations, searched in order:

    1. ``<office_dir>/roles/`` — what Pat writes. The authoritative
       source for this office. Files dropped here override built-ins
       of the same name.
    2. ``dissyslab/roles/`` — the framework's built-in library, used
       as a fallback so any office can reference common roles
       (``severity_classifier``, ``entity_extractor``, ...) without
       copying them. Pat typically builds ``<office>/roles/`` by
       inspecting these files and adapting the ones she wants to
       customise.
    """
    builtin = load_roles_dir(_builtin_roles_dir())
    local = load_roles_dir(office_dir / "roles")
    # Local entries win over framework defaults.
    merged: Dict[str, Any] = dict(builtin)
    merged.update(local)
    return merged


# ── Block-kind table for port translation ─────────────────────────────


@dataclass
class _BlockTable:
    """Compile-time bookkeeping the connection translator needs.

    One table per office (not recursive). Each block's kind tells the
    translator how to convert the user-written source-side port name
    into a runtime port name.

    * ``source`` agents always emit on ``"out_"``; whatever port name
      the user wrote (typically ``"destination"``) maps to ``"out_"``.
    * ``role`` agents (built from ``AgentRoleEntry``) carry an ordered
      tuple of semantic outport names; the i-th name maps to runtime
      ``"out_i"``.
    * ``subnetwork`` agents (sub-offices) declare their own external
      outport names; we pass the user-written name through verbatim
      and let ``Network.check()`` validate it.
    * ``sink`` agents have no outports; appearing as a connection
      source is a hard error.
    """

    sources: Dict[str, None] = field(default_factory=dict)
    sinks: Dict[str, None] = field(default_factory=dict)
    role_agents: Dict[str, Tuple[str, ...]] = field(default_factory=dict)
    subnetworks: Dict[str, Tuple[str, ...]] = field(default_factory=dict)

    def known(self, name: str) -> bool:
        return (
            name in self.sources
            or name in self.sinks
            or name in self.role_agents
            or name in self.subnetworks
        )


# ── Connection-port translation ───────────────────────────────────────


def _runtime_outport(
    block_name: str, semantic_port: str, table: _BlockTable
) -> str:
    """Map the source side of a connection to a runtime port name.

    See ``_BlockTable`` for the four cases. ``EXTERNAL`` passes
    through unchanged (the runtime treats ``"external"`` specially).
    """
    if block_name == EXTERNAL:
        return semantic_port
    if block_name in table.sources:
        # The user-written port name is just the literal word
        # "destination" (v1 convention); the runtime port is "out_".
        return "out_"
    if block_name in table.sinks:
        raise CompileError(
            f"connection has sink {block_name!r} on the sender side; "
            f"sinks have no outports"
        )
    if block_name in table.role_agents:
        ports = table.role_agents[block_name]
        if semantic_port not in ports:
            raise CompileError(
                f"agent {block_name!r} has no outport named "
                f"{semantic_port!r}; declared outports are: "
                f"{list(ports)}"
            )
        # Single-output convention: one declared outport → "out_".
        # Matches Role's runtime port naming and Source/MergeSynch.
        if len(ports) == 1:
            return "out_"
        return f"out_{ports.index(semantic_port)}"
    if block_name in table.subnetworks:
        # Pass through; the sub-office's runtime Network exposes the
        # named external outport directly.
        return semantic_port
    # Unknown block — let Network.check() produce the canonical error.
    return semantic_port


def _runtime_inport(
    block_name: str, semantic_port: str, _table: _BlockTable
) -> str:
    """Destination side passes through unchanged.

    The parser already inserts the implicit inport (``"in_"``) for
    bare destinations, so leaf agents and sinks already have the
    right port name. Sub-offices carry their declared external
    inport name verbatim. ``"external"`` passes through.
    """
    return semantic_port


__all__ = [
    "CompileError",
    "CompileWarning",
    "_BlockTable",
    "_load_office_library",
    "_resolve_subpath",
    "_runtime_inport",
    "_runtime_outport",
]
