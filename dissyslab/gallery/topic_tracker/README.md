# Topic Tracker

Monitors three news sources for articles about any topic you choose.
Out of the box it tracks MAGA, immigration policy, and the US border —
but you can change the topic to anything by editing a few lines.

## What it does

- Pulls from Al Jazeera, NPR News, and BBC World
- Filters out articles not related to your chosen topic
- Analyzes the sentiment of each article (positive / negative / neutral)
- Identifies the stance each article takes (pro / anti / neutral)
- Streams one line per article to your terminal
- Delivers a daily digest comparing coverage across sources

## How to run

```bash
export ANTHROPIC_API_KEY='your-key-here'
python3 -m gallery.topic_tracker.app
```

## What you'll see

```
🔴 [  al_jazeera] [   ANTI] Trump Signs Executive Order on Border Enforcement
⚪ [     npr_news] [NEUTRAL] Senate Debates Immigration Reform Package
🔵 [    bbc_world] [    PRO] White House Defends New Immigration Rules
```

A daily digest comparing how each source framed the topic is printed at midnight.

## How to customize

Open `app.py` and edit the topic in the three agent prompts. For example,
to track climate policy instead:

```python
relevance_agent = ai_agent("""
    Does this article discuss climate policy, carbon emissions, or the
    Paris Agreement?
    Return JSON only, no explanation: {"relevant": true or false}
""")

stance_agent = ai_agent("""
    Does this article present a pro, anti, or neutral stance on
    climate action and emissions reduction?
    Return JSON only, no explanation: {"stance": "PRO" | "ANTI" | "NEUTRAL", "confidence": 0.0 to 1.0}
""")
```

To track a different set of news sources, swap the imports at the top of
`app.py` — see `gallery/CLAUDE_CONTEXT.md` for the full list of available feeds.

## How it works

See [gallery/README.md](../README.md) for an explanation of the
gather-scatter pattern used by all gallery apps.
