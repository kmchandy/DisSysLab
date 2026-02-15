# Module 1: Describe and Build

*Your first distributed system in 10 minutes.*

---

## Part 1: Tell Claude What You Want (5 minutes)

Open [claude.ai](https://claude.ai) and paste this prompt:

```
Using the DisSysLab framework, build me a Python app that:

1. Reads articles from a mock Hacker News RSS feed
2. Filters out spam articles
3. Analyzes the sentiment of the remaining articles
4. Prints each article with its sentiment to the console

Use these existing components:
- MockRSSSource from components.sources.mock_rss_source (feed_name="hacker_news")
- MockClaudeAgent from components.transformers.mock_claude_agent (task="spam_detection")
- MockClaudeAgent from components.transformers.mock_claude_agent (task="sentiment_analysis")

The spam filter should return None for spam (which DisSysLab drops automatically)
and return the original text for non-spam.

The sentiment analyzer should return a dict with "text" and "sentiment" keys.

Use dsl's network() function and Source, Transform, Sink from dsl.blocks.
Source wraps a callable with fn=..., Transform wraps a function with fn=...,
Sink wraps a function with fn=....
Connect them with: g = network([(node1, node2), ...])
Run with: g.run_network()
```

Claude generates a complete working app. Copy the code into a file called `my_app.py` in the DisSysLab root directory. Run it:

```bash
python3 my_app.py
```

You should see articles printed with their sentiment — and no spam. **You just built a distributed system where four nodes run concurrently, passing messages through queues, with automatic filtering.**

If you don't have access to Claude, use the pre-built version in `example_generated.py` (described below).

---

## Part 2: Understanding What Claude Built (20 minutes)

Whether you generated the code or are using `example_generated.py`, let's walk through it. The complete app looks like this:

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.mock_rss_source import MockRSSSource
from components.transformers.mock_claude_agent import MockClaudeAgent

# --- Data source ---
rss = MockRSSSource(feed_name="hacker_news")

# --- AI components (mock versions — keyword-based) ---
spam_detector = MockClaudeAgent(task="spam_detection")
sentiment_analyzer = MockClaudeAgent(task="sentiment_analysis")

# --- Transform functions ---
def filter_spam(text):
    """Drop spam, pass through everything else."""
    result = spam_detector.run(text)
    if result["is_spam"]:
        return None      # ← Dropped by DisSysLab automatically
    return text          # ← Passed to next node

def analyze_sentiment(text):
    """Analyze sentiment, return text with analysis."""
    result = sentiment_analyzer.run(text)
    return {
        "text": text,
        "sentiment": result["sentiment"],
        "score": result["score"]
    }

def print_article(article):
    """Print each article with its sentiment."""
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    print(f"  {emoji} [{article['sentiment']}] {article['text']}")

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
print("\n📰 Hacker News Feed — Spam Filtered, Sentiment Analyzed\n")
g.run_network()
print("\n✅ Done!\n")
```

### What just happened?

When you called `g.run_network()`, DisSysLab:

1. **Created four threads** — one per node, all running concurrently.
2. **Created message queues** between connected nodes.
3. **Started all threads simultaneously.** The source began producing articles while downstream nodes waited for messages.
4. **Messages flowed through the network:**
   - `source` produced "Show HN: Built a new Python library for distributed systems"
   - `spam_gate` received it, checked for spam (not spam), returned the text
   - `sentiment` received the text, analyzed it, returned `{"text": ..., "sentiment": "NEUTRAL", ...}`
   - `display` received the dict and printed it
5. **Spam was silently dropped.** When `filter_spam` returned `None` for "CLICK HERE for FREE cryptocurrency!", DisSysLab simply didn't send it downstream. No error, no special handling — just gone.
6. **Clean shutdown.** When the source ran out of articles, it sent a STOP signal that propagated through every node, and all threads terminated.

You wrote zero threading code. Zero queue management. Zero synchronization logic. DisSysLab handled all of it.

### The four building blocks

Every DisSysLab app uses the same pattern:

**Source** — produces data. Your function returns the next item each time it's called, or `None` when done.

```python
source = Source(fn=rss.run, name="rss_feed")
```

**Transform** — processes data. Your function takes one input, returns one output (or `None` to drop the message).

```python
spam_gate = Transform(fn=filter_spam, name="spam_filter")
```

**Sink** — consumes data. Your function takes one input and does something with it (print, save, send) but doesn't pass it on.

```python
display = Sink(fn=print_article, name="display")
```

**network()** — connects nodes. You provide a list of edges as `(from_node, to_node)` tuples.

```python
g = network([
    (source, spam_gate),
    (spam_gate, sentiment),
    (sentiment, display)
])
```

### The topology

Our app is a **pipeline** — a linear chain:

```
rss_feed → spam_filter → sentiment → display
```

This is the simplest topology. Module 2 introduces more powerful shapes — multiple sources feeding into one processor, one processor sending to multiple destinations.

### Filtering: the power of None

The most important single concept in DisSysLab:

```python
def filter_spam(text):
    result = spam_detector.run(text)
    if result["is_spam"]:
        return None    # ← This message disappears from the network
    return text        # ← This message continues downstream
```

Any transform can filter by returning `None`. The framework drops the message silently. This means you can put a filter anywhere in your network — after a source, between two transforms, right before a sink — and it just works.

### Mock and real: one line to swap

The mock components use keyword matching. Crude, but instant and free:

```python
# Mock — keyword matching, no API key needed
spam_detector = MockClaudeAgent(task="spam_detection")
```

When you're ready for real AI, swap to:

```python
# Real — Claude API, requires ANTHROPIC_API_KEY
from components.transformers.claude_agent import ClaudeAgent
from components.transformers.prompts import get_prompt

spam_detector = ClaudeAgent(get_prompt("spam_detector"))
```

Same interface. Same `.run(text)` method. Everything else in your app stays exactly the same. Module 4 covers this in detail.

---

## Part 3: Make It Yours (15 minutes)

Now modify the app to prove you understand the pieces.

### Experiment 1: Change the feed

Replace `"hacker_news"` with `"tech_news"` or `"reddit_python"`:

```python
rss = MockRSSSource(feed_name="tech_news")
```

Run it again. Different articles, same network.

### Experiment 2: Add a transform

Add an urgency detector between sentiment analysis and display:

```python
urgency_detector = MockClaudeAgent(task="urgency_detection")

def analyze_urgency(article):
    """Add urgency info to each article."""
    result = urgency_detector.run(article["text"])
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

### Experiment 3: Filter by sentiment

Add a transform that drops negative articles:

```python
def only_positive(article):
    """Keep only positive or neutral articles."""
    if article["sentiment"] == "NEGATIVE":
        return None
    return article

positive_filter = Transform(fn=only_positive, name="positive_only")
```

Insert it into the network. Where should it go? Between `sentiment` and `display` — because it needs the sentiment analysis to already be in the article dict.

### Experiment 4: Add print statements to see concurrency

Add a print to each function:

```python
def filter_spam(text):
    print(f"  [spam_filter] checking: {text[:40]}...")
    result = spam_detector.run(text)
    if result["is_spam"]:
        return None
    return text
```

Do the same for `analyze_sentiment` and `print_article`. Run the app and watch the interleaved output — you'll see nodes processing different messages at the same time. That's concurrency, and you got it for free.

### Experiment 5: Ask Claude for a different app

Go back to Claude and describe a different app entirely:

> "Using DisSysLab, build me an app that monitors a tech news feed, filters articles about AI, detects urgency, and saves urgent AI articles to a list."

Compare what Claude generates with what you built by hand. The pattern is the same every time: functions → nodes → edges → run.

---

## What You've Learned

After this module, you know:

- **The DisSysLab pattern:** write functions, wrap into nodes (Source/Transform/Sink), connect with `network()`, run with `run_network()`.
- **Filtering:** return `None` from any transform to drop a message.
- **Concurrency for free:** each node runs in its own thread, messages flow through queues, and you write zero threading code.
- **Mock/real swap:** mock components use keywords, real components use AI. Same interface, one-line swap.
- **AI-assisted development:** describe your app to Claude, get working code, understand and customize it.

## What's Next

**[Module 2: Multiple Sources, Multiple Destinations](../module_02/)** — pull from several feeds at once (fanin), send results to multiple outputs (fanout). Your app goes from a single pipeline to a real monitoring system.