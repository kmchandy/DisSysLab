# examples/module_04/example_real.py

"""
Module 4: Smart Routing — Real Components

BlueSky → Claude AI sentiment → Split → archive / console / alerts

Requires: ANTHROPIC_API_KEY, internet connection
Run:  python3 -m examples.module_04.example_real
Cost: ~$0.02-0.04 for 20 posts
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.ai_agent import ai_agent
from components.sinks import JSONLRecorder, MockEmailAlerter

bluesky = BlueSkyJetstreamSource(
    search_keywords=["AI", "machine learning"], max_posts=20)
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)
recorder = JSONLRecorder(path="module_04_positive.jsonl",
                         mode="w", flush_every=1, name="positive_archive")
alerter = MockEmailAlerter(
    to_address="you@example.com", subject_prefix="[NEGATIVE]")


def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {
        "text": text,
        "sentiment": result.get("sentiment", "UNKNOWN"),
        "score": result.get("score", 0.0),
        "reasoning": result.get("reasoning", "")
    }


def route_by_sentiment(article):
    score = article["score"]
    if score > 0.2:
        return [article, article, None]
    elif score < -0.2:
        return [None, article, article]
    else:
        return [None, article, None]


def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(
        f"  [CONSOLE] {emoji} {article['sentiment']} ({article['score']:+.2f}): {article['text'][:70]}")


source = Source(fn=bluesky.run, name="bluesky")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
splitter = Split(fn=route_by_sentiment, num_outputs=3, name="router")
archive_sink = Sink(fn=recorder.run, name="archive")
console_sink = Sink(fn=print_article, name="console")
alert_sink = Sink(fn=alerter.run, name="alerts")

g = network([
    (source, sentiment),
    (sentiment, splitter),
    (splitter.out_0, archive_sink),
    (splitter.out_1, console_sink),
    (splitter.out_2, alert_sink)
])

if __name__ == "__main__":
    print("\n📡 Module 4: Smart Routing with Split")
    print("=" * 60)
    print("  bluesky → sentiment → split ─→ out_0 → archive (positive.jsonl)")
    print("                              ─→ out_1 → console (non-neutral)")
    print("                              ─→ out_2 → alerts  (negative)\n")
    g.run_network()
    print("\n" + "=" * 60)
    print("✅ Done! Positive archived: module_04_positive.jsonl\n")
