# DisSysLab — Context for Claude

You are helping a person to use natural language to build a custom DisSysLab application from scratch.
DisSysLab is a Python framework for building persistent streaming applications.
Ordinary Python functions are wrapped into concurrent nodes connected by message queues.
The framework handles all threading, synchronization, and shutdown automatically.

You write the logic. DisSysLab handles concurrency, message passing, and shutdown.

---

## The Three Building Blocks

**Source** — generates messages, has no inputs.
```python
from dsl.blocks import Source

source = Source(fn=my_generator, name="source_name")
```
The function is called repeatedly. Return one message per call. Generator
functions are accepted directly — `Source` wraps them automatically.

**Transform** — receives one message, returns one (or None to drop it).
```python
from dsl.blocks import Transform

transform = Transform(fn=my_function, name="transform_name")
```
Return `None` to drop the message — it will not reach downstream nodes.

**Sink** — receives messages, produces no output.
```python
from dsl.blocks import Sink

sink = Sink(fn=my_function, name="sink_name")
```

---

## Wiring a Network
```python
from dsl import network
from dsl.blocks import Source, Transform, Sink

g = network([
    (source,    transform),
    (transform, sink),
])

if __name__ == "__main__":
    g.run_network(timeout=None)   # runs forever — Ctrl+C to stop
```

**Filtering** — return `None` to drop a message:
```python
def only_long_articles(article):
    if len(article["text"]) < 100:
        return None   # dropped
    return article

filter_node = Transform(fn=only_long_articles, name="filter")
```

**Fanin** — merge multiple sources into one node:
```python
g = network([
    (source1, transform),
    (source2, transform),   # both feed the same node
    (transform, sink),
])
```

**Fanout** — send one message to multiple destinations:
```python
g = network([
    (source,    transform),
    (transform, sink1),     # same message goes to both
    (transform, sink2),
])
```

---

## Messages

Messages are plain Python dicts. Transforms add keys as a message flows
through the pipeline — they don't change the shape.
```python
# Starts as:
{"text": "Solar panels hit record efficiency"}

# After sentiment transform:
{"text": "Solar panels hit record efficiency", "sentiment": "POSITIVE", "score": 0.9}

# After topic transform:
{"text": "...", "sentiment": "POSITIVE", "score": 0.9, "topic": "energy"}
```

---

## Starting Point: A Simple Custom App

Here is the minimal pattern for a custom app. Fill in your own source,
transform logic, and sink:
```python
import json
from dsl import network
from dsl.blocks import Source, Transform, Sink

# ── Your data source ──────────────────────────────────────────
def my_source():
    """Replace this with your real data source."""
    items = [
        {"text": "First item", "id": 1},
        {"text": "Second item", "id": 2},
    ]
    for item in items:
        yield item

# ── Your processing logic ─────────────────────────────────────
def my_transform(msg):
    """Replace this with your real processing logic.
    Return None to drop the message."""
    msg["processed"] = True
    return msg

# ── Your output ───────────────────────────────────────────────
def my_sink(msg):
    """Replace this with your real output — print, save, send."""
    print(msg)

# ── Wire the network ──────────────────────────────────────────
source    = Source(fn=my_source,    name="source")
transform = Transform(fn=my_transform, name="transform")
sink      = Sink(fn=my_sink,        name="sink")

g = network([
    (source,    transform),
    (transform, sink),
])

if __name__ == "__main__":
    g.run_network(timeout=None)
```

---

## Real AI Transforms: ai_agent

To add AI analysis to any pipeline, use `ai_agent`. It takes a prompt string
and returns a callable. Call it with text, parse the JSON response.
```python
from components.transformers.ai_agent import ai_agent
import json

# Requires: export ANTHROPIC_API_KEY='your-key'
sentiment_agent = ai_agent("""
    What is the sentiment of this text?
    Return JSON only, no explanation: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "score": -1.0 to 1.0}
""")

def analyze_sentiment(msg):
    result = json.loads(sentiment_agent(msg["text"]))
    msg["sentiment"] = result["sentiment"]
    msg["score"]     = result["score"]
    return msg
```

**Filter with AI:**
```python
relevance_agent = ai_agent("""
    Is this article about renewable energy?
    Return JSON only, no explanation: {"relevant": true or false}
""")

def filter_relevant(msg):
    if not msg.get("text", "").strip():
        return None
    result = json.loads(relevance_agent(msg["text"]))
    if not result["relevant"]:
        return None
    return msg
```

**Prompt writing rules:**
- Always end JSON prompts with: `Return JSON only, no explanation: {"key": value}`
- One concern per transform — one new key per `ai_agent` call
- For plain text output (e.g. summaries): `"Return plain text, not JSON"`

---

## Demo Mode: Test Without an API Key

Every real component has a demo version. Use these to build and test your
app before spending API credits.

**ListSource** — emits items from a Python list instead of a live feed:
```python
from dsl.blocks import ListSource

items = [{"text": "Article one"}, {"text": "Article two"}]
source = Source(fn=ListSource(items=items).run, name="source")
```

**demo_ai_agent** — simulates AI responses with keyword matching, no API call:
```python
from components.transformers.demo_ai_agent import demo_ai_agent
from components.transformers.prompts import SENTIMENT_ANALYZER

agent = demo_ai_agent(prompt=SENTIMENT_ANALYZER)

def analyze_sentiment(msg):
    result = agent(msg["text"])
    msg["sentiment"] = result["sentiment"]
    return msg
```

**Swapping demo for real is one import change:**
```python
# Demo:
from components.transformers.demo_ai_agent import demo_ai_agent
agent = demo_ai_agent(prompt=SENTIMENT_ANALYZER)

# Real:
from components.transformers.ai_agent import ai_agent
agent = ai_agent("""
    Analyze sentiment.
    Return JSON only, no explanation: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "score": -1.0 to 1.0}
""")
```

**Available demo prompts** (import from `components.transformers.prompts`):
- `SENTIMENT_ANALYZER` — `{"sentiment": "POSITIVE"|"NEGATIVE"|"NEUTRAL", "score": float}`
- `SPAM_DETECTOR` — `{"is_spam": bool, "confidence": float}`
- `TOPIC_CLASSIFIER` — `{"topic": str, "confidence": float}`
- `SUMMARIZER` — `{"summary": str}`
- `ENTITY_EXTRACTOR` — `{"entities": [str]}`

---

## Common App Patterns

### Monitor a data source continuously
```python
import time

def my_source():
    while True:
        data = fetch_something()   # your fetch logic
        for item in data:
            yield item
        print("Sleeping 60s...")
        time.sleep(60)

source = Source(fn=my_source, name="monitor")
```

### Save results to a file
```python
import json

def save_to_file(msg):
    with open("results.jsonl", "a") as f:
        f.write(json.dumps(msg) + "\n")

file_sink = Sink(fn=save_to_file, name="file_sink")
```

### Stream to console and save to file simultaneously (fanout)
```python
def display(msg):
    print(f"[{msg.get('source', '?')}] {msg.get('title', '')}")

display_sink = Sink(fn=display,       name="display")
file_sink    = Sink(fn=save_to_file,  name="file_sink")

g = network([
    (source,    transform),
    (transform, display_sink),   # fanout
    (transform, file_sink),
])
```

### Merge two data sources (fanin)
```python
source1 = Source(fn=feed_one.run, name="feed_one")
source2 = Source(fn=feed_two.run, name="feed_two")

g = network([
    (source1, transform),   # fanin
    (source2, transform),
    (transform, sink),
])
```

---

## How to Ask for Help

Paste this document into Claude along with your spec:
```
I want to build a DisSysLab app that:

SOURCE:
  - [describe your data source — RSS feed, CSV file, API, database, etc.]

PROCESSING:
  - [one line per step, e.g. "filter out articles shorter than 100 words"]
  - [e.g. "classify each item as urgent or not using AI"]

OUTPUT:
  - [e.g. "print to console" or "save to a JSONL file" or "both"]

Start with demo components so I can run it without an API key.
```

Claude will generate a complete working app. Once it runs, swap the demo
components for real ones when you are ready.

---

## Want More Examples?

Browse `gallery/` for complete working apps — RSS monitors, email
assistants, research trackers, and more. Each folder has a README
explaining what it does and how to run it.