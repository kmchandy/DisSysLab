# examples/module_04/app.py

"""
Module 04: Build Your Own App — The Worked Example

A news intelligence monitor that combines everything from Modules 01-03:
  - Fanin: two feeds merge into one pipeline
  - Filtering: spam dropped before processing
  - Transform: sentiment analysis
  - Split: three-way routing by sentiment

Network topology:
    hacker_news ─┐
                  ├→ spam_filter → sentiment → split → out_0 → archive  (positive)
    tech_news   ─┘                                  → out_1 → alerts   (negative)
                                                    → out_2 → display  (neutral)

This app was designed by answering four questions:
  1. What to monitor?   → hacker_news + tech_news (fanin)
  2. What processing?   → spam filter, then sentiment analysis
  3. Where do results go? → file (positive), alerts (negative), display (neutral)
  4. Draw the topology  → see above

Run from the DisSysLab root directory:
    python3 -m examples.module_04.app
"""

from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink, Split
from dissyslab.components.sources.demo_rss_source import DemoRSSSource
from dissyslab.components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent
from dissyslab.components.sinks import DemoEmailAlerter, JSONLRecorder


# ── Data sources (fanin: both feed into spam_filter) ──────────────────────────
hn   = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")


# ── AI components ─────────────────────────────────────────────────────────────
# To use real Claude AI: change demo_ai_agent → ai_agent (see app_live.py).
spam_detector      = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


# ── Sink components ───────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="results.jsonl", mode="w", flush_every=1)
alerter  = DemoEmailAlerter(to_address="alerts@newsroom.com",
                             subject_prefix="[ALERT]")


# ── Transform functions ───────────────────────────────────────────────────────

def filter_spam(text):
    """Drop spam from either feed before it reaches sentiment analysis."""
    result = spam_detector(text)
    return None if result["is_spam"] else text


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
    Route each article to exactly one output port.
      out_0 → positive → archive
      out_1 → negative → alerts
      out_2 → neutral  → display
    """
    if article["sentiment"] == "POSITIVE":
        return [article, None,    None   ]
    elif article["sentiment"] == "NEGATIVE":
        return [None,    article, None   ]
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
# Each line in network() corresponds to one arrow in the topology drawing.

hn_source   = Source(fn=hn.run,              name="hacker_news")
tech_source = Source(fn=tech.run,            name="tech_news")
spam_gate   = Transform(fn=filter_spam,       name="spam_filter")
sentiment   = Transform(fn=analyze_sentiment, name="sentiment")
splitter    = Split(fn=route_by_sentiment,    num_outputs=3, name="router")
archive     = Sink(fn=recorder.run,           name="archive")
alerts      = Sink(fn=alerter.run,            name="alerts")
display     = Sink(fn=print_article,          name="display")

g = network([
    (hn_source,   spam_gate),      # fanin: hacker_news → spam_filter
    (tech_source, spam_gate),      # fanin: tech_news   → spam_filter
    (spam_gate,   sentiment),
    (sentiment,   splitter),
    (splitter.out_0, archive),     # positive → archive
    (splitter.out_1, alerts),      # negative → alerts
    (splitter.out_2, display)      # neutral  → display
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 News Intelligence Monitor")
    print("═" * 60)
    print()
    print("  hacker_news ─┐")
    print("                ├→ spam_filter → sentiment → split")
    print("  tech_news   ─┘                          → positive → archive")
    print("                                          → negative → alerts")
    print("                                          → neutral  → display")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done! Positive articles saved to results.jsonl")
    print()
    print("This app combines everything from Modules 01-03:")
    print("  fanin (two sources) + filtering + sentiment + Split routing")
    print()
