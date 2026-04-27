# Developer News Tracker

Monitors three tech sources for news about open source software, developer
tools, and programming. Categorizes each article by type and programming
language, and delivers a daily developer digest.

## What it does

- Pulls from Hacker News, TechCrunch, and BBC Tech
- Filters out articles not related to open source, developer tools, or programming
- Classifies each article by category (release / tutorial / opinion / news)
- Identifies the primary programming language discussed
- Streams one line per article to your terminal
- Delivers a daily digest grouped by category and language

## How to run

```bash
export ANTHROPIC_API_KEY='your-key-here'
python3 -m gallery.developer_news.app
```

## What you'll see

```
🛠️  [   hacker_news] [ RELEASE] [    Python] Python 3.14 Released with New Features
🛠️  [     techcrunch] [    NEWS] [      Rust] Mozilla Expands Rust Investment
🛠️  [      bbc_tech] [ OPINION] [      None] The Case Against Microservices
```

A daily developer digest grouped by category is printed at midnight.

## How to customize

Open `app.py` and edit the `relevance_agent` prompt to focus on specific
technologies. For example, to track only Python and JavaScript news:

```python
relevance_agent = ai_agent("""
    Does this article discuss Python or JavaScript development, tools, or ecosystem?
    Return JSON only, no explanation: {"relevant": true or false}
""")
```

## How it works

See [gallery/README.md](../README.md) for an explanation of the
gather-scatter pattern used by all gallery apps.