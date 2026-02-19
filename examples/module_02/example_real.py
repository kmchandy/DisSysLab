# examples/module_02/example_real.py

"""
Module 2: AI Integration — Real Components

BlueSky → Claude AI sentiment → Claude AI entity extraction → JSONL + display

Requires: ANTHROPIC_API_KEY, internet connection
Run:  python3 -m examples.module_02.example_real
Cost: ~$0.05-0.10 for 20 posts
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
from components.transformers.prompts import SENTIMENT_ANALYZER, ENTITY_EXTRACTOR
from components.transformers.ai_agent import ai_agent
from components.sinks import JSONLRecorder

bluesky = BlueSkyJetstreamSource(
    search_keywords=["AI", "machine learning"], max_posts=20)
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)
entity_extractor = ai_agent(ENTITY_EXTRACTOR)
recorder = JSONLRecorder(path="module_02_output.jsonl",
                         mode="w", flush_every=1, name="archive")


def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {
        "text": text,
        "sentiment": result.get("sentiment", "UNKNOWN"),
        "score": result.get("score", 0.0),
        "reasoning": result.get("reasoning", "")
    }


def extract_entities(article):
    result = entity_extractor(article["text"])
    article["people"] = result.get("people", [])
    article["organizations"] = result.get("organizations", [])
    article["locations"] = result.get("locations", [])
    return article


def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    people = ", ".join(article.get("people", [])) or "none"
    locations = ", ".join(article.get("locations", [])) or "none"
    print(f"  {emoji} [{article['sentiment']:>8}] {article['text'][:80]}")
    print(f"     People: {people} | Places: {locations}")


source = Source(fn=bluesky.run, name="bluesky")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
entities = Transform(fn=extract_entities, name="entities")
display = Sink(fn=print_article, name="display")
archive = Sink(fn=recorder.run, name="archive")

g = network([
    (source, sentiment),
    (sentiment, entities),
    (entities, display),
    (entities, archive)
])

if __name__ == "__main__":
    print("\n📡 Module 2: Real AI-Powered Social Media Monitor")
    print("=" * 60)
    print("  bluesky → sentiment → entities → display")
    print("                                 → archive (module_02_output.jsonl)\n")
    g.run_network()
    print("\n" + "=" * 60)
    print("✅ Done! Results saved to module_02_output.jsonl\n")
