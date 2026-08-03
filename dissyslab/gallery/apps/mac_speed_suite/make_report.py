# dissyslab/gallery/apps/mac_speed_suite/make_report.py

"""
Generates `report.html` -- a readable, finance-memo-style summary of
one run of the mac_speed_suite office, for a non-technical (but
finance-literate) reader like Vikram.

Runs the same worker functions the real office runs (three signal
computers -- MAC, Donchian, Turtle -- -> nine backtesters, one per
variant -> evaluator), on the same real CSV data and tickers office.md
uses, so this report's numbers are exactly what `dsl run` on this
office produces -- not a separate, re-transcribed copy of them. If you
change office.md's tickers or data directory, update the constants
below to match, or this report will describe a different run than the
one office.md actually performs.

Usage:
    python3 make_report.py
"""

import html
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "roles"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

from dissyslab.components.sources.csv_stock_history_source import (
    CSVStockHistorySource,
)
from _signal_common import make_signal_computer
from mac_signal import MAC_VARIANTS, _mac_compute_variant_signal
from donchian_signal import DONCHIAN_VARIANTS, _donchian_compute_variant_signal
from turtle_signal import TURTLE_VARIANTS, _turtle_compute_variant_signal
from _backtester_core import make_backtester
from evaluator import make_evaluator

# Must match office.md's Sources: line exactly.
TICKERS = ["AMD", "NFLX", "NVDA", "PLTR", "TSLA"]
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "sp100_data")

VARIANT_LABELS = {
    "mac_fast":      "MAC -- Fast (2/8 day EWMA)",
    "mac_med_fast":  "MAC -- Medium-Fast (4/16 day EWMA)",
    "mac_med":       "MAC -- Medium (8/32 day EWMA)",
    "mac_med_slow":  "MAC -- Medium-Slow (16/64 day EWMA)",
    "mac_slow":      "MAC -- Slow (32/128 day EWMA)",
    "donchian_20":   "Donchian -- 20-day channel",
    "donchian_55":   "Donchian -- 55-day channel",
    "turtle_s1":     "Turtle -- System 1 (20-day entry / 10-day exit)",
    "turtle_s2":     "Turtle -- System 2 (55-day entry / 20-day exit)",
}
VARIANT_ORDER = list(VARIANT_LABELS.keys())


def run_pipeline():
    src = CSVStockHistorySource(tickers=TICKERS, directory=DATA_DIR)
    history_msg = next(src.run())

    mac_fn = make_signal_computer("mac", MAC_VARIANTS, _mac_compute_variant_signal)
    don_fn = make_signal_computer("donchian", DONCHIAN_VARIANTS, _donchian_compute_variant_signal)
    turtle_fn = make_signal_computer("turtle", TURTLE_VARIANTS, _turtle_compute_variant_signal)

    merged = {}
    for signal_fn in (mac_fn, don_fn, turtle_fn):
        [(signal_msg, _)] = signal_fn(history_msg)
        for variant in signal_msg["variants"]:
            bt_fn = make_backtester(variant)
            [(bt_msg, _)] = bt_fn(signal_msg)
            merged.update(bt_msg)

    ev_fn = make_evaluator(rank_by="sharpe_ratio", target_annual_vol=0.10)
    [(eval_msg, _)] = ev_fn(merged)
    return history_msg, eval_msg


def pct(x, digits=1):
    return f"{x * 100:+.{digits}f}%" if x is not None else "n/a"


def num(x, digits=2):
    return f"{x:.{digits}f}" if x is not None else "n/a"


def label(name):
    return "Equal Blend (all 9 variants)" if name == "equal_blend" else VARIANT_LABELS.get(name, name)


def portfolio_rows_html(eval_msg):
    rows = []
    for rank_pos, name in enumerate(eval_msg["ranked"], start=1):
        s = eval_msg["portfolio_stats"][name]
        css = ' class="best-row"' if rank_pos == 1 else ""
        rows.append(f"""
        <tr{css}>
          <td>{rank_pos}</td>
          <td>{html.escape(label(name))}</td>
          <td>{pct(s['annualized_return'])}</td>
          <td>{pct(s['annualized_volatility'])}</td>
          <td>{num(s['sharpe_ratio'])}</td>
          <td>{pct(s['max_drawdown'])}</td>
          <td>{num(s['calmar_ratio'])}</td>
          <td>{num(s['sortino_ratio'])}</td>
        </tr>""")
    return "".join(rows)


def stock_tables_html(eval_msg):
    sections = []
    for ticker in sorted(eval_msg["table"]):
        per_variant = eval_msg["table"][ticker]
        rows = []
        for variant in VARIANT_ORDER:
            s = per_variant.get(variant)
            if not s:
                continue
            rows.append(f"""
            <tr>
              <td>{html.escape(VARIANT_LABELS.get(variant, variant))}</td>
              <td>{pct(s['annualized_return'])}</td>
              <td>{pct(s['annualized_volatility'])}</td>
              <td>{num(s['sharpe_ratio'])}</td>
              <td>{pct(s['max_drawdown'])}</td>
              <td>{num(s['calmar_ratio'])}</td>
              <td>{num(s['sortino_ratio'])}</td>
            </tr>""")
        sections.append(f"""
        <h3>{html.escape(ticker)}</h3>
        <table>
          <thead>
            <tr><th>Strategy / Variant</th><th>Ann. Return</th><th>Ann. Volatility</th>
                <th>Sharpe</th><th>Max Drawdown</th><th>Calmar</th><th>Sortino</th></tr>
          </thead>
          <tbody>{"".join(rows)}</tbody>
        </table>""")
    return "".join(sections)


def build_html(history_msg, eval_msg):
    best_name = eval_msg["ranked"][0]
    best_stats = eval_msg["portfolio_stats"][best_name]
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n_days = len(next(iter(history_msg["history"].values())))
    date_range = f"{history_msg.get('start', '?')} to {history_msg.get('end', '?')}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Trend-Following Strategy Suite -- Backtest Report</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; max-width: 950px;
         margin: 40px auto; padding: 0 20px; color: #1a1a1a; line-height: 1.5; }}
  h1 {{ font-size: 26px; margin-bottom: 4px; }}
  .subtitle {{ color: #555; font-size: 15px; margin-top: 0; }}
  .banner {{ background: #eef6ff; border: 1px solid #a9cdEB; border-radius: 8px;
             padding: 14px 18px; margin: 20px 0; font-size: 14px; }}
  .banner strong {{ color: #205081; }}
  h2 {{ border-bottom: 2px solid #eee; padding-bottom: 6px; margin-top: 36px; }}
  h3 {{ margin-top: 24px; margin-bottom: 6px; color: #333; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px 0; font-size: 13.5px; }}
  th, td {{ border: 1px solid #ddd; padding: 7px 9px; text-align: right; }}
  th {{ background: #f5f5f5; text-align: right; }}
  td:first-child, th:first-child {{ text-align: left; }}
  tr.best-row {{ background: #e8f5e9; font-weight: 600; }}
  .summary-box {{ background: #f4f7fb; border-radius: 8px; padding: 16px 20px; }}
  .caveats {{ font-size: 13.5px; color: #444; }}
  .caveats li {{ margin-bottom: 8px; }}
  footer {{ margin-top: 40px; font-size: 12px; color: #999; }}
</style>
</head>
<body>

<h1>Trend-Following Strategy Suite &mdash; Backtest Report</h1>
<p class="subtitle">Moving-average crossover, Donchian channels, and the Turtle system &middot; real market data &middot; generated {run_date}</p>

<div class="banner">
  <strong>Real market data:</strong> this run uses real daily prices for
  {", ".join(history_msg["tickers"])} ({date_range}, {n_days} trading days),
  loaded from local CSV files. That's 5 stocks over about one year &mdash;
  a small sample, not the full SP100 or a multi-year history. Treat results
  as a pipeline demonstration and a first look, not a final strategy
  recommendation.
</div>

<h2>Executive Summary</h2>
<div class="summary-box">
  <p>Tickers tested: <strong>{", ".join(history_msg["tickers"])}</strong>
     &middot; Period: <strong>{date_range}</strong>
     ({n_days} trading days) &middot; Portfolio construction:
     <strong>inverse-volatility weighted</strong>, scaled to a
     <strong>10% annualized volatility</strong> target per strategy variant.</p>
  <p>Best-ranked strategy (by Sharpe ratio): <strong>{html.escape(label(best_name))}</strong>
     &mdash; annualized return {pct(best_stats['annualized_return'])},
     Sharpe ratio {num(best_stats['sharpe_ratio'])},
     max drawdown {pct(best_stats['max_drawdown'])}.</p>
</div>

<h2>Portfolio-Level Comparison (ranked best to worst)</h2>
<table>
  <thead>
    <tr>
      <th>Rank</th><th>Strategy / Variant</th><th>Ann. Return</th><th>Ann. Volatility</th>
      <th>Sharpe</th><th>Max Drawdown</th><th>Calmar</th><th>Sortino</th>
    </tr>
  </thead>
  <tbody>{portfolio_rows_html(eval_msg)}</tbody>
</table>

<h2>Per-Stock Detail (each strategy variant, each stock)</h2>
{stock_tables_html(eval_msg)}

<h2>Methodology &amp; Assumptions</h2>
<ul class="caveats">
  <li><strong>Three strategy families, nine variants total.</strong>
      <em>MAC</em> (dual exponentially-weighted-moving-average crossover,
      five speeds, Man AHL-style): long when the fast average is above the
      slow average, short otherwise. <em>Donchian channel</em> (two window
      lengths, 20 and 55 days): long on a breakout above the highest high of
      the prior window, short on a breakout below the lowest low, holding
      until the opposite breakout. <em>Turtle</em> (Richard Dennis's System 1
      and System 2): the same breakout entries as Donchian, plus
      volatility-scaled position sizing (via Average True Range), pyramiding
      up to 4 units as a winning trade extends, and a stop-loss at 2x ATR.</li>
  <li><strong>Parameter choices:</strong> MAC's five fast/slow day-pairs
      (2/8, 4/16, 8/32, 16/64, 32/128) are a standard doubling-ladder
      stand-in, not Man AHL's own undisclosed exact parameters. Donchian and
      Turtle use 20/55-day windows, the periods most associated with the
      original Turtle system.</li>
  <li><strong>Portfolio weighting:</strong> inverse-volatility (each stock's
      weight is proportional to 1/its own volatility, so every stock
      contributes roughly equal risk, not equal share count), then the whole
      portfolio is scaled to 10% annualized volatility per variant &mdash; so
      all nine variants are compared on equal footing.</li>
  <li><strong>"Equal Blend"</strong> now averages all nine variants across
      all three strategy families equally weighted, not five same-family
      speeds as in an earlier MAC-only version of this report &mdash; a
      cruder blend than averaging within one strategy family, included for
      reference rather than as a recommended combination.</li>
  <li><strong>Risk-free rate:</strong> Sharpe and related ratios assume a 0%
      risk-free rate, not a real T-bill rate.</li>
  <li><strong>No look-ahead bias:</strong> each day's trading signal (MAC's
      crossover state, a Donchian/Turtle breakout level or ATR) is decided
      using only prices known by that day's close, and only affects the
      following day's return.</li>
  <li><strong>Turtle simplifications:</strong> no "skip this breakout if the
      last trade in this direction was a winner" filter (a real but often
      omitted refinement); position sizing is a fraction of one
      strategy-level unit, not real share counts or dollar risk; no
      cross-instrument correlation or portfolio-heat cap (handled instead,
      approximately, by this report's own inverse-volatility portfolio
      weighting across strategies).</li>
  <li><strong>Sample size:</strong> only {len(history_msg["tickers"])} tickers
      and about one year of real data tested here (a first real-data run,
      not yet the full SP100 or a multi-year history); the same pipeline
      scales to more tickers and a longer window once more data is loaded.</li>
</ul>

<footer>Generated by DisSysLab's mac_speed_suite office (make_report.py) &middot; not investment advice.</footer>
</body>
</html>
"""


def main():
    history_msg, eval_msg = run_pipeline()
    out_path = os.path.join(os.path.dirname(__file__), "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build_html(history_msg, eval_msg))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
