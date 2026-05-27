"""
Role library — the v2 way of describing the building blocks an office
wires together.

A *role* is a reusable, named building block. There are two kinds:

* **Agent role** — a callable + port shape. ``analyst``, ``rss``, and
  ``console_printer`` are agent roles. The implementation can be a
  natural-language prompt (`nl_role`), a built-in source/sink class,
  or any user-supplied factory.

* **Office role** — a path to another ``office.md`` (open or closed).
  When the compiler reaches an ``OfficeRoleEntry`` it recursively
  parses the referenced office and inlines the resulting child
  ``dissyslab.network.Network`` as a nested block.

Both kinds live in the same library, keyed by name. A library is
``Mapping[str, RoleEntry]`` — a plain ``dict`` works, and so does any
other Mapping. ``RoleEntry = AgentRoleEntry | OfficeRoleEntry``.

Two ways to build a library
===========================

Pedagogical (Path A) — drop one ``*.md`` per role into ``roles/``::

    my_office/
      office.md
      roles/
        analyst.md       # the prompt; "send to <name>" defines outports
        editor.md

Then ``load_roles_dir("my_office/roles")`` returns ``{"analyst":
AgentRoleEntry(...), "editor": AgentRoleEntry(...)}``. The compiler
also reads the framework's built-in ``dissyslab/roles/`` as a
fallback, so an office only needs a ``roles/`` file for roles it
defines or overrides.

Programmatic (Path B) — build a dict in Python::

    from dissyslab.office.library import nl_role, OfficeRoleEntry

    my_roles = {
        "analyst":      nl_role(prompt=ANALYST_PROMPT),
        "news_monitor": OfficeRoleEntry(name="news_monitor",
                                        path="../news_monitor"),
    }

The compiler (Layer 5) accepts either form interchangeably.

Lazy backend resolution
=======================

``nl_role`` does NOT contact the language-model backend at construction
time; it captures the desired backend name and resolves it the first
time the entry's factory is called. That means:

* Building a role library never requires an API key.
* Tests can register a stub backend right before they instantiate the
  agent.
* Importing a Python module that defines a role at top level is safe
  even in CI without LLM credentials.
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Tuple, Union

from dissyslab.backends import get_backend
from dissyslab.blocks.role import Role
from dissyslab.core import Agent


# ── Port extraction from a natural-language prompt ─────────────────────


# A line containing the phrase "send to" is a port-naming line.
_SEND_TO_LINE_RE = re.compile(r"\bsend\s+to\b", re.IGNORECASE)
# Inside such a line, every "to <identifier>" yields a port name.
_TO_NAME_RE = re.compile(r"\bto\s+([A-Za-z_][A-Za-z0-9_]*)\b")


def _extract_send_to_ports(text: str) -> Tuple[str, ...]:
    """Extract output port names from a prompt body.

    Strict pattern: a line that contains the phrase ``send to`` is a
    port-naming line. Within such a line, every ``to <identifier>``
    contributes a port name. Examples of accepted phrasings::

        Always send to briefing.            -> ("briefing",)
        Send to keep or to discard.         -> ("keep", "discard")
        If X, send to summary.              -> ("summary",)

    Duplicates are removed but order of first appearance is preserved
    — the compiler maps the i-th declared port to the runtime name
    ``out_i``, so order matters.
    """
    seen: list[str] = []
    seen_set: set[str] = set()
    for raw in text.splitlines():
        if not _SEND_TO_LINE_RE.search(raw):
            continue
        for m in _TO_NAME_RE.finditer(raw):
            name = m.group(1)
            if name in seen_set:
                continue
            seen_set.add(name)
            seen.append(name)
    return tuple(seen)


# ── Type aliases ──────────────────────────────────────────────────────


# Aliases mapping human-readable AI names to backend registry keys.
# ``DSL_BACKEND`` and ``register_backend`` use lower-case keys; this
# alias table lets students write ``AI="Claude"`` without learning the
# registry's vocabulary.
_AI_ALIASES: Dict[str, str] = {
    "claude": "anthropic",
}


# Default model name used by ``nl_role`` when the caller does not
# specify one. Centralised here so swapping the default is a one-line
# change.
DEFAULT_AI: str = "Claude"


# ── AgentRoleEntry ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class AgentRoleEntry:
    """A reusable agent role — name, port shape, and a zero-arg factory.

    An ``AgentRoleEntry`` is callable: ``entry()`` produces an
    *unnamed* runtime ``dissyslab.core.Agent``. Network construction
    later assigns the agent's name from the dict key it occupies in
    ``Network.blocks``.

    Parameters
    ----------
    name
        The role's identifier (e.g. ``"analyst"``). May be the empty
        string when the entry is built outside a library context;
        ``load_roles_dir`` fills it in from the source filename. The
        name is for diagnostics — the library's dict key is the
        authoritative identifier.
    in_ports
        Ordered names of input ports. ``("in_",)`` for prompt-driven
        roles built by ``nl_role``.
    out_ports
        Ordered names of output ports. The order is meaningful: the
        runtime maps ``out_ports[i]`` to the runtime name ``out_i``,
        which the compiler uses when emitting connection 4-tuples.
    factory
        Zero-arg callable that returns a runtime ``Agent``. The
        compiler / generated code calls this to materialise the agent
        for one office. Calling the entry directly (``entry()``) is a
        shortcut for ``entry.factory()``.
    description
        Free-text description; surfaced in error messages and used by
        ``dsl new`` / ``dsl edit`` UX. Optional.

    Examples
    --------
    Build an LLM-driven role from a prompt:

    >>> entry = nl_role(prompt="You triage emails. Send to keep "
    ...                        "or to discard.")
    >>> entry.in_ports
    ('in_',)
    >>> entry.out_ports
    ('keep', 'discard')

    Build a runtime ``Agent`` (requires the backend to be available):

    >>> agent = entry()                          # doctest: +SKIP
    >>> isinstance(agent, Agent)                 # doctest: +SKIP
    True
    """

    name: str
    in_ports: Tuple[str, ...]
    out_ports: Tuple[str, ...]
    factory: Callable[[], Agent]
    description: str = ""

    def __post_init__(self) -> None:
        # Coerce iterables to tuples so callers may pass lists.
        object.__setattr__(self, "in_ports", tuple(self.in_ports))
        object.__setattr__(self, "out_ports", tuple(self.out_ports))

        if not isinstance(self.name, str):
            raise TypeError(
                f"AgentRoleEntry.name must be a string, "
                f"got {type(self.name).__name__}"
            )

        for kind, ports in (("in_ports", self.in_ports),
                            ("out_ports", self.out_ports)):
            for p in ports:
                if not isinstance(p, str) or not p:
                    raise ValueError(
                        f"AgentRoleEntry {self.name!r} {kind} must "
                        f"contain non-empty strings, got {p!r}"
                    )
            if len(set(ports)) != len(ports):
                raise ValueError(
                    f"AgentRoleEntry {self.name!r} has duplicate "
                    f"{kind}: {list(ports)}"
                )

        if not self.in_ports and not self.out_ports:
            raise ValueError(
                f"AgentRoleEntry {self.name!r} has no ports at all; "
                f"a role must have at least one inport or outport"
            )

        if not callable(self.factory):
            raise TypeError(
                f"AgentRoleEntry {self.name!r} factory must be "
                f"callable, got {type(self.factory).__name__}"
            )

    def __call__(self) -> Agent:
        """Build a fresh runtime ``Agent`` for this role."""
        return self.factory()


# ── OfficeRoleEntry ────────────────────────────────────────────────────


@dataclass(frozen=True)
class OfficeRoleEntry:
    """A reference to a sub-office on disk — the compiler recurses on it.

    Unlike ``AgentRoleEntry``, this entry is *not* callable. The
    compiler (Layer 5) sees the entry, parses the referenced
    ``office.md`` recursively, and inlines the resulting runtime
    ``Network`` as a nested block. Recursion happens at compile time,
    not at library-build time, so the office library can mention
    sub-offices without eagerly loading them.

    Parameters
    ----------
    name
        The sub-office's identifier in the library.
    path
        Filesystem path to the sub-office directory (the directory
        containing its ``office.md``). Relative paths are resolved
        against the loading office's directory at compile time.
    description
        Free-text description; optional.
    """

    name: str
    path: str
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError(
                f"OfficeRoleEntry.name must be a string, "
                f"got {type(self.name).__name__}"
            )
        if not isinstance(self.path, str) or not self.path:
            raise ValueError(
                f"OfficeRoleEntry {self.name!r} has empty path"
            )


# A role library entry is one of the two record types.
RoleEntry = Union[AgentRoleEntry, OfficeRoleEntry]


# A library is any mapping from role-name to entry. ``dict`` is the
# common case; ``Mapping`` lets callers pass ``ChainMap`` or a custom
# proxy if they want overlay semantics.
Library = Mapping[str, RoleEntry]


# ── nl_role ────────────────────────────────────────────────────────────


# JSON contract appended to every prompt-driven role. The role's
# returned JSON tells the runtime which outport each message goes to.
# The contract is filled in with the role's actual outports so the
# model knows the legal values.
_NL_CONTRACT = (
    "\n\nReturn JSON only, no explanation, no nested JSON:\n"
    '{{"send_to": "<one of: {options}>", "text": "<content>"}}'
)


def _resolve_ai(ai: str) -> str:
    """Map a human-readable AI name to a backend-registry key."""
    if not isinstance(ai, str) or not ai:
        raise ValueError(
            f"nl_role(AI=...) must be a non-empty string, got {ai!r}"
        )
    key = ai.strip().lower()
    return _AI_ALIASES.get(key, key)


def _strip_code_fences(text: str) -> str:
    """Remove leading ``` fences (and language tag) from model output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    return text


def _nl_role_runtime_context_suffix() -> str:
    """Append prefetched tables from ``office_run_context`` env keys (when set).

    Populated by :func:`~dissyslab.office.office_run_context.apply_office_run_context_to_environ`
    (``dsl run``) inside the subprocess.
    """
    parts: list[str] = []
    d = os.environ.get("OFFICE_WEATHERAPI_DIGEST", "").strip()
    if d:
        parts.append("## Shared NOAA / prefetched forecast\n\n" + d)
    w = os.environ.get("OFFICE_WARDROBE_INVENTORY_DIGEST", "").strip()
    if w:
        parts.append("## Wardrobe inventory (canonical JSON snapshot)\n\n" + w)
    o = os.environ.get("OFFICE_OPEN_METEO_CITIES_DIGEST", "").strip()
    if o:
        parts.append("## Multi-city current weather (Open-Meteo snapshot)\n\n" + o)
    if not parts:
        return ""
    return "\n\n---\n\n" + "\n\n---\n\n".join(parts)


def nl_role(
    prompt: str,
    AI: Optional[str] = None,
) -> AgentRoleEntry:
    """Build an ``AgentRoleEntry`` from a natural-language prompt.

    The output ports are extracted from the prompt by the same
    ``send to <name>`` rule the parser already uses (strict — no LLM
    fall-back). The JSON-output contract that tells the model how to
    name the chosen outport is appended automatically; students never
    write it by hand.

    Parameters
    ----------
    prompt
        The role's natural-language description. Must contain at
        least one ``send to <name>`` phrase so the framework knows
        which destination ports the role can pick from.
    AI
        Human-readable name of the language-model backend to use for
        this role. When ``None`` (the default) the role uses whichever
        backend is active at run time — ``DSL_BACKEND`` env var if
        set, otherwise the registered default (``anthropic``). When
        given explicitly (``AI="ollama"``, ``AI="Claude"``, ...) the
        role is locked to that backend regardless of ``DSL_BACKEND``.

        This means: leave ``AI`` unset for roles that should follow
        the office-wide setting (the common case), and pass an
        explicit name only when you want one role to use a different
        backend than the rest of the office. Office-md role files
        loaded via ``load_roles_dir`` always leave ``AI`` unset, so
        the entire office honors ``DSL_BACKEND``.

    Returns
    -------
    AgentRoleEntry
        With ``name=""`` (the loader fills it in), ``in_ports=("in_",)``,
        ``out_ports`` extracted from the prompt, and a ``factory`` that
        builds a ``dissyslab.blocks.role.Role`` agent on demand.

    Raises
    ------
    ValueError
        If the prompt has no ``send to <name>`` phrase.

    Examples
    --------
    >>> entry = nl_role("You triage emails. Send to keep or to discard.")
    >>> entry.out_ports
    ('keep', 'discard')
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("nl_role prompt must be a non-empty string")

    out_ports = _extract_send_to_ports(prompt)
    if not out_ports:
        raise ValueError(
            "nl_role prompt declares no output ports — the framework "
            "extracts ports by scanning for the phrase 'send to <name>' "
            "in the prompt body. Add at least one line such as 'Send to "
            "<port>.' so the role's destinations are explicit."
        )

    # When AI is None, leave backend_name unset so the factory honors
    # DSL_BACKEND at run time. When AI is given, lock that backend in
    # for this role.
    backend_name: Optional[str] = _resolve_ai(AI) if AI else None
    options = ", ".join(out_ports)
    full_prompt = prompt.strip() + _NL_CONTRACT.format(options=options)
    default_dest = out_ports[0]

    # Closures captured by the factory. We deliberately resolve the
    # backend lazily (inside the factory) so that constructing a role
    # library does not require API credentials.
    def factory() -> Agent:
        backend = get_backend(backend_name)

        def call_llm(text: str) -> Any:
            """Send ``text`` to the model; return parsed JSON if possible."""
            if not text or not text.strip():
                return {}
            raw = backend.complete(
                system=full_prompt + _nl_role_runtime_context_suffix(),
                user=text,
                # 2048 is plenty for role outputs (typically 200–500
                # tokens of JSON). The previous default was 8192, sized
                # for *reasoning-enabled* SLMs like Qwen3.5-A3B that
                # spend a substantial fraction of their budget on
                # internal chain-of-thought before emitting JSON. The
                # current default model (Qwen-2.5-7B-Instruct) is a
                # plain instruct model — no reasoning — so 8192 was
                # both wasted budget and triggered provider-side
                # validation failures on some OpenRouter providers
                # (e.g. AtlasCloud returned HTTP 400). 2048 keeps
                # headroom while staying inside every provider's cap.
                #
                # If you point OPENROUTER_MODEL at a reasoning model
                # and start seeing empty completions, bump this here
                # or override per-call via ``backend.complete(..., max_tokens=8192)``.
                max_tokens=2048,
                temperature=1.0,
            )
            cleaned = _strip_code_fences(raw)
            if not cleaned:
                return {}
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return cleaned

        def role_fn(msg: Any):
            """Run the LLM and translate its reply into (msg, status) pairs.

            * If the LLM returns a dict, ``send_to`` selects the
              outport (``default_dest`` if absent).
            * If the LLM returns plain text, route it to the default
              outport — covers prompts that do not use the JSON
              contract (e.g., a single-status reporter role).
            * On exception, log and drop the message (return ``[]``).
            """
            text = json.dumps(msg) if isinstance(msg, dict) else str(msg)
            try:
                result = call_llm(text)
                if not isinstance(result, dict):
                    return [(result, default_dest)]
                # Merge the original dict with the model's reply when
                # both are dicts — this preserves upstream metadata.
                out_msg = {**msg, **result} if isinstance(msg, dict) else result
                destination = result.get("send_to", default_dest)
                if isinstance(destination, list):
                    return [(out_msg, dest) for dest in destination]
                return [(out_msg, destination)]
            except Exception as exc:
                print(f"[nl_role] error in role_fn: {exc}")
                return []

        return Role(fn=role_fn, statuses=list(out_ports))

    return AgentRoleEntry(
        name="",
        in_ports=("in_",),
        out_ports=out_ports,
        factory=factory,
    )


# ── specialist_role ─────────────────────────────────────────────────────


def specialist_role(
    transform: Callable[[str], Dict[str, Any]],
    *,
    input_field: str = "text",
    out_port: str = "out_",
) -> AgentRoleEntry:
    """Build an ``AgentRoleEntry`` that wraps a deterministic text → dict
    transform.

    Sibling of :func:`nl_role`. Where ``nl_role`` wraps an LLM behind a
    natural-language prompt, ``specialist_role`` wraps any pre-trained
    pipeline (HuggingFace classifier, spaCy NER, a hand-written
    keyword classifier, etc.) behind a Python function that maps text
    to an annotation dict.

    The framework wires this role exactly like an ``nl_role``:
    incoming message → role function → outgoing (message, status)
    pairs. The annotation dict is shallow-merged into the upstream
    message so downstream agents see both the original fields and the
    new annotation.

    Parameters
    ----------
    transform
        Callable taking the article's text (a string) and returning a
        flat dict of new fields to attach. Example::

            def entity_transform(text: str) -> dict:
                nlp = _load_spacy()
                doc = nlp(text)
                return {"entities": sorted({ent.text for ent in doc.ents})}

        The transform is called once per incoming message. It should
        be deterministic; the framework will not cache results across
        runs. If the transform raises, the message is dropped (matches
        ``nl_role`` behavior).
    input_field
        Key of the upstream message whose value is passed to
        ``transform``. Defaults to ``"text"``, matching the corpus
        format. If the upstream message is not a dict, the entire
        message is stringified and passed in.
    out_port
        Name of the single outport this role emits on. Defaults to
        ``"out_"`` matching framework convention for single-status
        roles.

    Returns
    -------
    AgentRoleEntry
        With ``name=""`` (the loader fills it in), ``in_ports=("in_",)``,
        ``out_ports=(out_port,)``, and a ``factory`` that builds a
        :class:`dissyslab.blocks.role.Role` agent on demand.

    Examples
    --------
    A spaCy-backed entity extractor::

        _nlp = None
        def _load():
            global _nlp
            if _nlp is None:
                import spacy
                _nlp = spacy.load("en_core_web_trf")
            return _nlp

        def transform(text):
            doc = _load()(text)
            return {"entities": sorted({e.text for e in doc.ents
                                        if e.label_ in {"PERSON","ORG","GPE","LOC"}})}

        role = specialist_role(transform)

    Drop this file at ``my_office/roles/entity_extractor.py`` and the
    office's `entity_extractor` role is now backed by spaCy rather
    than an LLM. No office.md changes needed.
    """
    if not callable(transform):
        raise TypeError(
            f"specialist_role(transform=...) must be callable, "
            f"got {type(transform).__name__}"
        )

    def factory() -> Agent:
        def role_fn(msg: Any):
            """Run ``transform`` on the message and route the merged result.

            * If the upstream message is a dict, ``transform`` receives
              ``msg[input_field]`` (defaults to ``msg["text"]``); the
              returned dict is shallow-merged with ``msg`` so downstream
              agents see both original fields and the new annotation.
            * If the upstream message is not a dict, ``transform``
              receives ``str(msg)`` and its return value goes downstream
              unmerged.
            * On exception, log and drop the message (return ``[]``),
              matching ``nl_role`` behavior.
            """
            if isinstance(msg, dict):
                text = str(msg.get(input_field, ""))
            else:
                text = str(msg) if msg is not None else ""
            if not text.strip():
                return [(msg, out_port)]
            try:
                annotation = transform(text)
            except Exception as exc:
                print(f"[specialist_role] error in transform: {exc}")
                return []
            if not isinstance(annotation, dict):
                # A non-dict return is treated as the whole downstream
                # payload, same as the nl_role plain-text case.
                return [(annotation, out_port)]
            out_msg = {**msg, **annotation} if isinstance(msg, dict) else annotation
            return [(out_msg, out_port)]

        return Role(fn=role_fn, statuses=[out_port])

    return AgentRoleEntry(
        name="",
        in_ports=("in_",),
        out_ports=(out_port,),
        factory=factory,
    )


# ── synchronizer_role ─────────────────────────────────────────────────


def synchronizer_role(inports: "list[str] | tuple[str, ...]") -> AgentRoleEntry:
    """Build a synchronizer role with the given named inports.

    A *synchronizer* is the framework's canonical fan-in primitive: it
    waits until it has received exactly one message on each of its
    named inports, dict-merges the messages into a single combined
    message, and emits the combined message on ``out``.

    The pattern shows up in every gallery office that forks an
    article into parallel annotators and then needs to merge the
    annotated copies back into one. Before this helper, each office
    shipped its own near-identical 25-line ``synchronizer.py``. Now
    each office's ``synchronizer.py`` is two lines::

        from dissyslab.office import synchronizer_role
        role = synchronizer_role(["entities", "severity", "topic", "location"])

    Parameters
    ----------
    inports
        Named inports the synchronizer will wait on. Must be a
        non-empty sequence of unique strings. The names show up in
        ``office.md`` connections as ``X's out is Sync's <name>``.

    Returns
    -------
    AgentRoleEntry
        With ``name="synchronizer"``, ``in_ports`` set to the names
        you passed, ``out_ports=("out",)``, and a factory that builds
        the Agent on demand.

    Raises
    ------
    ValueError
        If ``inports`` is empty or contains duplicates.

    Examples
    --------
    >>> entry = synchronizer_role(["a", "b"])
    >>> entry.in_ports
    ('a', 'b')
    >>> entry.out_ports
    ('out',)

    Notes
    -----
    The dict-merge step is order-independent only when each upstream
    branch preserves the original message fields and adds its own.
    That's the situation_room pattern (each parallel extractor adds
    one new field and passes the rest through). If your upstream
    branches produce overlapping keys with different values, the last
    one wins — caller's responsibility to design around that.
    """
    if not inports:
        raise ValueError("synchronizer_role requires at least one inport")
    inports_tuple = tuple(inports)
    if len(set(inports_tuple)) != len(inports_tuple):
        raise ValueError(
            f"synchronizer_role inports must be unique, got {list(inports_tuple)}"
        )
    if not all(isinstance(p, str) and p for p in inports_tuple):
        raise ValueError(
            f"synchronizer_role inports must all be non-empty strings, "
            f"got {list(inports_tuple)}"
        )

    class _Synchronizer(Agent):
        """Wait for one msg per named inport; dict-merge; emit on out_."""

        def __init__(self, name=None):
            super().__init__(
                name=name,
                inports=list(inports_tuple),
                outports=["out_"],
            )

        def run(self) -> None:
            while True:
                merged: dict = {}
                for p in self.inports:
                    msg = self.recv(p)
                    if isinstance(msg, dict):
                        merged.update(msg)
                self.send(merged, "out_")

    return AgentRoleEntry(
        name="synchronizer",
        in_ports=inports_tuple,
        out_ports=("out",),
        factory=_Synchronizer,
        description=(
            f"Wait for one message on each of {list(inports_tuple)}, "
            f"dict-merge, emit on 'out'."
        ),
    )


# ── PARAMETERIZED_LIBRARY ─────────────────────────────────────────────


# Roles that are constructed *with arguments* from the office.md call
# site, rather than registered as static AgentRoleEntry values in the
# library. The compiler looks here AFTER checking the (static) library
# and BEFORE the fn_lib lookup. The kwargs Pat writes in
# ``Sync is a synchronizer(inports=[...])`` are passed straight to the
# registered constructor, which returns a fresh ``AgentRoleEntry``.
#
# Why this exists separately from the static library: some library
# roles (like `synchronizer`) have port shapes that depend on the
# specific office's wiring. Forcing every office to ship a per-office
# Python file just to declare port names would break the "plain
# English" promise. Parameterized library roles close that gap —
# office.md kwargs become the parameterization vector, the framework
# owns the implementation.
#
# Override precedence (high to low):
#   1. Office's own ``roles/X.md`` or ``roles/X.py``  (load_roles_dir)
#   2. Framework's ``dissyslab/roles/X.md``           (load_roles_dir)
#   3. PARAMETERIZED_LIBRARY[X]                        (this dict)
#   4. ``dissyslab.fn_lib`` entry for X
#
# So a Pat who wants different synchronizer behaviour can still drop
# a local ``roles/synchronizer.py`` and the framework will prefer it.
PARAMETERIZED_LIBRARY: Dict[str, Callable[..., "AgentRoleEntry"]] = {
    "synchronizer": synchronizer_role,
}


# ── load_roles_dir ─────────────────────────────────────────────────────


def _import_role_module(py_path: Path):
    """Import ``py_path`` as a fresh module and return it.

    The module is loaded under a synthetic name (``office_role_<stem>``)
    so role files in different offices do not collide in
    ``sys.modules``.
    """
    spec = importlib.util.spec_from_file_location(
        f"office_role_{py_path.stem}", py_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load role module {py_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_INCLUDE_RE = re.compile(r"\{\{\s*include:\s*([^\s}]+)\s*\}\}")


def _resolve_includes(text: str, search_dirs: List[Path]) -> str:
    """Substitute ``{{include: filename}}`` directives with file contents.

    Designed for role markdown files that want to bake another file
    into their prompt (e.g. a matcher role embedding ``resume.md``).
    Each directive is replaced inline; ``search_dirs`` is consulted
    in order and the first hit wins. Missing files raise
    ``FileNotFoundError`` so the failure is loud at office-load time
    rather than silently producing a malformed prompt.

    Includes are *one level deep* — included content is not itself
    scanned for further ``{{include:}}`` directives. This keeps the
    feature simple and prevents accidental recursion.
    """

    def repl(match):
        fname = match.group(1)
        for d in search_dirs:
            candidate = d / fname
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        searched = ", ".join(str(d) for d in search_dirs)
        raise FileNotFoundError(
            f"include not found: {fname!r} (searched: {searched})"
        )

    return _INCLUDE_RE.sub(repl, text)


def load_roles_dir(roles_dir: Union[str, Path]) -> Dict[str, RoleEntry]:
    """Load every ``*.md`` and ``*.py`` role file in a directory.

    Discovery rules
    ---------------

    * **``*.md``** — the file's contents are passed verbatim to
      ``nl_role``, with one substitution step first: any
      ``{{include: filename}}`` directive is replaced by the
      contents of ``filename`` (resolved against the office
      directory, then the roles directory). The resulting entry
      is registered under the filename stem (``analyst.md`` →
      ``"analyst"``).
    * **``*.py``** — the module's top-level ``role`` attribute is
      taken as a ``RoleEntry`` and registered under the filename stem.
      Files whose name starts with ``_`` (e.g. ``__init__.py``) are
      skipped.

    A missing directory returns an empty mapping rather than raising
    — callers compose libraries from multiple directories and a
    missing one is a normal "no roles here" outcome.

    Parameters
    ----------
    roles_dir
        Path to the directory to scan.

    Returns
    -------
    dict[str, RoleEntry]
        Mapping from role name (filename stem) to the constructed
        ``AgentRoleEntry`` or ``OfficeRoleEntry``. The dict is fresh
        — callers may mutate it freely.

    Raises
    ------
    ValueError, TypeError
        If a ``.py`` file lacks a ``role`` attribute or its ``role``
        attribute is not a ``RoleEntry``.
    ValueError
        If two role files in the same directory share the same stem
        (e.g. both ``analyst.md`` and ``analyst.py``).
    """
    path = Path(roles_dir)
    out: Dict[str, RoleEntry] = {}
    if not path.is_dir():
        return out

    for md_path in sorted(path.glob("*.md")):
        if md_path.name.startswith("_"):
            continue
        # README.md is conventional documentation, not a role.
        if md_path.stem.lower() == "readme":
            continue
        text = md_path.read_text(encoding="utf-8")
        # Office dir (e.g. for resume.md), then the roles dir itself.
        text = _resolve_includes(text, [path.parent, path])
        entry = nl_role(text)
        entry = dataclasses.replace(entry, name=md_path.stem)
        if md_path.stem in out:
            raise ValueError(
                f"duplicate role {md_path.stem!r} in {path}"
            )
        out[md_path.stem] = entry

    for py_path in sorted(path.glob("*.py")):
        if py_path.name.startswith("_"):
            continue
        module = _import_role_module(py_path)
        if not hasattr(module, "role"):
            raise ValueError(
                f"{py_path}: module has no top-level 'role' attribute"
            )
        entry = module.role
        if not isinstance(entry, (AgentRoleEntry, OfficeRoleEntry)):
            raise TypeError(
                f"{py_path}: 'role' must be an AgentRoleEntry or "
                f"OfficeRoleEntry, got {type(entry).__name__}"
            )
        if not entry.name:
            entry = dataclasses.replace(entry, name=py_path.stem)
        if py_path.stem in out:
            raise ValueError(
                f"duplicate role {py_path.stem!r} in {path}"
            )
        out[py_path.stem] = entry

    return out


__all__ = [
    "AgentRoleEntry",
    "OfficeRoleEntry",
    "RoleEntry",
    "Library",
    "DEFAULT_AI",
    "nl_role",
    "load_roles_dir",
]
