# examples/module_03/app.py

"""
Module 03: Smart Routing — The Canonical Demo App

Reads from a Hacker News feed, analyzes sentiment, and routes each article
to a specific destination based on its sentiment:
  - Positive → archive (results.jsonl)
  - Negative → email-style alerts (terminal display)
  - Neutral  → direct display (terminal)

Network topology:
                              ┌→ out_0 → archive  (positive)
    hacker_news → sentiment → split
                              ├→ out_1 → alerts   (negative)
                              └→ out_2 → display  (neutral)

Run from the DisSysLab root directory:
    python3 -m examples.module_03.app

New concept vs Modules 01-02:
  Split — routes each message to a specific output port based on content.
  Unlike fanout (which copies to all), Split sends each message to one place.
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import DemoEmailAlerter, JSONLRecorder


# ── Data source ───────────────────────────────────────────────────────────────
rss = DemoRSSSource(feed_name="hacker_news")


# ── AI component ──────────────────────────────────────────────────────────────
# To use real Claude AI: change demo_ai_agent → ai_agent (see app_live.py).
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


# ── Sink components ───────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="results.jsonl", mode="w", flush_every=1)
alerter  = DemoEmailAlerter(to_address="alerts@newsroom.com",
                             subject_prefix="[ALERT]")


# ── Transform functions ───────────────────────────────────────────────────────

def analyze_sentiment(text):
    """Analyze sentiment and return an enriched dict."""
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],
        "score":     result["score"]
    }


def route_by_sentiment(article):
    """
    Route each article to exactly one output port based on sentiment.

    Returns a list of 3 elements — one per output port:
      index 0 (out_0) ← positive articles → archive
      index 1 (out_1) ← negative articles → alerts
      index 2 (out_2) ← neutral articles  → display

    Non-None elements are sent to the corresponding port.
    None elements mean "skip this port."

    The list length must match num_outputs=3 exactly.
    """
    if article["sentiment"] == "POSITIVE":
        return [article, None,    None   ]   # → out_0 (archive)
    elif article["sentiment"] == "NEGATIVE":
        return [None,    article, None   ]   # → out_1 (alerts)
    else:
        return [None,    None,    article]   # → out_2 (display)


def print_article(article):
    """Print neutral articles to the terminal."""
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  [DISPLAY - NEUTRAL]")
    print(f"  {emoji} {article['text']}")
    print()


# ── Build the network ─────────────────────────────────────────────────────────
# Split creates output ports out_0, out_1, out_2 automatically.
# Port references connect each output to its downstream node.

source    = Source(fn=rss.run,              name="rss_feed")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
splitter  = Split(fn=route_by_sentiment,    num_outputs=3,  name="router")
archive   = Sink(fn=recorder.run,           name="archive")
alerts    = Sink(fn=alerter.run,            name="alerts")
display   = Sink(fn=print_article,          name="display")

g = network([
    (source,          sentiment),
    (sentiment,       splitter),
    (splitter.out_0,  archive),    # positive → archive
    (splitter.out_1,  alerts),     # negative → alerts
    (splitter.out_2,  display)     # neutral  → display
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 Sentiment Router — Three-Way Split")
    print("═" * 60)
    print()
    print("  hacker_news → sentiment → split → positive → archive")
    print("                                  → negative → alerts")
    print("                                  → neutral  → display")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done! Positive articles saved to results.jsonl")
    print()
    print("Each article went to exactly one destination.")
    print("That's Split: route by content, not broadcast to all.")
    print()