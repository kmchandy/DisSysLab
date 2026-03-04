# DisSysLab Gallery — Context for Claude

You are generating a complete, runnable DisSysLab gallery application.
DisSysLab is a Python framework for building persistent streaming applications.
Ordinary Python functions are wrapped into concurrent nodes connected by message queues.
The framework handles all threading, synchronization, and shutdown automatically.

---

## The Standard Article Dict

Every article flowing through a gallery pipeline has exactly these five keys:

```python
{
    "source":    str,   # feed name, e.g. "hacker_news"
    "title":     str,   # article headline
    "text":      str,   # plain text content (HTML stripped)
    "url":       str,   # link to original article
    "timestamp": str,   # publication date string, or "" if unavailable
}
```

Transform functions receive this dict and return an enriched copy with additional keys added.

---

## Node Types

**Source** — generates messages, has no inputs.
```python
source = Source(fn=my_source.run, name="source_name")
```
Called repeatedly. Returns one message per call. Generator functions are accepted directly.

**Transform** — receives one message, returns one message (or None to drop it).
```python
transform = Transform(fn=my_function, name="transform_name")
```
Return `None` to drop the message — it will not be sent downstream.

**Sink** — receives messages, produces no output.
```python
sink = Sink(fn=my_function, name="sink_name")
```

---

## Network Wiring

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink

g = network([
    (source,     transform1),
    (transform1, transform2),
    (transform2, sink),
])

if __name__ == "__main__":
    g.run_network()
```

**Fanin** — multiple sources merge into one node:
```python
g = network([
    (source1, transform),
    (source2, transform),   # both feed the same node
    (transform, sink),
])
```

**Fanout** — one node sends to multiple destinations:
```python
g = network([
    (source,    transform),
    (transform, sink1),     # same message goes to both
    (transform, sink2),
])
```

---

## Sources: RSSNormalizer

`RSSNormalizer` fetches RSS feeds and produces standard article dicts directly.
Use it instead of `RSSSource` — it handles normalisation automatically.

```python
from components.sources.rss_normalizer import RSSNormalizer
from dsl.blocks import Source

feed = RSSNormalizer(
    urls=["https://hnrss.org/newest"],
    source_name="hacker_news",
    max_articles=20,           # articles per fetch (None = all)
    poll_interval=3600,        # re-fetch every N seconds (None = one-shot)
)
source = Source(fn=feed.run, name="hacker_news")
```

**Verified working feeds — use these exact URLs:**

| Name               | source_name          | URL                                                        |
|--------------------|----------------------|------------------------------------------------------------|
| Hacker News        | hacker_news          | https://hnrss.org/newest                                   |
| MIT Tech Review    | mit_tech_review      | https://www.technologyreview.com/feed/                     |
| TechCrunch         | techcrunch           | https://techcrunch.com/feed/                               |
| VentureBeat AI     | venturebeat_ai       | https://venturebeat.com/category/ai/feed/                  |
| Al Jazeera         | al_jazeera           | https://www.aljazeera.com/xml/rss/all.xml                  |
| NPR News           | npr_news             | https://feeds.npr.org/1001/rss.xml                         |
| BBC World          | bbc_world            | https://feeds.bbci.co.uk/news/world/rss.xml                |
| BBC Tech           | bbc_tech             | https://feeds.bbci.co.uk/news/technology/rss.xml           |
| NASA               | nasa                 | https://www.nasa.gov/rss/dyn/breaking_news.rss             |
| Python.org Jobs    | python_jobs          | https://www.python.org/jobs/feed/rss/                      |
| RemoteOK           | remoteok             | https://remoteok.com/rss                                   |
| We Work Remotely   | we_work_remotely     | https://weworkremotely.com/remote-jobs.rss                 |

**Convenience factory functions** (all pre-configured with correct URL and source_name):
```python
from components.sources.rss_normalizer import (
    hacker_news, mit_tech_review, techcrunch, venturebeat_ai,
    al_jazeera, npr_news, bbc_world, bbc_tech, nasa_news,
    python_jobs, remoteok, we_work_remotely,
)

feed   = hacker_news(max_articles=20)
source = Source(fn=feed.run, name="hacker_news")
```

---

## AI Transforms: ClaudeAgent

`ClaudeAgent` calls the Claude API to analyze articles. It receives the article dict,
analyzes the `text` field using your prompt, and adds a new key to the dict.

```python
from components.transforms.claude_agent import ClaudeAgent

# Requires: export ANTHROPIC_API_KEY='your-key'
agent = ClaudeAgent(
    prompt="Your English instruction here. Return JSON: {key_name: value}",
    output_format="json",   # always use "json" for gallery apps
)
```

**The standard transform pattern — add one key per transform:**

```python
agent = ClaudeAgent(prompt="""
    Analyze the sentiment of the article text.
    Return JSON: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "score": -1.0 to 1.0}
""", output_format="json")

def analyze_sentiment(article):
    result = agent.run(article["text"])
    article["sentiment"] = result["sentiment"]
    article["score"]     = result["score"]
    return article

transform = Transform(fn=analyze_sentiment, name="sentiment")
```

**Filter pattern — return None to drop the article:**

```python
agent = ClaudeAgent(prompt="""
    Does this article mention Python programming?
    Return JSON: {"relevant": true or false}
""", output_format="json")

def keep_python_articles(article):
    result = agent.run(article["text"])
    if not result["relevant"]:
        return None        # drop — not about Python
    return article

transform = Transform(fn=keep_python_articles, name="python_filter")
```

**Prompt writing conventions:**

- Name the new key explicitly: `{"sentiment": ...}` not just `{"result": ...}`
- For filters: `"discard articles that ..."` or `"only keep articles that ..."`
  Both are unambiguous — the filter returns None when the condition is not met.
- Keep each transform to one concern — one key added per transform.

---

## Batch Reporting: StatefulAgent + ClockSource

For periodic batch reports (e.g. daily summaries), use `StatefulAgent` and `ClockSource`.

`StatefulAgent` accumulates article dicts, de-duplicates by URL, and on each clock tick
emits one batch dict organised by source. Wire it using fanin alongside your article pipeline.

`ClockSource` emits periodic tick messages. Use `ClockSource.daily()` for daily reports.

```python
from components.transforms.stateful_agent import StatefulAgent
from components.sources.clock_source import ClockSource
from dsl.blocks import Source, Transform

batcher = StatefulAgent(
    max_articles=200,    # keep at most 200 articles in memory
    clear_on_tick=True,  # clear after each batch (articles since last tick only)
)
clock   = ClockSource.daily()   # also: .hourly(), .weekly(), or ClockSource(interval_seconds=N)

batcher_node = Transform(fn=batcher.run,  name="batcher")
clock_source = Source(fn=clock.run,       name="clock")
```

**Batch dict emitted on each tick:**
```python
{
    "type":      "batch",
    "count":     int,                    # total articles
    "tick_time": "2026-03-02T12:00:00",  # ISO timestamp
    "by_source": {
        "hacker_news":     [ {article}, {article}, ... ],
        "mit_tech_review": [ {article}, ... ],
        ...
    }
}
```

**Report writer pattern** — ClaudeAgent converts the batch dict to a text summary:

```python
reporter = ClaudeAgent(prompt="""
    You receive a batch dict with articles grouped by source in by_source.
    Write a concise daily digest. For each source, list the top articles
    with their title and one-sentence summary. Plain text, no markdown.
""", output_format="text")

def write_report(batch):
    import json
    summary = reporter.run(json.dumps(batch, indent=2))
    return {"report": summary}

report_node = Transform(fn=write_report, name="report_writer")
```

---

## Streaming Display

For real-time streaming output, use a simple print sink:

```python
def display(article):
    print(f"[{article['source']:>18}] {article['title'][:70]}")

display_sink = Sink(fn=display, name="display")
```

---

## Complete Network Pattern

Every gallery app follows this structure:

```
RSSNormalizer(s) → Transform(s) → ┬→ display_sink          (streaming)
                                   └→ StatefulAgent          (batch)
                                        ↑
                                   ClockSource
                                        
                   StatefulAgent → report_writer → report_sink
```

In code:

```python
g = network([
    # Sources
    (source1,       transform1),
    (source2,       transform1),   # fanin if multiple sources

    # Pipeline
    (transform1,    transform2),
    (transform2,    transform3),   # add as many transforms as needed

    # Fanout to streaming and batch
    (transform3,    display_sink),
    (transform3,    batcher_node),

    # Clock feeds into batcher (fanin)
    (clock_source,  batcher_node),

    # Batch reporting
    (batcher_node,  report_node),
    (report_node,   report_sink),
])
```

---

## Code Generation Rules

1. Always include all imports at the top.
2. Always wrap `g.run_network()` in `if __name__ == "__main__":`.
3. Always name every node with a descriptive `name=` parameter.
4. Add a header comment with the app name and ASCII topology diagram.
5. One ClaudeAgent per transform concern — one new key per transform.
6. Always use the convenience factory functions for sources (e.g. `hacker_news()`).
7. Always include a streaming display sink AND a batch report sink.
8. The batch report prompt should reference `by_source` explicitly.
9. Print a startup message showing what the app does before calling `run_network()`.

---

## Example 1: AI/ML Research Tracker

**Spec:**
```
SOURCES:
  - Hacker News
  - MIT Tech Review
  - TechCrunch
  - VentureBeat AI

PROCESSING:
  - only keep articles about artificial intelligence, machine learning, or LLMs
  - sentiment: is this article positive, negative, or neutral about AI progress?
  - impact: rate the potential impact of this development (high, medium, low)

REPORT:
  - Stream each article to console showing source, title, sentiment, and impact
  - Daily digest: for each source, list articles grouped by impact level
```

```python
# ============================================================
# AI/ML Research Tracker
# Monitors four tech sources for AI/ML developments.
#
# Topology:
#   hacker_news ────┐
#   mit_tech_review ┤
#   techcrunch      ┼→ ai_filter → sentiment → impact → ┬→ display
#   venturebeat_ai ─┘                                    └→ batcher → report
#                                              clock ────┘
# ============================================================

import json
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.rss_normalizer import (
    hacker_news, mit_tech_review, techcrunch, venturebeat_ai
)
from components.transforms.claude_agent import ClaudeAgent
from components.transforms.stateful_agent import StatefulAgent
from components.sources.clock_source import ClockSource

# ── Sources ──────────────────────────────────────────────────
hn_feed   = hacker_news(max_articles=20,     poll_interval=3600)
mit_feed  = mit_tech_review(max_articles=10, poll_interval=3600)
tc_feed   = techcrunch(max_articles=10,      poll_interval=3600)
vb_feed   = venturebeat_ai(max_articles=10,  poll_interval=3600)

hn_source  = Source(fn=hn_feed.run,  name="hacker_news")
mit_source = Source(fn=mit_feed.run, name="mit_tech_review")
tc_source  = Source(fn=tc_feed.run,  name="techcrunch")
vb_source  = Source(fn=vb_feed.run,  name="venturebeat_ai")

# ── AI Agents ─────────────────────────────────────────────────
ai_relevance_agent = ClaudeAgent(prompt="""
    Does this article discuss artificial intelligence, machine learning, or LLMs?
    Return JSON: {"relevant": true or false}
""", output_format="json")

sentiment_agent = ClaudeAgent(prompt="""
    Is this AI/ML article positive, negative, or neutral about progress in the field?
    Return JSON: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "score": -1.0 to 1.0}
""", output_format="json")

impact_agent = ClaudeAgent(prompt="""
    Rate the potential impact of this AI/ML development on the field.
    Return JSON: {"impact": "HIGH" | "MEDIUM" | "LOW", "reason": "one sentence"}
""", output_format="json")

reporter_agent = ClaudeAgent(prompt="""
    You receive a JSON batch of AI/ML articles grouped by source in by_source.
    Write a concise daily digest. For each source, list articles grouped by
    impact level (HIGH first). Include title and sentiment for each.
    Plain text only, no markdown.
""", output_format="text")

# ── Transform Functions ───────────────────────────────────────
def filter_ai_articles(article):
    result = ai_relevance_agent.run(article["text"])
    if not result["relevant"]:
        return None
    return article

def analyze_sentiment(article):
    result = sentiment_agent.run(article["text"])
    article["sentiment"] = result["sentiment"]
    article["score"]     = result["score"]
    return article

def rate_impact(article):
    result = impact_agent.run(article["text"])
    article["impact"] = result["impact"]
    article["reason"] = result["reason"]
    return article

def display(article):
    icons = {"POSITIVE": "✅", "NEGATIVE": "❌", "NEUTRAL": "➖"}
    stars = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    icon  = icons.get(article["sentiment"], "?")
    star  = stars.get(article["impact"], "?")
    print(f"{icon}{star} [{article['source']:>15}] {article['title'][:65]}")

def write_report(batch):
    summary = reporter_agent.run(json.dumps(batch, indent=2))
    return {"report": summary}

def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY AI/ML DIGEST")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")

# ── Batch Reporting ───────────────────────────────────────────
batcher     = StatefulAgent(max_articles=200, clear_on_tick=True)
clock       = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
ai_filter    = Transform(fn=filter_ai_articles, name="ai_filter")
sentiment    = Transform(fn=analyze_sentiment,  name="sentiment")
impact       = Transform(fn=rate_impact,        name="impact")
display_sink = Sink(fn=display,                 name="display")
batcher_node = Transform(fn=batcher.run,        name="batcher")
clock_source = Source(fn=clock.run,             name="clock")
report_node  = Transform(fn=write_report,       name="report_writer")
report_sink  = Sink(fn=print_report,            name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (hn_source,   ai_filter),
    (mit_source,  ai_filter),
    (tc_source,   ai_filter),
    (vb_source,   ai_filter),

    (ai_filter,   sentiment),
    (sentiment,   impact),

    (impact,      display_sink),
    (impact,      batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n🤖 AI/ML Research Tracker")
    print("   Sources: Hacker News, MIT Tech Review, TechCrunch, VentureBeat AI")
    print("   Streaming articles to console. Daily digest at midnight.")
    print("   Press Ctrl+C to stop.\n")
    g.run_network()
```

---

## Example 2: Topic Tracker

**Spec:**
```
SOURCES:
  - Al Jazeera
  - NPR News
  - BBC World

PROCESSING:
  - only keep articles that mention MAGA, immigration policy, or the US border
  - sentiment: what is the tone of this article (positive, negative, neutral)?
  - stance: does the article present a pro, anti, or neutral stance on the topic?

REPORT:
  - Stream each article showing source, title, and stance
  - Daily digest: summarize coverage by source, noting any differences in framing
```

```python
# ============================================================
# Topic Tracker: MAGA / Immigration Policy
# Monitors three news sources for topic mentions.
#
# Topology:
#   al_jazeera ─┐
#   npr_news    ┼→ topic_filter → sentiment → stance → ┬→ display
#   bbc_world  ─┘                                      └→ batcher → report
#                                           clock ─────┘
# ============================================================

import json
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.rss_normalizer import al_jazeera, npr_news, bbc_world
from components.transforms.claude_agent import ClaudeAgent
from components.transforms.stateful_agent import StatefulAgent
from components.sources.clock_source import ClockSource

# ── Sources ──────────────────────────────────────────────────
aj_feed  = al_jazeera(max_articles=20, poll_interval=3600)
npr_feed = npr_news(max_articles=10,   poll_interval=3600)
bbc_feed = bbc_world(max_articles=20,  poll_interval=3600)

aj_source  = Source(fn=aj_feed.run,  name="al_jazeera")
npr_source = Source(fn=npr_feed.run, name="npr_news")
bbc_source = Source(fn=bbc_feed.run, name="bbc_world")

# ── AI Agents ─────────────────────────────────────────────────
relevance_agent = ClaudeAgent(prompt="""
    Does this article mention MAGA, immigration policy, or the US border?
    Return JSON: {"relevant": true or false}
""", output_format="json")

sentiment_agent = ClaudeAgent(prompt="""
    What is the overall tone of this article?
    Return JSON: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "score": -1.0 to 1.0}
""", output_format="json")

stance_agent = ClaudeAgent(prompt="""
    Does this article present a pro, anti, or neutral stance on MAGA or immigration restriction?
    Return JSON: {"stance": "PRO" | "ANTI" | "NEUTRAL", "confidence": 0.0 to 1.0}
""", output_format="json")

reporter_agent = ClaudeAgent(prompt="""
    You receive a JSON batch of news articles grouped by source in by_source.
    Write a daily summary of how each source covered MAGA and immigration policy today.
    Note differences in framing or stance across sources.
    Plain text only, no markdown.
""", output_format="text")

# ── Transform Functions ───────────────────────────────────────
def filter_relevant(article):
    result = relevance_agent.run(article["text"])
    if not result["relevant"]:
        return None
    return article

def analyze_sentiment(article):
    result = sentiment_agent.run(article["text"])
    article["sentiment"] = result["sentiment"]
    article["score"]     = result["score"]
    return article

def analyze_stance(article):
    result = stance_agent.run(article["text"])
    article["stance"]      = result["stance"]
    article["confidence"]  = result["confidence"]
    return article

def display(article):
    icons = {"PRO": "🔵", "ANTI": "🔴", "NEUTRAL": "⚪"}
    icon  = icons.get(article["stance"], "?")
    print(f"{icon} [{article['source']:>12}] [{article['stance']:>7}] {article['title'][:60]}")

def write_report(batch):
    summary = reporter_agent.run(json.dumps(batch, indent=2))
    return {"report": summary}

def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY TOPIC DIGEST: MAGA / IMMIGRATION")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")

# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=200, clear_on_tick=True)
clock   = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
topic_filter = Transform(fn=filter_relevant,  name="topic_filter")
sentiment    = Transform(fn=analyze_sentiment, name="sentiment")
stance       = Transform(fn=analyze_stance,    name="stance")
display_sink = Sink(fn=display,                name="display")
batcher_node = Transform(fn=batcher.run,       name="batcher")
clock_source = Source(fn=clock.run,            name="clock")
report_node  = Transform(fn=write_report,      name="report_writer")
report_sink  = Sink(fn=print_report,           name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (aj_source,  topic_filter),
    (npr_source, topic_filter),
    (bbc_source, topic_filter),

    (topic_filter, sentiment),
    (sentiment,    stance),

    (stance,      display_sink),
    (stance,      batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n🗞️  Topic Tracker: MAGA / Immigration Policy")
    print("   Sources: Al Jazeera, NPR News, BBC World")
    print("   Streaming matching articles to console. Daily digest at midnight.")
    print("   Press Ctrl+C to stop.\n")
    g.run_network()
```

---

## Example 3: Climate and Environment Monitor

**Spec:**
```
SOURCES:
  - NASA
  - BBC Tech (covers environment)
  - NPR News

PROCESSING:
  - only keep articles about climate change, environment, or extreme weather
  - urgency: how urgent is the issue described (high, medium, low)?
  - region: which world region is primarily affected?

REPORT:
  - Stream articles showing source, urgency, and region
  - Daily digest: list high-urgency articles first, then by region
```

```python
# ============================================================
# Climate and Environment Monitor
# Monitors NASA, BBC, and NPR for climate and environment news.
#
# Topology:
#   nasa     ─┐
#   bbc_tech  ┼→ climate_filter → urgency → region → ┬→ display
#   npr_news ─┘                                       └→ batcher → report
#                                         clock ──────┘
# ============================================================

import json
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.rss_normalizer import nasa_news, bbc_tech, npr_news
from components.transforms.claude_agent import ClaudeAgent
from components.transforms.stateful_agent import StatefulAgent
from components.sources.clock_source import ClockSource

# ── Sources ──────────────────────────────────────────────────
nasa_feed = nasa_news(max_articles=10, poll_interval=3600)
bbc_feed  = bbc_tech(max_articles=20,  poll_interval=3600)
npr_feed  = npr_news(max_articles=10,  poll_interval=3600)

nasa_source = Source(fn=nasa_feed.run, name="nasa")
bbc_source  = Source(fn=bbc_feed.run,  name="bbc_tech")
npr_source  = Source(fn=npr_feed.run,  name="npr_news")

# ── AI Agents ─────────────────────────────────────────────────
relevance_agent = ClaudeAgent(prompt="""
    Does this article discuss climate change, the environment, or extreme weather?
    Return JSON: {"relevant": true or false}
""", output_format="json")

urgency_agent = ClaudeAgent(prompt="""
    How urgent is the environmental issue described in this article?
    Return JSON: {"urgency": "HIGH" | "MEDIUM" | "LOW", "reason": "one sentence"}
""", output_format="json")

region_agent = ClaudeAgent(prompt="""
    Which world region is primarily discussed in this article?
    Return JSON: {"region": "North America" | "Europe" | "Asia" | "Africa" |
                  "South America" | "Arctic/Antarctic" | "Global" | "Other"}
""", output_format="json")

reporter_agent = ClaudeAgent(prompt="""
    You receive a JSON batch of climate articles grouped by source in by_source.
    Write a daily climate digest. List HIGH urgency articles first, then MEDIUM,
    then LOW. For each article include the region affected and a one-sentence summary.
    Plain text only, no markdown.
""", output_format="text")

# ── Transform Functions ───────────────────────────────────────
def filter_climate(article):
    result = relevance_agent.run(article["text"])
    if not result["relevant"]:
        return None
    return article

def rate_urgency(article):
    result = urgency_agent.run(article["text"])
    article["urgency"] = result["urgency"]
    article["reason"]  = result["reason"]
    return article

def identify_region(article):
    result = region_agent.run(article["text"])
    article["region"] = result["region"]
    return article

def display(article):
    icons = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    icon  = icons.get(article["urgency"], "?")
    print(f"{icon} [{article['source']:>9}] [{article['region']:>14}] {article['title'][:55]}")

def write_report(batch):
    summary = reporter_agent.run(json.dumps(batch, indent=2))
    return {"report": summary}

def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY CLIMATE DIGEST")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")

# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=200, clear_on_tick=True)
clock   = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
climate_filter = Transform(fn=filter_climate,  name="climate_filter")
urgency        = Transform(fn=rate_urgency,     name="urgency")
region         = Transform(fn=identify_region,  name="region")
display_sink   = Sink(fn=display,               name="display")
batcher_node   = Transform(fn=batcher.run,      name="batcher")
clock_source   = Source(fn=clock.run,           name="clock")
report_node    = Transform(fn=write_report,     name="report_writer")
report_sink    = Sink(fn=print_report,          name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (nasa_source, climate_filter),
    (bbc_source,  climate_filter),
    (npr_source,  climate_filter),

    (climate_filter, urgency),
    (urgency,        region),

    (region,      display_sink),
    (region,      batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n🌍 Climate and Environment Monitor")
    print("   Sources: NASA, BBC Tech, NPR News")
    print("   Streaming climate articles to console. Daily digest at midnight.")
    print("   Press Ctrl+C to stop.\n")
    g.run_network()
```

---

## Example 4: Open Source / Developer News

**Spec:**
```
SOURCES:
  - Hacker News
  - TechCrunch
  - BBC Tech

PROCESSING:
  - only keep articles about open source software, developer tools, or programming
  - category: what kind of article is this (release, tutorial, opinion, news)?
  - language: which programming language is primarily discussed, if any?

REPORT:
  - Stream articles showing source, category, and language
  - Daily digest: group by category, then by language
```

```python
# ============================================================
# Open Source / Developer News
# Monitors tech sources for developer and open source content.
#
# Topology:
#   hacker_news ─┐
#   techcrunch   ┼→ dev_filter → category → language → ┬→ display
#   bbc_tech    ─┘                                      └→ batcher → report
#                                           clock ───────┘
# ============================================================

import json
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.rss_normalizer import hacker_news, techcrunch, bbc_tech
from components.transforms.claude_agent import ClaudeAgent
from components.transforms.stateful_agent import StatefulAgent
from components.sources.clock_source import ClockSource

# ── Sources ──────────────────────────────────────────────────
hn_feed  = hacker_news(max_articles=20, poll_interval=3600)
tc_feed  = techcrunch(max_articles=10,  poll_interval=3600)
bbc_feed = bbc_tech(max_articles=20,    poll_interval=3600)

hn_source  = Source(fn=hn_feed.run,  name="hacker_news")
tc_source  = Source(fn=tc_feed.run,  name="techcrunch")
bbc_source = Source(fn=bbc_feed.run, name="bbc_tech")

# ── AI Agents ─────────────────────────────────────────────────
relevance_agent = ClaudeAgent(prompt="""
    Does this article discuss open source software, developer tools, or programming?
    Return JSON: {"relevant": true or false}
""", output_format="json")

category_agent = ClaudeAgent(prompt="""
    What category best describes this developer article?
    Return JSON: {"category": "RELEASE" | "TUTORIAL" | "OPINION" | "NEWS" | "OTHER"}
""", output_format="json")

language_agent = ClaudeAgent(prompt="""
    Which programming language is primarily discussed in this article, if any?
    Return JSON: {"language": "Python" | "JavaScript" | "Rust" | "Go" | "Java" |
                  "C/C++" | "TypeScript" | "Other" | "None"}
""", output_format="json")

reporter_agent = ClaudeAgent(prompt="""
    You receive a JSON batch of developer news articles grouped by source in by_source.
    Write a daily developer digest. Group articles by category (RELEASE first, then
    TUTORIAL, OPINION, NEWS). Within each category note the programming language.
    Plain text only, no markdown.
""", output_format="text")

# ── Transform Functions ───────────────────────────────────────
def filter_dev_articles(article):
    result = relevance_agent.run(article["text"])
    if not result["relevant"]:
        return None
    return article

def classify_category(article):
    result = category_agent.run(article["text"])
    article["category"] = result["category"]
    return article

def identify_language(article):
    result = language_agent.run(article["text"])
    article["language"] = result["language"]
    return article

def display(article):
    cat  = article.get("category", "?")[:7]
    lang = article.get("language", "?")[:10]
    print(f"🛠️  [{article['source']:>12}] [{cat:>7}] [{lang:>10}] {article['title'][:50]}")

def write_report(batch):
    summary = reporter_agent.run(json.dumps(batch, indent=2))
    return {"report": summary}

def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY DEVELOPER DIGEST")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")

# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=200, clear_on_tick=True)
clock   = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
dev_filter   = Transform(fn=filter_dev_articles, name="dev_filter")
category     = Transform(fn=classify_category,   name="category")
language     = Transform(fn=identify_language,   name="language")
display_sink = Sink(fn=display,                  name="display")
batcher_node = Transform(fn=batcher.run,         name="batcher")
clock_source = Source(fn=clock.run,              name="clock")
report_node  = Transform(fn=write_report,        name="report_writer")
report_sink  = Sink(fn=print_report,             name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (hn_source,  dev_filter),
    (tc_source,  dev_filter),
    (bbc_source, dev_filter),

    (dev_filter, category),
    (category,   language),

    (language,    display_sink),
    (language,    batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n🛠️  Open Source / Developer News")
    print("   Sources: Hacker News, TechCrunch, BBC Tech")
    print("   Streaming developer articles to console. Daily digest at midnight.")
    print("   Press Ctrl+C to stop.\n")
    g.run_network()
```

---

## Example 5: Job Postings Monitor

**Spec:**
```
SOURCES:
  - Python.org Jobs
  - RemoteOK
  - We Work Remotely

PROCESSING:
  - only keep postings for software engineering or data science roles
  - seniority: is this a junior, mid-level, or senior role?
  - remote: is this role fully remote, hybrid, or on-site?

REPORT:
  - Stream each posting showing source, seniority, and remote status
  - Daily digest: list new postings grouped by seniority level
```

```python
# ============================================================
# Job Postings Monitor
# Monitors three job boards for software and data science roles.
#
# Topology:
#   python_jobs      ─┐
#   remoteok          ┼→ job_filter → seniority → remote → ┬→ display
#   we_work_remotely ─┘                                     └→ batcher → report
#                                               clock ───────┘
# ============================================================

import json
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.rss_normalizer import python_jobs, remoteok, we_work_remotely
from components.transforms.claude_agent import ClaudeAgent
from components.transforms.stateful_agent import StatefulAgent
from components.sources.clock_source import ClockSource

# ── Sources ──────────────────────────────────────────────────
pj_feed  = python_jobs(max_articles=20,      poll_interval=3600)
rok_feed = remoteok(max_articles=20,         poll_interval=3600)
wwr_feed = we_work_remotely(max_articles=20, poll_interval=3600)

pj_source  = Source(fn=pj_feed.run,  name="python_jobs")
rok_source = Source(fn=rok_feed.run, name="remoteok")
wwr_source = Source(fn=wwr_feed.run, name="we_work_remotely")

# ── AI Agents ─────────────────────────────────────────────────
relevance_agent = ClaudeAgent(prompt="""
    Is this a job posting for a software engineering or data science role?
    Return JSON: {"relevant": true or false}
""", output_format="json")

seniority_agent = ClaudeAgent(prompt="""
    What seniority level is this job posting targeting?
    Return JSON: {"seniority": "JUNIOR" | "MID" | "SENIOR" | "LEAD" | "ANY"}
""", output_format="json")

remote_agent = ClaudeAgent(prompt="""
    What is the remote work arrangement for this job posting?
    Return JSON: {"remote": "REMOTE" | "HYBRID" | "ON-SITE" | "UNKNOWN"}
""", output_format="json")

reporter_agent = ClaudeAgent(prompt="""
    You receive a JSON batch of job postings grouped by source in by_source.
    Write a daily jobs digest. Group postings by seniority (JUNIOR first, then
    MID, SENIOR, LEAD). For each posting include the source board and remote status.
    Plain text only, no markdown.
""", output_format="text")

# ── Transform Functions ───────────────────────────────────────
def filter_jobs(article):
    result = relevance_agent.run(article["text"])
    if not result["relevant"]:
        return None
    return article

def classify_seniority(article):
    result = seniority_agent.run(article["text"])
    article["seniority"] = result["seniority"]
    return article

def classify_remote(article):
    result = remote_agent.run(article["text"])
    article["remote"] = result["remote"]
    return article

def display(article):
    sen    = article.get("seniority", "?")[:6]
    remote = article.get("remote", "?")[:8]
    icons  = {"REMOTE": "🌐", "HYBRID": "🏠", "ON-SITE": "🏢", "UNKNOWN": "❓"}
    icon   = icons.get(article.get("remote", ""), "❓")
    print(f"{icon} [{article['source']:>16}] [{sen:>6}] {article['title'][:55]}")

def write_report(batch):
    summary = reporter_agent.run(json.dumps(batch, indent=2))
    return {"report": summary}

def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY JOBS DIGEST")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")

# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=200, clear_on_tick=True)
clock   = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
job_filter   = Transform(fn=filter_jobs,         name="job_filter")
seniority    = Transform(fn=classify_seniority,  name="seniority")
remote       = Transform(fn=classify_remote,     name="remote")
display_sink = Sink(fn=display,                  name="display")
batcher_node = Transform(fn=batcher.run,         name="batcher")
clock_source = Source(fn=clock.run,              name="clock")
report_node  = Transform(fn=write_report,        name="report_writer")
report_sink  = Sink(fn=print_report,             name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (pj_source,  job_filter),
    (rok_source, job_filter),
    (wwr_source, job_filter),

    (job_filter, seniority),
    (seniority,  remote),

    (remote,      display_sink),
    (remote,      batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n💼 Job Postings Monitor")
    print("   Sources: Python.org Jobs, RemoteOK, We Work Remotely")
    print("   Streaming new postings to console. Daily digest at midnight.")
    print("   Press Ctrl+C to stop.\n")
    g.run_network()
```

---

## How to Build Your Own App

Fill in this spec and paste it to Claude along with this entire document:

```
SOURCES:
  - [list the feed names from the verified feeds table above]

PROCESSING:
  - [one line per transform step]
  - Use "only keep articles that ..." for filters
  - Use "key_name: what to detect or extract" for transforms

REPORT:
  - [describe what streaming output should look like]
  - [describe what the daily digest should contain]

Build me a DisSysLab app from this spec.
```

Claude will generate a complete working app following the pattern shown in the five examples above.

**Note:** AI analysis costs money. Each article passing through an AI transform makes one API call to Claude. Filters reduce cost by dropping irrelevant articles early in the pipeline.