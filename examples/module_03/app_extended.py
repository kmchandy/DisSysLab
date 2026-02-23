# examples/module_03/app_extended.py

"""
Module 03: Smart Routing — Extended App

This extends app.py by adding spam filtering before sentiment analysis.
Spam is dropped before reaching the Split node, so only legitimate articles
are routed to the three destinations.

Network topology:
                                          ┌→ out_0 → archive  (positive)
    hacker_news → spam_filter → sentiment → split
                                          ├→ out_1 → alerts   (negative)
                                          └→ out_2 → display  (neutral)

Compare with app.py:
  - Same Split routing (three-way by sentiment)
  - One new Transform node inserted before sentiment

Run from the DisSysLab root directory:
    python3 -m examples.module_03.app_extended
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import DemoEmailAlerter, JSONLRecorder


# ── Data source ───────────────────────────────────────────────────────────────
rss = DemoRSSSource(feed_name="hacker_news")


# ── AI components ─────────────────────────────────────────────────────────────
spam_detector = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


# ── Sink components ───────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="results_extended.jsonl",
                         mode="w", flush_every=1)
alerter = DemoEmailAlerter(to_address="alerts@newsroom.com",
                           subject_prefix="[ALERT]")


# ── Transform functions ───────────────────────────────────────────────────────

def filter_spam(text):
    """Drop spam before it reaches the sentiment analyzer or router."""
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


def route_by_sentiment(article):
    """Route each article to exactly one output port based on sentiment."""
    if article["sentiment"] == "POSITIVE":
        return [article, None,    None]
    elif article["sentiment"] == "NEGATIVE":
        return [None,    article, None]
    else:
        return [None,    None,    article]


def print_article(article):
    """Print neutral articles to the terminal."""
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  [DISPLAY - NEUTRAL]")
    print(f"  {emoji} {article['text']}")
    print()


# ── Build the network ─────────────────────────────────────────────────────────

source = Source(fn=rss.run,              name="rss_feed")
spam_gate = Transform(fn=filter_spam,       name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
splitter = Split(fn=route_by_sentiment,    num_outputs=3,  name="router")
archive = Sink(fn=recorder.run,           name="archive")
alerts = Sink(fn=alerter.run,            name="alerts")
display = Sink(fn=print_article,          name="display")

g = network([
    (source,          spam_gate),
    (spam_gate,       sentiment),
    (sentiment,       splitter),
    (splitter.out_0,  archive),
    (splitter.out_1,  alerts),
    (splitter.out_2,  display)
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Sentiment Router — Spam Filtered, Three-Way Split")
    print("═" * 60)
    print()
    print("  hacker_news → spam_filter → sentiment → split")
    print("                                        → positive → archive")
    print("                                        → negative → alerts")
    print("                                        → neutral  → display")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done! Positive articles saved to results_extended.jsonl")
    print()
    print("Spam was dropped before reaching the router.")
    print("Only legitimate articles were classified and routed.")
    print()
