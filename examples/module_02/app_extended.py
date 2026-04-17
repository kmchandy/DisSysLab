# examples/module_02/app_extended.py

"""
Module 02: Multiple Sources, Multiple Destinations — Extended App

This extends app.py by adding spam filtering before sentiment analysis.
Only non-spam articles reach the sentiment node and the two sinks.

Network topology:
    hacker_news ─┐
                  ├→ spam_filter → sentiment → display
    tech_news   ─┘                          └→ results.jsonl

Compare with app.py:
  - Same fanin (two sources → one node)
  - Same fanout (one node → two sinks)
  - One new Transform node inserted between fanin and fanout

Run from the DisSysLab root directory:
    python3 -m examples.module_02.app_extended
"""

from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink
from dissyslab.components.sources.demo_rss_source import DemoRSSSource
from dissyslab.components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent
from dissyslab.components.sinks import JSONLRecorder


# ── Data sources ──────────────────────────────────────────────────────────────
hn = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")


# ── AI components ─────────────────────────────────────────────────────────────
spam_detector = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


# ── Sink component ────────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="results_extended.jsonl",
                         mode="w", flush_every=1)


# ── Transform functions ───────────────────────────────────────────────────────

def filter_spam(text):
    """
    Drop spam, pass legitimate articles through.

    Sits between the fanin point and the sentiment analyzer.
    Spam from either feed is dropped before reaching sentiment.
    """
    result = spam_detector(text)
    if result["is_spam"]:
        return None
    return text


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

hn_source = Source(fn=hn.run,              name="hacker_news")
tech_source = Source(fn=tech.run,            name="tech_news")
spam_gate = Transform(fn=filter_spam,       name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display = Sink(fn=print_article,          name="display")
archive = Sink(fn=recorder.run,           name="archive")

g = network([
    (hn_source,   spam_gate),   # ← fanin: both sources feed spam_filter
    (tech_source, spam_gate),   # ← fanin
    (spam_gate,   sentiment),   # spam-free articles → sentiment
    (sentiment,   display),     # ← fanout: sentiment sends to display
    (sentiment,   archive)      # ← fanout: and also to archive
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Two-Feed Monitor — Spam Filtered, Sentiment Analyzed")
    print("═" * 60)
    print()
    print("  hacker_news ─┐")
    print("                ├→ spam_filter → sentiment → display")
    print("  tech_news   ─┘                          └→ results_extended.jsonl")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done! Results saved to results_extended.jsonl")
    print()
    print("Spam from both feeds was filtered before sentiment analysis.")
    print("The fanin and fanout structure is identical to app.py —")
    print("one new Transform node was inserted between them.")
    print()
