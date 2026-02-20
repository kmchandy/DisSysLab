# Module 1: Describe and Build

*Your first distributed system in 10 minutes.*

---

## Files in This Module

| File | What it does |
|------|-------------|
| `README.md` | This guide |
| `example_generated.py` | Pre-built app: Hacker News → spam filter → sentiment → display |
| `example_modified.py` | Extended app: adds positive-only filter and urgency detection |
| `test_module_01.py` | Test suite — run with `python3 -m pytest examples/module_01/test_module_01.py -v` |

Run any example from the DisSysLab root:
```bash
python3 -m examples.module_01.example_generated
python3 -m examples.module_01.example_modified
```

---

This module uses **demo components** — simulated data sources and keyword-based AI analyzers that run instantly with no API keys, no accounts, and no cost. But here's the important part: demo and real components share the same interface. When you're ready to connect to live data and real AI, you swap one import line. The network topology, the transform functions, the entire architecture of your app stays exactly the same. What you build here is the real structure of a concurrent, distributed application — only the data sources are simulated.

---

## Before You Start

**All DisSysLab files must be run from the DisSysLab root directory using `python3 -m`:**

```bash
cd ~/Documents/DisSysLab
python3 -m examples.module_01.example_generated
```

This is because DisSysLab uses Python package imports. Running `python3 some_file.py` directly will fail with `ModuleNotFoundError`. Always use `python3 -m` with the dotted module path. This applies to every file in every module.

---

## Part 1: Generate Your App With Claude (5 minutes)

### One-Time Setup

DisSysLab includes a context file called `CLAUDE_CONTEXT.md` that teaches Claude how to generate DisSysLab applications. You set this up once, and then every conversation in the project understands the framework.

**Option A — Claude Project (recommended):**

1. Go to [claude.ai](https://claude.ai) and sign in.
2. In the left sidebar, click **Projects**, then **Create Project**.
3. Name the project **DisSysLab** (or any name you like).
4. You'll see two sections: **Instructions** and **Files**.
5. Click **Files** and upload `CLAUDE_CONTEXT.md` from the DisSysLab root directory. (You can drag and drop it, or click to browse.) Do **not** put it in Instructions — that section is for behavioral guidance, not reference material.
6. Click into the project to start a new conversation.

That's it. Every conversation you open inside this project now has access to the full DisSysLab component catalog, conventions, and code generation rules. You never need to upload the file again — just open a new conversation in the project and start describing what you want.

**Option B — No Claude access:**

If you don't have access to Claude, skip ahead to Part 2. The pre-built example files contain the same code Claude would generate. You can run and study them directly:

```bash
python3 -m examples.module_01.example_generated
```

### Build Your First App

Inside your DisSysLab project, start a new conversation and type:

> Build me an app that monitors Hacker News for articles, filters out spam, analyzes the sentiment of each article, and prints the results. Use demo components.

Claude generates a complete, runnable application. Copy the code into a file called `my_app.py` in the DisSysLab root directory and run it:

```bash
python3 -m my_app
```

You should see articles printed with their sentiment — and no spam. **You just built a distributed system where four nodes run concurrently, passing messages through queues, with automatic spam filtering.**

---

## Part 2: Understanding What Claude Built (20 minutes)

Whether Claude generated your code or you're using `example_generated.py`, the app looks like this:

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent

# --- Data source ---
rss = DemoRSSSource(feed_name="hacker_news")

# --- AI components (demo versions — keyword-based) ---
spam_detector = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

# --- Transform functions ---
def filter_spam(text):
    """Drop spam, pass through everything else."""
    result = spam_detector(text)
    if result["is_spam"]:
        return None      # ← Dropped by DisSysLab automatically
    return text          # ← Passed to next node

def analyze_sentiment(text):
    """Analyze sentiment, return text with analysis."""
    result = sentiment_analyzer(text)
    return {
        "text": text,
        "sentiment": result["sentiment"],
        "score": result["score"]
    }

def print_article(article):
    """Print each article with its sentiment."""
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} [{article['sentiment']:>8}] {article['text']}")

# --- Build the network ---
source    = Source(fn=rss.run, name="rss_feed")
spam_gate = Transform(fn=filter_spam, name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")
display   = Sink(fn=print_article, name="display")

g = network([
    (source, spam_gate),
    (spam_gate, sentiment),
    (sentiment, display)
])

# --- Run ---
if __name__ == "__main__":
    print("\n📰 Hacker News Feed — Spam Filtered, Sentiment Analyzed\n")
    g.run_network()
    print("\n✅ Done!\n")
```

### What just happened?

Here's what DisSysLab built from your code:

```
  rss_feed  →  spam_filter  →  sentiment  →  display
  (Source)     (Transform)     (Transform)    (Sink)
  Thread 1      Thread 2        Thread 3     Thread 4
```

Each name is a **node** — an agent that runs concurrently in its own thread. The arrows are **message queues** that carry data between nodes. You wrote ordinary Python functions; DisSysLab turned them into a concurrent system.

When you called `g.run_network()`, DisSysLab:

1. **Created four threads** — one per node, all running concurrently.
2. **Created message queues** between connected nodes.
3. **Started all threads simultaneously.** The source began producing articles while downstream nodes waited for messages.
4. **Routed messages automatically.** Each article flowed from source → spam_filter → sentiment → display, passing through queues between threads.
5. **Shut down cleanly** when the source ran out of articles, propagating a stop signal through the network.

### The four-step pattern

Every DisSysLab app follows the same structure:

**Step 1: Create components** — data sources, analyzers, output handlers.
```python
rss = DemoRSSSource(feed_name="hacker_news")
spam_detector = demo_ai_agent(SPAM_DETECTOR)
```

**Step 2: Write transform functions** — ordinary Python functions that process data.
```python
def filter_spam(text):
    result = spam_detector(text)
    if result["is_spam"]:
        return None
    return text
```

**Step 3: Wrap into nodes and connect** — Source, Transform, Sink, then edges.
```python
source    = Source(fn=rss.run, name="rss_feed")
spam_gate = Transform(fn=filter_spam, name="spam_filter")
g = network([(source, spam_gate), ...])
```

**Step 4: Run.**
```python
g.run_network()
```

That's it. This pattern scales from four-node demos to complex multi-source, multi-destination monitoring systems. You'll use it in every module.

### Filtering: the power of None

An important concept in DisSysLab:

```python
def filter_spam(text):
    result = spam_detector(text)
    if result["is_spam"]:
        return None    # ← This message disappears from the network
    return text        # ← This message continues downstream
```

Any transform can filter by returning `None`. The framework drops the message silently. You can put a filter anywhere in your network and it just works.

### Demo and real: one line to swap

The demo components use keyword matching — crude, but instant and free:

```python
# Demo — keyword matching, no API key needed
from components.transformers.demo_ai_agent import demo_ai_agent
spam_detector = demo_ai_agent(SPAM_DETECTOR)
result = spam_detector("some text")
```

When you're ready for real AI, swap to:

```python
# Real — Claude API, requires ANTHROPIC_API_KEY
from components.transformers.ai_agent import ai_agent
spam_detector = ai_agent(SPAM_DETECTOR)
result = spam_detector("some text")
```

Same interface. Same call pattern. Everything else in your app stays exactly the same. Module 2 covers AI integration in depth.

---

## Part 3: Make It Yours (15 minutes)

Now modify the app to prove you understand the pieces — or ask Claude to do it for you.

### Experiment 1: Ask Claude for a variation

Try these prompts (or make up your own):

> Add an urgency detector to my app. After sentiment analysis, check how urgent each article is, and include the urgency level in the output.

> Change my app to use two feeds — Hacker News and tech news — both feeding into the same spam filter.

> Modify my app so it only shows positive articles. Drop anything negative.

Each time, Claude generates updated code. Save it to a `.py` file and run with `python3 -m filename` (without the `.py`). Compare with what you had before. Notice that the pattern is always the same: functions → nodes → edges → run.

### Experiment 2: Change the feed by hand

Replace `"hacker_news"` with `"tech_news"` or `"reddit_python"`:

```python
rss = DemoRSSSource(feed_name="tech_news")
```

Run it again. Different articles, same network.

### Experiment 3: Add a transform by hand

Add an urgency detector between sentiment analysis and display. First, add the import and create the component:

```python
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER, URGENCY_DETECTOR

urgency_detector = demo_ai_agent(URGENCY_DETECTOR)
```

Then write the transform function:

```python
def analyze_urgency(article):
    """Add urgency info to each article."""
    result = urgency_detector(article["text"])
    article["urgency"] = result["urgency"]
    return article

urgency = Transform(fn=analyze_urgency, name="urgency")
```

Update the network:

```python
g = network([
    (source, spam_gate),
    (spam_gate, sentiment),
    (sentiment, urgency),      # ← New node
    (urgency, display)
])
```

Update the display function to show urgency. Run it. You just added a node to a distributed system by writing one function and adding one edge.

### Experiment 4: Filter by sentiment

Add a transform that drops negative articles:

```python
def only_positive(article):
    """Keep only positive or neutral articles."""
    if article["sentiment"] == "NEGATIVE":
        return None
    return article

positive_filter = Transform(fn=only_positive, name="positive_only")
```

Insert it into the network between `sentiment` and `display`.

### Experiment 5: See concurrency in action

Add a print to each function:

```python
def filter_spam(text):
    print(f"  [spam_filter] checking: {text[:40]}...")
    result = spam_detector(text)
    if result["is_spam"]:
        return None
    return text
```

Do the same for `analyze_sentiment` and `print_article`. Run the app and watch the interleaved output — nodes process different messages at the same time. That's concurrency, and you got it for free.

### Experiment 6: Something completely different

Go back to Claude and describe an entirely different app:

> Build me a DisSysLab app that reads from three different news feeds, merges them, filters for articles about Python, checks urgency, and saves urgent Python articles to a JSON file. Use demo components.

Compare what Claude generates with what you built by hand. The pattern is the same every time.

---

## What You've Learned

After this module, you know:

- **Claude can generate DisSysLab apps from natural language descriptions.** Describe what you want, get working code.
- **The DisSysLab pattern:** write functions, wrap into nodes (Source/Transform/Sink), connect with `network()`, run with `run_network()`.
- **Filtering:** return `None` from any transform to drop a message.
- **Concurrency for free:** each node runs in its own thread, messages flow through queues, you write zero threading code.
- **Demo/real swap:** demo components use keywords, real components use AI. Same interface, one-line swap.

## What's Next

**[Module 2: AI Integration](../module_02/)** — swap demo components for real Claude AI. Your keyword-based analyzers become genuine AI-powered transforms, and you see what happens when real intelligence processes your data.