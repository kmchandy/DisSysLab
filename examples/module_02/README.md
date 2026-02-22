# Module 02: Multiple Sources, Multiple Destinations

*Read from two feeds at once. Send results to two places at once.*

---

## What You'll Build

A news monitor that reads from two demo feeds simultaneously (fanin), analyzes
the sentiment of every article, and sends results to two destinations at the
same time (fanout) — a live display and a file that saves every result.

```
hacker_news ─┐
              ├→ sentiment → display
tech_news   ─┘           └→ results.jsonl
```

Two new ideas appear here that weren't in Module 01:

**Fanin** — multiple sources feed into one node. Messages from both feeds
merge into a single stream and are processed by the same sentiment analyzer.

**Fanout** — one node sends to multiple destinations. Every analyzed article
goes to both the display and the file simultaneously.

This module uses demo components — no API keys needed. Part 3 shows the
two-line change to connect real Claude AI.

---

## Files in This Module

| File                      | What it is                                              |
|---------------------------|---------------------------------------------------------|
| `README.md`               | This file                                               |
| `app.py`                  | The canonical demo app — run this first                 |
| `claude_generated_app.py` | Exactly what Claude produced from the Part 4 prompt     |
| `app_live.py`             | Same app with real Claude API (Part 3)                  |
| `app_extended.py`         | Extended version with spam filtering added              |
| `test_module_02.py`       | Tests you can run to verify everything works            |

---

## Part 1: Run the App (2 minutes)

From the DisSysLab root directory:

```bash
python3 -m examples.module_02.app
```

You should see something like:

```
📰 Two-Feed Sentiment Monitor
════════════════════════════════════════════════════════════

  hacker_news ─┐
                ├→ sentiment → display
  tech_news   ─┘           └→ results.jsonl

  😊 [ POSITIVE] New Python 3.13 features are incredible
  😐 [  NEUTRAL] Stack Overflow Developer Survey results
  😊 [ POSITIVE] Open source project hits 10k GitHub stars
  😊 [ POSITIVE] Rust adoption growing in systems programming
  😞 [ NEGATIVE] Why most software projects fail
  ...

════════════════════════════════════════════════════════════
✅ Done! Results also saved to results.jsonl
```

If you see this output, everything is working. Move to Part 2.

**If something went wrong:** make sure you're running from the DisSysLab
root directory. The command starts with `python3 -m`, not `python3 app.py`.

---

## Part 2: Understand What You Just Built (10 minutes)

Open `app.py`. Two things are new compared to Module 01.

### The network topology

```
  [DemoRSSSource: hacker_news] ──┐
                                  ├──→ [sentiment] ──→ [display]
  [DemoRSSSource: tech_news]   ──┘              └──→ [jsonl_recorder]
```

The sentiment node has **two upstream sources** (fanin) and the sentiment
node sends to **two downstream sinks** (fanout).

### Step 1: Imports

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import DemoEmailAlerter, JSONLRecorder
```

`JSONLRecorder` saves every message to a file in JSON Lines format —
one JSON object per line. This is a common format for storing streaming data.

### Step 2: Create components

```python
hn   = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")

sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

recorder = JSONLRecorder(path="results.jsonl", mode="w", flush_every=1)
```

Two source instances — one for each feed. They run concurrently in separate
threads, producing articles independently.

### Step 3: Write ordinary Python functions

**Source**, **Transform**, **Sink**, and **Message** contracts are the same
as Module 01. The only new behavior is in how the network is wired.

```python
def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],
        "score":     result["score"]
    }

def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} [{article['sentiment']:>8}] {article['text']}")
```

These functions are identical to Module 01. Nothing about them changes when
you add more sources or more sinks — the functions stay simple and focused.

### Step 4: Wrap functions into nodes

```python
hn_source   = Source(fn=hn.run,              name="hacker_news")
tech_source = Source(fn=tech.run,            name="tech_news")
sentiment   = Transform(fn=analyze_sentiment, name="sentiment")
display     = Sink(fn=print_article,          name="display")
archive     = Sink(fn=recorder.run,           name="archive")
```

Two Source nodes, one Transform node, two Sink nodes.

### Step 5: Connect and run — where fanin and fanout happen

```python
g = network([
    (hn_source,   sentiment),   # ← fanin: both sources send to sentiment
    (tech_source, sentiment),   # ← fanin: same destination node
    (sentiment,   display),     # ← fanout: sentiment sends to display
    (sentiment,   archive)      # ← fanout: and also to archive
])
```

**Fanin** happens because `sentiment` appears as the destination in two
edges. The `network()` call specifies a list of edges of a graph, where
each edge is a tuple `(from_node, to_node)`. The agent at `sentiment`
receives messages from whichever source produces them first — the order
is non-deterministic because both source threads run concurrently.

**Fanout** happens because `sentiment` appears as the source in two edges.
DisSysLab automatically copies each outgoing message so that both `display`
and `archive` receive it. The two sink threads run independently — one slow
sink does not delay the other.

```python
g.run_network()
```

DisSysLab starts a thread for each of the five nodes, routes messages
through queues between connected nodes, and shuts everything down cleanly
when both sources have exhausted their articles.

### What's actually happening when you run it

```
hn_source   → produces articles from hacker_news (its own thread)
tech_source → produces articles from tech_news   (its own thread)
sentiment   → receives from both, analyzes each  (its own thread)
display     → receives copies, prints them        (its own thread)
archive     → receives copies, writes to file     (its own thread)
```

All five threads run simultaneously. Articles from the two feeds arrive at
`sentiment` interleaved — you'll see hacker_news and tech_news articles
mixed together in the output. That's correct distributed systems behavior.

---

## Part 3: Connect Real Claude AI (5 minutes)

`app.py` uses demo components. `app_live.py` shows the two-line change for
real Claude AI — identical to Module 01.

**Setup:**

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

**Run:**

```bash
python3 -m examples.module_02.app_live
```

`app_live.py` sets `max_articles=2` per feed. This keeps the number of API
calls small and the cost of running the demo low. You can increase it once
you're comfortable with how the app behaves.

The topology, the transform functions, the sinks — all identical to `app.py`.
Only the import and the agent constructor change.

---

## Part 4: Build Your Own App (homework)

Use your DisSysLab Claude project (set up in Module 01) to describe your
own fanin/fanout app. Here are some prompts to try — or write your own.

### The prompt that generated `claude_generated_app.py`

> Build me a DisSysLab app that reads from the hacker_news and tech_news
> demo feeds, merges them, analyzes sentiment, and sends results to both
> a display and a jsonl file called my_results.jsonl. Use demo components.

### Ideas for your own app

- *"Read from hacker_news and reddit_python, filter spam from both, analyze
  sentiment, and save only positive articles to a file."*
- *"Monitor tech_news and hacker_news simultaneously, detect urgency in each
  article, and print HIGH urgency articles to the terminal."*
- *"Read from all three demo feeds, merge them, analyze sentiment, and send
  results to both a display and a file."*

### Available demo feeds

| Feed name       | What it simulates                    |
|-----------------|--------------------------------------|
| `hacker_news`   | Programming and tech articles        |
| `tech_news`     | General technology news              |
| `reddit_python` | Python community discussions         |

### Available demo AI analyzers

| Constant             | Returns                                                  |
|----------------------|----------------------------------------------------------|
| `SPAM_DETECTOR`      | `{"is_spam": bool, "confidence": float, "reason": str}`  |
| `SENTIMENT_ANALYZER` | `{"sentiment": str, "score": float, "reasoning": str}`   |
| `URGENCY_DETECTOR`   | `{"urgency": str, "metrics": dict, "reasoning": str}`    |

### Available sinks

| Component          | What it does                                  |
|--------------------|-----------------------------------------------|
| `print`            | Prints to terminal                            |
| `DemoEmailAlerter` | Prints formatted email-style alerts           |
| `JSONLRecorder`    | Saves every result to a `.jsonl` file         |

---

## Key Concepts

**Three basic node types.** `Source` generates data. `Transform` processes
it. `Sink` consumes it. Additional node types — such as Split, Broadcast,
and MergeAsynch — are introduced in later modules.

**`None` drops messages.** Any Transform that returns `None` silently removes
that message from the network. Downstream nodes never see it.

**Fanin: multiple sources, one destination.** When two edges share the same
`to_node`, messages from both sources merge into that node's input queue.
The order of arrival is non-deterministic — it depends on thread timing.
Do not write code that assumes a particular order.

**Fanout: one source, multiple destinations.** When two edges share the same
`from_node`, DisSysLab copies each message and delivers it independently to
each destination. Both destinations receive every message. One slow sink does
not delay the other.

**Demo and real components are interchangeable.** The only difference is the
import line. Your app's architecture doesn't change when you go live.

**You write functions; DisSysLab handles the rest.** Threading, queuing,
message copying, shutdown coordination — none of that is your problem.

---

## What's Next

**Module 03** introduces smart routing with the Split node — sending
different messages to different destinations based on their content. You'll
build a monitor that routes positive, negative, and neutral articles to three
separate outputs.