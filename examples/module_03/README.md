# Module 03: Smart Routing

*Send the right message to the right place.*

---

## What You'll Build

A news monitor that reads from a Hacker News feed, analyzes the sentiment
of each article, and routes articles to three different destinations based
on their sentiment:

```
                              ┌→ positive → archive (results.jsonl)
hacker_news → sentiment → split ┤→ negative → alerts  (email-style display)
                              └→ neutral  → display  (terminal)
```

One new idea appears here that wasn't in Modules 01 or 02:

**Split** — a node that routes each message to a specific output port based
on your logic. Unlike fanout, which copies every message to every destination,
Split sends each message to exactly the destination it belongs in.

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
| `test_module_03.py`       | Tests you can run to verify everything works            |

---

## Part 1: Run the App (2 minutes)

From the DisSysLab root directory:

```bash
python3 -m examples.module_03.app
```

You should see something like:

```
📰 Sentiment Router — Three-Way Split
════════════════════════════════════════════════════════════

  hacker_news → sentiment → split → positive → archive
                                  → negative → alerts
                                  → neutral  → display

[DISPLAY - NEUTRAL]
  😐 Stack Overflow Developer Survey results

[ALERT - NEGATIVE]
  📧 To: alerts@newsroom.com
  📧 Subject: [ALERT] Negative article detected
  😞 Why most software projects fail

════════════════════════════════════════════════════════════
✅ Done! Positive articles saved to results.jsonl
```

If you see output routed to different destinations, everything is working.
Move to Part 2.

**If something went wrong:** make sure you're running from the DisSysLab
root directory. The command starts with `python3 -m`, not `python3 app.py`.

---

## Part 2: Understand What You Just Built (10 minutes)

Open `app.py`. One thing is new compared to Modules 01 and 02.

### The network topology

```
  [DemoRSSSource]
        |
        ↓
  [sentiment]  ← adds sentiment + score to each article
        |
        ↓
  [splitter]   ← routes each article to one of three ports
     |    |    |
     ↓    ↓    ↓
  out_0 out_1 out_2
     |    |    |
     ↓    ↓    ↓
 [archive][alerts][display]
```

### Step 1: Imports

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import DemoEmailAlerter, JSONLRecorder
```

`Split` is the new import. It is the fourth basic node type.

### Step 2: Create components

```python
rss                = DemoRSSSource(feed_name="hacker_news")
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
recorder           = JSONLRecorder(path="results.jsonl", mode="w", flush_every=1)
alerter            = DemoEmailAlerter(to_address="alerts@newsroom.com",
                                      subject_prefix="[ALERT]")
```

### Step 3: Write ordinary Python functions

The routing function is the key new concept. It receives one message and
returns a list — one element per output port. Non-None elements are sent
to the corresponding port. None elements mean "skip this port."

```python
def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {
        "text":      text,
        "sentiment": result["sentiment"],
        "score":     result["score"]
    }


def route_by_sentiment(article):
    """
    Route each article to exactly one output port based on sentiment.

    Returns a list of 3 elements — one per output port:
      out_0 ← positive articles  → archive
      out_1 ← negative articles  → alerts
      out_2 ← neutral articles   → display

    Non-None elements are sent to the corresponding port.
    None elements mean "skip this port."
    """
    if article["sentiment"] == "POSITIVE":
        return [article, None,    None   ]   # → out_0
    elif article["sentiment"] == "NEGATIVE":
        return [None,    article, None   ]   # → out_1
    else:
        return [None,    None,    article]   # → out_2


def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} {article['text']}")
```

**The Split function contract:**
- Receives one message
- Returns a list of exactly `num_outputs` elements
- Each element is either the message (to send) or `None` (to skip)
- The list length must match `num_outputs` exactly

### Step 4: Wrap functions into nodes

```python
source    = Source(fn=rss.run,              name="rss_feed")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
splitter  = Split(fn=route_by_sentiment,    num_outputs=3,  name="router")
archive   = Sink(fn=recorder.run,           name="archive")
alerts    = Sink(fn=alerter.run,            name="alerts")
display   = Sink(fn=print_article,          name="display")
```

`Split` takes a `num_outputs` parameter. DisSysLab automatically creates
output ports named `out_0`, `out_1`, `out_2`, and so on.

### Step 5: Connect and run — where Split happens

```python
g = network([
    (source,          sentiment),
    (sentiment,       splitter),
    (splitter.out_0,  archive),    # ← positive articles → archive
    (splitter.out_1,  alerts),     # ← negative articles → alerts
    (splitter.out_2,  display)     # ← neutral articles  → display
])
```

Port references (`splitter.out_0`, `splitter.out_1`, `splitter.out_2`)
connect each output port to its downstream node. The port number corresponds
to the index in the list returned by the routing function.

The `network()` call specifies a list of edges of a graph, where each edge
is a tuple `(from_node, to_node)`. For Split nodes, the `from_node` is a
port reference rather than the node itself. DisSysLab starts a thread for
each node, routes messages through queues, and shuts everything down cleanly
when the source runs out of articles.

### Split vs. Fanout — the key difference

**Fanout** (Module 02) copies every message to every destination:
```
article → [archive, alerts, display]   ← all three get every article
```

**Split** (this module) routes each message to one destination:
```
positive article → [archive, None,   None   ]  ← only archive
negative article → [None,    alerts, None   ]  ← only alerts
neutral article  → [None,    None,   display]  ← only display
```

Use fanout when every destination needs every message.
Use Split when each message belongs in exactly one place.

---

## Part 3: Connect Real Claude AI (5 minutes)

`app.py` uses demo components. `app_live.py` shows the two-line change for
real Claude AI.

**Setup:**

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

**Run:**

```bash
python3 -m examples.module_03.app_live
```

`app_live.py` sets `max_articles=2` to keep API calls and cost low. You
can increase this once you're comfortable with how the app behaves.

---

## Part 4: Build Your Own App (homework)

Use your DisSysLab Claude project to describe your own routing app.

### The prompt that generated `claude_generated_app.py`

> Build me a DisSysLab app that reads from the hacker_news demo feed,
> analyzes sentiment, and routes articles to three outputs: positive
> articles saved to a jsonl file, negative articles printed as email
> alerts, and neutral articles printed to the terminal. Use demo components.

### Ideas for your own app

- *"Read from tech_news, detect urgency, and route HIGH urgency articles
  to an email alert, MEDIUM to a file, and LOW to the terminal."*
- *"Monitor hacker_news and reddit_python, filter spam, analyze sentiment,
  and route only positive articles to a file."*
- *"Read from all three feeds, analyze sentiment, and route positive and
  neutral articles to a file while dropping negative ones."*

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

**Split is the fourth basic node type.** It routes each message to one or
more specific output ports based on your routing function. Port references
(`splitter.out_0`, `splitter.out_1`, etc.) connect each port to its
downstream node.

**The Split function contract.** Your routing function receives one message
and returns a list of exactly `num_outputs` elements. Non-None elements are
sent to the corresponding port. None elements skip that port. The list
length must match `num_outputs` exactly.

**Split vs. Fanout.** Fanout copies every message to every destination.
Split routes each message to the destination it belongs in. Use Split when
messages need to be sorted by content.

**`None` drops messages.** Any Transform that returns `None` silently removes
that message. In a Split routing function, `None` at a list position means
"skip this port" — not a dropped message, just a skipped destination.

**Demo and real components are interchangeable.** The only difference is the
import line.

---

## What's Next

**Module 04** puts it all together — fanin, fanout, and Split combined in
one app that reads from multiple sources, filters, analyzes, and routes
to multiple destinations.
