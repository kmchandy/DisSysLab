# dissyslab/gallery/apps/mac_speed_suite/roles/rs_trend.py

"""
RS_TREND -- a relative-strength trend-following strategy: go long only
when a stock's own trend is up AND it is strong relative to its peers
(top half of the basket by momentum), otherwise stay flat.

This is the strategy a per-ticker compute function could not express
before: "strong relative to the market / peers" needs to compare this
stock against the others -- exactly the wall an outside tester hit
describing an ordinary trend rule in relatively strong stocks. It works by
opting into the optional `context` argument (see _signal_common.py): the
MARKET_CONTEXT stage upstream supplies each ticker's causal relative-
strength percentile, and this strategy gates its long on that.

Requires MARKET_CONTEXT upstream. Without it (e.g. isolated worker
testing) there is no relative-strength signal, so the strategy stays flat.

Long-only (position 0.0 or +1.0): when it is not both trending and strong,
it holds nothing -- so it genuinely spends days out of the market, which the
report now surfaces (Days-in-market / "no trades").
"""

import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _signal_common import make_signal_computer  # noqa: E402

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

# trend_lb:        the stock's own up-trend lookback (price today vs then).
# min_percentile:  how strong vs peers it must be to qualify (0.5 = top half).
RS_TREND_VARIANTS = {
    "fast": {"trend_lb": 20, "min_percentile": 0.5},
    "slow": {"trend_lb": 60, "min_percentile": 0.5},
}


def _rs_trend_compute_variant_signal(
    bars: List[dict],
    params: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> List[float]:
    """+1.0 when the stock's own trend is up and it is strong vs peers,
    else 0.0 (flat).

    No lookahead: signal[t] uses only closes[0..t] and the causal
    relative-strength percentile at day t (supplied by MARKET_CONTEXT).
    """
    closes = [b["close"] for b in bars]
    trend_lb = params["trend_lb"]
    min_pct = params["min_percentile"]
    pct = (context or {}).get("rs_percentile") or [None] * len(closes)

    out: List[float] = []
    for t in range(len(closes)):
        trend_up = t >= trend_lb and closes[t] >= closes[t - trend_lb]
        p = pct[t] if t < len(pct) else None
        strong = p is not None and p >= min_pct
        out.append(1.0 if (trend_up and strong) else 0.0)
    return out


role = AgentRoleEntry(
    name="rs_trend",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda: Role(
        fn=make_signal_computer(
            "rs", RS_TREND_VARIANTS, _rs_trend_compute_variant_signal
        ),
        statuses=["out"],
    ),
)
