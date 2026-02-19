# examples/module_04/example_demo.py

"""
Module 4: Smart Routing — Demo Version

DemoRSS → demo sentiment → Split 3 outputs → archive / console / alerts

Run:  python3 -m examples.module_04.example_demo
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent

rss = DemoRSSSource(feed_name="hacker_news")
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}


def route_by_sentiment(article):
    score = article["score"]
    if score > 0.2:
        return [article, article, None]
    elif score < -0.2:
        return [None, article, article]
    else:
        return [None, article, None]


archive_results = []
alert_results = []


def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(
        f"  [CONSOLE] {emoji} {article['sentiment']:>8} ({article['score']:+.1f}): {article['text'][:60]}")


def print_alert(article):
    print(f"  🚨 [ALERT] {article['text'][:70]}")


source = Source(fn=rss.run, name="rss_feed")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
splitter = Split(fn=route_by_sentiment, num_outputs=3, name="router")
archive_sink = Sink(fn=archive_results.append, name="archive")
console_sink = Sink(fn=print_article, name="console")
alert_sink = Sink(fn=print_alert, name="alerts")

g = network([
    (source, sentiment),
    (sentiment, splitter),
    (splitter.out_0, archive_sink),
    (splitter.out_1, console_sink),
    (splitter.out_2, alert_sink)
])

if __name__ == "__main__":
    print("\n📰 Module 4 (Demo): Smart Routing with Split")
    print("=" * 60)
    print("  rss_feed → sentiment → split ─→ out_0 → archive (positive)")
    print("                               ─→ out_1 → console (all)")
    print("                               ─→ out_2 → alerts  (negative)\n")
    g.run_network()
    print(f"\n  Archive: {len(archive_results)} positive articles saved")
    print(f"  Alerts:  {len(alert_results)} negative articles flagged\n")
    print("=" * 60)
    print("✅ Done! Run example_real.py for live BlueSky + real AI.\n")
