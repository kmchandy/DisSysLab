# examples/module_02/claude_generated_app.py

"""
This is the unedited output Claude produced when given this prompt:

    "Build me a DisSysLab app that reads from the hacker_news and tech_news
    demo feeds, merges them, analyzes sentiment, and sends results to both
    a display and a jsonl file called my_results.jsonl. Use demo components."

It runs identically to app.py. Compare the two files to see what Claude
generates versus the hand-commented teaching version.

Run from the DisSysLab root directory:
    python3 -m examples.module_02.claude_generated_app
"""

# Two-Feed Sentiment Monitor
# Topology: hacker_news ─┐
#                          ├→ sentiment → display
#           tech_news    ─┘           └→ my_results.jsonl

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import JSONLRecorder

hn = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")

sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

recorder = JSONLRecorder(path="my_results.jsonl", mode="w", flush_every=1)


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


hn_source = Source(fn=hn.run,              name="hacker_news")
tech_source = Source(fn=tech.run,            name="tech_news")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display = Sink(fn=print_article,          name="display")
archive = Sink(fn=recorder.run,           name="archive")

g = network([
    (hn_source,   sentiment),
    (tech_source, sentiment),
    (sentiment,   display),
    (sentiment,   archive)
])

if __name__ == "__main__":
    print()
    print("📰 Two-Feed Sentiment Monitor")
    print("═" * 60)
    print()
    print("  hacker_news ─┐")
    print("                ├→ sentiment → display")
    print("  tech_news   ─┘           └→ my_results.jsonl")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done! Results saved to my_results.jsonl")
    print()
