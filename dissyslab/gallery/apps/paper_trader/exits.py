"""
exits.py -- EXITS: the optional, pluggable exit-policy slot between SIGNAL and
SIZER. Pure Python.

Policies (a small, tested menu -- a sibling of the strategy and sizing policies,
disclosed in the receipt):

  market_defined  (default) -- pass-through: exits come from the strategy's own
                               signal (a name whose signal is 0 is exited),
                               exactly as in the backtester. Book-independent, so
                               backtest and live match by construction.

  realized_entry  (opt-in)  -- stops keyed to your realized entry / high-water
                               mark (reads the book). Gated on the fill-modeling
                               backtester (EXECUTION_DESIGN.md §8): until that
                               exists it would silently diverge from the backtest,
                               so selecting it RAISES rather than no-ops. That
                               refuse-loudly behavior is the intended guard.

Keeping the default a pass-through means the MVP office is consistent with the
backtester with no extra machinery; the `EXITS` slot exists so a real exit policy
plugs in later without touching SIZER / RECON / BOOK.
"""

from __future__ import annotations

from typing import Any, Dict


def apply_exits(
    signals: Dict[str, float],
    positions: Dict[str, float],
    prices: Dict[str, float],
    book: Any,
    policy: Dict[str, Any],
) -> Dict[str, float]:
    """Return possibly-adjusted target signals. Default is identity."""
    pol = policy.get("exit_policy", "market_defined")
    if pol == "market_defined":
        return dict(signals)                      # exits are already in the signal
    if pol == "realized_entry":
        raise NotImplementedError(
            "exit_policy 'realized_entry' requires the fill-modeling backtester "
            "for backtest-live consistency (see EXECUTION_DESIGN.md §8); it is not "
            "yet built. Refusing rather than silently diverging from the backtest."
        )
    raise ValueError(f"unknown exit_policy: {pol!r} (known: market_defined, realized_entry)")
