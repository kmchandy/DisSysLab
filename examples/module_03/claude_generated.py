# News Sentiment Monitor
# Topology:
#   hacker_news ─┐
#                ├→ sentiment_analyzer → email_alert
#   tech_news   ─┘                    → file_collector

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import get_prompt
from components.transformers.demo_ai_agent import demo_ai_agent

# ─── Demo Sources ────────────────────────────────────────────
hn_feed = DemoRSSSource(feed_name="hacker_news", max_articles=5)
tech_feed = DemoRSSSource(feed_name="tech_news",   max_articles=5)

hn_source = Source(fn=hn_feed.run,   name="hacker_news")
tech_source = Source(fn=tech_feed.run, name="tech_news")

# ─── Sentiment Analysis (demo — swap demo_ai_agent → ai_agent for real AI) ───
_analyze = demo_ai_agent(get_prompt("sentiment_analyzer"))


def analyze_sentiment(text):
    """Analyze sentiment of each article. Returns enriched dict."""
    result = _analyze(text)
    return {
        "text":      text[:120] + "..." if len(text) > 120 else text,
        "sentiment": result["sentiment"],   # POSITIVE / NEGATIVE / NEUTRAL
        "score":     result["score"],
        "reasoning": result["reasoning"],
    }


# ─── Sinks ───────────────────────────────────────────────────
collected_articles = []


def email_alert(article):
    """Simulates sending an email alert (prints to console)."""
    icon = {"POSITIVE": "✅", "NEGATIVE": "🚨",
            "NEUTRAL": "📰"}.get(article["sentiment"], "❓")
    print(f"\n{icon} [{article['sentiment']}]  score={article['score']:+.2f}")
    print(f"   {article['text']}")
    print(f"   Reason: {article['reasoning']}")


def file_collector(article):
    """Collects articles into a list (simulates writing to a file)."""
    collected_articles.append(article)


sentiment_transform = Transform(
    fn=analyze_sentiment, name="sentiment_analyzer")
email_sink = Sink(fn=email_alert,    name="email_alert")
file_sink = Sink(fn=file_collector, name="file_collector")

# ─── Network Topology ─────────────────────────────────────────
print("Network topology:")
print("  hacker_news ─┐")
print("               ├→ sentiment_analyzer → email_alert")
print("  tech_news   ─┘                    → file_collector")
print()

g = network([
    (hn_source,          sentiment_transform),   # fanin
    (tech_source,        sentiment_transform),   # fanin
    (sentiment_transform, email_sink),           # fanout
    (sentiment_transform, file_sink),            # fanout
])

if __name__ == "__main__":
    g.run_network()

    print(
        f"\n─── File Collector: {len(collected_articles)} articles saved ───")
    for a in collected_articles:
        print(f"  [{a['sentiment']}] {a['text'][:60]}...")
