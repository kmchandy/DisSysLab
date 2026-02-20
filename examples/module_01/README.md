# Module 01: Describe and Build

*Ask Claude for an app. Run it. It works. Then make it yours.*

---

## What You'll Build

A live news monitor that reads from a Hacker News feed, automatically filters out
spam, analyzes the sentiment of every article, and prints the results — all running
concurrently in a distributed pipeline.

```
hacker_news → spam_filter → sentiment → display
```

You don't need to understand threads, queues, or concurrency to build this. DisSysLab
handles all of that. You write ordinary Python functions. The framework connects them
into a distributed system.

This module uses **demo components** — simulated data and keyword-based AI that run
instantly with no API keys. Part 3 shows you the one-line change that connects the
same app to real Claude AI.

---

## Files in This Module

| File               | What it is                                              |
|--------------------|---------------------------------------------------------|
| `README.md`        | This file                                               |
| `app.py`           | The canonical demo app — run this first                 |
| `app_live.py`      | Same app with real Claude API (Part 3)                  |
| `app_extended.py`  | Extended version with urgency detection (experiments)   |
| `test_module_01.py`| Tests you can run to verify everything works            |

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
  😞 [NEGATIVE] Why most software projects fail
  😊 [ POSITIVE] Rust adoption growing in systems programming

════════════════════════════════════════════════════════════
✅ Done! Four concurrent nodes processed 10 articles.

Spam articles were silently dropped (filter returned None).
Each remaining article was analyzed for sentiment.
```

If you see this output, everything is working. Move to Part 2.

**If something went wrong**, check that you're running from the DisSysLab root
directory (not from inside the module folder). The command starts with `python3 -m`.

---

## Part 2: Understand What You Just Built (10 minutes)

Open `app.py`. Here's the complete code with annotations:

### Step 1: Import the framework and components

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
```

`Source`, `Transform`, and `Sink` are the three node types. Every DisSysLab app
uses exactly these building blocks.

### Step 2: Create the data source and AI components

```python
rss = DemoRSSSource(feed_name="hacker_news")

spam_detector    = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
```

`DemoRSSSource` simulates a live RSS feed. `demo_ai_agent` is a keyword-based
analyzer that behaves like real Claude AI but needs no API key.

### Step 3: Write ordinary Python functions

```python
def filter_spam(text):
    result = spam_detector(text)
    if result["is_spam"]:
        return None      # ← returning None drops the message
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
The key insight: **returning `None` from any transform drops that message
from the network.** Spam articles disappear silently.

### Step 4: Wrap functions into nodes

```python
source    = Source(fn=rss.run,            name="rss_feed")
spam_gate = Transform(fn=filter_spam,     name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display   = Sink(fn=print_article,        name="display")
```

Each node runs in its own thread. Messages flow between them through queues
that DisSysLab manages automatically.

### Step 5: Connect the nodes and run

```python
g = network([
    (source,    spam_gate),
    (spam_gate, sentiment),
    (sentiment, display)
])

g.run_network()
```

The `network()` call reads like a wiring diagram. Each tuple is one connection.
Left side sends, right side receives.

### What's actually happening when you run it

```
source      → produces articles one at a time (its own thread)
spam_gate   → receives each article, drops spam (its own thread)
sentiment   → receives clean articles, adds sentiment (its own thread)
display     → receives analyzed articles, prints them (its own thread)
```

All four threads run simultaneously. DisSysLab shuts everything down cleanly
when the source runs out of articles.

---

## Part 3: Connect Real Claude AI (5 minutes)

`app.py` uses demo components so that it always works with no setup. When you're
ready to use real Claude AI, `app_live.py` shows you the exact change.

**The only difference between `app.py` and `app_live.py` is two lines:**

```python
# app.py (demo)                          # app_live.py (real)
from components.transformers             from components.transformers
    .demo_ai_agent import demo_ai_agent      .ai_agent import ai_agent

spam_detector = demo_ai_agent(...)       spam_detector = ai_agent(...)
```

Everything else — the transform functions, the network topology, the sink — stays
exactly the same. This is intentional. DisSysLab is designed so that demo and real
components are interchangeable.

### Setting up your API key

You need an Anthropic API key. If you completed Module 0, you already have one.

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

Then run:

```bash
python3 -m examples.module_01_describe_and_build.app_live
```

The output looks identical to `app.py`, but the sentiment analysis is now done
by Claude. You'll notice it's slower — that's the network round-trip to the API.
That's real distributed systems behavior.

**If you don't have an API key yet**, that's fine. Stay with `app.py` for now.
You can come back to `app_live.py` any time.

---

## Part 4: Build Your Own App (homework)

Now that you've seen the pattern, describe your own app and let Claude generate it.

### One-time setup: teach Claude about DisSysLab

1. Go to [claude.ai](https://claude.ai) and sign in.
2. In the left sidebar, click **Projects** → **Create Project**. Name it **DisSysLab**.
3. Inside the project, click **Files** and upload `CLAUDE_CONTEXT.md` from the
   DisSysLab root directory. (This is the file that teaches Claude how to generate
   DisSysLab apps. Put it in **Files**, not in Instructions.)
4. Every conversation you start inside this project will now know DisSysLab.

### Describe your app

Start a new conversation inside your DisSysLab project and write a prompt like:

> Build me a DisSysLab app that monitors the tech_news feed, filters out
> articles shorter than 20 words, analyzes sentiment, and saves the results
> to a file called `results.jsonl`. Use demo components.

Claude will generate a complete, runnable Python file. Save it, run it, see it work.

### Available demo feeds

Use any of these in your prompt:

| Feed name        | What it simulates                        |
|------------------|------------------------------------------|
| `hacker_news`    | Programming and tech articles            |
| `tech_news`      | General technology news                  |
| `reddit_python`  | Python community discussions             |

Stick to these feeds for now. Other sources (like X/Twitter) require API
authentication that can turn into a debugging session rather than a win.
You'll add real sources in later modules.

### Available demo AI analyzers

| Constant             | What it returns                                          |
|----------------------|----------------------------------------------------------|
| `SPAM_DETECTOR`      | `{"is_spam": bool, "confidence": float, "reason": str}`  |
| `SENTIMENT_ANALYZER` | `{"sentiment": str, "score": float, "reasoning": str}`   |
| `URGENCY_DETECTOR`   | `{"urgency": str, "metrics": dict, "reasoning": str}`    |

### Available sinks

| Component           | What it does                                 |
|---------------------|----------------------------------------------|
| `print`             | Prints to terminal                           |
| `MockEmailAlerter`  | Prints formatted email alerts to terminal    |
| `JSONLRecorder`     | Saves results to a `.jsonl` file             |

### Describe something you'd actually want

The best homework app is one you'd genuinely use. Some ideas:

- Monitor gaming news and flag articles about your favorite games
- Track Python community posts and highlight the ones about topics you're learning
- Filter tech news to only show positive stories (good for Monday mornings)
- Collect all articles mentioning a technology you're curious about

The constraint is the feed list above. Work within it and you'll have a running
app in under 10 minutes.

---

## Key Concepts

**Three node types:** `Source` generates data. `Transform` processes it.
`Sink` consumes it. Every DisSysLab app is some combination of these.

**`None` drops messages:** Any transform that returns `None` silently removes
that message from the network. Downstream nodes never see it.

**Demo and real components are interchangeable:** The only difference is the
import line. Your app's architecture doesn't change when you go live.

**You write functions, DisSysLab handles the rest:** Threading, queuing,
shutdown coordination — none of that is your problem.

---

## What's Next

**Module 02** introduces fanin and fanout — merging multiple sources into one
pipeline, and splitting one pipeline into multiple destinations. You'll build a
monitor that reads from two feeds simultaneously.