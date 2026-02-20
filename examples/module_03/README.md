# Module 3: Multiple Sources, Multiple Destinations

*Aggregate and distribute — your app becomes a real monitoring system.*

---

## Files in This Module

| File | What it does |
|------|-------------|
| `README.md` | This guide |
| `claude_generated.py` | Example of app produced by Claude — demo version |
| `example_demo.py` | Demo version: two DemoRSS feeds → sentiment → display + collector (no API key) |
| `example_real.py` | Real version: BlueSky + RSS → Claude AI sentiment → JSONL + email alerts |
| `test_module_03.py` | Test suite — run with `python3 -m pytest examples/module_03/test_module_03.py -v` |

Run any example from the DisSysLab root:
```bash
python3 -m examples.module_03.example_demo
python3 -m examples.module_03.example_real    # requires ANTHROPIC_API_KEY
```

---

In Modules 1 and 2 you built pipelines: one source, a chain of transforms, one sink. Real monitoring systems pull from multiple data streams and send results to multiple destinations. This module teaches you how — and it's simpler than you'd expect. You add edges to the network definition. That's it.

---

## Part 1: Try the Demo First (5 minutes)

Before using real AI, run the demo version to see the new topology:

```bash
python3 -m examples.module_03.example_demo
```

This uses two `DemoRSSSource` feeds merging into one sentiment analyzer, with results going to both a display sink and a collector sink. No API key needed. The output shows messages from both sources arriving interleaved — that's fanin in action.

```
  hacker_news ─┐
                ├→  sentiment  →  email_alerts (console)
  tech_news   ─┘               →  file (collected in memory)
```

### Generate with Claude

Just like Module 1, you can ask Claude to build this for you. Try this prompt in your DisSysLab project:

> Build me a demo app that reads from two feeds — hacker_news and tech_news — merges them into one pipeline, analyzes sentiment, and sends results to both email alerts on the console and a file collector. Use demo components.

Claude generates the complete app. You can also design the app yourself, which is what we do next.

---

## Part 2: Run With Real Data (10 minutes)

### Setup

You already have your API key from Module 2. The only new step is uploading one more component file to your Claude Project so Claude can generate code with the new components.

1. Open your **DisSysLab** project on [claude.ai](https://claude.ai).
2. Go to **Files** and upload:
   - `components/sources/rss_source.py`
   - `components/sinks/mock_email_alerter.py`

### Run it

```bash
python3 -m examples.module_03.example_real
```

You'll see posts from BlueSky and articles from Hacker News arriving interleaved, analyzed by real AI, with results appearing as email alerts on screen while simultaneously being saved to a JSONL file.

The real version looks like this:

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
from components.sources.rss_source import RSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.ai_agent import ai_agent
from components.sinks import JSONLRecorder, MockEmailAlerter

# --- Two data sources ---
bluesky = BlueSkyJetstreamSource(filter_keywords=["AI", "machine learning"], max_posts=5)
rss = RSSSource(urls=["https://news.ycombinator.com/rss"], max_articles=5)

# --- Real AI ---
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)

# --- Two sinks ---
recorder = JSONLRecorder(path="module_03_output.jsonl", mode="w", flush_every=1, name="archive")
alerter = MockEmailAlerter(to_address="you@example.com", subject_prefix="[MONITOR]")
```

**Two sources, one processor, two outputs — all running concurrently.**

---

## Part 3: Understanding Fanin and Fanout (15 minutes)

### The network topology

Your app has this shape:

```
  bluesky    ─┐
               ├→  sentiment  →  file (JSONL)
  hackernews ─┘               →  email (console)
```

This isn't a pipeline anymore — it's a **diamond**. Two sources converge (fanin), processing happens, then results diverge (fanout).

### Fanin: multiple sources, one destination

Look at the network definition:

```python
g = network([
    (bluesky_source, sentiment),    # BlueSky posts go to sentiment
    (rss_source, sentiment),        # RSS articles also go to sentiment
    (sentiment, file_sink),
    (sentiment, email_sink)
])
```

Both sources connect to the same transform. DisSysLab merges the streams automatically. The sentiment analyzer doesn't know or care whether each message came from BlueSky or RSS — it just receives text and analyzes it.

**What this means:** You can add a third source (Reddit, another RSS feed, email inbox) by adding *one line* to the network. The rest of the app doesn't change. The transform functions don't change. The sinks don't change. Only the network edges change.

### Fanout: one source, multiple destinations

The sentiment transform connects to both sinks. Every result goes to both. DisSysLab copies messages automatically. The file sink and email sink don't know about each other — they each receive every result independently.

**What this means:** You can add a third sink (webhook, database, Slack notification) by adding one line. The rest of the app doesn't change.

### The key insight

Adding sources and sinks is adding *edges to the network*, not rewriting processing logic. The transform functions are identical to Module 2. The only thing that changed is the shape of the graph.

---

## Part 4: Side-by-Side with Module 2 (10 minutes)

| | Module 2 | Module 3 |
|---|---|---|
| Sources | 1 (BlueSky) | 2 (BlueSky + RSS) |
| Transforms | sentiment + entities | sentiment |
| Sinks | 1 (JSONL + display) | 2 (JSONL + email alerts) |
| Network shape | pipeline | diamond (fanin + fanout) |

The `analyze_sentiment` function is the same from Module 2. The `network()` call is the same function. The `run_network()` call is identical.

You didn't learn new Python to do fanin and fanout. You learned a new *topology*. The framework handles the rest.

---

## Part 5: The New Components (10 minutes)

### RSSSource

Reads articles from any public RSS feed. No authentication, no API key, completely free. It's a generator — each `yield` produces one article as a string (the article title and description). When the feed is exhausted, the generator ends.

```python
from components.sources.rss_source import RSSSource

rss = RSSSource(urls=["https://news.ycombinator.com/rss"], max_articles=5)
```

Note: `RSSSource` takes `urls` as a **list** (even for one feed) and `max_articles` to limit how many articles are processed.

Because `RSSSource.run()` is a generator (not a one-item-per-call function), the real example wraps it for the Source block:

```python
rss_gen = rss.run()

def rss_next():
    return next(rss_gen, None)

rss_source = Source(fn=rss_next, name="hackernews")
```

Some feeds to try:

- Hacker News: `https://news.ycombinator.com/rss`
- BBC News: `http://feeds.bbci.co.uk/news/rss.xml`
- Reddit Python: `https://www.reddit.com/r/python/.rss`

### MockEmailAlerter

Formats each result as an email notification and prints it to the console. No real email is sent — this simulates what email alerts would look like. It has the same interface as a real email sink, so when you're ready to send actual emails, you swap one import.

```python
from components.sinks import MockEmailAlerter

alerter = MockEmailAlerter(to_address="you@example.com", subject_prefix="[ALERT]")
```

---

## Part 6: Make It Yours (15 minutes)

### Experiment 1: Add a third source

Ask Claude:

> Add a third source to my app: the BBC News RSS feed. Merge it into the same pipeline with BlueSky and Hacker News.

One new Source node, one new edge. Everything else stays the same.

### Experiment 2: Filter before the sinks

Ask Claude:

> Only send email alerts for posts with negative sentiment. Save everything to the file.

This is where fanout gets interesting: the file sink gets all results, but the email path has a filter that returns `None` for non-negative posts. Different destinations see different subsets of the data. This previews Module 4's routing concept.

### Experiment 3: Different AI analysis

Ask Claude:

> Replace sentiment analysis with urgency detection. Use the URGENCY_DETECTOR prompt. Send HIGH urgency items as email alerts and save everything to the file.

Same topology, different intelligence inside the transforms.

### Experiment 4: Change the RSS feed

Point the RSS source at a feed that interests you — a subreddit, a tech blog, a news outlet in your field. The framework doesn't care what the data is — it's all just text flowing through nodes.

### Experiment 5: Add enrichment

Ask Claude:

> After sentiment analysis, add entity extraction using the ENTITY_EXTRACTOR prompt. Include the extracted names in both the file output and the email alerts.

Now both sinks receive the fully enriched data — sentiment plus entity extraction — from both sources.

---

## What You've Learned

- **Fanin:** multiple sources → one processor. Add sources by adding edges.
- **Fanout:** one processor → multiple sinks. Add sinks by adding edges.
- **The topology is the design.** Transform functions don't change when you add sources or sinks.
- **Concurrency is automatic.** Both sources run simultaneously. Both sinks receive results simultaneously. You wrote zero threading code.
- **RSSSource** reads any public RSS feed — free, no authentication. Takes `urls` as a list and `max_articles` to limit volume.
- **MockEmailAlerter** simulates email alerts on the console.

## What's Next

**[Module 4: Smart Routing](../module_04/)** — your app currently sends all results to both sinks. But what if you want to send *different* results to different places — positive posts to an archive, negative posts to email alerts, and neutral posts just to the console? That's the Split node, and it gives you complete control over where every message goes.