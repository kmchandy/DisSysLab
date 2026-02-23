# examples/module_04/claude_generated_app.py

"""
This is the unedited output Claude produced when given this prompt:

    "Build me a DisSysLab app that reads from the hacker_news and tech_news
    demo feeds, filters spam, analyzes sentiment, and routes articles to
    three outputs: positive articles saved to a jsonl file, negative articles
    printed as email alerts, and neutral articles printed to the terminal.
    Use demo components."

It runs identically to app.py. Compare the two files to see what Claude
generates versus the hand-commented teaching version.

Run from the DisSysLab root directory:
    python3 -m examples.module_04.claude_generated_app
"""

# News Intelligence Monitor
# Topology: hacker_news ─┐
#                          ├→ spam_filter → sentiment → split → out_0 → archive
#           tech_news    ─┘                                  → out_1 → alerts
#                                                            → out_2 → display

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import DemoEmailAlerter, JSONLRecorder

hn   = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")

spam_detector      = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

recorder = JSONLRecorder(path="my_results.jsonl", mode="w", flush_every=1)
alerter  = DemoEmailAlerter(to_address="alerts@newsroom.com",
                             subject_prefix="[ALERT]")


def filter_spam(text):
    result = spam_detector(text)
    return None if result["is_spam"] else text


def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],
        "score":     result["score"]
    }


def route_by_sentiment(article):
    if article["sentiment"] == "POSITIVE":
        return [article, None,    None   ]
    elif article["sentiment"] == "NEGATIVE":
        return [None,    article, None   ]
    else:
        return [None,    None,    article]


def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} {article['text']}")


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

if __name__ == "__main__":
    print()
    print("📰 News Intelligence Monitor")
    print("═" * 60)
    print()
    print("  hacker_news ─┐")
    print("                ├→ spam_filter → sentiment → split")
    print("  tech_news   ─┘                          → positive → archive")
    print("                                          → negative → alerts")
    print("                                          → neutral  → display")
    print()

    g.run_network()

    print()
    print("═" * 60)
    print("✅ Done!")
    print()
