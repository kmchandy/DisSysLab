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
        cost_bps = msg.get("cost_bps")
        cost_note = (
            f" (assumed {cost_bps:.0f} bps per unit traded)"
            if isinstance(cost_bps, (int, float)) else ""
        )
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
  tr.no-trades td {{ color: #999; font-style: italic; }}
  .muted {{ color: #999; }}
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

{self._walk_forward_section(msg)}

<h2>Full-Window Comparison (whole history, in-sample)</h2>
{self._portfolio_table(portfolio_variants, portfolio_stats)}

{self._correlation_section(msg)}

<h2>Per-Stock Detail (each strategy variant, each stock)</h2>
{self._per_stock_tables(tickers, table, per_stock_variants)}

<h2>Methodology &amp; Assumptions</h2>
<ul class="caveats">
  <li><strong>No look-ahead:</strong> each day's signal is decided using only
      prices known by that day's close and applied to the next day's return.</li>
  <li><strong>Transaction costs:</strong> returns are net of a cost charged on
      every change of position{cost_note}.</li>
  <li><strong>Portfolio construction:</strong> inverse-volatility weighted across
      stocks, then scaled to a common annualized-volatility target, so variants
      are compared on equal footing.</li>
  <li><strong>Risk-free rate:</strong> Sharpe and related ratios assume 0%.</li>
  <li><strong>Trade activity:</strong> the <em>Days in mkt</em> and
      <em>Turnover</em> columns show how much each variant actually traded; a
      variant marked <em>no trades</em> never took a position, which is different
      from one that traded to a flat result.</li>
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
            cells, no_trades = _metric_cells_or_notrades(s)
            label = html.escape(_label(name)) + (
                ' <span class="muted">(no trades)</span>' if no_trades else "")
            css = (
                ' class="no-trades"' if no_trades
                else (' class="best-row"' if rank_pos == 1 else "")
            )
            rows.append(
                f'<tr{css}><td>{rank_pos}</td>'
                f'<td>{label}</td>{cells}{_turnover_cell(s)}</tr>'
            )
        return (
            "<table><thead><tr><th>Rank</th><th>Strategy / Variant</th>"
            f"{head}<th>Turnover</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
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
                cells, no_trades = _metric_cells_or_notrades(s)
                label = html.escape(_label(variant)) + (
                    ' <span class="muted">(no trades)</span>' if no_trades else "")
                css = ' class="no-trades"' if no_trades else ""
                rows.append(
                    f"<tr{css}><td>{label}</td>{cells}"
                    f"{_exposure_cell(s)}{_turnover_cell(s)}</tr>"
                )
            sections.append(
                f"<h3>{html.escape(ticker)}</h3>"
                "<table><thead><tr><th>Strategy / Variant</th>"
                f"{head}<th>Days in mkt</th><th>Turnover</th></tr>"
                f"</thead><tbody>{''.join(rows)}</tbody></table>"
            )
        return "".join(sections)

    def _correlation_section(self, msg: Dict[str, Any]) -> str:
        corr = msg.get("correlation") or {}
        names = corr.get("variants") or []
        matrix = corr.get("matrix") or {}
        if len(names) < 2:
            return ""
        head = "".join(f"<th>{html.escape(_label(n))}</th>" for n in names)
        rows = []
        for a in names:
            cells = "".join(_corr_cell(matrix.get(a, {}).get(b)) for b in names)
            rows.append(f"<tr><td>{html.escape(_label(a))}</td>{cells}</tr>")
        return (
            "<h2>Strategy Correlation &mdash; are these the same bet?</h2>"
            "<p>Correlation of each variant's portfolio return series. Values near "
            "<strong>+1</strong> (shaded red) mean two variants move together and "
            "are effectively one bet; low or negative values (green) mean they "
            "diversify each other.</p>"
            f"<table><thead><tr><th></th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    def _walk_forward_section(self, msg: Dict[str, Any]) -> str:
        wf = msg.get("walk_forward") or {}
        ranked = wf.get("ranked_by_oos") or []
        per = wf.get("per_variant") or {}
        if not ranked:
            return ""
        n_folds = wf.get("n_folds")
        rows = []
        for pos, v in enumerate(ranked, start=1):
            d = per.get(v, {})
            css = ' class="best-row"' if pos == 1 else ""
            rows.append(
                f'<tr{css}><td>{pos}</td><td>{html.escape(_label(v))}</td>'
                f'<td>{_num(d.get("oos_sharpe"))}</td>'
                f'<td>{_num(d.get("is_sharpe"))}</td>'
                f'<td>{_pct(d.get("oos_return"))}</td>'
                f'<td>{_pct(d.get("is_return"))}</td></tr>'
            )
        return (
            "<h2>Walk-Forward (out-of-sample) validation</h2>"
            f"<p>Each variant ranked over {n_folds} expanding train/test fold(s): "
            "ranked on an earlier window, then measured on a later window it had no "
            "part in choosing. <strong>Out-of-sample</strong> is the number to "
            "trust &mdash; a variant whose out-of-sample Sharpe falls well short of "
            "its in-sample Sharpe was likely overfit. The full-window tables below "
            "are in-sample (the whole history), shown for detail.</p>"
            "<table><thead><tr><th>Rank</th><th>Strategy / Variant</th>"
            "<th>OOS Sharpe</th><th>In-sample Sharpe</th>"
            "<th>OOS Return</th><th>In-sample Return</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )


# ── Formatting helpers (module-level; no strategy knowledge) ───────────


def _metric_cells_or_notrades(stats: Dict[str, Any]):
    """Return (cells_html, no_trades).

    When a variant never took a position (days_in_market == 0), the metric
    columns become muted dashes, so a never-entered variant is visibly
    distinct from one that traded to a flat result (item 3)."""
    if stats.get("days_in_market") == 0:
        return "".join('<td class="muted">&mdash;</td>' for _ in _METRIC_COLUMNS), True
    return "".join(_cell(stats.get(k), kind) for k, _, kind in _METRIC_COLUMNS), False


def _exposure_cell(stats: Dict[str, Any]) -> str:
    dim = stats.get("days_in_market")
    n_days = stats.get("n_days")
    if dim is None:
        return '<td class="muted">n/a</td>'
    return f"<td>{dim} / {n_days}</td>" if n_days else f"<td>{dim}</td>"


def _turnover_cell(stats: Dict[str, Any]) -> str:
    to = stats.get("turnover")
    if not isinstance(to, (int, float)):
        return '<td class="muted">n/a</td>'
    return f"<td>{_num(to, 1)}</td>"


def _pct(x: Optional[float], digits: int = 1) -> str:
    return f"{x * 100:+.{digits}f}%" if isinstance(x, (int, float)) else "n/a"


def _num(x: Optional[float], digits: int = 2) -> str:
    return f"{x:.{digits}f}" if isinstance(x, (int, float)) else "n/a"


def _cell(value: Any, kind: str) -> str:
    text = _pct(value) if kind == "pct" else _num(value)
    return f"<td>{text}</td>"


def _corr_cell(v: Any) -> str:
    """One correlation cell, shaded so a strongly-correlated pair (the
    'same bet' warning) stands out and a diversifying pair reads calm."""
    if not isinstance(v, (int, float)):
        return '<td class="muted">n/a</td>'
    if v >= 0.8:
        bg = "#f8d7da"
    elif v >= 0.5:
        bg = "#fff3cd"
    elif v <= -0.3:
        bg = "#d1e7dd"
    else:
        bg = ""
    style = f' style="background:{bg}"' if bg else ""
    return f'<td{style}>{v:+.2f}</td>'


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
