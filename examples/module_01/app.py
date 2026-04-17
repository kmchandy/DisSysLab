# examples/module_01/app.py

"""
Module 01: Describe and Build — The Canonical Demo App

Monitors a Hacker News feed, filters spam, analyzes sentiment, prints results.
Uses demo components: no API keys needed, runs instantly.

Network topology:
    hacker_news → spam_filter → sentiment → display

Run from the DisSysLab root directory:
    python3 -m examples.module_01_describe_and_build.app

To use real Claude AI instead of demo components, see app_live.py.
The only change is two import lines — everything else stays the same.
"""

from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink
from dissyslab.components.sources.demo_rss_source import DemoRSSSource
from dissyslab.components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent


# ── Data source ───────────────────────────────────────────────────────────────
# DemoRSSSource simulates a live RSS feed with 10 articles (some spam included).
# Available feeds: "hacker_news", "tech_news", "reddit_python"
rss = DemoRSSSource(feed_name="hacker_news")


# ── AI components (demo — keyword-based, no API key needed) ───────────────────
# demo_ai_agent() returns a callable with the same interface as the real ai_agent.
# To switch to real Claude AI: change demo_ai_agent → ai_agent (see app_live.py).
spam_detector = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


# ── Transform functions ───────────────────────────────────────────────────────
# These are ordinary Python functions — no DSL concepts inside them.
# The decorators (Source, Transform, Sink) handle all the network wiring.

def filter_spam(text):
    """
    Drop spam articles, pass everything else through.

    Returning None tells DisSysLab to drop this message silently.
    Downstream nodes never see it — it's as if it never existed.
    """
    result = spam_detector(text)
    if result["is_spam"]:
        return None     # ← drop spam
    return text         # ← pass legitimate articles through


def analyze_sentiment(text):
    """
    Analyze the sentiment of an article and return a dict.

    The next node (display) will receive this dict, not the raw text.
    This is how data gets enriched as it flows through the network.
    """
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        # "POSITIVE", "NEGATIVE", or "NEUTRAL"
        "sentiment": result["sentiment"],
        "score":     result["score"]        # -1.0 to +1.0
    }


def print_article(article):
    """Print each article with a sentiment emoji and label."""
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} [{article['sentiment']:>8}] {article['text']}")


# ── Build the network ─────────────────────────────────────────────────────────
# Each node runs in its own thread. Messages flow through queues automatically.
# The network() call is the wiring diagram: (sender, receiver).

source = Source(fn=rss.run,              name="rss_feed")
spam_gate = Transform(fn=filter_spam,       name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display = Sink(fn=print_article,          name="display")

g = network([
    (source,    spam_gate),     # all articles → spam filter
    (spam_gate, sentiment),     # non-spam articles → sentiment analysis
    (sentiment, display)        # analyzed articles → display
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Hacker News Feed — Spam Filtered, Sentiment Analyzed")
    print("═" * 60)
    print()
    print("  hacker_news → spam_filter → sentiment → display")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done!")
    print()
    print("Spam articles were silently dropped (filter_spam returned None).")
    print("Each remaining article was analyzed for sentiment.")
    print()
    print("Next: open app_live.py to see the two-line change for real AI.")
    print()
