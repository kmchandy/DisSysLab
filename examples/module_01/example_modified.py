# examples/module_01/example_modified.py

"""
Module 1: Modified App — Experiments 2 and 3

This extends the generated app with:
- Urgency detection (Experiment 2)
- Positive-only filter (Experiment 3)

Network topology:
    rss_feed → spam_filter → sentiment → positive_only → urgency → display

Run:
    python3 -m examples.module_01.example_modified
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER, URGENCY_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_agent

# ─── Data source ───────────────────────────────────────────────
rss = DemoRSSSource(feed_name="hacker_news")

# ─── AI components (demo versions) ────────────────────────────
spam_detector = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
urgency_detector = demo_ai_agent(URGENCY_DETECTOR)


# ─── Transform functions ──────────────────────────────────────
def filter_spam(text):
    """Drop spam, pass through everything else."""
    result = spam_detector(text)
    if result["is_spam"]:
        return None
    return text


def analyze_sentiment(text):
    """Analyze sentiment, return dict with text + analysis."""
    result = sentiment_analyzer(text)
    return {
        "text": text,
        "sentiment": result["sentiment"],
        "score": result["score"]
    }


def only_positive(article):
    """Keep only positive or neutral articles. Drop negative."""
    if article["sentiment"] == "NEGATIVE":
        return None
    return article


def analyze_urgency(article):
    """Add urgency info to each article."""
    result = urgency_detector(article["text"])
    article["urgency"] = result["urgency"]
    return article


def print_article(article):
    """Print each article with sentiment and urgency."""
    sentiment_icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    urgency_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

    s_emoji = sentiment_icon.get(article["sentiment"], "❓")
    u_emoji = urgency_icon.get(article["urgency"], "⚪")

    print(
        f"  {s_emoji} {u_emoji} [{article['sentiment']:>8}] [{article['urgency']:>6}] {article['text']}")


# ─── Build the network ────────────────────────────────────────
source = Source(fn=rss.run, name="rss_feed")
spam_gate = Transform(fn=filter_spam, name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
positive_filter = Transform(fn=only_positive, name="positive_only")
urgency = Transform(fn=analyze_urgency, name="urgency")
display = Sink(fn=print_article, name="display")

g = network([
    (source, spam_gate),
    (spam_gate, sentiment),
    (sentiment, positive_filter),
    (positive_filter, urgency),
    (urgency, display)
])

# ─── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Hacker News — Positive Articles Only, With Urgency")
    print("=" * 60)
    print()

    g.run_network()

    print()
    print("=" * 60)
    print("✅ Done! Six concurrent nodes, two filters, three analyses.")
    print()
    print("Spam was dropped (filter_spam returned None).")
    print("Negative articles were dropped (only_positive returned None).")
    print("Remaining articles show sentiment + urgency.")
    print()
