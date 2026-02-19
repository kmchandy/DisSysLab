# Module 3: Multiple Sources, Multiple Destinations

*Aggregate and distribute — your app becomes a real monitoring system.*

In Modules 1 and 2 you built pipelines: one source, a chain of transforms, one sink. Real monitoring systems pull from multiple data streams and send results to multiple destinations. This module teaches you how — and it's simpler than you'd expect. You add edges to the network definition. That's it.

---

## Part 1: Setup (5 minutes)

You already have your Anthropic API key and Claude Project from Module 2. The only new step is uploading two more component files so Claude can generate code with the new components.

1. Open your **DisSysLab** project on [claude.ai](https://claude.ai).
2. Go to **Files** and upload:
   - `components/sources/rss_source.py`
   - `components/sinks/mock_email_alerter.py`

Your project now has all the components for Modules 1, 2, and 3.

---

## Part 2: Describe Your App to Claude (5 minutes)

Open a new conversation in your DisSysLab project and type:

> Build me an app that monitors two sources simultaneously: BlueSky posts mentioning AI (using BlueSkyJetstreamSource with max_posts=10) and articles from the Hacker News RSS feed (using RSSSource with "https://news.ycombinator.com/rss"). Merge both streams into one pipeline. Analyze sentiment using real Claude AI with the sentiment_analyzer prompt. Send all results to TWO destinations: save to a JSONL file AND display as email alerts on the console using MockEmailAlerter. Use real components.

Claude generates the app. Save it, run it:

```bash
python3 my_monitor.py
```

You'll see posts from BlueSky and articles from Hacker News arriving interleaved, analyzed by real AI, with results appearing as email alerts on screen while simultaneously being saved to a file.

**Two sources, one processor, two outputs — all running concurrently.**

---

## Part 3: Understanding Fanin and Fanout (15 minutes)

### The network topology

Your app has this shape:

```
BlueSky ──→ ┐
             ├──→ sentiment ──→ ┬──→ save_to_file
RSS feed ──→ ┘                  └──→ email_alert
```

This isn't a pipeline anymore — it's a **diamond**. Two sources converge (fanin), processing happens, then results diverge (fanout).

### Fanin: multiple sources, one destination

Look at the network definition Claude generated:

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
| Transforms | sentiment + entity extraction | sentiment |
| Sinks | 1 (JSONL file) | 2 (JSONL file + email alerts) |
| Network shape | pipeline | diamond (fanin + fanout) |

The transform function is the same `analyze_sentiment` from Module 2. The `network()` call is the same function. The `run_network()` call is identical.

You didn't learn new Python to do fanin and fanout. You learned a new *topology*. The framework handles the rest.

---

## Part 5: The Components (10 minutes)

### RSSSource

Reads articles from any public RSS feed. No authentication, no API key, completely free. Returns one article per `.run()` call as a string (the article title or description). Returns `None` when the feed is exhausted.

```python
from components.sources.rss_source import RSSSource

rss = RSSSource("https://news.ycombinator.com/rss")
```

Some feeds to try:

- Hacker News: `https://news.ycombinator.com/rss`
- BBC News: `http://feeds.bbci.co.uk/news/rss.xml`
- Reddit Python: `https://www.reddit.com/r/python/.rss`
- TechCrunch: `https://techcrunch.com/feed/`

### MockEmailAlerter

Formats each result as an email notification and prints it to the console. No real email is sent — this is a mock sink that shows what email alerts *would* look like. It has the same interface as a real email sink, so when you're ready to send actual emails, you swap one import.

```python
from components.sinks import MockEmailAlerter

alerter = MockEmailAlerter(to_address="you@example.com", subject_prefix="[ALERT]")
```

---

## Part 6: Make It Yours (15 minutes)

### Experiment 1: Add a third source

Ask Claude:

> Add a third source to my app: the BBC News RSS feed at http://feeds.bbci.co.uk/news/rss.xml. Merge it into the same pipeline with BlueSky and Hacker News.

One new Source node, one new edge. Everything else stays the same.

### Experiment 2: Filter before the sinks

Ask Claude:

> Only send email alerts for posts with negative sentiment. Save everything to the file.

This is where fanout gets interesting: the file sink gets all results, but the email path has a filter that returns `None` for non-negative posts. Different destinations see different subsets of the data. This previews Module 4's routing concept.

### Experiment 3: Different AI analysis

Ask Claude:

> Replace sentiment analysis with urgency detection. Use the urgency_detector prompt. Send HIGH urgency items as email alerts and save everything to the file.

Same topology, different intelligence inside the transforms.

### Experiment 4: Change the RSS feed

Point the RSS source at a feed that interests you — a subreddit, a tech blog, a news outlet in your field. The framework doesn't care what the data is — it's all just text flowing through nodes.

### Experiment 5: Add enrichment

Ask Claude:

> After sentiment analysis, add entity extraction using the entity_extractor prompt. Include the extracted names in both the file output and the email alerts.

Now both sinks receive the fully enriched data — sentiment plus entity extraction — from both sources.

---

## Part 7: What You Should See

```
📡 Monitoring: BlueSky (AI, machine learning) + Hacker News RSS
   Outputs: output.jsonl + email alerts

  📧 EMAIL ALERT:
     To: you@example.com
     Subject: [ALERT] Sentiment: NEGATIVE
     Body: "Tech layoffs hit another major company amid AI spending concerns"
     Sentiment: NEGATIVE | Score: -0.72

  📧 EMAIL ALERT:
     To: you@example.com
     Subject: [ALERT] Sentiment: POSITIVE
     Body: "Just deployed my first ML model to production!"
     Sentiment: POSITIVE | Score: 0.85

  📧 EMAIL ALERT:
     To: you@example.com
     Subject: [ALERT] Sentiment: NEUTRAL
     Body: "New paper on transformer architectures published today"
     Sentiment: NEUTRAL | Score: 0.08

  ...

✅ Done! Results from 2 sources processed.
   Email alerts: 18 displayed
   File records: 18 saved to output.jsonl
```

Notice that posts from BlueSky and articles from RSS are interleaved — both sources run concurrently, and results arrive in whatever order they're processed.

---

## What You've Learned

- **Fanin:** multiple sources → one processor. Add sources by adding edges.
- **Fanout:** one processor → multiple sinks. Add sinks by adding edges.
- **The topology is the design.** Transform functions don't change when you add sources or sinks.
- **Concurrency is automatic.** Both sources run simultaneously. Both sinks receive results simultaneously. You wrote zero threading code.
- **RSSSource** reads any public RSS feed — free, no authentication.
- **MockEmailAlerter** simulates email alerts on the console.

## What's Next

**[Module 4: Smart Routing](../module_04/)** — your app sends all results to both sinks. But what if you want to send *different* results to different places — positive posts to an archive, negative posts to email alerts, and neutral posts just to the console? That's the Split node, and it gives you complete control over where every message goes.
