# dissyslab/roles/confidence_filter.py

"""
``confidence_filter`` — a framework-level specialist agent.

Watches a stream of classifier outputs (or any messages that carry
a confidence score) and **passes through only those above a
threshold**, with an optional category whitelist. Drops the rest.

Why it lives at framework level
-------------------------------

This role does one well-defined job — gate a stream of dicts on a
numeric field plus an optional category field — and its contract is
on *shape* not on *content*. The same role works for vision
classifiers (drop low-confidence species guesses), audio classifiers
(drop low-confidence transcripts), NLP classifiers (drop ambiguous
sentiment labels), and anomaly detectors (drop weak signals).

That makes it part of the framework's library of reusable
specialists, alongside ``synchronizer``, ``deduplicator``, the
English-prompt roles in ``dissyslab/roles/``, and the sources and
sinks in ``SOURCE_REGISTRY`` / ``SINK_REGISTRY``.

Usage in office.md
------------------

Minimal — gate on confidence alone::

    Bryn is a confidence_filter(min_confidence=0.5).

With a category whitelist (only keep messages whose ``category``
field is in a particular set or matches a particular string)::

    Bryn is a confidence_filter(
        min_confidence=0.4,
        category_field="category",
        category_whitelist="animal",
    ).

The whitelist can be one of:

- A single string  →  match if ``msg[category_field] == whitelist``
- A list / tuple   →  match if ``msg[category_field] in whitelist``
- A callable       →  match if ``whitelist(msg[category_field])`` is truthy
- ``None``         →  no category check; gate on confidence only

Input
-----

Any dict that contains the configured ``confidence_field`` (default
``"confidence"``) as a numeric value. Other fields pass through
untouched.

Output
------

The input message, untouched, when both gates pass. Nothing
otherwise. Use this between a classifier and a sink (or between two
classifiers) when you want to suppress noise without changing the
shape of the messages downstream sees.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


def _make_predicate(whitelist) -> Callable[[Any], bool]:
    """Coerce the user's ``category_whitelist`` value into a predicate.

    Accepts a string (exact match), an iterable of strings (set
    membership), a callable (used directly), or ``None`` (always
    True — no category check).
    """
    if whitelist is None:
        return lambda _value: True
    if callable(whitelist):
        return whitelist
    if isinstance(whitelist, str):
        target = whitelist
        return lambda value: value == target
    if isinstance(whitelist, (list, tuple, set, frozenset)):
        members = frozenset(whitelist)
        return lambda value: value in members
    # Anything else: stringify and exact-match.
    target = str(whitelist)
    return lambda value: value == target


class _ConfidenceFilter(Agent):
    """Passthrough when both the confidence and category gates pass."""

    def __init__(
        self,
        name: str | None = None,
        min_confidence: float = 0.5,
        confidence_field: str = "confidence",
        category_field: str | None = None,
        category_whitelist=None,
    ):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=["out_"],
        )
        self.min_confidence = float(min_confidence)
        self.confidence_field = str(confidence_field)
        self.category_field = (
            None if category_field is None else str(category_field)
        )
        self._category_predicate = _make_predicate(category_whitelist)

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict):
                continue

            # Gate 1: confidence
            conf = msg.get(self.confidence_field)
            if conf is None:
                continue
            try:
                conf_value = float(conf)
            except (TypeError, ValueError):
                continue
            if conf_value < self.min_confidence:
                continue

            # Gate 2: category (optional)
            if self.category_field is not None:
                category = msg.get(self.category_field)
                if not self._category_predicate(category):
                    continue

            # Both gates passed — forward the message untouched.
            self.send(msg, "out_")


role = AgentRoleEntry(
    name="confidence_filter",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_ConfidenceFilter,
)
