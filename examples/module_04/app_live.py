# examples/module_04/app_live.py

"""
Module 04: Build Your Own App — Real Claude API Version

This is app.py connected to real Claude AI instead of demo components.
The network topology and all functions are identical to app.py.
The only changes are two import lines (marked with ← CHANGED below).

max_articles=2 per feed keeps API calls and cost low. Increase it once
you're comfortable with how the app behaves.

Setup:
    export ANTHROPIC_API_KEY='your-key-here'

Run from the DisSysLab root directory:
    python3 -m examples.module_04.app_live
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.ai_agent import ai_agent             # ← CHANGED
from components.sinks import DemoEmailAlerter, JSONLRecorder


# ── Data sources ──────────────────────────────────────────────────────────────
# max_articles=2 per feed to keep API costs low.
hn   = DemoRSSSource(feed_name="hacker_news", max_articles=2)
tech = DemoRSSSource(feed_name="tech_news",   max_articles=2)


# ── AI components (real Claude API) ──────────────────────────────────────────
spam_detector      = ai_agent(SPAM_DETECTOR)                      # ← CHANGED
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)                 # ← CHANGED


# ── Sink components ───────────────────────────────────────────────────────────
recorder = JSONLRecorder(path="results_live.jsonl", mode="w", flush_every=1)
alerter  = DemoEmailAlerter(to_address="alerts@newsroom.com",
                             subject_prefix="[ALERT]")


# ── Transform functions ───────────────────────────────────────────────────────
# Identical to app.py — nothing changes here.

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
    """Route each article to exactly one output port."""
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
# Identical to app.py — nothing changes here.

hn_source   = Source(fn=hn.run,              name="hacker_news")
tech_source = Source(fn=tech.run,            name="tech_news")
spam_gate   = Transform(fn=filter_spam,       name="spam_filter")
sentiment   = Transform(fn=analyze_sentiment, name="sentiment")
splitter    = Split(fn=route_by_sentiment,    num_outputs=3, name="router")
archive     = Sink(fn=recorder.run,           name="archive")
alerts      = Sink(fn=alerter.run,            name="alerts")
display     = Sink(fn=print_article,          name="display")

g = network([
    (hn_source,   spam_gate),
    (tech_source, spam_gate),
    (spam_gate,   sentiment),
    (sentiment,   splitter),
    (splitter.out_0, archive),
    (splitter.out_1, alerts),
    (splitter.out_2, display)
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("📰 News Intelligence Monitor — Real Claude AI")
    print("═" * 60)
    print()
    print("  hacker_news ─┐")
    print("                ├→ spam_filter → sentiment → split")
    print("  tech_news   ─┘                          → positive → archive")
    print("                                          → negative → alerts")
    print("                                          → neutral  → display")
    print()
    print("  (Using real Claude API — expect a few seconds per article)")
    print("  (max_articles=2 per feed to keep API costs low)")
    print()

    g.run_network(timeout=60)

    print()
    print("═" * 60)
    print("✅ Done! Positive articles saved to results_live.jsonl")
    print()
    print("Same app as app.py. Same network. Same functions.")
    print("Two import lines changed. That's it.")
    print()
