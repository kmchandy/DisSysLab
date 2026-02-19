# examples/module_03/example_demo.py

"""
Module 3: Multiple Sources, Multiple Destinations — Demo Version

DemoRSS("hacker_news") + DemoRSS("tech_news") → sentiment → display + collector

Run:  python3 -m examples.module_03.example_demo
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent

rss_hn = DemoRSSSource(feed_name="hacker_news", max_articles=5)
rss_tech = DemoRSSSource(feed_name="tech_news", max_articles=5)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}


file_results = []


def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  📧 {emoji} [{article['sentiment']:>8}] {article['text'][:60]}")


source1 = Source(fn=rss_hn.run, name="hacker_news")
source2 = Source(fn=rss_tech.run, name="tech_news")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display = Sink(fn=print_article, name="email_alerts")
collector = Sink(fn=file_results.append, name="file")

g = network([
    (source1, sentiment),
    (source2, sentiment),
    (sentiment, display),
    (sentiment, collector)
])

if __name__ == "__main__":
    print("\n📰 Module 3 (Demo): Fanin + Fanout")
    print("=" * 60)
    print("  hacker_news ─┐")
    print("                ├→ sentiment → email_alerts (console)")
    print("  tech_news   ─┘              → file (collected in memory)\n")
    g.run_network()
    print(f"\n  File sink collected {len(file_results)} results\n")
    print("=" * 60)
    print("✅ Done! Run example_real.py for live BlueSky + RSS + real AI.\n")
