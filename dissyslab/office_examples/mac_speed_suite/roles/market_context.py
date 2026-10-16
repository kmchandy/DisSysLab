"""
---
emits: market context for the relative-strength rule: ranks and returns by date
in: history
out: context
---
Arguments: lookback -- trading days of momentum (default 63).
"""

from _market import DEFAULT_LOOKBACK, make_market_context


class MarketContext:
    def __init__(self, lookback=DEFAULT_LOOKBACK):
        self.compute = make_market_context(lookback)

    def __call__(self, item):
        ((out, _port),) = self.compute(item)
        return {"context": out["context"]}
