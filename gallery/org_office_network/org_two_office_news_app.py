# gallery/org_two_office_news/app.py
#
# A two-office news network.
#
# news_monitor filters incoming articles for significance.
# news_editor routes by topic and rewrites as briefing notes.
#
# Topology:
#
#   al_jazeera ─┐
#   bbc_world  ─┼→  news_monitor  →  news_editor  →  news_dashboard
#   npr_news   ─┘
#
# Each office is a black box — this file only knows their
# input and output port names, nothing about what's inside.

from dsl import network
from dsl.blocks import Source, Sink

from components.sources.rss_normalizer import al_jazeera, bbc_world, npr_news
from components.sinks.intelligence_display import IntelligenceDisplay

from gallery.news_monitor.app import news_monitor
from gallery.news_editor.app import news_editor


# ── Sources ───────────────────────────────────────────────────────────────────

_al_jazeera = al_jazeera(max_articles=5)
_bbc_world  = bbc_world(max_articles=5)
_npr_news   = npr_news(max_articles=5)

src_al_jazeera = Source(fn=_al_jazeera.run, name="al_jazeera")
src_bbc_world  = Source(fn=_bbc_world.run,  name="bbc_world")
src_npr_news   = Source(fn=_npr_news.run,   name="npr_news")


# ── Sink ──────────────────────────────────────────────────────────────────────

_display     = IntelligenceDisplay()
news_dashboard = Sink(fn=_display.run, name="news_dashboard")


# ── Network ───────────────────────────────────────────────────────────────────

g = network([
    (src_al_jazeera,          news_monitor.article_in),
    (src_bbc_world,           news_monitor.article_in),
    (src_npr_news,            news_monitor.article_in),
    (news_monitor.article_out, news_editor.article_in),
    (news_editor.article_out,  news_dashboard),
])


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("Two-Office News Network")
    print("=" * 60)
    print()
    print("  al_jazeera ─┐")
    print("  bbc_world  ─┼→  news_monitor  →  news_editor  →  news_dashboard")
    print("  npr_news   ─┘")
    print()
    g.run_network(timeout=120)
    print()
    print("Done!")
    print()
