# examples/module_03/claude_generated_app.py

"""
This is the unedited output Claude produced when given this prompt:

    "Build me a DisSysLab app that reads from the hacker_news demo feed,
    analyzes sentiment, and routes articles to three outputs: positive
    articles saved to a jsonl file, negative articles printed as email
    alerts, and neutral articles printed to the terminal.
    Use demo components."

It runs identically to app.py. Compare the two files to see what Claude
generates versus the hand-commented teaching version.

Run from the DisSysLab root directory:
    python3 -m examples.module_03.claude_generated_app
"""

# Sentiment Router
# Topology: hacker_news → sentiment → split → out_0 → archive  (positive)
#                                            → out_1 → alerts   (negative)
#                                            → out_2 → display  (neutral)

from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink, Split
from dissyslab.components.sources.demo_rss_source import DemoRSSSource
from dissyslab.components.transformers.prompts import SENTIMENT_ANALYZER
from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent
from dissyslab.components.sinks import DemoEmailAlerter, JSONLRecorder

rss = DemoRSSSource(feed_name="hacker_news")
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
recorder = JSONLRecorder(path="my_results.jsonl", mode="w", flush_every=1)
alerter = DemoEmailAlerter(to_address="alerts@newsroom.com",
                                      subject_prefix="[ALERT]")


def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],
        "score":     result["score"]
    }


def route_by_sentiment(article):
    if article["sentiment"] == "POSITIVE":
        return [article, None,    None]
    elif article["sentiment"] == "NEGATIVE":
        return [None,    article, None]
    else:
        return [None,    None,    article]


def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} {article['text']}")


source = Source(fn=rss.run,              name="rss_feed")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
splitter = Split(fn=route_by_sentiment,    num_outputs=3,  name="router")
archive = Sink(fn=recorder.run,           name="archive")
alerts = Sink(fn=alerter.run,            name="alerts")
display = Sink(fn=print_article,          name="display")

g = network([
    (source,          sentiment),
    (sentiment,       splitter),
    (splitter.out_0,  archive),
    (splitter.out_1,  alerts),
    (splitter.out_2,  display)
])

if __name__ == "__main__":
    print()
    print("📰 Sentiment Router")
    print("═" * 60)
    print()
    print("  hacker_news → sentiment → split → positive → archive")
    print("                                  → negative → alerts")
    print("                                  → neutral  → display")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done!")
    print()
