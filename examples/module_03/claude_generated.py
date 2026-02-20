# Tech News Aggregator
# Topology: hacker_news ─┐
#                         ├→ sentiment → email_alert
#           tech_news   ─┘           ↘ file_collector

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import MockEmailAlerter, JSONLRecorder

# ─── Data sources ─────────────────────────────────────────────
hn = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")

# ─── AI component (demo — no API key needed) ──────────────────
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

# ─── Transform function ───────────────────────────────────────


def analyze_sentiment(text):
    """Tag each article with its sentiment and score."""
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],   # POSITIVE / NEGATIVE / NEUTRAL
        "score":     result["score"],
    }

# ─── Output functions ─────────────────────────────────────────


def email_display(article):
    """Print a mock email alert for each article."""
    icons = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    icon = icons.get(article["sentiment"], "❓")
    print(f"  📧 {icon} [{article['sentiment']:8s}]  {article['text']}")


# ─── Sinks ────────────────────────────────────────────────────
recorder = JSONLRecorder(
    path="news_results.jsonl",
    mode="w",
    flush_every=1,
    name="news_archive",
)

# ─── Build the network ────────────────────────────────────────
hn_source = Source(fn=hn.run,             name="hacker_news")
tech_source = Source(fn=tech.run,           name="tech_news")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
email_sink = Sink(fn=email_display,        name="email_alert")
file_sink = Sink(fn=recorder.run,         name="file_collector")

g = network([
    (hn_source,   sentiment),   # ─┐ fanin: both feeds
    (tech_source, sentiment),   # ─┘ merge into sentiment
    (sentiment,   email_sink),  # ─┐ fanout: results go to
    (sentiment,   file_sink),   # ─┘ both sinks simultaneously
])

if __name__ == "__main__":
    print("\n📰 Tech News Aggregator")
    print("   hacker_news ─┐")
    print("                ├→ sentiment ─┬→ email_alert")
    print("   tech_news   ─┘             └→ file_collector\n")
    g.run_network()
    print("\n✅ Done! Results saved to news_results.jsonl")
