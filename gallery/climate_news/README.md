# Climate and Environment Monitor

Monitors NASA, BBC Tech, and NPR for news about climate change, the
environment, and extreme weather. Rates urgency and identifies the
affected region for each article.

## What it does

- Pulls from NASA, BBC Tech, and NPR News
- Filters out articles not related to climate, environment, or extreme weather
- Rates the urgency of each issue (high / medium / low)
- Identifies the world region primarily affected
- Streams one line per article to your terminal
- Delivers a daily climate digest with high-urgency articles first

## How to run

```bash
export ANTHROPIC_API_KEY='your-key-here'
python3 -m gallery.climate_monitor.app
```

## What you'll see

```
🔴 [     nasa] [  North America] Record Arctic Ice Loss Reported for Third Consecutive Year
🟡 [  bbc_tech] [         Europe] EU Announces New Carbon Border Tax Mechanism
🟢 [ npr_news] [         Global] Scientists Develop More Efficient Solar Panel Material
```

A daily climate digest is printed at midnight, with high-urgency articles first.

## How to customize

Open `app.py` and edit `CLIMATE_TOPICS` at the top of the file:

```python
CLIMATE_TOPICS = [
    "renewable energy",
    "solar and wind power",
    "energy storage",
    "grid modernization",
]
```

This focuses the app on energy transition news rather than general climate coverage.
You can also add more sources — see `gallery/CLAUDE_CONTEXT.md` for the full
list of available feeds.

## How it works

See [gallery/README.md](../README.md) for an explanation of the
gather-scatter pattern used by all gallery apps.