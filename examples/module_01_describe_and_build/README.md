# Module 1: Describe and Build

*Your first distributed system in 10 minutes.*

---

## Part 1: Generate Your App With Claude (5 minutes)

### One-Time Setup

DisSysLab includes a context file that teaches Claude how to generate DisSysLab applications. You only need to set this up once.

**Option A — Claude Project (recommended):**
1. Go to [claude.ai](https://claude.ai) and create a new Project
2. Name it "DisSysLab"
3. Add `CLAUDE_CONTEXT.md` (from the DisSysLab root directory) to the project knowledge
4. Start a conversation inside the project

**Option B — Paste into conversation:**
1. Open [claude.ai](https://claude.ai)
2. Copy the contents of `CLAUDE_CONTEXT.md` and paste it at the start of your conversation
3. Then type your request

### Build Your First App

Now just tell Claude what you want in plain English:

> Build me an app that monitors Hacker News for articles, filters out spam, analyzes the sentiment of each article, and prints the results. Use mock components.

Claude generates a complete, runnable application. Copy the code into a file called `my_app.py` in the DisSysLab root directory and run it:

```bash
python3 my_app.py
```

You should see articles printed with their sentiment — and no spam. **You just built a distributed system where four nodes run concurrently, passing messages through queues, with automatic spam filtering.**

### No Claude Access?

Use the pre-built version instead:

```bash
python3 -m examples.module_01_describe_and_build.example_generated
```

This runs the same app. Read on to understand what it does.

---

## Part 2: Understanding What Claude Built (20 minutes)

Whether Claude generated your code or you're using `example_generated.py`, the app looks like this:

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
g.run_network()
```

### What just happened?

When you called `g.run_network()`, DisSysLab:

1. **Created four threads** — one per node, all running concurrently.
2. **Created message queues** between connected nodes.
3. **Started all threads simultaneously.** The source began producing articles while downstream nodes waited for messages.
4. **Messages flowed through the network:**
   - `source` produced "Show HN: Built a new Python library..."
   - `spam_gate` received it, checked for spam (not spam), returned the text
   - `sentiment` received the text, analyzed it, returned `{"text": ..., "sentiment": "NEUTRAL", ...}`
   - `display` received the dict and printed it
5. **Spam was silently dropped.** When `filter_spam` returned `None` for "CLICK HERE for FREE cryptocurrency!", DisSysLab didn't send it downstream. No error, no special handling — just gone.
6. **Clean shutdown.** When the source ran out of articles, it sent a STOP signal that propagated through every node, and all threads terminated.

You wrote zero threading code. Zero queue management. Zero synchronization logic.

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

Any transform can filter by returning `None`. The framework drops the message silently. You can put a filter anywhere in your network and it just works.

### Mock and real: one line to swap

The mock components use keyword matching — crude, but instant and free:

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

Same interface. Same `.run(text)` method. Everything else in your app stays exactly the same. Module 4 covers AI integration in depth.

---

## Part 3: Make It Yours (15 minutes)

Now modify the app to prove you understand the pieces — or ask Claude to do it for you.

### Experiment 1: Ask Claude for a variation

Try these prompts (or make up your own):

> Add an urgency detector to my app. After sentiment analysis, check how urgent each article is, and include the urgency level in the output.

> Change my app to use two feeds — Hacker News and tech news — both feeding into the same spam filter.

> Modify my app so it only shows positive articles. Drop anything negative.

Each time, Claude generates updated code. Run it. Compare with what you had before. Notice that the pattern is always the same: functions → nodes → edges → run.

### Experiment 2: Change the feed by hand

Replace `"hacker_news"` with `"tech_news"` or `"reddit_python"`:

```python
rss = MockRSSSource(feed_name="tech_news")
```

Run it again. Different articles, same network.

### Experiment 3: Add a transform by hand

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
    result = spam_detector.run(text)
    if result["is_spam"]:
        return None
    return text
```

Do the same for `analyze_sentiment` and `print_article`. Run the app and watch the interleaved output — nodes process different messages at the same time. That's concurrency, and you got it for free.

### Experiment 6: Something completely different

Go back to Claude and describe an entirely different app:

> Build me a DisSysLab app that reads from three different news feeds, merges them, filters for articles about Python, checks urgency, and saves urgent Python articles to a JSON file. Use mock components.

Compare what Claude generates with what you built by hand. The pattern is the same every time.

---

## What You've Learned

After this module, you know:

- **Claude can generate DisSysLab apps from natural language descriptions.** Describe what you want, get working code.
- **The DisSysLab pattern:** write functions, wrap into nodes (Source/Transform/Sink), connect with `network()`, run with `run_network()`.
- **Filtering:** return `None` from any transform to drop a message.
- **Concurrency for free:** each node runs in its own thread, messages flow through queues, you write zero threading code.
- **Mock/real swap:** mock components use keywords, real components use AI. Same interface, one-line swap.

## What's Next

**[Module 2: Multiple Sources, Multiple Destinations](../module_02/)** — pull from several feeds at once (fanin), send results to multiple outputs (fanout). Your app goes from a single pipeline to a real monitoring system. And yes — you can ask Claude to build that too.