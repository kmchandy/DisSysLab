# examples/module_01/example_generated.py

"""
Module 1: Describe and Build — Your First DisSysLab App

This is the pre-built version of the app described in Module 1.
It monitors a demo Hacker News feed, filters out spam,
analyzes sentiment, and prints the results.

If you have access to Claude, try generating this yourself
using the prompt in README.md. Otherwise, run this directly:

    python3 -m examples.module_01.example_generated

All four nodes run concurrently in their own threads.
Messages flow through queues automatically.
Spam is dropped by returning None.
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent

# ─── Data source ───────────────────────────────────────────────
rss = DemoRSSSource(feed_name="hacker_news")

# ─── AI components (demo versions — keyword-based) ─────────────
spam_detector = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


# ─── Transform functions ──────────────────────────────────────
def filter_spam(text):
    """
    Drop spam, pass through everything else.

    Returns None for spam → DisSysLab drops the message automatically.
    Returns original text for non-spam → continues to next node.
    """
    result = spam_detector(text)
    if result["is_spam"]:
        return None
    return text


def analyze_sentiment(text):
    """
    Analyze sentiment and return a dict with text + analysis.

    The next node receives this dict, not the raw text.
    """
    result = sentiment_analyzer(text)
    return {
        "text": text,
        "sentiment": result["sentiment"],
        "score": result["score"]
    }


def print_article(article):
    """Print each article with its sentiment."""
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} [{article['sentiment']:>8}] {article['text']}")


# ─── Build the network ────────────────────────────────────────
source = Source(fn=rss.run, name="rss_feed")
spam_gate = Transform(fn=filter_spam, name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display = Sink(fn=print_article, name="display")

g = network([
    (source, spam_gate),
    (spam_gate, sentiment),
    (sentiment, display)
])

# ─── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Hacker News Feed — Spam Filtered, Sentiment Analyzed")
    print("=" * 60)
    print()

    g.run_network()

    print()
    print("=" * 60)
    print("✅ Done! Four concurrent nodes processed 10 articles.")
    print()
    print("Spam articles were silently dropped (filter returned None).")
    print("Each remaining article was analyzed for sentiment.")
    print()
    print("Try: Change 'hacker_news' to 'tech_news' or 'reddit_python'")
    print("Try: Add an urgency detector (see README.md Experiment 2)")
    print()
