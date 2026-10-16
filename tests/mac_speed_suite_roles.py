"""The mac_speed_suite gallery office's code, for its unit tests.

The office's roles import their helpers by bare name
(``from _signal_common import ...``), as a role does when ``dsl run``
loads it with its folder on the path. Importing this module puts the
office's ``roles/`` and ``sinks/`` folders on the path the same way, so
a test can say ``from _backtester_core import make_backtester``.

The version 1 office ran its validation loop with two Agent classes,
``_ValidationGate.next_span`` and ``_Comparator.accept``; the 2.0 office
does it with two roles, ``Plan`` and ``Comparator``, connected through a
router. ``next_span`` and ``accept`` below drive the roles the way the
office does, so the tests of that logic carried over unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

OFFICE = Path(__file__).resolve().parents[1] / "dissyslab" / "gallery" / "mac_speed_suite"

for _folder in (OFFICE / "roles", OFFICE / "sinks"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

from comparator import Comparator  # noqa: E402
from plan import Plan  # noqa: E402

__all__ = ["NEXT", "OFFICE", "Comparator", "Plan", "accept", "next_span"]

#: What the comparator sends back to Plan for the next span.
NEXT = {"msg_type": "next"}


def next_span(plan: Plan, msg: dict[str, Any]) -> dict[str, Any] | None:
    """The span Plan sends for ``msg``, or None when every span is done."""
    out = plan(msg)
    return out[0] if out else None


def accept(comp: Comparator, evaluation: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """("next", ...) or ("scorecard", the report), as the router would route it."""
    (out,) = comp(evaluation)
    if out["msg_type"] == "scorecard":
        return "scorecard", out["scorecard"]
    return "next", out
