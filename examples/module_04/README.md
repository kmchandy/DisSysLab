# Module 4: Smart Routing

*Send the right data to the right place.*

In Module 3 you used fanout — every result went to every sink. That's useful when you want everything everywhere, but real systems need smarter routing. Positive customer feedback should go to the marketing archive. Negative feedback should trigger an alert. Neutral posts might just go to a log. The Split node gives you this control.

---

## Part 1: Setup (2 minutes)

No new setup. Everything is in your Claude Project from Modules 2 and 3.

One addition: the Split node documentation should be in your `CLAUDE_CONTEXT.md`. If Claude doesn't generate split-based code correctly, upload the updated `CLAUDE_CONTEXT.md` from the DisSysLab root directory (it now includes the Split section).

---

## Part 2: Describe Your App to Claude (5 minutes)

Open a new conversation in your DisSysLab project and type:

> Build me an app that monitors BlueSky for posts about AI using BlueSkyJetstreamSource with max_posts=20. Analyze sentiment using real Claude AI with the sentiment_analyzer prompt. Then use a Split node with 3 outputs to route posts based on sentiment score:
>
> - If score > 0.2 (positive): send to out_0 AND out_1
> - If score < -0.2 (negative): send to out_1 AND out_2
> - Otherwise (neutral): send to out_1 only
>
> Connect out_0 to a JSONLRecorder that saves to positive.jsonl (archive of positive posts). Connect out_1 to a console display using print (sees all non-neutral posts). Connect out_2 to a MockEmailAlerter (alerts for negative posts only).
>
> Use real components. Import Split from dsl.blocks.

Claude generates the app. Save it, run it:

```bash
python3 my_router.py
```

Positive posts appear on the console and silently accumulate in `positive.jsonl`. Negative posts appear on the console and trigger email alerts. Neutral posts only go to the console. Each post is routed by its sentiment — not copied everywhere.

---

## Part 3: Understanding the Split Node (15 minutes)

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

Notice the new syntax: `splitter.out_0`, `splitter.out_1`, `splitter.out_2`. These are **port references** — they tell the network which output port connects to which downstream node. Regular nodes don't need port references because they have only one output.

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

## Part 4: Side-by-Side with Module 3 (10 minutes)

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

> Change my app to use urgency_detector instead of sentiment_analyzer. Route HIGH urgency to email alerts, LOW urgency to the archive, and MEDIUM urgency to console only.

Same Split pattern, different AI analysis, different routing logic.

### Experiment 2: Add a "catch all" path

Ask Claude:

> Add a fourth output to the split. Send ALL posts to out_3, connected to a JSONL file called all_posts.jsonl. Keep the other routing the same.

Now you have selective routing for three paths plus a complete archive. The routing function returns a list of 4 elements instead of 3.

### Experiment 3: Combine fanin with split

Ask Claude:

> Add an RSS source (Hacker News) that merges with the BlueSky source before sentiment analysis. Keep the split routing the same.

This combines Module 3's fanin with Module 4's split — a full diamond network. Two sources fan in, processing happens, results route to three different destinations based on content.

### Experiment 4: Two-stage routing

Ask Claude:

> After the sentiment split, add a second split on the negative path (out_2). Use urgency_detector on negative posts and route HIGH urgency to email alerts and LOW urgency to a separate log file.

Hierarchical routing — split by sentiment, then split again by urgency. This shows that Split nodes can chain.

### Experiment 5: Drop messages entirely

Try modifying the routing function to drop neutral posts completely:

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

## Part 6: What You Should See

```
📡 Monitoring BlueSky for: AI, machine learning
   Routing: positive → archive + console, negative → console + alerts, neutral → console only

  [CONSOLE] 😊 POSITIVE (0.75): "Excited about the new Claude features for code generation"
  [CONSOLE] 😞 NEGATIVE (-0.62): "Frustrated with AI-generated content flooding the internet"
  📧 ALERT: NEGATIVE (-0.62): "Frustrated with AI-generated content flooding the internet"
  [CONSOLE] 😊 POSITIVE (0.88): "Our team just shipped an ML pipeline that saves 20 hours/week"
  [CONSOLE] 😞 NEGATIVE (-0.45): "Major security vulnerability found in popular AI framework"
  📧 ALERT: NEGATIVE (-0.45): "Major security vulnerability found in popular AI framework"
  ...

✅ Done! 20 posts processed.
   Positive (archived): 7 posts → positive.jsonl
   Console (non-neutral): 15 posts displayed
   Negative (alerted): 8 posts → email alerts
   Neutral (console only): 5 posts
```

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
