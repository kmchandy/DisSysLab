# examples/module_01/app_extended.py

"""
Module 01: Describe and Build — Extended App

This extends app.py with two additional nodes:
  - A positive-only filter (drops negative articles)
  - An urgency detector (adds urgency level to each article)

Network topology:
    hacker_news → spam_filter → sentiment → positive_only → urgency → display

This app shows what you can build by adding nodes to the basic pipeline.
Each new node is an ordinary Python function — the network wiring does the rest.

Run from the DisSysLab root directory:
    python3 -m examples.module_01_describe_and_build.app_extended
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import (
    SPAM_DETECTOR, SENTIMENT_ANALYZER, URGENCY_DETECTOR
)
from components.transformers.demo_ai_agent import demo_ai_agent


# ── Data source ───────────────────────────────────────────────────────────────
rss = DemoRSSSource(feed_name="hacker_news")


# ── AI components ─────────────────────────────────────────────────────────────
spam_detector = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
urgency_detector = demo_ai_agent(URGENCY_DETECTOR)


# ── Transform functions ───────────────────────────────────────────────────────

def filter_spam(text):
    """Drop spam, pass legitimate articles through."""
    result = spam_detector(text)
    if result["is_spam"]:
        return None
    return text


def analyze_sentiment(text):
    """Add sentiment information to each article."""
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],
        "score":     result["score"]
    }


def only_positive(article):
    """
    Drop negative articles, keep positive and neutral ones.

    This is a second filter in the pipeline — it comes after sentiment
    analysis, so it can make decisions based on the sentiment score.
    Two filters in sequence: first spam is dropped, then negativity.
    """
    if article["sentiment"] == "NEGATIVE":
        return None     # ← drop negative articles
    return article


def analyze_urgency(article):
    """
    Add urgency information to each article.

    Note: this function receives a dict (from analyze_sentiment), not raw text.
    It pulls out the text field, analyzes it, then adds urgency back to the dict.
    """
    result = urgency_detector(article["text"])
    article["urgency"] = result["urgency"]  # "HIGH", "MEDIUM", or "LOW"
    return article


def print_article(article):
    """Print each article with sentiment and urgency indicators."""
    sentiment_icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    urgency_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

    s_emoji = sentiment_icon.get(article["sentiment"], "❓")
    u_emoji = urgency_icon.get(article["urgency"], "⚪")

    print(
        f"  {s_emoji} {u_emoji} "
        f"[{article['sentiment']:>8}] [{article['urgency']:>6}] "
        f"{article['text']}"
    )


# ── Build the network ─────────────────────────────────────────────────────────

source = Source(fn=rss.run,              name="rss_feed")
spam_gate = Transform(fn=filter_spam,       name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
positive_filter = Transform(fn=only_positive,     name="positive_only")
urgency = Transform(fn=analyze_urgency,   name="urgency")
display = Sink(fn=print_article,          name="display")

g = network([
    (source,          spam_gate),
    (spam_gate,       sentiment),
    (sentiment,       positive_filter),
    (positive_filter, urgency),
    (urgency,         display)
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Hacker News — Positive Articles Only, With Urgency")
    print("═" * 60)
    print()
    print("  hacker_news → spam_filter → sentiment")
    print("                                  ↓")
    print("                           positive_only → urgency → display")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done!")
    print()
    print("Two filters ran in sequence:")
    print("  spam_filter   — dropped spam (returned None)")
    print("  positive_only — dropped negative articles (returned None)")
    print()
    print("Remaining articles have both sentiment and urgency labels.")
    print()
