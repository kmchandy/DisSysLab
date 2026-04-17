# examples/module_09/app.py

"""
Module 09: Container Edition

Identical to the BlueSky sentiment monitor you already know.
The only new thing in this module is the Dockerfile that wraps it.

Network:
    bluesky_stream → sentiment → display (stdout)

Stops automatically after MAX_POSTS messages — no runaway processes,
no cost surprises, safe to run in any container or cloud environment.

Run locally:
    python3 -m examples.module_09.app

Run in a container (after module_09 README):
    docker build -t dissyslab-monitor examples/module_09/
    docker run dissyslab-monitor
"""

from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink
from dissyslab.components.transformers.prompts import SENTIMENT_ANALYZER
from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent

# ── Configuration ─────────────────────────────────────────────────────────────
MAX_POSTS = 20   # Fixed limit — the network stops cleanly after this many posts

# ── Data source (live BlueSky, with automatic demo fallback) ──────────────────
print()
print("  Connecting to BlueSky Jetstream...")
print()

try:
    from dissyslab.components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
    _src = BlueSkyJetstreamSource(max_posts=MAX_POSTS, lifetime=60)
    source_fn = _src.run
    print("  ✓ Connected to live BlueSky stream")
except Exception as e:
    print(f"  ⚠️  BlueSky unavailable ({type(e).__name__}) — using demo posts")
    from dissyslab.components.sources.demo_bluesky_jetstream import DemoBlueSkyJetstream
    _src = DemoBlueSkyJetstream(max_posts=MAX_POSTS, delay_seconds=0)
    source_fn = _src.run

print()

# ── AI component (demo — no API key needed) ───────────────────────────────────
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


# ── Transform functions ───────────────────────────────────────────────────────
def analyze_sentiment(post):
    """Analyze sentiment of a BlueSky post."""
    result = sentiment_analyzer(post["text"])
    return {
        **post,
        "sentiment": result["sentiment"],
        "score":     result["score"],
    }


def display(article):
    """Print each post with sentiment label to stdout."""
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    label = article["sentiment"]
    author = article["author"]
    text = article["text"][:72]
    print(f"  {emoji} [{label:>8}]  @{author}: {text}")


# ── Build the network ─────────────────────────────────────────────────────────
bluesky = Source(fn=source_fn,          name="bluesky")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
output = Sink(fn=display,              name="display")

g = network([
    (bluesky,   sentiment),
    (sentiment, output),
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("📡 BlueSky Sentiment Monitor")
    print("═" * 60)
    print()
    print("  bluesky_stream → sentiment → display")
    print()
    print(f"  Stops automatically after {MAX_POSTS} posts.")
    print()
    print("─" * 60)
    print()

    g.run_network(timeout=120)

    print()
    print("─" * 60)
    print(f"✅  Done — {MAX_POSTS} posts processed.")
    print()
