# examples/module_01/claude_generated_app.py

"""
This is the unedited output Claude produced when given this prompt:

    "Build me a DisSysLab app that monitors the hacker_news demo feed,
    filters out spam, analyzes the sentiment of each article, and prints
    the results. Use demo components."

It runs identically to app.py. Compare the two files to see what Claude
generates versus the hand-commented teaching version.

Run from the DisSysLab root directory:
    python3 -m examples.module_01_describe_and_build.claude_generated_app
"""

# Hacker News Sentiment Monitor
# Topology: hacker_news → spam_filter → sentiment → display

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent

rss = DemoRSSSource(feed_name="hacker_news")

spam_detector = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


def filter_spam(text):
    result = spam_detector(text)
    if result["is_spam"]:
        return None
    return text


def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],
        "score":     result["score"]
    }


def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} [{article['sentiment']:>8}] {article['text']}")


source = Source(fn=rss.run,              name="rss_feed")
spam_gate = Transform(fn=filter_spam,       name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display = Sink(fn=print_article,          name="display")

g = network([
    (source,    spam_gate),
    (spam_gate, sentiment),
    (sentiment, display)
])

if __name__ == "__main__":
    print()
    print("📰 Hacker News Sentiment Monitor")
    print("═" * 60)
    print()
    print("  hacker_news → spam_filter → sentiment → display")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done!")
    print()
