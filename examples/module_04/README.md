# Module 4: Smart Routing

*Send the right data to the right place.*

---

## Files in This Module

| File | What it does |
|------|-------------|
| `README.md` | This guide |
| `example_demo.py` | Demo version: DemoRSS → demo sentiment → Split 3 ways → display (no API key) |
| `example_real.py` | Real version: BlueSky → Claude AI sentiment → Split → archive + console + alerts |
| `test_module_04.py` | Test suite — run with `python3 -m pytest examples/module_04/test_module_04.py -v` |

Run any example from the DisSysLab root:
```bash
python3 -m examples.module_04.example_demo
python3 -m examples.module_04.example_real    # requires ANTHROPIC_API_KEY
```

---

In Module 3 you used fanout — every result went to every sink. That's useful when you want everything everywhere, but real systems need smarter routing. Positive customer feedback should go to the marketing archive. Negative feedback should trigger an alert. Neutral posts might just go to a log. The Split node gives you this control.

---

## Part 1: Try the Demo First (5 minutes)

Run the demo version to see Split routing in action without needing an API key:

```bash
python3 -m examples.module_04.example_demo
```

This uses `DemoRSSSource` and `demo_ai_agent(SENTIMENT_ANALYZER)` — familiar components from earlier modules. The new piece is the Split node that routes posts to different outputs based on sentiment.

```
  rss_feed  →  sentiment  →  splitter  →  out_0: archive (positive)
                                        →  out_1: console (all non-neutral)
                                        →  out_2: alerts (negative)
```

Watch the output: positive posts go to the archive and console, negative posts go to console and email alerts, neutral posts go to console only.

---

## Part 2: Understanding the Split Node (15 minutes)

### What's new: a node with multiple outputs

Up to now, every node had one output. Source produces data, Transform processes it, Sink consumes it — all single-output. The Split node has **multiple output ports**, and your function decides which ports each message goes to.

### The routing function

The core of Split is a Python function that returns a list:

```python
def route_by_sentiment(article):
    score = article["score"]
    if score > 0.2:
        return [article, article, None]    # positive → out_0 AND out_1
    elif score < -0.2:
        return [None, article, article]    # negative → out_1 AND out_2
    else:
        return [None, article, None]       # neutral → out_1 only
```

The list has one element per output port. Non-None elements get sent. None elements are skipped. That's the entire contract.

### Why this routing is interesting

Look at what each output receives:

- **out_0 (archive):** positive posts only
- **out_1 (console):** positive AND negative posts — everything except neutral
- **out_2 (alerts):** negative posts only

A single message can go to *multiple* destinations selectively. This is something fanout can't do cleanly. Fanout sends everything everywhere; Split sends each message exactly where you want it.

### The network definition

```python
from dsl.blocks import Source, Transform, Sink, Split

splitter = Split(fn=route_by_sentiment, num_outputs=3, name="router")

g = network([
    (source, sentiment),
    (sentiment, splitter),
    (splitter.out_0, archive),     # positive → file
    (splitter.out_1, console),     # positive + negative → screen
    (splitter.out_2, alerts)       # negative → email
])
```

Notice the syntax: `splitter.out_0`, `splitter.out_1`, `splitter.out_2`. These are **port references** — they tell the network which output port connects to which downstream node. Regular nodes don't need port references because they have only one output.

### Split vs. Fanout

| | Fanout (Module 3) | Split (this module) |
|---|---|---|
| How it works | Copies every message to all destinations | Your function chooses which destinations |
| Each message goes to | ALL connected nodes | The ports YOU specify |
| Syntax | `(transform, sink1), (transform, sink2)` | `(splitter.out_0, sink1), (splitter.out_1, sink2)` |
| Use when | Everyone should see everything | Different destinations need different data |

### The mental model

Think of Split as a mail sorter. Every letter arrives at the sorting desk. The sorter reads the address and puts each letter in the right bin. Some letters go to one bin, some to another, some to multiple bins, and junk mail goes in the trash (all Nones — the message is dropped).

---

## Part 3: Run With Real AI (10 minutes)

### Setup

No new setup needed. Everything is in your Claude Project from Modules 2 and 3. Make sure your `CLAUDE_CONTEXT.md` includes the Split section (the latest version does).

### Run it

```bash
python3 -m examples.module_04.example_real
```

The real version uses BlueSky + Claude AI:

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.ai_agent import ai_agent
from components.sinks import JSONLRecorder, MockEmailAlerter

# --- Live data ---
bluesky = BlueSkyJetstreamSource(filter_keywords=["AI", "machine learning"], max_posts=5)

# --- Real AI ---
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)

def analyze_sentiment(post):
    text = post["text"] if isinstance(post, dict) else post
    result = sentiment_analyzer(text)
    return {
        "text": text,
        "sentiment": result.get("sentiment", "UNKNOWN"),
        "score": result.get("score", 0.0),
        "reasoning": result.get("reasoning", "")
    }

def route_by_sentiment(article):
    score = article["score"]
    if score > 0.2:
        return [article, article, None]    # positive → archive + console
    elif score < -0.2:
        return [None, article, article]    # negative → console + alerts
    else:
        return [None, article, None]       # neutral → console only
```

Real posts from real people, analyzed by real AI, routed to different destinations based on what the AI found.

---

## Part 4: Side-by-Side — Fanout vs Split (10 minutes)

Module 3's fanout:
```python
g = network([
    (source, sentiment),
    (sentiment, file_sink),      # ALL results → file
    (sentiment, email_sink)      # ALL results → email (same data!)
])
```

Module 4's split:
```python
g = network([
    (source, sentiment),
    (sentiment, splitter),
    (splitter.out_0, archive),   # positive only → file
    (splitter.out_1, console),   # non-neutral → screen
    (splitter.out_2, alerts)     # negative only → email
])
```

The difference is one new node (the splitter) and port references instead of direct connections. The source, the sentiment transform, and the sinks are all unchanged. The routing logic lives in a single Python function.

---

## Part 5: Make It Yours (15 minutes)

### Experiment 1: Route by urgency

Ask Claude:

> Change my app to use URGENCY_DETECTOR instead of SENTIMENT_ANALYZER. Route HIGH urgency to email alerts, LOW urgency to the archive, and MEDIUM urgency to console only.

Same Split pattern, different AI analysis, different routing logic.

### Experiment 2: Add a "catch all" path

Ask Claude:

> Add a fourth output to the split. Send ALL posts to out_3, connected to a JSONL file called all_posts.jsonl. Keep the other routing the same.

Now you have selective routing for three paths plus a complete archive. The routing function returns a list of 4 elements instead of 3.

### Experiment 3: Combine fanin with split

Ask Claude:

> Add an RSS source (Hacker News) that merges with the BlueSky source before sentiment analysis. Keep the split routing the same.

This combines Module 3's fanin with Module 4's split — a full diamond network:

```
  bluesky    ─┐
               ├→  sentiment  →  splitter  →  out_0: archive
  hackernews ─┘                            →  out_1: console
                                           →  out_2: alerts
```

Two sources fan in, processing happens, results route to three different destinations based on content.

### Experiment 4: Drop messages entirely

Modify the routing function to drop neutral posts completely:

```python
def route_by_sentiment(article):
    score = article["score"]
    if score > 0.2:
        return [article, None, None]     # positive → archive only
    elif score < -0.2:
        return [None, None, article]     # negative → alerts only
    else:
        return [None, None, None]        # neutral → DROPPED
```

Neutral posts go nowhere — they're filtered out by the split. This shows that Split can filter too, not just route.

---

## What You've Learned

- **The Split node** routes messages to specific output ports based on your logic.
- **Port references** (`splitter.out_0`, `splitter.out_1`, etc.) connect split outputs to downstream nodes.
- **The routing function** returns a list — non-None elements go to their port, None elements are skipped.
- **A message can go to multiple ports** — selective broadcasting, not just one-to-one routing.
- **Split can also filter** — return all Nones to drop a message entirely.
- **Patterns compose:** fanin (Module 3) + split (Module 4) = a complete monitoring and routing system.

## What's Next

**[Module 5: Build Your Own App](../module_05/)** — you now know pipelines, fanin, fanout, AI integration, and content-based routing. Module 5 gives you a systematic process for designing and building the application *you* want — not a textbook exercise.