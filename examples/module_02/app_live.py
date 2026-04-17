# examples/module_02/app_live.py

"""
Module 02: Multiple Sources, Multiple Destinations — Real Claude API Version

This is app.py connected to real Claude AI instead of demo components.
The network topology, transform functions, and sinks are identical to app.py.
The only changes are two import lines (marked with ← CHANGED below).

Setup:
    export ANTHROPIC_API_KEY='your-key-here'

Run from the DisSysLab root directory:
    python3 -m examples.module_02.app_live
"""

from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink
from dissyslab.components.sources.demo_rss_source import DemoRSSSource
from dissyslab.components.transformers.prompts import SENTIMENT_ANALYZER
from dissyslab.components.transformers.ai_agent import ai_agent             # ← CHANGED
from dissyslab.components.sinks import JSONLRecorder


# ── Data sources ──────────────────────────────────────────────────────────────
# Still using demo RSS feeds — same articles as app.py.
# This lets you compare demo vs real AI output on identical input.
hn = DemoRSSSource(feed_name="hacker_news", max_articles=2)
tech = DemoRSSSource(feed_name="tech_news",   max_articles=2)


# ── AI component (real Claude API) ───────────────────────────────────────────
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)                 # ← CHANGED


# ── Sink component ────────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="results_live.jsonl", mode="w", flush_every=1)


# ── Transform functions ───────────────────────────────────────────────────────
# Identical to app.py — nothing changes here.

def analyze_sentiment(text):
    """Analyze sentiment and return an enriched dict."""
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],
        "score":     result["score"]
    }


def print_article(article):
    """Print each article with a sentiment emoji and label."""
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} [{article['sentiment']:>8}] {article['text']}")


# ── Build the network ─────────────────────────────────────────────────────────
# Identical to app.py — nothing changes here.

hn_source = Source(fn=hn.run,              name="hacker_news")
tech_source = Source(fn=tech.run,            name="tech_news")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display = Sink(fn=print_article,          name="display")
archive = Sink(fn=recorder.run,           name="archive")

g = network([
    (hn_source,   sentiment),
    (tech_source, sentiment),
    (sentiment,   display),
    (sentiment,   archive)
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Two-Feed Sentiment Monitor — Real Claude AI")
    print("═" * 60)
    print()
    print("  hacker_news ─┐")
    print("                ├→ sentiment → display")
    print("  tech_news   ─┘           └→ results_live.jsonl")
    print()
    print("  (Using real Claude API — expect a few seconds per article)")
    print("  (max_articles=2 per feed to keep API costs low)")
    print()

    g.run_network(timeout=60)

    print()
    print("═" * 60)
    print("✅ Done! Results saved to results_live.jsonl")
    print()
    print("Same app as app.py. Same network. Same functions.")
    print("Two import lines changed. That's it.")
    print()
