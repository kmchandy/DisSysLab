# dissyslab/gallery/apps/mac_speed_suite/roles/_signal_common.py
# Shared helper -- underscore prefix so load_roles_dir skips it as a
# role file (same convention as _backtester_core.py).

"""
Shared signal-computer wrapper + factory, used by every strategy family
(MAC, Donchian, Turtle, and any future strategy) in this office.

This is the generalized version of the 3-part contract worked out
before any of this was built: (1) a VARIANTS table, (2) a per-ticker
compute function, (3) a shared wrapper. BACKTESTER and EVALUATOR need
zero changes to support a new strategy family -- only a new
`compute_variant_signal` needs to be written. Confirmed in practice,
not just in design: adding Donchian and Turtle alongside MAC required
no changes anywhere downstream of this module.

The three-part contract
========================
1. VARIANTS: Dict[str, Any] -- variant name -> whatever parameters
   that strategy family's compute function needs (MAC's
   (fast_span, slow_span) tuple; Donchian's breakout window in days;
   Turtle's dict of entry/exit/atr periods, max pyramided units, and
   stop-loss multiple).

2. compute_variant_signal(bars, params) -> List[float]: the one
   strategy-specific piece. `bars` is a ticker's full list of daily bar
   dicts (date/open/high/low/close/volume) -- not just closes, so a
   strategy that needs the day's high/low (Donchian, Turtle) can use
   them, while one that only needs closes (MAC) can ignore the rest.
   Contract: signal[t] must depend only on bars[0..t] (no lookahead).
   **This module enforces that**, on each variant's first real message,
   along with determinism and finiteness -- see
   `_verify_before_first_use`. It used to be on the author to uphold
   and on an assistant to remember to check, which meant a strategy
   nobody checked produced a ranking indistinguishable from one that
   had been. `checks='off'` in office.md waives it, in writing.

   The returned signal is a *position size*, not just a direction:
   +1.0 / -1.0 for a strategy that's always fully long or fully short
   (MAC, Donchian here), or a fractional value in between for a
   strategy that scales its position in and out (Turtle's pyramided
   units, here in steps of 1/max_units times sign). BACKTESTER's math
   (`prior_signal * today_return`) already handles a continuous value
   correctly -- confirmed by running Turtle through the unmodified
   BACKTESTER, not just reasoned about.

3. The wrapper below (`make_signal_computer`'s inner `signal_computer`):
   shared, written once. Per ticker: extracts closes, computes
   day-over-day returns and annualized volatility (a property of the
   stock, not of any one strategy or variant), then loops every variant
   calling that strategy family's `compute_variant_signal`, and
   assembles the message.

Variant names are prefixed with the strategy family's own name (e.g.
"mac_fast", "donchian_20", "turtle_s1") before being placed in the
output message, so several strategy families' SIGNAL_COMPUTERs can all
feed the same JOIN/EVALUATOR without their variant names colliding.

Input message shape (from any registered `*_stock_history` source):
    {
        "type":    "stock_history",
        "tickers": ["AMD", "NFLX", ...],
        "history": {
            "AMD": [{"date": "2025-08-01", "open": ..., "high": ...,
                     "low": ..., "close": ..., "volume": ...}, ...],
            ...
        },
        ...
    }

Output message shape:
    {
        "type":     "trend_signals",
        "tickers":  [...],
        "variants": ["mac_fast", ..., "donchian_20", ..., "turtle_s1", ...],
        "series": {
            "AMD": {
                "dates":   [...],
                "returns": [None, 0.0031, ...],
                "signals": {"mac_fast": [...], "donchian_20": [...], ...},
            },
            ...
        },
        "ticker_volatility": {"AMD": 0.44, ...},
    }
"""

import inspect
from typing import Any, Callable, Dict, List, Optional

TRADING_DAYS_PER_YEAR = 252.0


def _accepts_context(fn: Callable) -> bool:
    """Whether a strategy's compute function opts into cross-sectional
    context. Existing per-ticker strategies keep the two-argument signature
    ``(bars, params)`` and are called exactly as before; a strategy that
    declares ``(bars, params, context)`` (or a ``context`` keyword) is handed
    a per-ticker context dict (market series + this ticker's relative-strength
    rank/percentile), enabling relative-strength rules without touching any
    other strategy or the shared machinery downstream."""
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return False
    if any(p.name == "context" for p in params):
        return True
    positional = [p for p in params
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return len(positional) >= 3


def _daily_returns(closes: List[float]) -> List[Optional[float]]:
    """Day-over-day simple returns. Day 0 has no prior day -> None."""
    returns: List[Optional[float]] = [None]
    for prev, cur in zip(closes, closes[1:]):
        returns.append((cur - prev) / prev if prev else None)
    return returns


def _annualized_volatility(returns: List[Optional[float]]) -> float:
    """Sample std of the stock's own raw-price returns, annualized. A
    property of the stock, not of any one strategy -- computed once per
    ticker here rather than separately inside every variant/strategy."""
    values = [r for r in returns if r is not None]
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((r - mean) ** 2 for r in values) / (n - 1)
    return (variance ** 0.5) * (TRADING_DAYS_PER_YEAR ** 0.5)


#: How often the look-ahead check re-truncates history. 1 checks every
#: day, 5 every fifth. A strategy that peeks does so on essentially
#: every bar -- the bug is a line of code, not an occasional event --
#: so sampling finds it, and eleven variants stay a few seconds rather
#: than half a minute. Set to 1 for the exhaustive answer.
CHECK_SAMPLE_EVERY = 5

#: (strategy, variant, function identity) already verified this run.
#: Eleven backtesters share four signal functions, and the property is
#: a property of the function, so this runs once per variant rather
#: than once per message.
_VERIFIED: set = set()


class StrategyContractError(AssertionError):
    """A strategy failed a mechanical check before its first use.

    Raised where the strategy is *used* rather than where it was
    written, which is the difference between a check and a request.
    This check used to be a sentence in a SKILL.md telling an assistant
    to run a script; if it did not, nothing recorded the fact, and the
    office produced a ranking indistinguishable from a checked one.
    """


def _verify_before_first_use(
    strategy_name: str,
    variant_name: str,
    compute_fn,
    params,
    bars: List[dict],
    identity=None,
) -> None:
    """Run the declaration-free contract checks once, on real bars.

    **Why here and not at assembly.** The look-ahead check needs data:
    it recomputes the signal on truncated history and asserts day t's
    value does not move when later bars are added. At assembly no data
    has flowed. Fetching some here would couple the check to the source
    and would verify the strategy against data the office will not use.
    Waiting for the first message is what makes the subject and the
    sample arrive together.

    Three checks run -- the three that need nothing declared: no
    look-ahead, determinism, and every value finite. Range and warm-up
    need a strategy to declare what it promises, which the contract
    does not yet carry in machine-readable form; the skill asks for
    them and `assert_strategy_contract` takes them.
    """
    # Keyed on the *strategy's own* function, not on whatever wrapper
    # was built to call it: a context-taking strategy gets a fresh
    # closure per ticker, and keying on that would re-verify every
    # variant on every ticker.
    key = (strategy_name, variant_name, id(identity if identity is not None else compute_fn))
    if key in _VERIFIED:
        return

    from _contract_checks import (  # the office's own copy
        check_deterministic,
        check_finite,
        check_no_lookahead,
    )

    failures = []
    result = check_no_lookahead(
        compute_fn, params, bars, sample_every=CHECK_SAMPLE_EVERY
    )
    if not result["passed"]:
        v = result["first_violation"] or {}
        failures.append(
            f"it uses a later bar to decide an earlier day. On "
            f"{v.get('date')} (day {v.get('day')}) the signal is "
            f"{v.get('full_signal_value')!r} computed from the whole "
            f"history and {v.get('truncated_signal_value')!r} computed "
            f"from the history that existed on the day. A backtest of a "
            f"strategy that can see tomorrow measures nothing."
        )
    if not check_deterministic(compute_fn, params, bars)["passed"]:
        failures.append(
            "it gives two different answers for one input. Hidden "
            "randomness, a clock read, or shared mutable state -- and a "
            "run that cannot be repeated cannot be checked."
        )
    finite = check_finite(compute_fn, params, bars)
    if not finite["passed"]:
        failures.append(
            f"it produced a value that is not a finite number "
            f"({finite.get('first_violation')}). Usually a division by a "
            f"zero average, or a window read before it has filled."
        )

    if failures:
        joined = "\n  - ".join(failures)
        raise StrategyContractError(
            f"{strategy_name}_{variant_name} did not pass the strategy "
            f"contract, so the office stopped before ranking it:\n"
            f"  - {joined}\n\n"
            f"To rank it anyway, say so in office.md, where anyone "
            f"reading the office can see that you did:\n"
            f"    <AGENT> is a {strategy_name}_signal(checks='off').\n"
        )

    _VERIFIED.add(key)


def make_signal_computer(
    strategy_name: str,
    variants: Dict[str, Any],
    compute_variant_signal: Callable[[List[dict], Any], List[float]],
    checks: str = "on",
) -> Callable[[Dict[str, Any]], list]:
    """
    Factory: builds a SIGNAL_COMPUTER worker body for one strategy family.

    Args:
        strategy_name: short prefix for this family's variant names in
            the output message (e.g. "mac", "donchian", "turtle").
        variants: variant name -> params, passed through unchanged to
            `compute_variant_signal` for that variant.
        compute_variant_signal: the strategy-specific per-ticker signal
            function -- see module docstring's 3-part contract.
        checks: ``"on"`` (default) verifies every variant against the
            contract on its first real message; ``"off"`` skips it.

            The waiver is written in ``office.md`` -- ``DONCHIAN_SIGNAL
            is a donchian_signal(checks='off').`` -- and deliberately
            not as a command-line flag. A flag is invisible six weeks
            later; the office file is the artifact of record, so a
            waived check is something anyone reading the office can
            see.

            Nothing found so far needs it. Look-ahead is not a matter
            of taste -- the property is what makes a backtest mean
            anything, and it costs seconds. The hatch exists so that a
            false positive is a nuisance rather than a wall.
    """

    accepts_context = _accepts_context(compute_variant_signal)
    run_checks = str(checks).lower() not in ("off", "false", "0", "no")

    def signal_computer(msg: Dict[str, Any]):
        """Worker body: (message) -> [(message, outport_name), ...]."""
        history = msg.get("history", {}) or {}
        context = msg.get("context") or {}
        market_return_by_date = context.get("market_return_by_date", {}) or {}
        context_per_ticker = context.get("per_ticker", {}) or {}
        series: Dict[str, dict] = {}
        ticker_volatility: Dict[str, float] = {}
        variant_names = [f"{strategy_name}_{v}" for v in variants]

        for ticker, bars in history.items():
            # Skip a ticker with no usable closing prices rather than
            # crashing the whole batch over one bad ticker.
            usable_bars = [b for b in bars if b.get("close") is not None]
            if len(usable_bars) < 2:
                continue

            closes = [b["close"] for b in usable_bars]
            dates = [b["date"] for b in usable_bars]
            returns = _daily_returns(closes)

            # Per-ticker cross-sectional context, aligned to THIS ticker's
            # usable bars by date so signal[t] and context[t] index the same
            # day. Built only for strategies that opted in; MARKET_CONTEXT
            # upstream computes the values causally.
            ticker_context: Optional[Dict[str, Any]] = None
            if accepts_context and context:
                tp = context_per_ticker.get(ticker, {})
                rank_by_date = tp.get("rs_rank_by_date", {})
                pct_by_date = tp.get("rs_percentile_by_date", {})
                rel_by_date = tp.get("rel_strength_by_date", {})
                ticker_context = {
                    "market_returns": [market_return_by_date.get(d) for d in dates],
                    "rs_rank":        [rank_by_date.get(d) for d in dates],
                    "rs_percentile":  [pct_by_date.get(d) for d in dates],
                    "rel_strength":   [rel_by_date.get(d) for d in dates],
                    "n_tickers":      context.get("n_tickers"),
                    "lookback":       context.get("lookback"),
                }

            signals: Dict[str, List[float]] = {}
            for variant_name, params in variants.items():
                if accepts_context:
                    # The checker calls fn(bars, params); a
                    # context-taking strategy needs its context sliced
                    # to the same length, or truncating history would
                    # leave signal[t] reading a context array that
                    # still runs to the end -- which is the very thing
                    # being checked for.
                    def _with_context(b, p, _ctx=ticker_context):
                        n = len(b)
                        sliced = {
                            k: (v[:n] if isinstance(v, list) else v)
                            for k, v in (_ctx or {}).items()
                        }
                        return compute_variant_signal(b, p, sliced)

                    checkable = _with_context
                else:
                    checkable = compute_variant_signal

                if run_checks:
                    _verify_before_first_use(
                        strategy_name, variant_name, checkable,
                        params, usable_bars,
                        identity=compute_variant_signal,
                    )

                if accepts_context:
                    sig = compute_variant_signal(usable_bars, params, ticker_context)
                else:
                    sig = compute_variant_signal(usable_bars, params)
                signals[f"{strategy_name}_{variant_name}"] = sig

            series[ticker] = {
                "dates": dates,
                "returns": returns,
                "signals": signals,
            }
            ticker_volatility[ticker] = _annualized_volatility(returns)

        out_msg = {
            "type":              "trend_signals",
            "tickers":           list(series.keys()),
            "variants":          variant_names,
            "series":            series,
            "ticker_volatility": ticker_volatility,
            "_wf_tag":           msg.get("_wf_tag"),
        }
        return [(out_msg, "out")]

    return signal_computer
