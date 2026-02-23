# Module 04: Build Your Own App

*You know enough to build anything. Here's how to design it.*

---

## What You'll Build

In this module you build two things:

1. **A worked example** — a multi-feed news intelligence monitor that combines
   everything from Modules 01-03: fanin, filtering, sentiment analysis, and
   three-way Split routing. Run it first to see what a complete app looks like.

2. **Your own app** — using the same design process, you describe what you
   personally want to monitor or analyze, give the description to Claude, and
   get a working DisSysLab app.

```
hacker_news ─┐
              ├→ spam_filter → sentiment → split → positive → archive
tech_news   ─┘                                  → negative → alerts
                                                → neutral  → display
```

This module introduces no new node types. Everything here uses Source,
Transform, Sink, and Split — the building blocks from Modules 01-03.

---

## Files in This Module

| File                      | What it is                                              |
|---------------------------|---------------------------------------------------------|
| `README.md`               | This file                                               |
| `app.py`                  | The worked example — run this first                     |
| `claude_generated_app.py` | Exactly what Claude produced from the Part 4 prompt     |
| `app_live.py`             | Same app with real Claude API (Part 3)                  |
| `app_extended.py`         | Extended version with topic classification added        |
| `test_module_04.py`       | Tests you can run to verify everything works            |

---

## Part 1: Run the App (2 minutes)

From the DisSysLab root directory:

```bash
python3 -m examples.module_04.app
```

You should see articles from two feeds interleaved, spam dropped, and results
routed to three destinations:

```
📰 News Intelligence Monitor
════════════════════════════════════════════════════════════

  hacker_news ─┐
                ├→ spam_filter → sentiment → split
  tech_news   ─┘                          → positive → archive
                                          → negative → alerts
                                          → neutral  → display

  [DISPLAY - NEUTRAL]
  😐 Stack Overflow Developer Survey results

  [ALERT - NEGATIVE]
  📧 To: alerts@newsroom.com
  😞 Why most software projects fail

════════════════════════════════════════════════════════════
✅ Done! Positive articles saved to results.jsonl
```

This is everything from Modules 01-03 combined in one app. Move to Part 2
to see how the design was arrived at before any code was written.

---

## Part 2: The Design Process (10 minutes)

Before writing `app.py`, the network was designed by answering four questions.
Use this same process for your own app in Part 4.

### Question 1: What do I want to monitor?

*Two tech news feeds: Hacker News and tech_news.*

This immediately suggests **fanin** — two sources merging into one pipeline.

### Question 2: What processing do I need?

*Filter out spam, then classify each article by sentiment.*

Two Transform nodes in sequence: `spam_filter → sentiment`.

### Question 3: Where do I want results to go?

*Positive articles saved to a file. Negative ones emailed as alerts.
Neutral ones printed to the terminal.*

Three different destinations based on content → **Split** with three output ports.

### Question 4: Draw the topology

```
  hacker_news ─┐
                ├→ [spam_filter] → [sentiment] → [splitter]
  tech_news   ─┘                               → out_0 → [archive]
                                               → out_1 → [alerts]
                                               → out_2 → [display]
```

Once the drawing exists, the code writes itself — each box becomes a node,
each arrow becomes an edge in the `network()` call.

### The rule: draw first, code second

Every working DisSysLab app starts as ASCII art. The drawing forces you to
answer the four questions before you touch a keyboard. It also gives Claude
exactly what it needs to generate correct code.

---

## Part 3: Read the Code (10 minutes)

Open `app.py`. Every section maps directly to the design above.

### Imports

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import DemoEmailAlerter, JSONLRecorder
```

### Components — one per box in the drawing

```python
hn   = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")

spam_detector      = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

recorder = JSONLRecorder(path="results.jsonl", mode="w", flush_every=1)
alerter  = DemoEmailAlerter(to_address="alerts@newsroom.com",
                             subject_prefix="[ALERT]")
```

### Transform functions — one per arrow in the drawing

```python
def filter_spam(text):
    result = spam_detector(text)
    return None if result["is_spam"] else text

def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

def route_by_sentiment(article):
    if article["sentiment"] == "POSITIVE":
        return [article, None,    None   ]
    elif article["sentiment"] == "NEGATIVE":
        return [None,    article, None   ]
    else:
        return [None,    None,    article]

def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    print(f"  {icon.get(article['sentiment'], '❓')} {article['text']}")
```

### Network — the drawing as code

```python
hn_source   = Source(fn=hn.run,              name="hacker_news")
tech_source = Source(fn=tech.run,            name="tech_news")
spam_gate   = Transform(fn=filter_spam,       name="spam_filter")
sentiment   = Transform(fn=analyze_sentiment, name="sentiment")
splitter    = Split(fn=route_by_sentiment,    num_outputs=3, name="router")
archive     = Sink(fn=recorder.run,           name="archive")
alerts      = Sink(fn=alerter.run,            name="alerts")
display     = Sink(fn=print_article,          name="display")

g = network([
    (hn_source,   spam_gate),    # fanin
    (tech_source, spam_gate),    # fanin
    (spam_gate,   sentiment),
    (sentiment,   splitter),
    (splitter.out_0, archive),   # positive
    (splitter.out_1, alerts),    # negative
    (splitter.out_2, display)    # neutral
])
```

Every edge in the `network()` list corresponds to one arrow in the drawing.
If your drawing is right, your network is right.

### Connect real Claude AI

`app_live.py` shows the two-line change — identical to previous modules:

```bash
export ANTHROPIC_API_KEY='your-key-here'
python3 -m examples.module_04.app_live
```

`app_live.py` sets `max_articles=2` per feed to keep API costs low.

---

## Part 4: Build Your Own App (homework)

You now know the full toolkit. The only question is: what do you want to build?

### Step 1: Answer the four design questions

Write down answers to these before opening Claude:

1. **What do I want to monitor?**
   Pick one or more demo feeds: `hacker_news`, `tech_news`, `reddit_python`

2. **What processing do I need?**
   Pick from the available analyzers below.

3. **Where do I want results to go?**
   Pick from the available sinks below.

4. **Draw the topology.**
   ASCII art, on paper, in a text file — anything. Don't skip this.

### Step 2: Give Claude your design

Open your DisSysLab Claude project and use a prompt like this:

> Build me a DisSysLab app that reads from [your feeds], [your processing],
> and [your outputs]. Use demo components.

Or paste in your ASCII drawing and say:

> Build me a DisSysLab app with this topology: [paste drawing].
> Use demo components.

Claude will generate a complete, runnable app.

### Step 3: Run it, then make it yours

Run exactly what Claude generates. Then modify it — change the feeds, add a
step, change the routing logic. Each change teaches you something.

### Example designs to get you started

**Option A — Urgency monitor:**
```
reddit_python → urgency → split → HIGH   → alerts
                                → MEDIUM → display
                                → LOW    → (drop)
```

**Option B — Topic filter:**
```
hacker_news ─┐
              ├→ spam_filter → topic → keep only "technology" → archive
tech_news   ─┘
```

**Option C — Full pipeline:**
```
hacker_news ─┐
              ├→ spam_filter → sentiment → urgency → display
reddit_python─┘
```

---

## Available Components

### Demo feeds

| Feed name       | What it simulates                    |
|-----------------|--------------------------------------|
| `hacker_news`   | Programming and tech articles        |
| `tech_news`     | General technology news              |
| `reddit_python` | Python community discussions         |

### Demo AI analyzers

| Constant             | Returns                                                  |
|----------------------|----------------------------------------------------------|
| `SPAM_DETECTOR`      | `{"is_spam": bool, "confidence": float, "reason": str}`  |
| `SENTIMENT_ANALYZER` | `{"sentiment": str, "score": float, "reasoning": str}`   |
| `URGENCY_DETECTOR`   | `{"urgency": str, "metrics": dict, "reasoning": str}`    |
| `TOPIC_CLASSIFIER`   | `{"primary_topic": str, "confidence": float, ...}`       |
| `EMOTION_DETECTOR`   | `{"primary_emotion": str, "emotion_scores": dict, ...}`  |
| `TEXT_SUMMARIZER`    | `{"summary": str, "key_points": list, ...}`              |

### Available sinks

| Component          | What it does                                  |
|--------------------|-----------------------------------------------|
| `print`            | Prints to terminal                            |
| `DemoEmailAlerter` | Prints formatted email-style alerts           |
| `JSONLRecorder`    | Saves every result to a `.jsonl` file         |

---

## Key Concepts

**Three basic node types.** `Source` generates data. `Transform` processes
it. `Sink` consumes it. `Split` routes each message to a specific output
port. These four building blocks cover every app in this module.

**Draw first, code second.** The network topology diagram is the real design
artifact. Code is just the diagram written in Python.

**The four design questions.** What to monitor → what processing → where
results go → draw the topology. Answer these before writing any code, and
the code becomes straightforward.

**Fanin, fanout, Split are not special.** They emerge naturally from your
design. If two sources feed the same node, that's fanin. If one node sends
to two sinks, that's fanout. If messages need sorting, that's Split.

**Demo and real components are interchangeable.** Your design doesn't change
when you go live. Two import lines change. Nothing else does.

---

## What's Next

**Module 05+** moves into the Gallery — domain-specific example apps you
can run, study, and adapt. Sports monitoring, music feeds, finance alerts,
science news — complete working applications built with the same four
building blocks you now know.
