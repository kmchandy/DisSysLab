# examples/module_02/app.py

"""
Module 02: Multiple Sources, Multiple Destinations — The Canonical Demo App

Reads from two demo RSS feeds simultaneously (fanin), analyzes sentiment,
and sends results to two destinations simultaneously (fanout):
  - a live display in the terminal
  - a results.jsonl file

Network topology:
    hacker_news ─┐
                  ├→ sentiment → display
    tech_news   ─┘           └→ results.jsonl

Run from the DisSysLab root directory:
    python3 -m examples.module_02.app

Two new concepts vs Module 01:
  Fanin  — two sources feed into one transform node
  Fanout — one transform node sends to two sink nodes
"""

from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink
from dissyslab.components.sources.demo_rss_source import DemoRSSSource
from dissyslab.components.transformers.prompts import SENTIMENT_ANALYZER
from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent
from dissyslab.components.sinks import JSONLRecorder


# ── Data sources ──────────────────────────────────────────────────────────────
# Two independent sources — each runs in its own thread.
# Articles from both feeds will be interleaved at the sentiment node.
hn = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")


# ── AI component ──────────────────────────────────────────────────────────────
# One sentiment analyzer shared by both sources.
# To use real Claude AI: change demo_ai_agent → ai_agent (see app_live.py).
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


# ── Sink component ────────────────────────────────────────────────────────────
# JSONLRecorder saves each result as a JSON object on its own line.
# mode="w" starts a fresh file each run.
recorder = JSONLRecorder(path="results.jsonl", mode="w", flush_every=1)


# ── Transform functions ───────────────────────────────────────────────────────

def analyze_sentiment(text):
    """
    Analyze the sentiment of one article.

    Receives plain text from either source (fanin merges them).
    Returns an enriched dict that both sinks will receive (fanout copies it).
    """
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

hn_source = Source(fn=hn.run,              name="hacker_news")
tech_source = Source(fn=tech.run,            name="tech_news")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display = Sink(fn=print_article,          name="display")
archive = Sink(fn=recorder.run,           name="archive")

g = network([
    (hn_source,   sentiment),   # ← fanin: hacker_news feeds sentiment
    (tech_source, sentiment),   # ← fanin: tech_news also feeds sentiment
    (sentiment,   display),     # ← fanout: sentiment sends to display
    (sentiment,   archive)      # ← fanout: sentiment also sends to archive
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Two-Feed Sentiment Monitor")
    print("═" * 60)
    print()
    print("  hacker_news ─┐")
    print("                ├→ sentiment → display")
    print("  tech_news   ─┘           └→ results.jsonl")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done! Results also saved to results.jsonl")
    print()
    print("Articles from both feeds were interleaved — that's")
    print("non-deterministic fanin: order depends on thread timing.")
    print()
    print("Next: open app_live.py to connect real Claude AI.")
    print()
