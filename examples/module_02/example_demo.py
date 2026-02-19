# examples/module_02/example_demo.py

"""
Module 2: AI Integration — Demo Version

DemoRSSSource → demo sentiment → demo entity extraction → display

Run:  python3 -m examples.module_02.example_demo
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent

rss = DemoRSSSource(feed_name="hacker_news")
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}


def extract_entities(article):
    words = article["text"].split()
    names = [w for w in words if w[0].isupper() and len(w) > 2
             and w not in ("The", "This", "How", "What", "Show", "Ask")]
    article["people"] = names[:3]
    article["locations"] = []
    return article


def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    people = ", ".join(article.get("people", [])) or "none"
    print(f"  {emoji} [{article['sentiment']:>8}] {article['text'][:70]}")
    print(f"     People: {people}")


source = Source(fn=rss.run, name="rss_feed")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
entities = Transform(fn=extract_entities, name="entities")
display = Sink(fn=print_article, name="display")

g = network([(source, sentiment), (sentiment, entities), (entities, display)])

if __name__ == "__main__":
    print("\n📰 Module 2 (Demo): Sentiment + Entity Extraction Pipeline")
    print("=" * 60)
    print("  rss_feed → sentiment → entities → display\n")
    g.run_network()
    print("\n" + "=" * 60)
    print("✅ Done! Run example_real.py for live BlueSky + real AI.\n")
