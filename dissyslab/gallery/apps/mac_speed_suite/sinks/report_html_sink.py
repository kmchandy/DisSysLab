# dissyslab/gallery/apps/mac_speed_suite/sinks/report_html_sink.py

"""
ReportHtmlSink — the mac_speed_suite backtest report, as an office sink.

Why it lives here
-----------------

This is the single source of truth for `report.html`. It renders whatever
the EVALUATOR (or, later, the walk-forward COMPARATOR) actually emitted —
it does **not** re-run the pipeline or hardcode which strategies exist.
That is the whole point: `dsl run` and `report.html` can never again
disagree about the strategy list, because the report is built from the
same evaluation message the console prints. (The previous `make_report.py`
kept its own private copy of the pipeline with the three strategy families
hardcoded, so adding a strategy updated `dsl run` but not the report.)

Convention follows job_html_sink / periodic_brief_html_sink: an app-owned
renderer lives under the app's `sinks/` folder and registers a name in
SINK_REGISTRY (here, `report_html`).

Message it consumes
-------------------

The EVALUATOR's output message:

    {
        "type":     "mac_evaluation",
        "rank_by":  "sharpe_ratio",
        "n_days":   251,                       # added by the evaluator
        "table":    {ticker: {variant: stats}},
        "portfolio_stats": {variant: stats, "equal_blend": stats},
        "ranked":   [name, ...],               # best -> worst
    }

where `stats` has annualized_return, annualized_volatility, sharpe_ratio,
max_drawdown, calmar_ratio, sortino_ratio (any may be None).

The strategy list, labels, tickers, and day count are all derived from
this message — nothing about MAC/Donchian/Turtle is baked in here.

Example office.md
-----------------

::

    Sinks: console_printer, report_html(path="report.html")
    EVAL's out are console_printer and report_html.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_METRIC_COLUMNS = [
    ("annualized_return", "Ann. Return", "pct"),
    ("annualized_volatility", "Ann. Volatility", "pct"),
    ("sharpe_ratio", "Sharpe", "num"),
    ("max_drawdown", "Max Drawdown", "pct"),
    ("calmar_ratio", "Calmar", "num"),
    ("sortino_ratio", "Sortino", "num"),
]


class ReportHtmlSink:
    """Render the backtest evaluation message to a self-contained HTML file."""

    def __init__(self, path: str = "report.html", title: str = "Backtest Report"):
        self.path = Path(path)
        self.title = title
        self.count = 0

    # ── DisSysLab sink interface ──────────────────────────────────────

    def run(self, msg):
        if not isinstance(msg, dict):
            return
        self.count += 1
        self.path.write_text(self._build_html(msg), encoding="utf-8")

    def finalize(self):
        pass

    # ── Derivation (everything comes from the message) ────────────────

    @staticmethod
    def _portfolio_variants(msg: Dict[str, Any]) -> List[str]:
        """Portfolio-level candidates, best-first, from `ranked`."""
        ranked = list(msg.get("ranked") or [])
        stats = msg.get("portfolio_stats") or {}
        # Fall back to stats keys if ranked is absent.
        if not ranked:
            ranked = list(stats.keys())
        return [n for n in ranked if n in stats]

    @staticmethod
    def _per_stock_variants(msg: Dict[str, Any]) -> List[str]:
        """Strategy variants shown per stock, in ranked order where known."""
        table = msg.get("table") or {}
        seen: Dict[str, None] = {}
        for per_variant in table.values():
            for v in per_variant:
                seen.setdefault(v, None)
        ranked = [n for n in (msg.get("ranked") or []) if n in seen]
        # Any variant not in ranked (shouldn't happen) appended stably.
        tail = [v for v in seen if v not in ranked]
        return ranked + tail

    # ── Rendering ─────────────────────────────────────────────────────

    def _build_html(self, msg: Dict[str, Any]) -> str:
        table = msg.get("table") or {}
        portfolio_stats = msg.get("portfolio_stats") or {}
        rank_by = msg.get("rank_by", "sharpe_ratio")
        n_days = msg.get("n_days")
        tickers = sorted(table.keys())

        portfolio_variants = self._portfolio_variants(msg)
        per_stock_variants = self._per_stock_variants(msg)
        n_strategies = len([v for v in per_stock_variants])

        run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        best_name = portfolio_variants[0] if portfolio_variants else None
        best = portfolio_stats.get(best_name, {}) if best_name else {}

        sample_bits = [f"{len(tickers)} ticker(s)"]
        if n_days:
            sample_bits.append(f"{n_days} trading days")
        sample_bits.append(f"{n_strategies} strategy variant(s)")
        sample_line = " · ".join(sample_bits)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(self.title)}</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; max-width: 950px;
         margin: 40px auto; padding: 0 20px; color: #1a1a1a; line-height: 1.5; }}
  h1 {{ font-size: 26px; margin-bottom: 4px; }}
  .subtitle {{ color: #555; font-size: 15px; margin-top: 0; }}
  .banner {{ background: #eef6ff; border: 1px solid #a9cdeb; border-radius: 8px;
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

<h1>{html.escape(self.title)}</h1>
<p class="subtitle">Backtest of {n_strategies} strategy variant(s) on real daily price data &middot; generated {run_date}</p>

<div class="banner">
  <strong>Scope:</strong> {html.escape(sample_line)}
  for {html.escape(", ".join(tickers) if tickers else "no tickers")}.
  Treat results as a pipeline run and a first look, not a final strategy
  recommendation &mdash; a short window and a handful of tickers cannot separate
  a real edge from luck.
</div>

<h2>Executive Summary</h2>
<div class="summary-box">
  <p>Tickers: <strong>{html.escape(", ".join(tickers) if tickers else "n/a")}</strong>
     &middot; {html.escape(sample_line)}
     &middot; ranked by <strong>{html.escape(str(rank_by))}</strong>.</p>
  {self._summary_best(best_name, best, rank_by)}
</div>

<h2>Portfolio-Level Comparison (ranked best to worst)</h2>
{self._portfolio_table(portfolio_variants, portfolio_stats)}

<h2>Per-Stock Detail (each strategy variant, each stock)</h2>
{self._per_stock_tables(tickers, table, per_stock_variants)}

<h2>Methodology &amp; Assumptions</h2>
<ul class="caveats">
  <li><strong>No look-ahead:</strong> each day's signal is decided using only
      prices known by that day's close and applied to the next day's return.</li>
  <li><strong>Portfolio construction:</strong> inverse-volatility weighted across
      stocks, then scaled to a common annualized-volatility target, so variants
      are compared on equal footing.</li>
  <li><strong>Risk-free rate:</strong> Sharpe and related ratios assume 0%.</li>
  <li><strong>Sample size:</strong> {html.escape(sample_line)} &mdash; small; the
      same pipeline scales to more tickers and a longer window as more data is
      loaded.</li>
</ul>

<footer>Generated by DisSysLab's mac_speed_suite office (report_html sink) &middot; not investment advice.</footer>
</body>
</html>
"""

    # ── Rendering helpers ─────────────────────────────────────────────

    def _summary_best(self, name, stats, rank_by) -> str:
        if not name:
            return "<p>No portfolio candidates to rank.</p>"
        return (
            f'<p>Best-ranked (by {html.escape(str(rank_by))}): '
            f'<strong>{html.escape(_label(name))}</strong> &mdash; '
            f'annualized return {_pct(stats.get("annualized_return"))}, '
            f'Sharpe {_num(stats.get("sharpe_ratio"))}, '
            f'max drawdown {_pct(stats.get("max_drawdown"))}.</p>'
        )

    def _portfolio_table(self, variants, portfolio_stats) -> str:
        if not variants:
            return "<p>No portfolio-level results.</p>"
        head = "".join(f"<th>{html.escape(h)}</th>" for _, h, _ in _METRIC_COLUMNS)
        rows = []
        for rank_pos, name in enumerate(variants, start=1):
            s = portfolio_stats.get(name, {})
            css = ' class="best-row"' if rank_pos == 1 else ""
            cells = "".join(_cell(s.get(k), kind) for k, _, kind in _METRIC_COLUMNS)
            rows.append(
                f'<tr{css}><td>{rank_pos}</td>'
                f'<td>{html.escape(_label(name))}</td>{cells}</tr>'
            )
        return (
            "<table><thead><tr><th>Rank</th><th>Strategy / Variant</th>"
            f"{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
        )

    def _per_stock_tables(self, tickers, table, variant_order) -> str:
        if not tickers:
            return "<p>No per-stock results.</p>"
        head = "".join(f"<th>{html.escape(h)}</th>" for _, h, _ in _METRIC_COLUMNS)
        sections = []
        for ticker in tickers:
            per_variant = table.get(ticker, {})
            rows = []
            for variant in variant_order:
                s = per_variant.get(variant)
                if not s:
                    continue
                cells = "".join(_cell(s.get(k), kind) for k, _, kind in _METRIC_COLUMNS)
                rows.append(
                    f"<tr><td>{html.escape(_label(variant))}</td>{cells}</tr>"
                )
            sections.append(
                f"<h3>{html.escape(ticker)}</h3>"
                "<table><thead><tr><th>Strategy / Variant</th>"
                f"{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
            )
        return "".join(sections)


# ── Formatting helpers (module-level; no strategy knowledge) ───────────


def _pct(x: Optional[float], digits: int = 1) -> str:
    return f"{x * 100:+.{digits}f}%" if isinstance(x, (int, float)) else "n/a"


def _num(x: Optional[float], digits: int = 2) -> str:
    return f"{x:.{digits}f}" if isinstance(x, (int, float)) else "n/a"


def _cell(value: Any, kind: str) -> str:
    text = _pct(value) if kind == "pct" else _num(value)
    return f"<td>{text}</td>"


def _label(name: str) -> str:
    """Prettify a variant name for display, with no hardcoded family list.

    "mac_fast" -> "MAC · fast", "donchian_20" -> "DONCHIAN · 20",
    "equal_blend" -> "Equal blend". Purely derived from the name, so a new
    strategy family shows up correctly without editing this file.
    """
    if name == "equal_blend":
        return "Equal blend (all variants)"
    parts = str(name).split("_", 1)
    if len(parts) == 2:
        family, rest = parts
        return f"{family.upper()} · {rest.replace('_', ' ')}"
    return str(name)
