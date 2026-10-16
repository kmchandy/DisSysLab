"""
---
emits: the scorecard of every variant for one span
kind: author
in: span, results
out: span, type, rank_by, n_days, cost_bps, table, portfolio_stats, ranked, correlation, trade_stats, trades, stop_pct, _wf_tag
---
The synchronizer collects the backtesters' messages into ``results``
(inbox -> message); each says which variant it is. The evaluation code
(``_evaluation.py``) is unchanged: it is given one field per variant.
"""

from _evaluation import make_evaluator


class Evaluate:
    def __init__(self, rank_by="sharpe_ratio", target_annual_vol=0.10):
        self.compute = make_evaluator(rank_by=rank_by, target_annual_vol=target_annual_vol)

    def __call__(self, item):
        results = list(item["results"].values())
        merged = {
            "type": "backtest",
            "ticker_volatility": results[0]["ticker_volatility"],
            "_wf_tag": results[0].get("_wf_tag"),
        }
        for r in results:
            merged[r["variant"]] = r["result"]
        ((out, _port),) = self.compute(merged)
        return [{**out, "span": item["span"]}]
