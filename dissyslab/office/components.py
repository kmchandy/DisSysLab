"""Built-in sources and sinks: an entry in the component registry, made an agent.

A declaration like ``bbc_world: rss_normalizer(...)`` or
``jsonl_recorder(path="out.jsonl")`` names a component in
:data:`dissyslab.office.utils.COMPONENT_REGISTRY`. Each entry says how to
make it: import a class (or call a factory function) with the
declaration's arguments. ``build_component`` does that and wraps the
result in the runtime's ``Source`` or ``Sink``.

Kind resolution (:mod:`dissyslab.office.resolve`) has already checked
that the name is a built-in source or sink in the right section, so the
problems left are the ones only construction finds -- chiefly an
argument the component does not take, which is reported with the
arguments it does take.
"""

from __future__ import annotations

import difflib
import importlib
import inspect
import re
from typing import Any, Callable

from dissyslab.office.model import Declaration
from dissyslab.runtime.agent import Agent


class ComponentError(Exception):
    """A built-in source or sink that could not be constructed."""


_UNEXPECTED_KW = re.compile(r"unexpected keyword argument '([^']+)'")


def _accepted(callable_obj: Callable[..., Any]) -> list[str]:
    """The keyword arguments ``callable_obj`` accepts, or [] if unknowable."""
    try:
        sig = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return []
    return [
        p.name for p in sig.parameters.values()
        if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY) and p.name != "self"
    ]


def _construct(make: Callable[..., Any], args: dict[str, Any], what: str) -> Any:
    """``make(**args)``; a bad argument becomes a ComponentError naming the good ones."""
    try:
        return make(**args)
    except TypeError as exc:
        m = _UNEXPECTED_KW.search(str(exc))
        if m is None:
            raise ComponentError(f"{what} could not be built: {exc}") from None
        bad, accepted = m.group(1), _accepted(make)
        near = difflib.get_close_matches(bad, accepted, n=1)
        hint = f" Did you mean {near[0]!r}?" if near else ""
        valid = f" It takes: {', '.join(accepted)}." if accepted else ""
        raise ComponentError(f"{what} takes no argument {bad!r}.{hint}{valid}") from None


def _attribute(module: str, name: str) -> Any:
    return getattr(importlib.import_module(module), name)


def _maker(name: str, entry: dict[str, Any]) -> Callable[..., Any]:
    """What to call to make component ``name``: its class, or its factory."""
    kind = entry.get("type")
    if kind == "rss":
        return _attribute("dissyslab.components.sources.rss_normalizer", name)  # type: ignore[no-any-return]
    if kind == "web_scraper_factory":
        return _attribute("dissyslab.components.sources.web_scraper", name)  # type: ignore[no-any-return]
    # "from dissyslab.x.y import Cls" -> import dissyslab.x.y, take Cls
    module = entry["import"].split()[1]
    return _attribute(module, entry["class"])  # type: ignore[no-any-return]


def build_component(decl: Declaration) -> Agent:
    """The runtime agent for a built-in source or sink declaration."""
    from dissyslab.blocks import Sink, Source
    from dissyslab.office.utils import expand_shortcut, lookup_component

    entry = lookup_component(decl.kind)
    if entry is None:  # resolve has already reported it; a direct caller gets this
        raise ComponentError(f"there is no built-in component called {decl.kind!r}.")
    args = dict(decl.args)
    what = f"{decl.section[:-1]} {decl.kind!r}"

    if decl.section == "sources":
        # A property of the source agent, not an argument of the class: a
        # source for which producing nothing is a legitimate outcome.
        allow_empty = bool(args.pop("allow_empty", False))
        if entry.get("type") == "mcp_shortcut":
            args = expand_shortcut(decl.kind, args)
        obj = _construct(_maker(decl.kind, entry), args, what)
        source: Agent = Source(fn=obj.run, name=decl.name, allow_empty=allow_empty)
        return source

    obj = _construct(_maker(decl.kind, entry), args, what)
    sink: Agent = Sink(fn=getattr(obj, entry["call"]), name=decl.name)
    return sink
