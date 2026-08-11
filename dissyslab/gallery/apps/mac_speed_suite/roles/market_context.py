# dissyslab/gallery/apps/mac_speed_suite/roles/market_context.py

"""
MARKET_CONTEXT -- a shared stage that enriches the stock-history message
with cross-sectional ("relative strength") information, so a strategy can
say "buy stocks that are strong relative to the market / their peers" --
something a per-ticker compute function cannot do on its own, because it
only ever sees one ticker's bars. (That is exactly the wall an outside
tester hit trying to express an ordinary relative-strength trend rule.)

It sits between the source and the signal computers, adds a `context`
field, and passes everything else (notably `history`) through unchanged.
Existing strategies ignore `context`; a relative-strength strategy reads it
(see rs_trend.py and _signal_common.py's optional-context contract). The
backtester and evaluator downstream are untouched.

Everything here is causal: each day t's values use only prices up to day t,
so the no-lookahead property still holds through the whole pipeline.

context shape added to the message:
    {
      "lookback": 63,
      "n_tickers": 5,
      "market_return_by_date": {date: mean daily return across tickers},
      "per_ticker": {
        ticker: {
          "rs_rank_by_date":       {date: 1..N, 1 = strongest by momentum},
          "rs_percentile_by_date": {date: 0..1, fraction of peers weaker},
          "rel_strength_by_date":  {date: this ticker's momentum - mean momentum},
        }, ...
      },
    }

`_signal_common.make_signal_computer` reshapes this per-ticker context into
positional arrays aligned to each ticker's usable bars before handing it to
a strategy's compute function.
"""

from typing import Any, Callable, Dict, List, Tuple

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

DEFAULT_LOOKBACK = 63  # ~3 trading months -- a standard momentum window


def _usable(bars: List[dict]) -> Tuple[List[str], List[float]]:
    ub = [b for b in bars if b.get("close") is not None]
    return [b["date"] for b in ub], [b["close"] for b in ub]


def make_market_context(
    lookback: int = DEFAULT_LOOKBACK,
) -> Callable[[Dict[str, Any]], list]:
    """Build the MARKET_CONTEXT worker body for a given momentum lookback."""

    def market_context(msg: Dict[str, Any]):
        """Worker body: (message) -> [(message, outport_name), ...]."""
        history = msg.get("history", {}) or {}

        dates_of: Dict[str, List[str]] = {}
        closes_of: Dict[str, List[float]] = {}
        for ticker, bars in history.items():
            d, c = _usable(bars)
            if len(c) >= 2:
                dates_of[ticker] = d
                closes_of[ticker] = c
        tickers = list(dates_of.keys())

        # Daily returns and trailing-lookback momentum per ticker, keyed by
        # date -- both causal (use only prices up to that date).
        ret_by_date: Dict[str, Dict[str, float]] = {t: {} for t in tickers}
        mom_by_date: Dict[str, Dict[str, float]] = {t: {} for t in tickers}
        for t in tickers:
            d, c = dates_of[t], closes_of[t]
            for i in range(1, len(c)):
                if c[i - 1]:
                    ret_by_date[t][d[i]] = (c[i] - c[i - 1]) / c[i - 1]
            for i in range(lookback, len(c)):
                if c[i - lookback]:
                    mom_by_date[t][d[i]] = c[i] / c[i - lookback] - 1.0

        all_dates = sorted({d for t in tickers for d in dates_of[t]})

        # Equal-weight basket ("the market") daily return, per date.
        market_return_by_date: Dict[str, float] = {}
        for d in all_dates:
            vals = [ret_by_date[t][d] for t in tickers if d in ret_by_date[t]]
            if vals:
                market_return_by_date[d] = sum(vals) / len(vals)

        # Cross-sectional rank / percentile / relative strength, per date.
        per_ticker: Dict[str, Dict[str, Dict[str, float]]] = {
            t: {
                "rs_rank_by_date": {},
                "rs_percentile_by_date": {},
                "rel_strength_by_date": {},
            }
            for t in tickers
        }
        for d in all_dates:
            present = [(t, mom_by_date[t][d]) for t in tickers if d in mom_by_date[t]]
            if not present:
                continue
            nd = len(present)
            mean_mom = sum(m for _, m in present) / nd
            # Rank descending: 1 = strongest momentum. Stable order breaks
            # ties deterministically.
            ordered = sorted(present, key=lambda x: x[1], reverse=True)
            for rank, (t, m) in enumerate(ordered, start=1):
                per_ticker[t]["rs_rank_by_date"][d] = rank
                per_ticker[t]["rs_percentile_by_date"][d] = (
                    (nd - rank) / (nd - 1) if nd > 1 else 1.0
                )
                per_ticker[t]["rel_strength_by_date"][d] = m - mean_mom

        out = dict(msg)
        out["context"] = {
            "lookback": lookback,
            "n_tickers": len(tickers),
            "market_return_by_date": market_return_by_date,
            "per_ticker": per_ticker,
        }
        return [(out, "out")]

    return market_context


role = AgentRoleEntry(
    name="market_context",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda lookback=DEFAULT_LOOKBACK: Role(
        fn=make_market_context(lookback), statuses=["out"]
    ),
)
