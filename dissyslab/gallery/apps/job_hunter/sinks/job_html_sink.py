# dissyslab/gallery/apps/job_hunter/sinks/job_html_sink.py

"""
JobHtmlSink — live-refresh HTML report for the job_hunter office.

Why it lives here
-----------------

The sink hardcodes the matcher schema (title / company / location /
salary / match_rating / resume_matches / skills_match / gaps /
application_link) and the visual language of a job-match card. That
knowledge belongs to job_hunter, not to the framework's
``components/sinks/`` folder. Convention follows periodic_brief: any
sink whose schema/layout is owned by one gallery app ships under that
app's ``sinks/`` folder and registers a name in SINK_REGISTRY.

Behaviour
---------

* On every incoming match record, rebuild ``matched_jobs.html`` in
  the working directory from scratch using the accumulated buffer.
* Records are displayed newest-first, capped at ``max_items`` (default
  50) so the page stays light.
* The page is self-contained: inline CSS, no external assets. It is
  safe to open from disk and works offline.
* If a record only carries the bullet-formatted ``text`` field
  (older / fallback matcher output), the sink still renders a card
  with that body as a preformatted block — better than empty.

Example office.md
-----------------

::

    Sinks: job_html_sink(path="matched_jobs.html", max_items=50)
    Morgan's matched_jobs is job_html_sink.
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dissyslab.components.sinks.message_coerce import coerce_sink_message


# Colour palette per match-rating badge. Anchors the visual hierarchy
# of the page: EXCELLENT pops, FAIR sits quietly.
_RATING_COLOR = {
    "EXCELLENT": ("#0b6e3a", "#d6f5e3"),
    "STRONG":    ("#0a5fa6", "#dceeff"),
    "GOOD":      ("#8a6a0d", "#fff4d1"),
    "FAIR":      ("#7a3939", "#fde2e2"),
}
_RATING_DEFAULT = ("#3a3a3a", "#ececec")


class JobHtmlSink:
    """Append-and-rerender HTML report for matched job postings."""

    def __init__(
        self,
        path: str = "matched_jobs.html",
        max_items: int = 50,
        title: str = "Job Matches",
    ):
        self.path = Path(path)
        self.max_items = max_items
        self.title = title
        self.items: List[Dict[str, Any]] = []
        self.count = 0
        # Write an initial empty page so the user can open the file
        # immediately and watch matches appear as the office runs.
        self._rerender()

    # ── DisSysLab sink interface ──────────────────────────────────────

    def run(self, msg):
        msg = coerce_sink_message(msg)
        # Normalise: if the matcher emitted a JSON string under text,
        # try to recover the structured fields.
        msg = _try_unwrap_json_text(msg)
        self.items.insert(0, msg)
        if len(self.items) > self.max_items:
            self.items = self.items[: self.max_items]
        self.count += 1
        self._rerender()

    def finalize(self):
        self._rerender()

    # ── Rendering ─────────────────────────────────────────────────────

    def _rerender(self) -> None:
        body = "\n".join(self._render_card(it) for it in self.items)
        if not body:
            body = (
                '<div class="empty">No matches yet — the office is still '
                "screening incoming postings.</div>"
            )
        page = _HTML_SHELL.format(
            title=html.escape(self.title),
            updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            count=self.count,
            cards=body,
        )
        self.path.write_text(page, encoding="utf-8")

    def _render_card(self, item: Dict[str, Any]) -> str:
        title   = _field(item, "title")
        company = _field(item, "company")
        loc     = _field(item, "location")
        salary  = _field(item, "salary")
        rating  = str(item.get("match_rating", "")).upper().strip() or "FAIR"
        text    = (item.get("text") or "").strip()
        reason  = (item.get("reason") or "").strip()
        apply_url = (item.get("application_link") or item.get("url") or "").strip()

        matches = item.get("resume_matches") or []
        skills  = item.get("skills_match") or []
        gaps    = item.get("gaps") or []

        # Older / fallback matcher output: only `text` is present.
        # Parse the bullet block lazily to fill in the cards.
        if isinstance(matches, str):
            matches = [matches]
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        if isinstance(gaps, str):
            gaps = [g.strip() for g in gaps.split(",") if g.strip()]

        if not matches and text:
            matches = _parse_bullet_section(text, "Resume Matches")
        if not skills and text:
            skills = _parse_bullet_section(text, "Skills Match", as_csv=True)
        if not gaps and text:
            gaps = _parse_bullet_section(text, "Gaps", as_csv=True)

        # If even title/company are missing, try to recover from text.
        if not title or title == "Not specified":
            title = _parse_inline_field(text, "Title") or title
        if not company or company == "Not specified":
            company = _parse_inline_field(text, "Company") or company

        fg, bg = _RATING_COLOR.get(rating, _RATING_DEFAULT)

        matches_html = (
            "".join(f"<li>{html.escape(str(m))}</li>" for m in matches)
            if matches else "<li class='muted'>No specific matches recorded.</li>"
        )
        skills_html = (
            ", ".join(html.escape(str(s)) for s in skills)
            if skills else "<span class='muted'>None recorded.</span>"
        )
        gaps_html = (
            ", ".join(html.escape(str(g)) for g in gaps)
            if gaps else "<span class='muted'>None recorded.</span>"
        )

        apply_html = (
            f'<a class="apply" href="{html.escape(apply_url)}" target="_blank">'
            f'Apply &rarr;</a>'
            if apply_url and apply_url != "Not specified" else ""
        )

        reason_html = (
            f'<p class="reason">{html.escape(reason)}</p>' if reason else ""
        )

        return f"""
<article class="card">
  <header class="card-header">
    <span class="badge" style="color:{fg};background:{bg};">{html.escape(rating)}</span>
    <h2>{html.escape(title or 'Untitled posting')}</h2>
  </header>
  <div class="meta">
    <span><strong>Company:</strong> {html.escape(company or 'Not specified')}</span>
    <span><strong>Location:</strong> {html.escape(loc or 'Not specified')}</span>
    <span><strong>Salary:</strong> {html.escape(salary or 'Not specified')}</span>
  </div>
  {reason_html}
  <section>
    <h3>Resume matches</h3>
    <ul>{matches_html}</ul>
  </section>
  <section class="row">
    <div><h3>Skills match</h3><p>{skills_html}</p></div>
    <div><h3>Gaps</h3><p>{gaps_html}</p></div>
  </section>
  {apply_html}
</article>
""".strip()


# ── Helpers ───────────────────────────────────────────────────────────


def _field(item: Dict[str, Any], key: str) -> str:
    v = item.get(key, "")
    if v is None:
        return ""
    return str(v).strip()


def _try_unwrap_json_text(msg: Dict[str, Any]) -> Dict[str, Any]:
    """If ``msg['text']`` is itself JSON (small models occasionally
    wrap their entire output in a JSON string), parse it and merge.

    Defensive — when parsing fails we leave the message alone."""
    text = msg.get("text")
    if not isinstance(text, str):
        return msg
    stripped = text.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return msg
    try:
        inner = json.loads(stripped)
        if isinstance(inner, dict):
            merged = dict(msg)
            merged.update(inner)
            return merged
    except json.JSONDecodeError:
        pass
    return msg


def _parse_bullet_section(text: str, header: str, as_csv: bool = False) -> List[str]:
    """Pull a section out of bullet-formatted text.

    For ``Resume Matches:`` we return the bullet lines that follow.
    For ``Skills Match:`` we return the comma-separated tail.
    """
    lines = text.splitlines()
    out: List[str] = []
    in_section = False
    for ln in lines:
        stripped = ln.strip()
        head = stripped.lstrip("•:* ").strip()
        if head.lower().startswith(header.lower()):
            in_section = True
            tail = head[len(header):].lstrip(":").strip()
            if as_csv:
                if tail and tail.lower() != "none":
                    return [p.strip() for p in tail.split(",") if p.strip()]
                return []
            continue
        if in_section:
            if not stripped:
                break
            if stripped.lstrip("•:* ").lower().startswith(
                ("skills match", "gaps:", "apply", "resume matches")
            ) and stripped.lstrip("•:* ").lower() != header.lower() + ":":
                break
            out.append(stripped.lstrip("•:* ").strip())
    return out


def _parse_inline_field(text: str, label: str) -> Optional[str]:
    """Recover ``Label: value`` from a bullet block."""
    for ln in text.splitlines():
        stripped = ln.lstrip("•:* ").strip()
        if stripped.lower().startswith(label.lower() + ":"):
            return stripped.split(":", 1)[1].strip()
    return None


# ── HTML shell ────────────────────────────────────────────────────────

_HTML_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  :root {{
    --bg: #f7f7f6;
    --panel: #ffffff;
    --ink: #1a1a1a;
    --muted: #6b6b6b;
    --line: #e4e4e2;
    --accent: #2563eb;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0;
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI",
          Roboto, Helvetica, Arial, sans-serif;
    color: var(--ink); background: var(--bg);
  }}
  header.hero {{
    padding: 28px 40px 18px;
    border-bottom: 1px solid var(--line);
    background: linear-gradient(180deg, #ffffff 0%, #f1f1ef 100%);
  }}
  header.hero h1 {{ margin: 0 0 4px; font-size: 22px; }}
  header.hero .sub {{ color: var(--muted); font-size: 13px; }}
  main {{ max-width: 880px; margin: 0 auto; padding: 22px 24px 60px; }}
  .empty {{
    color: var(--muted); padding: 30px 0; text-align: center;
    font-style: italic;
  }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 18px 20px;
    margin: 0 0 18px;
    box-shadow: 0 1px 1px rgba(0,0,0,0.025);
  }}
  .card-header {{
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 8px;
  }}
  .card-header h2 {{
    font-size: 17px; margin: 0; font-weight: 600;
  }}
  .badge {{
    display: inline-block;
    padding: 2px 9px; border-radius: 999px;
    font-size: 11px; font-weight: 700; letter-spacing: .04em;
  }}
  .meta {{
    display: flex; flex-wrap: wrap; gap: 12px 22px;
    color: var(--muted); font-size: 13px;
    margin: 6px 0 10px;
  }}
  .meta strong {{ color: var(--ink); font-weight: 600; }}
  .reason {{
    color: #2c2c2c; font-size: 13px;
    background: #fafaf9; padding: 8px 12px;
    border-left: 3px solid var(--accent); border-radius: 0 6px 6px 0;
    margin: 8px 0 12px;
  }}
  section {{ margin-top: 8px; }}
  section h3 {{
    font-size: 12px; text-transform: uppercase;
    letter-spacing: .06em; color: var(--muted);
    margin: 8px 0 4px;
  }}
  section ul {{ margin: 0; padding-left: 20px; }}
  section ul li {{ margin: 2px 0; }}
  .row {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 18px;
  }}
  .muted {{ color: var(--muted); font-style: italic; }}
  a.apply {{
    display: inline-block; margin-top: 12px;
    padding: 7px 14px; border-radius: 7px;
    background: var(--accent); color: #fff;
    text-decoration: none; font-weight: 600; font-size: 13px;
  }}
  a.apply:hover {{ filter: brightness(1.05); }}
</style>
</head>
<body>
<header class="hero">
  <h1>{title}</h1>
  <div class="sub">Last updated {updated} &middot; {count} match record(s) so far</div>
</header>
<main>
{cards}
</main>
</body>
</html>
"""
