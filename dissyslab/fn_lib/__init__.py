"""
Function library — pre-built Python transformers an office can name.

Where ``dissyslab/roles/`` ships LLM-driven roles (markdown prompts) and
custom Python roles (``.py`` files exporting an ``AgentRoleEntry``),
``dissyslab/fn_lib/`` ships *plain Python functions* with first-class
state, wrapped automatically by the compiler as ``Transform`` blocks.

The deduplicator is the first entry. Pat writes::

    Sasha is a deduplicator(by="url").

and the compiler:

1. Looks up ``deduplicator`` in this registry.
2. Partitions Pat's kwargs by signature: ``by`` is consumed by
   ``fn`` (per message), not by ``initial_state`` (deduplicator's
   memory does not depend on the chosen field). So
   ``initial_state()`` is called bare and ``by`` flows into
   ``params``.
3. Builds ``Transform(fn=entry.fn, params={"by": "url"},
   state={"seen": set()}, name="Sasha")``.

Pat never writes the ``Transform(...)`` line — the registry is the
seam between her plain-English office and the framework's runtime.

Authoring an entry
==================

A function-library entry has three pieces:

* ``fn(msg, state, **params) -> Optional[Any]`` — the per-message
  logic. Mutates ``state`` in place. Returns the output message, or
  ``None`` to drop.
* ``initial_state(**params) -> dict`` — builds a fresh mutable state
  dict from the kwargs Pat passed in office.md.
* A short description for diagnostics.

Wrap them in an ``FnEntry`` and register under a name in ``FN_LIB``.

Lookup order at compile time (later entries lose on conflict):

1. ``<office>/roles/`` — Pat's local roles (``.md`` or ``.py``).
2. ``dissyslab/roles/`` — framework-shipped roles.
3. ``dissyslab/fn_lib/`` — this registry.

So an office can override a built-in deduplicator by dropping its own
``deduplicator.py`` into its ``roles/`` folder.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Set, Tuple


@dataclass(frozen=True)
class FnEntry:
    """A reusable Python transformer — function, state factory, name.

    Parameters
    ----------
    name
        The entry's identifier in ``FN_LIB`` (e.g. ``"deduplicator"``).
        The dict key is authoritative; this field is for diagnostics.
    fn
        Per-message callable. Signature::

            fn(msg, state, **params) -> Optional[Any]

        Mutates ``state`` in place. Returns the output message or
        ``None`` to drop. The compiler always calls ``fn`` with the
        ``state=`` keyword and unpacked ``**params``.
    initial_state
        Zero- or kwarg-only callable that returns a fresh mutable
        state dict. Called once per agent at construction time with
        only the kwargs whose names appear in its signature — the
        framework filters Pat's kwargs through ``inspect.signature``
        so unused names do not need to be repeated here.
    description
        Free-text description. Optional.
    """

    name: str
    fn: Callable[..., Optional[Any]]
    initial_state: Callable[..., Dict[str, Any]]
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                f"FnEntry.name must be a non-empty string, got {self.name!r}"
            )
        if not callable(self.fn):
            raise TypeError(
                f"FnEntry {self.name!r} fn must be callable, "
                f"got {type(self.fn).__name__}"
            )
        if not callable(self.initial_state):
            raise TypeError(
                f"FnEntry {self.name!r} initial_state must be callable, "
                f"got {type(self.initial_state).__name__}"
            )


# A function library is any mapping from name to FnEntry.
FnLibrary = Mapping[str, FnEntry]


# ── Kwarg partitioning ────────────────────────────────────────────────


def _accepted_kwargs(
    fn: Callable, exclude: Optional[Set[str]] = None
) -> Tuple[Set[str], bool]:
    """Inspect a callable's signature.

    Returns ``(named_kwargs, has_var_keyword)``:

    * ``named_kwargs`` — the set of explicit kwarg names ``fn``
      declares (after removing any names in ``exclude``).
    * ``has_var_keyword`` — True iff ``fn`` has a ``**kwargs``
      catch-all and therefore accepts any kwarg by name.
    """
    exclude = exclude or set()
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        # Builtins / C-funcs without introspectable sigs: be permissive.
        return set(), True

    named: Set[str] = set()
    has_var_kw = False
    for p in sig.parameters.values():
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            has_var_kw = True
        elif p.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            if p.name not in exclude:
                named.add(p.name)
    return named, has_var_kw


def partition_kwargs(
    entry: FnEntry, kwargs: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any], Set[str]]:
    """Split user-provided kwargs across an entry's two callables.

    Pat writes ``(by="url", window=1000)`` in office.md. Some of those
    kwargs are consumed by ``initial_state`` (used once at construction
    to seed mutable state); others are consumed by ``fn`` (passed on
    every call). The framework partitions them by introspecting each
    callable's signature, so:

    * ``initial_state`` receives only what its signature names.
    * ``fn`` receives only what its signature names (excluding the
      framework-managed ``msg`` and ``state`` parameters).
    * Anything Pat wrote that neither callable declares is reported
      to the caller as an *unknown* kwarg — typically a typo. Callers
      should raise a ``CompileError`` with a helpful message rather
      than silently dropping it.

    Callables that declare ``**kwargs`` accept any name; in that case
    everything Pat wrote flows in.

    Returns ``(init_kwargs, fn_kwargs, unknown)``.
    """
    init_named, init_has_var = _accepted_kwargs(entry.initial_state)
    fn_named, fn_has_var = _accepted_kwargs(
        entry.fn, exclude={"msg", "state"}
    )

    init_kwargs: Dict[str, Any] = {}
    fn_kwargs: Dict[str, Any] = {}
    unknown: Set[str] = set()

    for name, value in kwargs.items():
        accepted = False
        if init_has_var or name in init_named:
            init_kwargs[name] = value
            accepted = True
        if fn_has_var or name in fn_named:
            fn_kwargs[name] = value
            accepted = True
        if not accepted:
            unknown.add(name)

    return init_kwargs, fn_kwargs, unknown


# ── Registry assembly ─────────────────────────────────────────────────


from dissyslab.fn_lib.dedup import deduplicator_entry  # noqa: E402


FN_LIB: Dict[str, FnEntry] = {
    deduplicator_entry.name: deduplicator_entry,
}


__all__ = ["FN_LIB", "FnEntry", "FnLibrary", "partition_kwargs"]
