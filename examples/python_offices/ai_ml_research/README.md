# AI/ML Research Tracker

Monitors four tech sources for developments in artificial intelligence and
machine learning. Streams matching articles to your terminal as they arrive,
and delivers a daily digest at midnight.

## What it does

- Pulls from Hacker News, MIT Tech Review, TechCrunch, and VentureBeat AI
- Filters out articles not related to AI, ML, or LLMs
- Classifies each article by sentiment (positive / negative / neutral)
- Rates each article's potential impact (high / medium / low)
- Streams one line per article to your terminal
- Delivers a daily digest grouped by source and impact level

## How to run

```bash
# Set your API key once
export ANTHROPIC_API_KEY='your-key-here'

# Run the app (runs forever — Ctrl+C to stop)
python3 -m gallery.ai_ml_research.app
```

**No API key?** Run the demo version instead:

```bash
python3 -m gallery.ai_ml_research.demo
```

The demo uses prepackaged articles and responses — no API key needed.

## What you'll see

```
✅🔴 [   hacker_news] LLaMA 4 Released: Open Weights, 400B Parameters
❌🟡 [mit_tech_review] AI Hiring Tools Found to Discriminate in New Study
➖🟢 [      techcrunch] Startup Raises $12M for AI Code Review Platform
```

A daily digest is printed at midnight.

## How to customize

Open `app.py` — the app has no configuration variables. To change what it
tracks, edit the AI agent prompts directly. For example, to focus only on
open-source AI:

```python
relevance_agent = ai_agent("""
    Does this article discuss open-source AI models or tools?
    Return JSON only, no explanation: {"relevant": true or false}
""")
```

To add a new source, add it to the `rss_normalizer` imports and wire it
into the network alongside the existing sources.

## How it works

See [gallery/README.md](../README.md) for an explanation of the
gather-scatter pattern used by all gallery apps.
