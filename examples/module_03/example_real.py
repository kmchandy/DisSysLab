# examples/module_03/example_real.py

"""
Module 3: Multiple Sources, Multiple Destinations — Real Components

BlueSky + Hacker News RSS → Claude AI sentiment → JSONL + email alerts

Requires: ANTHROPIC_API_KEY, internet connection
Run:  python3 -m examples.module_03.example_real
Cost: ~$0.03-0.06 for 20 items
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
from components.sources.rss_source import RSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.ai_agent import ai_agent
from components.sinks import JSONLRecorder, MockEmailAlerter

bluesky = BlueSkyJetstreamSource(
    search_keywords=["AI", "machine learning"], max_posts=10)
rss = RSSSource("https://news.ycombinator.com/rss")
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)
recorder = JSONLRecorder(path="module_03_output.jsonl",
                         mode="w", flush_every=1, name="archive")
alerter = MockEmailAlerter(
    to_address="you@example.com", subject_prefix="[MONITOR]")


def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {
        "text": text,
        "sentiment": result.get("sentiment", "UNKNOWN"),
        "score": result.get("score", 0.0),
        "reasoning": result.get("reasoning", "")
    }


bluesky_source = Source(fn=bluesky.run, name="bluesky")
rss_source = Source(fn=rss.run, name="hackernews")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
file_sink = Sink(fn=recorder.run, name="file")
email_sink = Sink(fn=alerter.run, name="email")

g = network([
    (bluesky_source, sentiment),
    (rss_source, sentiment),
    (sentiment, file_sink),
    (sentiment, email_sink)
])

if __name__ == "__main__":
    print("\n📡 Module 3: Multiple Sources + Multiple Destinations")
    print("=" * 60)
    print("  bluesky    ─┐")
    print("               ├→ sentiment → file (module_03_output.jsonl)")
    print("  hackernews ─┘              → email alerts (console)\n")
    g.run_network()
    print("\n" + "=" * 60)
    print("✅ Done! File: module_03_output.jsonl\n")
