"""Kept as the path people already type. The checks live with the office.

They moved to ``roles/_contract_checks.py`` inside the backtest office
when they stopped being something a person runs and became something
the office runs for itself: ``make_signal_computer`` verifies a
strategy on its first message, so the checks have to travel with the
office that `dsl init` copies, not sit in a scripts/ folder that only
exists in a clone.

This shim exists because the skill, the tester instructions and two
design notes all name the old path, and a moved file that answers
"No such file" teaches nobody anything.
"""
from __future__ import annotations

import sys
from pathlib import Path

_OFFICE_ROLES = (
    Path(__file__).resolve().parents[2]
    / "dissyslab" / "gallery" / "apps" / "mac_speed_suite" / "roles"
)
sys.path.insert(0, str(_OFFICE_ROLES))

from _contract_checks import *  # noqa: F401,F403,E402
from _contract_checks import (  # noqa: E402
    assert_deterministic,
    assert_finite,
    assert_matches_golden_example,
    assert_no_lookahead,
    assert_signal_range,
    assert_strategy_contract,
    assert_trend_sanity,
    assert_warmup,
    check_deterministic,
    check_finite,
    check_no_lookahead,
    check_signal_range,
    check_trend_sanity,
    check_warmup,
    make_monotonic_bars,
)

if __name__ == "__main__":  # pragma: no cover
    import runpy

    runpy.run_path(str(_OFFICE_ROLES / "_contract_checks.py"), run_name="__main__")
