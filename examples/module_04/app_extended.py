# examples/module_04/app_extended.py

"""
Module 04: Build Your Own App — Extended App

This extends app.py by adding topic classification after sentiment analysis.
Each article is now labeled with both a sentiment and a topic before routing.

Network topology:
    hacker_news ─┐
                  ├→ spam_filter → sentiment → topic → split → out_0 → archive
    tech_news   ─┘                                         → out_1 → alerts
                                                           → out_2 → display

The routing is still by sentiment — topic is added as extra information
stored in the article dict and saved to the archive file.

This shows how to enrich messages with additional analysis by chaining
Transform nodes. Each node adds a new key to the dict and passes it on.

Run from the DisSysLab root directory:
    python3 -m examples.module_04.app_extended
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import (
    SPAM_DETECTOR, SENTIMENT_ANALYZER, TOPIC_CLASSIFIER
)
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import DemoEmailAlerter, JSONLRecorder


# ── Data sources ──────────────────────────────────────────────────────────────
hn   = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")


# ── AI components ─────────────────────────────────────────────────────────────
spam_detector      = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
topic_classifier   = demo_ai_agent(TOPIC_CLASSIFIER)


# ── Sink components ───────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="results_extended.jsonl", mode="w", flush_every=1)
alerter  = DemoEmailAlerter(to_address="alerts@newsroom.com",
                             subject_prefix="[ALERT]")


# ── Transform functions ───────────────────────────────────────────────────────

def filter_spam(text):
    """Drop spam before any analysis."""
    result = spam_detector(text)
    return None if result["is_spam"] else text


def analyze_sentiment(text):
    """Add sentiment to the article dict."""
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],
        "score":     result["score"]
    }


def classify_topic(article):
    """
    Add topic classification to the article dict.

    Receives the dict from analyze_sentiment, adds a topic key,
    and passes the enriched dict downstream.
    Each Transform node adds its contribution to the flowing dict.
    """
    result = topic_classifier(article["text"])
    article["topic"] = result["primary_topic"]
    return article


def route_by_sentiment(article):
    """Route by sentiment — topic is carried along as extra data."""
    if article["sentiment"] == "POSITIVE":
        return [article, None,    None   ]
    elif article["sentiment"] == "NEGATIVE":
        return [None,    article, None   ]
    else:
        return [None,    None,    article]


def print_article(article):
    """Print neutral articles with topic label."""
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  [DISPLAY - NEUTRAL | topic: {article.get('topic', '?')}]")
    print(f"  {emoji} {article['text']}")
    print()


# ── Build the network ─────────────────────────────────────────────────────────

hn_source   = Source(fn=hn.run,              name="hacker_news")
tech_source = Source(fn=tech.run,            name="tech_news")
spam_gate   = Transform(fn=filter_spam,       name="spam_filter")
sentiment   = Transform(fn=analyze_sentiment, name="sentiment")
topic       = Transform(fn=classify_topic,    name="topic")
splitter    = Split(fn=route_by_sentiment,    num_outputs=3, name="router")
archive     = Sink(fn=recorder.run,           name="archive")
alerts      = Sink(fn=alerter.run,            name="alerts")
display     = Sink(fn=print_article,          name="display")

g = network([
    (hn_source,   spam_gate),
    (tech_source, spam_gate),
    (spam_gate,   sentiment),
    (sentiment,   topic),           # new: topic added after sentiment
    (topic,       splitter),
    (splitter.out_0, archive),
    (splitter.out_1, alerts),
    (splitter.out_2, display)
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 News Intelligence Monitor — With Topic Classification")
    print("═" * 60)
    print()
    print("  hacker_news ─┐")
    print("                ├→ spam_filter → sentiment → topic → split")
    print("  tech_news   ─┘                                  → positive → archive")
    print("                                                  → negative → alerts")
    print("                                                  → neutral  → display")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done! Positive articles (with topic) saved to results_extended.jsonl")
    print()
    print("Each article now carries both sentiment and topic.")
    print("Adding a new analysis step = one new Transform node.")
    print()
