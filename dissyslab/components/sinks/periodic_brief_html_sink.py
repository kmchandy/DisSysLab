# dissyslab/components/sinks/periodic_brief_html_sink.py

"""
PeriodicBriefHtmlSink — write a Pat-grade HTML brief assembled from
multiple sources.

A drop-in replacement for ``periodic_brief_sink`` whose output is a
self-contained single-page HTML file (inline CSS, no JavaScript)
rather than markdown. Pat opens ``brief.html`` in any browser; the
file emails cleanly, drags into Notion, prints to a single-page
PDF, and renders identically across devices.

Routing
=======

Each incoming message is sorted into one of five buckets based on
the ``source`` or ``type`` field of the message:

- ``"weather"`` (in ``type``) → Weather (one-of, latest wins).
- ``"stocks"`` (in ``type``) → Markets (keyed by ticker, latest wins).
- ``"calendar"`` (in ``source``) → Schedule.
- ``"gmail"`` (in ``source``) → Email worth knowing about.
- Anything else (RSS feed names like ``"bbc_world"``,
  ``"npr_news"``, ``"al_jazeera"``, …) → News.

Messages with no recognised ``source`` or ``type`` are silently
dropped rather than mis-categorised.

Output sections
===============

In order: a hero banner at the top with today's date and at-a-glance
stats, then one card per non-empty bucket — Schedule, Weather,
Markets, News, Email — each styled as a clean white card on a soft
gray background. Sections only render when their bucket has content.

The sink rewrites the file on every incoming message so Pat can
keep the page open and have it reflect the office's progress as
agents work.

Customisation
=============

The ``accent_color`` constructor argument changes the single CSS
variable that controls links, badges, and the hero gradient. Pat
picks her own brand color in one place. Defaults to a calm
slate-blue.

A ``<meta http-equiv="refresh" content="60">`` reload tag is
included by default so an open browser tab auto-refreshes as the
brief updates. Pat can disable this with ``auto_refresh=False``.

Used in office.md as
``Sinks: periodic_brief_html_sink(path="brief.html")``.
"""

from __future__ import annotations

import html
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Module-level template helpers ─────────────────────────────────────


_DEFAULT_ACCENT = "#3b82f6"   # calm slate-blue


def _esc(value: Any) -> str:
    """HTML-escape a value, coercing to string. None → empty string."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _badge(label: str, kind: str = "default") -> str:
    """Render a small pill-shaped badge."""
    return f'<span class="badge badge-{_esc(kind)}">{_esc(label)}</span>'


def _short_url(url: str, max_len: int = 60) -> str:
    """Truncate a URL for display."""
    if not url:
        return ""
    if len(url) <= max_len:
        return url
    return url[: max_len - 1] + "…"


# ── The sink class ────────────────────────────────────────────────────


class PeriodicBriefHtmlSink:
    """Multi-source sink that assembles a periodic morning briefing as HTML."""

    def __init__(
        self,
        path: str = "brief.html",
        *,
        name: Optional[str] = None,
        title: Optional[str] = None,
        accent_color: str = _DEFAULT_ACCENT,
        auto_refresh: bool = True,
    ):
        self.path = Path(os.path.expanduser(path)).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._title = title or f"Brief — {datetime.now().strftime('%A, %B %-d, %Y')}"
        self._name = name or "periodic_brief_html_sink"
        self._accent = accent_color
        self._auto_refresh = auto_refresh

        # Per-bucket accumulators
        self._schedule: List[dict] = []
        self._weather: Optional[dict] = None
        self._markets: Dict[str, dict] = {}     # by ticker, latest wins
        self._news: List[dict] = []
        self._email: List[dict] = []

        # Write an empty shell so a fresh file exists from t=0.
        self._rewrite()

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Any) -> Any:
        """Route one message into its bucket; rewrite the brief."""
        if not isinstance(msg, dict):
            return msg
        category = self._categorise(msg)
        if category == "schedule":
            self._schedule.append(msg)
        elif category == "weather":
            self._weather = msg
        elif category == "markets":
            ticker = msg.get("ticker", "?")
            self._markets[ticker] = msg
        elif category == "email":
            self._email.append(msg)
        elif category == "news":
            self._news.append(msg)
        self._rewrite()
        return msg

    # The framework's Sink wrapper calls .run(msg).
    run = __call__

    # ── Categorisation ───────────────────────────────────────────────

    @staticmethod
    def _categorise(msg: Dict[str, Any]) -> Optional[str]:
        """Return one of {schedule, weather, markets, email, news, None}."""
        type_field = msg.get("type") or ""
        source_field = msg.get("source") or ""
        type_lower = type_field.lower() if isinstance(type_field, str) else ""
        src_lower = source_field.lower() if isinstance(source_field, str) else ""

        if type_lower == "weather" or "weather" in src_lower:
            return "weather"
        if type_lower == "stocks" or src_lower == "stocks":
            return "markets"
        if "calendar" in src_lower:
            return "schedule"
        if "gmail" in src_lower or src_lower == "email":
            return "email"
        if src_lower:
            return "news"
        return None

    # ── Rendering ────────────────────────────────────────────────────

    def _rewrite(self) -> None:
        """Re-render the entire brief to disk."""
        self.path.write_text(self._render(), encoding="utf-8")

    def _render(self) -> str:
        """Build the full HTML document."""
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
            + (
                '  <meta http-equiv="refresh" content="60">\n'
                if self._auto_refresh
                else ""
            )
            + f"  <title>{_esc(self._title)}</title>\n"
            f"  <style>{self._css()}</style>\n"
            "</head>\n"
            "<body>\n"
            f"  <main class=\"container\">\n"
            f"    {self._render_hero()}\n"
            f"    {self._render_schedule()}\n"
            f"    {self._render_weather()}\n"
            f"    {self._render_markets()}\n"
            f"    {self._render_email()}\n"
            f"    {self._render_news()}\n"
            f"    {self._render_footer()}\n"
            "  </main>\n"
            "</body>\n"
            "</html>\n"
        )

    def _css(self) -> str:
        """Inline CSS — single source of truth for all styling."""
        return f"""
:root {{
  --accent:           {self._accent};
  --accent-soft:      {self._accent}1a;
  --bg:               #fafafa;
  --card-bg:          #ffffff;
  --border:           #e5e7eb;
  --text:             #111827;
  --text-soft:        #6b7280;
  --text-faint:       #9ca3af;
  --good:             #10b981;
  --bad:              #ef4444;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: var(--bg); }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Oxygen, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
  color: var(--text);
  line-height: 1.5;
  font-size: 15px;
}}
.container {{
  max-width: 760px;
  margin: 0 auto;
  padding: 32px 24px 48px 24px;
}}
.hero {{
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  color: white;
  padding: 28px 32px;
  border-radius: 16px;
  margin-bottom: 24px;
}}
.hero h1 {{
  margin: 0 0 4px 0;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.01em;
}}
.hero .hero-stats {{
  margin-top: 12px;
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  font-size: 14px;
  opacity: 0.95;
}}
.hero .hero-stat {{
  display: flex;
  flex-direction: column;
}}
.hero .hero-stat-label {{
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.85;
}}
.hero .hero-stat-value {{
  font-size: 18px;
  font-weight: 600;
}}
.card {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
}}
.card h2 {{
  margin: 0 0 14px 0;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-soft);
}}
.item {{
  padding: 10px 0;
  border-top: 1px solid var(--border);
}}
.item:first-of-type {{ border-top: none; padding-top: 0; }}
.item-title {{
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: var(--text);
}}
.item-title a {{ color: var(--text); text-decoration: none; }}
.item-title a:hover {{ color: var(--accent); text-decoration: underline; }}
.item-meta {{
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-soft);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}}
.badge {{
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
  letter-spacing: 0.02em;
}}
.badge-default {{ background: #f3f4f6; color: var(--text-soft); }}
.badge-source  {{ background: var(--accent-soft); color: var(--accent); }}
.badge-urgent  {{ background: #fef2f2; color: var(--bad); }}
.badge-low     {{ background: #f0fdf4; color: var(--good); }}
.badge-topic   {{ background: #f5f3ff; color: #7c3aed; }}
.market-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-top: 1px solid var(--border);
}}
.market-row:first-of-type {{ border-top: none; padding-top: 0; }}
.market-ticker {{
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.02em;
}}
.market-price {{
  font-size: 15px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}}
.market-change {{
  margin-left: 12px;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}}
.market-up   {{ color: var(--good); }}
.market-down {{ color: var(--bad);  }}
.empty {{
  color: var(--text-faint);
  font-style: italic;
  margin: 0;
}}
.footer {{
  margin-top: 32px;
  color: var(--text-faint);
  font-size: 12px;
  text-align: center;
}}
@media print {{
  body {{ background: white; }}
  .container {{ padding: 0; max-width: 100%; }}
  .hero {{
    background: white !important;
    color: var(--text) !important;
    border: 1px solid var(--border);
    border-radius: 0;
  }}
  .card {{ break-inside: avoid; border-radius: 0; }}
  meta[http-equiv="refresh"] {{ display: none; }}
}}
"""

    # ── Section renderers ────────────────────────────────────────────

    def _render_hero(self) -> str:
        date_str = datetime.now().strftime("%A, %B %-d, %Y")
        stats: List[str] = []

        if self._weather is not None:
            temp = self._weather.get("temp_f") or self._weather.get("temp_c")
            cond = self._weather.get("conditions") or self._weather.get("title", "")
            if temp is not None:
                unit = "°F" if self._weather.get("temp_f") is not None else "°C"
                stats.append(self._hero_stat("Now", f"{temp}{unit}"))
            elif cond:
                # Strip leading "City — " bits from a title-style weather msg
                stats.append(self._hero_stat("Now", cond[:40]))

        if self._schedule:
            stats.append(
                self._hero_stat("Today",
                                f"{len(self._schedule)} event"
                                + ("" if len(self._schedule) == 1 else "s"))
            )

        if self._email:
            stats.append(
                self._hero_stat("Email",
                                f"{len(self._email)} item"
                                + ("" if len(self._email) == 1 else "s"))
            )

        if self._news:
            stats.append(
                self._hero_stat("News",
                                f"{len(self._news)} brief"
                                + ("" if len(self._news) == 1 else "s"))
            )

        stats_html = (
            f'<div class="hero-stats">{"".join(stats)}</div>'
            if stats else ""
        )
        return (
            '<section class="hero">'
            f"<h1>{_esc(date_str)}</h1>"
            f"{stats_html}"
            "</section>"
        )

    @staticmethod
    def _hero_stat(label: str, value: str) -> str:
        return (
            '<div class="hero-stat">'
            f'<span class="hero-stat-label">{_esc(label)}</span>'
            f'<span class="hero-stat-value">{_esc(value)}</span>'
            "</div>"
        )

    def _render_schedule(self) -> str:
        if not self._schedule:
            return ""
        rows = []
        for item in self._schedule:
            title = _esc(item.get("title") or "(untitled event)")
            ts = _esc(item.get("timestamp", ""))
            meta = f'<div class="item-meta">{ts}</div>' if ts else ""
            rows.append(
                f'<div class="item"><p class="item-title">{title}</p>{meta}</div>'
            )
        return self._card("Schedule", "".join(rows))

    def _render_weather(self) -> str:
        if self._weather is None:
            return ""
        w = self._weather
        title = w.get("title")
        if title:
            body = f'<p class="item-title">{_esc(title)}</p>'
        else:
            city = w.get("city", "")
            cond = w.get("conditions", "")
            parts = [p for p in (cond, city) if p]
            body = f'<p class="item-title">{_esc(", ".join(parts) or "(weather data received)")}</p>'
        meta = []
        if w.get("temp_f") is not None and w.get("temp_c") is not None:
            meta.append(f'{_esc(w["temp_f"])}°F / {_esc(w["temp_c"])}°C')
        if w.get("wind_kmh") is not None:
            meta.append(f'wind {_esc(w["wind_kmh"])} km/h')
        meta_html = (
            f'<div class="item-meta">{" · ".join(meta)}</div>'
            if meta else ""
        )
        return self._card("Weather", f'<div class="item">{body}{meta_html}</div>')

    def _render_markets(self) -> str:
        if not self._markets:
            return ""
        rows = []
        for ticker in sorted(self._markets):
            m = self._markets[ticker]
            price = m.get("price")
            change = m.get("change")
            change_pct = m.get("change_pct")
            up = isinstance(change, (int, float)) and change >= 0
            direction_class = "market-up" if up else "market-down"
            arrow = "▲" if up else "▼"
            price_str = f"{price:,.2f}" if isinstance(price, (int, float)) else _esc(price)
            change_str = ""
            if isinstance(change, (int, float)) and isinstance(change_pct, (int, float)):
                sign = "+" if up else ""
                change_str = (
                    f' <span class="market-change {direction_class}">'
                    f'{arrow} {sign}{change:,.2f} ({sign}{change_pct:.2f}%)'
                    "</span>"
                )
            rows.append(
                '<div class="market-row">'
                f'<span class="market-ticker">{_esc(ticker)}</span>'
                f'<span><span class="market-price">{price_str}</span>{change_str}</span>'
                "</div>"
            )
        return self._card("Markets", "".join(rows))

    def _render_email(self) -> str:
        if not self._email:
            return ""
        rows = []
        for item in self._email:
            headline = _esc(item.get("headline") or item.get("title") or "(no subject)")
            url = item.get("url", "")
            if url:
                title_html = f'<a href="{_esc(url)}">{headline}</a>'
            else:
                title_html = headline
            rows.append(
                f'<div class="item"><p class="item-title">{title_html}</p></div>'
            )
        return self._card("Email worth knowing about", "".join(rows))

    def _render_news(self) -> str:
        if not self._news:
            return ""
        rows = []
        for item in self._news:
            headline = (
                item.get("brief")
                or item.get("summary")
                or item.get("headline")
                or item.get("title")
                or "(untitled)"
            )
            # For long brief/summary outputs, fall back to title for display.
            if len(headline) > 240 and item.get("title"):
                headline = item["title"]
            url = item.get("url", "")
            if url:
                title_html = f'<a href="{_esc(url)}">{_esc(headline)}</a>'
            else:
                title_html = _esc(headline)

            badges: List[str] = []
            src = item.get("source")
            if src:
                badges.append(_badge(src, "source"))
            urgency = item.get("urgency")
            severity = item.get("severity")
            if isinstance(urgency, str) and urgency.upper() == "HIGH":
                badges.append(_badge("urgent", "urgent"))
            elif isinstance(severity, str) and severity.upper() in {"CRITICAL", "HIGH"}:
                badges.append(_badge(severity.lower(), "urgent"))
            topic = item.get("topic")
            if isinstance(topic, str) and topic:
                badges.append(_badge(topic, "topic"))
            meta_html = (
                f'<div class="item-meta">{"".join(badges)}</div>'
                if badges else ""
            )

            rows.append(
                f'<div class="item"><p class="item-title">{title_html}</p>{meta_html}</div>'
            )
        return self._card("News", "".join(rows))

    def _render_footer(self) -> str:
        now = datetime.now().strftime("%-I:%M %p")
        return (
            f'<p class="footer">Brief refreshed at {_esc(now)} · '
            "generated by DisSysLab</p>"
        )

    @staticmethod
    def _card(title: str, body: str) -> str:
        return f'<section class="card"><h2>{_esc(title)}</h2>{body}</section>'

    def finalize(self) -> None:
        """Final flush. Idempotent; safe to call at office shutdown."""
        self._rewrite()
