"""
Regression test: per-agent kwargs from a RoleRef (office.md ``role(k=v)``
or a graph vertex's ``params``) must reach a file-based AgentRoleEntry's
factory. Previously ``_resolve_role_ref`` called ``entry()`` with no
kwargs, so a role silently fell back to its constructor defaults.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.core import Agent
from dissyslab.office._internals import CompileError
from dissyslab.office.compiler import _resolve_role_ref
from dissyslab.office.library import AgentRoleEntry
from dissyslab.office.office_spec import RoleRef


class _Configurable(Agent):
    def __init__(self, name=None, db_threshold=-30.0, debounce_ms=400.0):
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self.db_threshold = db_threshold
        self.debounce_ms = debounce_ms

    def run(self):  # pragma: no cover - not executed in this test
        while True:
            self.recv("in_")


def _entry() -> AgentRoleEntry:
    return AgentRoleEntry(
        name="threshold_detector",
        in_ports=("in_",),
        out_ports=("out",),
        factory=_Configurable,
    )


def _resolve(args):
    ref = RoleRef(
        agent_name="Bryn", role_name="threshold_detector", args=tuple(args)
    )
    library = {"threshold_detector": _entry()}
    block, kind, ports = _resolve_role_ref(ref, library, Path("."), [])
    return block


def test_kwargs_forwarded_to_factory():
    block = _resolve([("db_threshold", -15.0), ("debounce_ms", 250.0)])
    assert block.db_threshold == -15.0
    assert block.debounce_ms == 250.0


def test_no_kwargs_uses_defaults():
    block = _resolve([])
    assert block.db_threshold == -30.0


def test_bad_kwarg_raises_pat_error():
    with pytest.raises(CompileError):
        _resolve([("nonexistent_arg", 1)])
