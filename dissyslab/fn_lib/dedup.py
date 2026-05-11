"""
Deduplicator — drop messages whose chosen field has been seen before.

Pat writes in office.md::

    Sasha is a deduplicator(by="url").

Read ``by="url"`` as **"deduplicate by the value of the 'url' field
in each incoming message"**. The compiler builds a ``Transform``
whose state is a ``seen`` set keyed by ``msg["url"]``. The first
time a value appears, the message passes through; on every later
sighting it is dropped. The kwarg name ``by`` is the framework's
convention for "the field name to key on" — it appears in
``params={'by': 'url'}`` in the generated artifact, where the same
reading applies.

Choice of field
===============

The default is ``by="url"`` because the framework's normalised article
shape (``{source, title, text, url, timestamp}``) treats ``url`` as
the canonical identifier. Other useful keys:

* ``by="title"`` — drop articles with identical headlines (riskier:
  small wording differences keep duplicates).
* ``by="id"`` or ``by="message_id"`` — for sources that emit explicit
  IDs (Gmail, webhooks).

Edge cases
==========

* Messages that are not dicts, or dicts missing the chosen key, are
  dropped. Pat is told via diagnostics rather than a runtime crash —
  the deduper is the wrong place to surface a malformed-input error
  loudly. (A future ``log_dropped`` param can surface them when Pat
  is debugging.)
* The ``seen`` set grows unboundedly. For 24/7 offices this is fine
  for thousands of messages; long-running deployments needing months
  of de-duplication will want a windowed variant — to be added as a
  separate entry, not as more parameters here.

State shape
===========

::

    {"seen": set[str]}

That's it. ``by`` lives in ``params``, not state — it's configuration
that doesn't change between messages.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def deduplicator_initial_state() -> Dict[str, Any]:
    """Build a fresh state dict for a deduplicator agent.

    Called by the compiler once per agent at construction time. Takes
    no kwargs — the deduplicator's only mutable memory is the set of
    keys it has already seen. Pat's ``by="url"`` choice lives in
    ``params`` (read by ``deduplicator`` on every call), not in
    state, because it is configuration that does not change between
    messages.
    """
    return {"seen": set()}


def deduplicator(
    msg: Any,
    state: Dict[str, Any],
    by: str = "url",
) -> Optional[Any]:
    """Drop ``msg`` if ``msg[by]`` has been seen before; else pass through.

    Parameters
    ----------
    msg
        The incoming message. Expected to be a dict containing the
        key named by ``by``. Non-dicts and dicts missing the key are
        dropped silently.
    state
        Mutable state dict; keys: ``seen`` (a ``set``).
    by
        Name of the field in ``msg`` whose value identifies a
        duplicate. ``by="url"`` means "two messages are duplicates
        if their ``url`` values are equal." Defaults to ``"url"``.
    """
    if not isinstance(msg, dict) or by not in msg:
        return None  # malformed input; can't dedupe what we can't key
    key = msg[by]
    if key in state["seen"]:
        return None
    state["seen"].add(key)
    return msg


# Wrapped into an FnEntry by ``__init__`` to register in ``FN_LIB``.
# Imported lazily there to avoid a circular import.

from dissyslab.fn_lib import FnEntry  # noqa: E402  — registered above


deduplicator_entry = FnEntry(
    name="deduplicator",
    fn=deduplicator,
    initial_state=deduplicator_initial_state,
    description=(
        "Drop messages whose chosen field (default 'url') has been seen "
        "before. State is a 'seen' set; configuration is the field name."
    ),
)
