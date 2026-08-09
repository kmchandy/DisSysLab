"""Shared helpers for the tests that sweep every gallery office.

Both ``test_parser.py`` and ``test_compiler.py`` parametrize over every
office directory under ``dissyslab/gallery/``. That sweep is what keeps
the gallery honest, but it also means an office still being built turns
the whole suite red — and CONTRIBUTING tells contributors that a failing
suite means their environment is broken, which sends them looking in
entirely the wrong place.

An office that is not finished can opt out by dropping a file named
``WIP`` in its own directory. The office is then reported as an expected
failure with the marker's text as the reason, instead of a hard failure.
The mark is deliberately non-strict, so a sweep the office already
passes reports XPASS rather than failing. Because the two sweeps report
separately, an office that parses but does not compile shows up as one
XPASS and one XFAIL — a free diagnosis of how far it gets. The marker
comes out when no XFAIL is left.

Keeping the opt-out inside the office folder — rather than in a list in
a test file — means an unfinished office needs no edit to any tracked
test, which matters because unfinished offices are usually untracked.
"""

from __future__ import annotations

from pathlib import Path

import pytest

WIP_MARKER = "WIP"

_DEFAULT_REASON = "office is marked work-in-progress (see its WIP file)"


def wip_reason(office_dir: Path) -> str | None:
    """Return the reason this office is WIP, or None if it is not.

    The reason is the first non-empty, non-comment line of the marker
    file, so ``echo "salton_wind is not registered yet" > WIP`` is all
    it takes to leave a useful note for whoever sees the XFAIL.
    """
    marker = Path(office_dir) / WIP_MARKER
    if not marker.exists():
        return None
    try:
        text = marker.read_text(encoding="utf-8")
    except OSError:
        return _DEFAULT_REASON
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return _DEFAULT_REASON


def gallery_params(office_dirs) -> list:
    """Wrap office dirs as pytest params, xfailing the WIP ones."""
    params = []
    for d in office_dirs:
        reason = wip_reason(d)
        marks = (
            [pytest.mark.xfail(reason=f"WIP: {reason}", strict=False)]
            if reason
            else []
        )
        params.append(pytest.param(d, id=d.name, marks=marks))
    return params
