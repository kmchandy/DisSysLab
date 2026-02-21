# Module 01: Describe and Build

*Ask Claude for an app. Run it. It works. Then make it yours.*

---

## What You'll Build

A live news monitor that reads from a Hacker News feed, automatically filters
out spam, analyzes the sentiment of every article, and prints the results —
all running concurrently in a distributed pipeline.

```
hacker_news → spam_filter → sentiment → display
```

You don't need to understand threads, queues, or concurrency to build this.
DisSysLab handles all of that. You write ordinary Python functions. The
framework connects them into a distributed system.

This module uses **demo components** — simulated data and keyword-based AI
that run instantly with no API keys. Part 3 shows you the one-line change
that connects the same app to real Claude AI. Part 4 is homework: describe
your own app and Claude will generate it.

---

## Files in This Module

| File                    | What it is                                              |
|-------------------------|---------------------------------------------------------|
| `README.md`             | This file                                               |
| `app.py`                | The canonical demo app — run this first                 |
| `claude_generated_app.py` | Exactly what Claude produced from the Part 4 prompt   |
| `app_live.py`           | Same app with real Claude API (Part 3)                  |
| `app_extended.py`       | Extended version with urgency detection (experiments)   |
| `test_module_01.py`     | Tests you can run to verify everything works            |

`app.py` and `claude_generated_app.py` run identically. `app.py` has extra
comments to help you read it. `claude_generated_app.py` is the unedited
output from Claude — useful for comparing with what Claude generates for you.

---

## Part 1: Run the App (2 minutes)

From the DisSysLab root directory:

```bash
python3 -m examples.module_01_describe_and_build.app
```

You should see something like:

```
📰 Hacker News Feed — Spam Filtered, Sentiment Analyzed
════════════════════════════════════════════════════════════

  😊 [ POSITIVE] New Python 3.13 features are incredible
  😐 [  NEUTRAL] Stack Overflow Developer Survey results
  😊 [ POSITIVE] Open source project hits 10k GitHub stars
  😞 [ NEGATIVE] Why most software projects fail
  😊 [ POSITIVE] Rust adoption growing in systems programming

════════════════════════════════════════════════════════════
✅ Done! Four concurrent nodes processed 10 articles.

Spam articles were silently dropped (filter returned None).
Each remaining article was analyzed for sentiment.
```

If you see this output, everything is working. Move to Part 2.

**If something went wrong:** make sure you're running from the DisSysLab
root directory, not from inside the module folder. The command starts with
`python3 -m`, not `python3 app.py`.

---

## Part 2: Understand What You Just Built (10 minutes)

Open `app.py`. Here's a walkthrough of every section.

### The network topology

```
  [DemoRSSSource]
        |
        | "Python 3.13 features are incredible"
        ↓
  [spam_filter]  ← returns None for spam → message dropped
        |
        | "Python 3.13 features are incredible"
        ↓
  [sentiment]    ← adds sentiment + score to a dict
        |
        | {"text": "Python 3.13...", "sentiment": "POSITIVE", "score": 0.9}
        ↓
  [display]      ← prints with emoji
```

Each box is a node running in its own thread. Messages flow between them
through queues that DisSysLab manages automatically.

### Step 1: Imports

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
```

`Source`, `Transform`, and `Sink` are the three node types. Every DisSysLab
app uses exactly these building blocks.

### Step 2: Create components

```python
rss = DemoRSSSource(feed_name="hacker_news")

spam_detector      = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
```

`DemoRSSSource` simulates a live RSS feed — 10 articles including a few spam
ones. `demo_ai_agent` is a keyword-based analyzer that behaves like real
Claude AI but needs no API key. `SPAM_DETECTOR` and `SENTIMENT_ANALYZER` are
prompt constants that tell the agent what to analyze.

### Step 3: Write ordinary Python functions

Before reading the code, here are the contracts each node type enforces:

**Source** — has a method called `run()` that takes no arguments and returns
one message per call. When there are no more messages, it returns `None` to
signal the network to shut down. A Source never receives messages from other
nodes.

**Transform** — receives one message and returns one message. The returned
message is passed to the next node. Returning `None` drops the message
silently — downstream nodes never see it. This is how filtering works.

**Sink** — receives one message and takes some action (print, write to file,
send an alert). It does not return a message. A Sink is the end of the line.

**Message** — any Python object that can be sent between threads. In
practice this means strings, numbers, dicts, lists, and combinations of
those. See the [Python docs on pickleable objects](https://docs.python.org/3/library/pickle.html#what-can-be-pickled-and-unpickled)
for the full definition.

```python
def filter_spam(text):
    result = spam_detector(text)
    if result["is_spam"]:
        return None      # ← returning None drops the message silently
    return text


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

These are plain Python functions. They know nothing about threads or queues.

**The key insight:** returning `None` from any Transform function silently
drops that message. Downstream nodes never see it. This is how filtering
works in DisSysLab.

### Step 4: Wrap functions into nodes

```python
source    = Source(fn=rss.run,              name="rss_feed")
spam_gate = Transform(fn=filter_spam,       name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display   = Sink(fn=print_article,          name="display")
```

`Source` wraps a function that *produces* data. `Transform` wraps a function
that *processes* data. `Sink` wraps a function that *consumes* data and sends
nothing further downstream. Each runs in its own thread.

### Step 5: Connect and run

```python
g = network([
    (source,    spam_gate),
    (spam_gate, sentiment),
    (sentiment, display)
])

g.run_network()
```

The `network()` call specifies a list of edges of a graph, where each edge
is a tuple `(from_node, to_node)`. Associated with each node is an agent —
a Source, Transform, Sink, or other agent type discussed in later modules.
The stream of messages produced by the agent at `from_node` is received by
the agent at `to_node`. This is like a wiring diagram.

DisSysLab starts a thread that runs the agent at each node, routes messages
through queues between connected nodes, and shuts everything down cleanly
when the source agent signals it has no more messages to send.

---

## Part 3: Connect Real Claude AI (5 minutes)

`app.py` uses demo components so it always works with no setup. `app_live.py`
shows the exact change needed to use real Claude AI.

**The only difference between `app.py` and `app_live.py` is two lines:**

```python
# app.py (demo)                              # app_live.py (real)
from components.transformers                 from components.transformers
    .demo_ai_agent import demo_ai_agent          .ai_agent import ai_agent

spam_detector = demo_ai_agent(...)           spam_detector = ai_agent(...)
```

Everything else — the transform functions, the network topology, the sink —
stays exactly the same. This is intentional: DisSysLab is designed so that
demo and real components are interchangeable.

### Set up your API key

You need an Anthropic API key. If you completed Module 0, you already have one.

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

Then run:

```bash
python3 -m examples.module_01_describe_and_build.app_live
```

The output looks identical to `app.py`, but the analysis is now done by
Claude. You'll notice it's slower — that's the network round-trip to the API.
That's real distributed systems behavior: your pipeline is now talking to an
AI running on a server somewhere in the world.

**If you don't have an API key yet**, that's fine. Stay with `app.py` for
now. You can come back to `app_live.py` any time.

---

## Part 4: Build Your Own App (homework)

Now that you've seen the pattern, describe your own app and let Claude
generate it. For reference, `claude_generated_app.py` in this module is the
exact unedited output Claude produced when given the prompt below — you can
run it and compare it with `app.py`.

### One-time setup: teach Claude about DisSysLab

1. Go to [claude.ai](https://claude.ai) and sign in.
2. In the left sidebar, click **Projects** → **Create Project**.
   Name it **DisSysLab**.
3. Inside the project, find the **Files** section (not Instructions)
   and upload `CLAUDE_CONTEXT.md` from the DisSysLab root directory.
   You can drag and drop it, or click to browse.
4. Every conversation you start inside this project will now understand
   DisSysLab and generate correct apps.

> **Why Files, not Instructions?** Instructions are for telling Claude how to
> behave. Files are reference material Claude reads when it needs context.
> `CLAUDE_CONTEXT.md` is a technical reference — it belongs in Files.

### The prompt that generated `claude_generated_app.py`

Start a new conversation inside your DisSysLab project and use this prompt
to reproduce what's in `claude_generated_app.py`:

> Build me a DisSysLab app that monitors the hacker_news demo feed, filters
> out spam, analyzes the sentiment of each article, and prints the results.
> Use demo components.

Save Claude's output as a `.py` file, run it, and compare it with
`claude_generated_app.py` in this module.

### Now describe something you'd actually want

The best homework app is one you'd genuinely use. Change the prompt to
describe your own idea. Some starting points:

- *"Monitor the tech_news feed, keep only articles about open source
  software, analyze sentiment, and save results to a file."*
- *"Read from the reddit_python feed, filter out anything shorter than
  20 words, analyze urgency, and print HIGH urgency articles only."*
- *"Monitor hacker_news and tech_news simultaneously, filter spam from
  both, and print a combined sentiment-analyzed feed."*

### Available demo feeds

| Feed name       | What it simulates                    |
|-----------------|--------------------------------------|
| `hacker_news`   | Programming and tech articles        |
| `tech_news`     | General technology news              |
| `reddit_python` | Python community discussions         |

Stick to these feeds for now. Sources like X/Twitter require API
authentication that can turn a 10-minute win into a debugging session.
You'll add real-world sources in later modules.

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
it. `Sink` consumes it. Every DisSysLab app is some combination of these.
Additional node types — such as Split, Broadcast, and MergeAsynch — are
introduced in later modules.

**`None` drops messages.** Any Transform that returns `None` silently removes
that message from the network. Downstream nodes never see it. This is how
filtering works.

**Demo and real components are interchangeable.** The only difference is the
import line. Your app's architecture doesn't change when you go live.

**You write functions; DisSysLab handles the rest.** Threading, queuing,
shutdown coordination — none of that is your problem.

---

## What's Next

**Module 02** introduces fanin and fanout — merging multiple sources into
one pipeline, and splitting one pipeline into multiple destinations. You'll
build a monitor that reads from two feeds simultaneously and sends results
to two different outputs.