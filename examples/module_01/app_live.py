# examples/module_01/app_live.py

"""
Module 01: Describe and Build — Real Claude API Version

This is app.py connected to real Claude AI instead of demo components.
The network topology, transform functions, and sink are identical to app.py.
The only changes are two import lines (marked with ← CHANGED below).

Setup:
    export ANTHROPIC_API_KEY='your-key-here'

Run from the DisSysLab root directory:
    python3 -m examples.module_01_describe_and_build.app_live

You'll notice it runs slower than app.py — each article makes a real API
call to Claude. That's distributed systems behavior: your pipeline is now
talking to an AI running on a server somewhere in the world.
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.ai_agent import ai_agent             # ← CHANGED


# ── Data source ───────────────────────────────────────────────────────────────
# Still using the demo RSS feed — same articles as app.py.
# This lets you compare demo vs real AI output on identical input.
rss = DemoRSSSource(feed_name="hacker_news", max_articles=2)


# ── AI components (real Claude API) ──────────────────────────────────────────
# ai_agent() has the same interface as demo_ai_agent().
# If ANTHROPIC_API_KEY is not set, this will raise a clear error message.
spam_detector = ai_agent(SPAM_DETECTOR)                      # ← CHANGED
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)                 # ← CHANGED


# ── Transform functions ───────────────────────────────────────────────────────
# Identical to app.py — nothing changes here.

def filter_spam(text):
    """Drop spam articles, pass everything else through."""
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
# Identical to app.py — nothing changes here.

source = Source(fn=rss.run,              name="rss_feed")
spam_gate = Transform(fn=filter_spam,       name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display = Sink(fn=print_article,          name="display")

g = network([
    (source,    spam_gate),
    (spam_gate, sentiment),
    (sentiment, display)
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Hacker News Feed — Real Claude AI")
    print("═" * 60)
    print()
    print("  hacker_news → spam_filter → sentiment → display")
    print()
    print("  (Using real Claude API — expect a few seconds per article)")
    print()

    g.run_network(timeout=60)

    print()
    print("═" * 60)
    print("✅ Done!")
    print()
    print("Same app as app.py. Same network. Same functions.")
    print("Two import lines changed. That's it.")
    print()
    print("Next: open app_extended.py to see urgency detection added.")
    print()
