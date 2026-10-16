"""
---
emits: one variant's daily strategy returns and trades, for one span
kind: author
in: span, series, ticker_volatility
out: span, variant, result, ticker_volatility, _wf_tag
---
Arguments: variant -- which signal column to trade (e.g. "mac_fast");
cost_bps -- one-way transaction cost in basis points (default 5).
"""

from _backtester_core import DEFAULT_COST_BPS, make_backtester


class Backtester:
    def __init__(self, variant, cost_bps=DEFAULT_COST_BPS):
        self.variant = variant
        self.compute = make_backtester(variant, cost_bps)

    def __call__(self, item):
        ((out, _port),) = self.compute(item)
        return [{
            "span": item["span"],
            "variant": self.variant,
            "result": out[self.variant],
            "ticker_volatility": out["ticker_volatility"],
            "_wf_tag": out.get("_wf_tag"),
        }]
