"""
brief.py -- render a day's brief (the "what do I hold / what did I do today"
output) as concise text or a small HTML page. Pure Python.

Input is a brief dict as produced by day_runner.run_day:
  {trade_date, committed, healed, holdings{ticker:{shares,avg_cost,price}},
   orders[], fills[], skipped[], decisions{ticker:{...,reason,order,signal}},
   equity{cash,positions_value,total,cum_pnl}, receipt}

The trader role writes render_html() to book/brief.html and prints render_text().
This is deliberately state-focused (holdings + today's actions), not statistics --
the backtester answers "is the strategy good?"; the brief answers "what do I hold,
and what changed today?"
"""

from __future__ import annotations

import html
from typing import Any, Dict, List


def _money(x) -> str:
    return f"${x:,.0f}" if isinstance(x, (int, float)) else "n/a"


def _signed(x) -> str:
    return f"{x:+,.0f}" if isinstance(x, (int, float)) else "n/a"


def _actions(brief: Dict[str, Any]) -> List[str]:
    """Human phrases for what happened per ticker, from the decision trace."""
    out = []
    for t, d in sorted((brief.get("decisions") or {}).items()):
        order = d.get("order")
        if order:
            out.append(f"{order['side'].upper()} {order['qty']:.0f} {t} ({d.get('reason','')})")
    return out


def render_text(brief: Dict[str, Any]) -> str:
    if not brief.get("committed"):
        return (f"[{brief.get('trade_date')}] no action "
                f"({brief.get('reason', 'nothing to do')}).")
    eq = brief.get("equity") or {}
    lines = [f"Paper trade — {brief.get('trade_date')}   "
             f"equity {_money(eq.get('total'))}  (cum P&L {_signed(eq.get('cum_pnl'))})"]
    hold = brief.get("holdings") or {}
    if hold:
        parts = []
        for t, h in sorted(hold.items()):
            mv = (h.get("shares") or 0) * (h.get("price") or 0)
            parts.append(f"{t} {h['shares']:.0f} @ {h.get('avg_cost',0):.2f} ({_money(mv)})")
        lines.append("Holdings: " + "; ".join(parts))
    else:
        lines.append("Holdings: (flat / all cash)")
    acts = _actions(brief)
    lines.append("Today: " + ("; ".join(acts) if acts else "no trades"))
    skipped = brief.get("skipped") or []
    if skipped:
        lines.append("Skipped: " + ", ".join(f"{s['ticker']} ({s.get('reason','')})"
                                              for s in skipped))
    if brief.get("healed"):
        lines.append("NOTE: book snapshot was healed from the ledger on load.")
    return "\n".join(lines)


def render_html(brief: Dict[str, Any]) -> str:
    date = html.escape(str(brief.get("trade_date")))
    eq = brief.get("equity") or {}
    rows_hold = ""
    for t, h in sorted((brief.get("holdings") or {}).items()):
        price = h.get("price")
        mv = (h.get("shares") or 0) * (price or 0)
        rows_hold += (f"<tr><td>{html.escape(t)}</td><td>{h['shares']:.0f}</td>"
                      f"<td>{h.get('avg_cost',0):.2f}</td>"
                      f"<td>{price if price is not None else 'n/a'}</td>"
                      f"<td>{_money(mv)}</td></tr>")
    rows_act = ""
    for t, d in sorted((brief.get("decisions") or {}).items()):
        o = d.get("order")
        act = (f"{o['side'].upper()} {o['qty']:.0f}" if o else "—")
        rows_act += (f"<tr><td>{html.escape(t)}</td><td>{d.get('signal',0)}</td>"
                     f"<td>{act}</td><td>{html.escape(str(d.get('reason','')))}</td></tr>")
    heal = ("<p class='warn'>Book snapshot was healed from the ledger on load.</p>"
            if brief.get("healed") else "")
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Paper trade — {date}</title><style>
 body{{font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:820px;margin:40px auto;padding:0 20px;color:#1a1a1a}}
 h1{{font-size:22px;margin-bottom:2px}} .sub{{color:#555;margin-top:0}}
 table{{border-collapse:collapse;width:100%;margin:10px 0 22px;font-size:14px}}
 th,td{{border:1px solid #ddd;padding:6px 9px;text-align:right}} th{{background:#f5f5f5}}
 td:first-child,th:first-child{{text-align:left}} .warn{{color:#a15c00}}
</style></head><body>
<h1>Paper trade — {date}</h1>
<p class="sub">Equity {_money(eq.get('total'))} &middot; cash {_money(eq.get('cash'))} &middot; cumulative P&amp;L {_signed(eq.get('cum_pnl'))} &middot; <em>simulated (paper) — not investment advice</em></p>
{heal}
<h2>Holdings</h2>
<table><thead><tr><th>Ticker</th><th>Shares</th><th>Avg cost</th><th>Price</th><th>Mkt value</th></tr></thead>
<tbody>{rows_hold or '<tr><td colspan=5>flat / all cash</td></tr>'}</tbody></table>
<h2>Today's decisions</h2>
<table><thead><tr><th>Ticker</th><th>Signal</th><th>Order</th><th>Why</th></tr></thead>
<tbody>{rows_act or '<tr><td colspan=4>no names</td></tr>'}</tbody></table>
</body></html>"""
