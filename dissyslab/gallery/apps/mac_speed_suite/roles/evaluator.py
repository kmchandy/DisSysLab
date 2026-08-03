# dissyslab/gallery/apps/mac_speed_suite/draft_workers/evaluator.py

"""
EVALUATOR -- Phase 2 draft worker body (NOT yet wired into any
office.md, NOT yet approved). Sits downstream of JOIN in the "MAC
speed suite" demo office: one source -> SIGNAL_COMPUTER -> five
concurrent BACKTESTER workers -> JOIN -> EVALUATOR -> REPORT.

What this worker does, in plain terms
======================================

Each BACKTESTER already answered, per stock, "what would this one
speed's rule have earned, day by day" -- but deliberately stops there
(see backtester.py's docstring). EVALUATOR does two distinct jobs on
top of that:

1. **The per-stock table (Vikram's actual, stated goal).** For every
   stock and every one of the five speeds, turn that stock's own
   day-by-day story into the same six summary numbers (defined below).
   With 100 stocks and 5 speeds that's a 500-row table -- the direct
   answer to "tables with the appropriate metrics for each of the 100
   stocks for each of the 5 parameter settings."

2. **The portfolio-level ranking (anticipated, not yet requested).**
   Combine all the stocks into one number per speed -- "if you'd
   traded this one speed's rule across the whole portfolio, day by
   day, what would have happened" -- and rank the five speeds (plus a
   blend of all five) against each other. This needs a real decision
   Vikram hasn't made yet: how much of each stock is "in" the
   portfolio. See "Portfolio weighting" below for the default used
   here.

The six numbers computed for every (stock, speed) pair and for every
portfolio-level candidate (plain-English definitions, no finance
background assumed):

- **Annualized return** -- if the daily gains and losses had
  compounded at the same average rate for a full year, what would the
  total return have been? Turns "195 days of small daily moves" into
  one "if this kept up all year" percentage.
- **Annualized volatility** -- how much the daily returns bounced
  around, scaled up to a yearly figure. A rule that's up 1% one day
  and down 1% the next has high volatility even if it nets out to
  zero; a rule that's up 0.1% every single day has very low
  volatility. Higher volatility = a bumpier ride, for better or worse.
- **Sharpe ratio** -- annualized return divided by annualized
  volatility. The standard way to ask "how much return did this
  actually earn *per unit of bumpiness*?" (We assume a 0% "risk-free
  rate" here -- a simplification, not a hidden assumption.)
- **Max drawdown** -- the single worst peak-to-trough decline over
  the whole period: if you'd invested at the best possible moment and
  it then went downhill for a while before recovering, how far down
  did it go before turning back up?
- **Calmar ratio** -- annualized return divided by (the size of) max
  drawdown.
- **Sortino ratio** -- like Sharpe, but only penalizes *downside*
  bumpiness (bad days), not upside. A rule that sometimes has a big
  *good* day looks unfairly "risky" under Sharpe; Sortino doesn't ding
  it for that. (Beyond Vikram's named list -- added for the same
  reason Sharpe is useful.)

Portfolio weighting (the "how do you build one portfolio out of 100
stocks" question)
====================================================================

Default here: **inverse-volatility weighting** -- each stock's share
of the portfolio is proportional to 1 / (that stock's own recent
volatility), so a calm stock gets more weight and a jumpy one gets
less, and every stock ends up contributing roughly *equal risk*
rather than equal share count. This is the real industry convention
for this kind of strategy (matches Man AHL's own "volatility scaled
such that each has equal risk weight" approach), needs no data beyond
what SIGNAL_COMPUTER already computes (`ticker_volatility` -- each
stock's own raw-price volatility, not any one speed's strategy
volatility), and is a property of the *stock*, so it's the same
weighting for all five speeds.

After weighting, the whole combined portfolio is additionally scaled
(`target_annual_vol`, default 10%) to hit one target volatility level
for every speed -- matching Man's own "each speed scaled to 10%
annualised vol" convention, so the five speeds' portfolio-level
numbers are being compared on equal footing rather than one speed
simply looking better because it happened to run hotter.

This is a real, tunable design choice, not a fact -- easy to swap for
equal-weighting, a user-supplied weight dict, or (once real
fundamentals data exists) market-cap weighting, without touching
anything upstream of EVALUATOR.

Input message shape (JOIN's merged output -- see backtester.py's
docstring for why BACKTESTER nests its result under its own
`speed_name` key, and passes `ticker_volatility` through unchanged,
which is what makes this merge collision-free):
    {
        "type": "mac_backtest",
        "ticker_volatility": {"AAPL": 0.183, "MSFT": 0.201, ...},
        "fast":     {"per_ticker_returns": {"AAPL": [...], ...}},
        "med_fast": {"per_ticker_returns": {...}},
        "med":      {"per_ticker_returns": {...}},
        "med_slow": {"per_ticker_returns": {...}},
        "slow":     {"per_ticker_returns": {...}},
    }

Output message shape:
    {
        "type":    "mac_evaluation",
        "rank_by": "sharpe_ratio",
        "table": {
            "AAPL": {
                "fast":     {"annualized_return": ..., "sharpe_ratio": ..., ...},
                "med_fast": {...}, "med": {...}, "med_slow": {...}, "slow": {...},
            },
            "MSFT": {...},
            ...
        },
        "portfolio_stats": {
            "fast":        {"annualized_return": ..., "sharpe_ratio": ..., ...},
            "med_fast":    {...}, "med": {...}, "med_slow": {...}, "slow": {...},
            "equal_blend": {...},
        },
        "ranked": ["equal_blend", "fast", "med", ...],  # best -> worst,
                                                          # by `rank_by`
    }
"""

from typing import Any, Callable, Dict, List, Optional

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

TRADING_DAYS_PER_YEAR = 252.0


# ── Per-series statistics ───────────────────────────────────────────────


def annualized_return(daily_returns: List[float]) -> float:
    """Compound `daily_returns` and scale to a one-year-equivalent rate."""
    if not daily_returns:
        return 0.0
    wealth = 1.0
    for r in daily_returns:
        wealth *= (1.0 + r)
    n_days = len(daily_returns)
    return wealth ** (TRADING_DAYS_PER_YEAR / n_days) - 1.0


def annualized_volatility(daily_returns: List[float]) -> float:
    """Sample standard deviation of daily returns, scaled to a yearly figure."""
    n = len(daily_returns)
    if n < 2:
        return 0.0
    mean = sum(daily_returns) / n
    variance = sum((r - mean) ** 2 for r in daily_returns) / (n - 1)
    daily_vol = variance ** 0.5
    return daily_vol * (TRADING_DAYS_PER_YEAR ** 0.5)


def sharpe_ratio(ann_return: float, ann_volatility: float) -> Optional[float]:
    """Return per unit of volatility. Assumes a 0% risk-free rate -- see
    module docstring's "Risk-free rate assumption" note."""
    if ann_volatility == 0:
        return None
    return ann_return / ann_volatility


def max_drawdown(daily_returns: List[float]) -> float:
    """Worst peak-to-trough decline of the compounded wealth curve.

    Returned as a negative number or 0.0 (e.g. -0.23 means -23%) --
    never positive, by construction.
    """
    wealth = 1.0
    peak = 1.0
    worst = 0.0
    for r in daily_returns:
        wealth *= (1.0 + r)
        peak = max(peak, wealth)
        drawdown = (wealth - peak) / peak
        worst = min(worst, drawdown)
    return worst


def calmar_ratio(ann_return: float, max_dd: float) -> Optional[float]:
    """Annualized return divided by the size of the max drawdown."""
    if max_dd == 0:
        return None
    return ann_return / abs(max_dd)


def sortino_ratio(
    daily_returns: List[float], ann_return: float, target: float = 0.0
) -> Optional[float]:
    """Like Sharpe, but only penalizes returns below `target` (default 0%)."""
    n = len(daily_returns)
    if n == 0:
        return None
    downside_sq_sum = sum(min(r - target, 0.0) ** 2 for r in daily_returns)
    downside_deviation = (downside_sq_sum / n) ** 0.5 * (TRADING_DAYS_PER_YEAR ** 0.5)
    if downside_deviation == 0:
        return None
    return ann_return / downside_deviation


def compute_stats(daily_returns: List[float]) -> Dict[str, Optional[float]]:
    """All six metrics for one daily-return series, in one dict."""
    if not daily_returns:
        return {
            "annualized_return": 0.0, "annualized_volatility": 0.0,
            "sharpe_ratio": None, "max_drawdown": 0.0,
            "calmar_ratio": None, "sortino_ratio": None,
        }
    ann_return = annualized_return(daily_returns)
    ann_vol = annualized_volatility(daily_returns)
    mdd = max_drawdown(daily_returns)
    return {
        "annualized_return":     ann_return,
        "annualized_volatility": ann_vol,
        "sharpe_ratio":          sharpe_ratio(ann_return, ann_vol),
        "max_drawdown":          mdd,
        "calmar_ratio":          calmar_ratio(ann_return, mdd),
        "sortino_ratio":         sortino_ratio(daily_returns, ann_return),
    }


# ── Portfolio construction: inverse-volatility weighting ────────────────


def _inverse_volatility_weights(
    ticker_volatility: Dict[str, float], tickers: List[str]
) -> Dict[str, float]:
    """Weight each ticker proportional to 1/volatility, normalized to
    sum to 1 -- equal *risk* contribution, not equal share count.

    A ticker with unknown or zero volatility (e.g. too little price
    history) is excluded rather than given a division-by-zero weight.
    If every ticker lacks volatility info, falls back to equal-weight
    across whatever tickers are present, rather than producing an
    empty portfolio.
    """
    inverse = {
        t: 1.0 / ticker_volatility[t]
        for t in tickers
        if ticker_volatility.get(t, 0.0) > 0
    }
    total = sum(inverse.values())
    if total == 0:
        n = len(tickers)
        return {t: 1.0 / n for t in tickers} if n else {}
    return {t: w / total for t, w in inverse.items()}


def _weighted_portfolio_returns(
    per_ticker_returns: Dict[str, List[float]], weights: Dict[str, float]
) -> List[float]:
    """Combine each ticker's own daily return series into one weighted
    portfolio return series, day by day."""
    tickers = [t for t in per_ticker_returns if t in weights]
    if not tickers:
        return []
    n_days = len(per_ticker_returns[tickers[0]])
    return [
        sum(weights[t] * per_ticker_returns[t][day] for t in tickers)
        for day in range(n_days)
    ]


def _scale_to_target_volatility(
    daily_returns: List[float], target_annual_vol: float
) -> List[float]:
    """Scale a whole return series so its own annualized volatility
    equals `target_annual_vol` -- puts every speed's portfolio on equal
    footing rather than letting whichever speed ran hottest look best
    by default. A no-op if the series has no volatility to scale."""
    if not daily_returns:
        return daily_returns
    current_vol = annualized_volatility(daily_returns)
    if current_vol == 0:
        return daily_returns
    scale = target_annual_vol / current_vol
    return [r * scale for r in daily_returns]


def _equal_blend(speed_portfolio_returns: Dict[str, List[float]]) -> List[float]:
    """Average every speed's (already weighted/scaled) portfolio return,
    day by day.

    Mirrors Man AHL's own "Equal Blend": since the five speeds are
    only weakly correlated, combining them tends to smooth out any one
    speed's rough patch -- worth scoring as a sixth candidate, not
    just the five speeds alone.
    """
    series_list = [s for s in speed_portfolio_returns.values() if s]
    if not series_list:
        return []
    n_speeds = len(series_list)
    n_days = len(series_list[0])
    return [
        sum(series[day] for series in series_list) / n_speeds
        for day in range(n_days)
    ]


# ── Worker body ──────────────────────────────────────────────────────────


def make_evaluator(
    rank_by: str = "sharpe_ratio",
    target_annual_vol: float = 0.10,
) -> Callable[[Dict[str, Any]], list]:
    """
    Build the EVALUATOR worker body.

    Args:
        rank_by: which of the six metrics to sort portfolio-level
            candidates by, best first. Default "sharpe_ratio" -- the
            standard risk-adjusted return metric for comparing trading
            rules against each other. All six metrics are still
            reported for every candidate regardless of which one is
            used to rank.
        target_annual_vol: every speed's inverse-volatility-weighted
            portfolio is scaled to this annualized volatility (default
            10%, matching Man AHL's own convention) before being
            scored and ranked, so the comparison isn't skewed by one
            speed simply running hotter than another.
    """

    def evaluator(msg: Dict[str, Any]):
        """Worker body: (message) -> [(message, outport_name), ...]."""
        ticker_volatility = msg.get("ticker_volatility", {}) or {}
        # Every key except "type" and "ticker_volatility" is one
        # speed's nested backtest result -- see backtester.py's
        # docstring for why BACKTESTER's message is shaped this way.
        speed_results = {
            k: v for k, v in msg.items()
            if k not in ("type", "ticker_volatility")
        }

        # ---- 1. Per-stock x per-speed table (Vikram's actual ask) ----
        table: Dict[str, Dict[str, dict]] = {}
        for speed, result in speed_results.items():
            for ticker, returns in result.get("per_ticker_returns", {}).items():
                table.setdefault(ticker, {})[speed] = compute_stats(returns)

        # ---- 2. Portfolio-level ranking (anticipated future ask) ----
        speed_portfolio_returns: Dict[str, List[float]] = {}
        for speed, result in speed_results.items():
            per_ticker_returns = result.get("per_ticker_returns", {})
            weights = _inverse_volatility_weights(
                ticker_volatility, list(per_ticker_returns.keys())
            )
            weighted = _weighted_portfolio_returns(per_ticker_returns, weights)
            speed_portfolio_returns[speed] = _scale_to_target_volatility(
                weighted, target_annual_vol
            )

        portfolio_stats = {
            speed: compute_stats(returns)
            for speed, returns in speed_portfolio_returns.items()
        }
        portfolio_stats["equal_blend"] = compute_stats(
            _equal_blend(speed_portfolio_returns)
        )

        def sort_key(name: str) -> float:
            value = portfolio_stats[name].get(rank_by)
            return value if value is not None else float("-inf")

        ranked = sorted(portfolio_stats, key=sort_key, reverse=True)

        out_msg = {
            "type":            "mac_evaluation",
            "rank_by":         rank_by,
            "table":           table,
            "portfolio_stats": portfolio_stats,
            "ranked":          ranked,
        }
        return [(out_msg, "out")]

    return evaluator


# ── Role registration (this office's roles/ dir; see library.py) ───────

role = AgentRoleEntry(
    name="evaluator",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda: Role(
        fn=make_evaluator(rank_by="sharpe_ratio", target_annual_vol=0.10),
        statuses=["out"],
    ),
)
