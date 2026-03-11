# DisSysLab

**Build persistent distributed systems by describing what you want.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Get Started in Three Steps

### Step 1 — Run a live app (no coding required)

The `gallery/` directory has six apps you can run immediately. Each monitors
real data sources, analyzes content with AI, and streams results to your terminal.

| App | What it tracks |
|-----|---------------|
| `gallery/ai_ml_research/` | AI and ML news across four tech sources |
| `gallery/topic_tracker/` | Any news topic across three global sources |
| `gallery/job_postings/` | Software and data science job postings |
| `gallery/developer_news/` | Open source and developer tool news |
| `gallery/climate_monitor/` | Climate and environment news |
| `gallery/arxiv_tracker/` | New research papers on arXiv |

**Try it now — no API key needed:**

```bash
python3 -m gallery.ai_ml_research.demo
```

**Run a live app (requires an Anthropic API key):**

```bash
export ANTHROPIC_API_KEY='your-key-here'
python3 -m gallery.ai_ml_research.app
```

Each app has a README explaining what it does and how to customize it.
See [gallery/README.md](gallery/README.md) for the full overview.

---

### Step 2 — Build your own app

To build an app that doesn't exist in the gallery, paste
`gallery/CLAUDE_CONTEXT.md` into Claude along with a spec:

```
SOURCES:
  - Hacker News
  - TechCrunch

PROCESSING:
  - only keep articles about cybersecurity
  - severity: how serious is the threat described (critical, high, medium, low)?

REPORT:
  - Stream articles showing source, severity, and title
  - Daily digest: list critical and high severity articles first

Build me a DisSysLab app from this spec.
```

Claude will generate a complete working app following the same pattern as
the gallery apps.

---

### Step 3 — Learn how it works

The `examples/` directory contains eight modules that teach the framework
from first principles, starting with a single source → transform → sink
pipeline and building up to full AI-powered agentic applications.

| Module | Concept |
|--------|---------|
| Module 01 | Source, Transform, Sink — the three building blocks |
| Module 02 | Filtering — dropping messages with `return None` |
| Module 03 | Fanout — one source, multiple destinations |
| Module 04 | Fanin — multiple sources, one destination |
| Module 05 | Split — routing messages by content |
| Module 06 | Merge — synchronizing streams |
| Module 07 | Topologies — fork, join, diamond, DAG |
| Module 08 | AI Agents — prompts as transforms |

To extend an existing example with Claude's help, paste `CLAUDE_CONTEXT.md`
into Claude along with the code you want to modify.

## What Is DisSysLab?

DisSysLab lets you build AI-powered distributed systems that run forever — monitoring news, analyzing social media, filtering content, sending alerts — using ordinary Python.

You don't need to know anything about threads, processes, locks, or message passing. You don't even need to write most of the code. Describe what you want to Claude, and it generates a working DisSysLab application. Then learn how it works, customize it, and make it yours.

## The Fastest Way to Start

Tell Claude (or any AI assistant):

> "Using the DisSysLab framework, build me an app that monitors an RSS feed for articles about AI, filters out irrelevant ones, analyzes sentiment, and saves the results to a file. Use mock components so I can run it without API keys."

Claude generates a complete working application. You run it. It works.

**That's Module 01.** The rest of the course teaches you what just happened and how to build your own.

## Five Live Apps You Can Run Right Now

No setup beyond an API key. Each monitors real data sources continuously
and delivers a daily AI-generated digest.

| App | What it does | Customize |
|-----|-------------|-----------|
| 🤖 [AI/ML Research Tracker](gallery/ai_ml_research/) | Tracks AI developments across 4 tech sources | — |
| 📰 [Topic Tracker](gallery/topic_tracker/) | Monitors 3 international outlets for your topics | `TOPICS` list |
| 💼 [Job Postings Monitor](gallery/job_postings/) | Finds jobs matching your profile across 3 boards | `JOB_CRITERIA` paragraph |
| 🛠️ [Developer News Tracker](gallery/developer_news/) | Filters dev news by your interests across 3 sources | `DEV_INTERESTS` list |
| 🌍 [Climate Monitor](gallery/climate_monitor/) | Tracks climate news across NASA, BBC, NPR | `CLIMATE_TOPICS` list |
```bash
export ANTHROPIC_API_KEY='your-key'
python -m gallery.topic_tracker.app
```

Streams matching articles to the console. Prints a digest once a day.
`Ctrl+C` to stop. To personalize, edit the config variables at the top
of `app.py` — no other code needs to change.

See the [Gallery README](gallery/README.md) for details on all five apps.

---

## Quick Example: What DisSysLab Code Looks Like
```python
from dsl import network
from dsl.blocks import Source, Transform, Sink

# Three ordinary Python functions
rss_feed = Source(fn=mock_rss.run, name="news")
analyze  = Transform(fn=sentiment_analyzer, name="sentiment")
save     = Sink(fn=file_writer.run, name="archive")

# Connect them into a network
g = network([
    (rss_feed, analyze),
    (analyze, save)
])

# Run — nodes execute concurrently, messages flow automatically
g.run_network()
```

Every DisSysLab app follows this pattern: wrap Python functions into nodes, connect nodes into a network, run. The framework handles concurrency, message passing, and clean shutdown.

## Who Is This For?

**Students** learning distributed systems. You'll build real applications from the first module — news monitors, social media analyzers, content filters — and learn the underlying concepts by understanding what you've built.

**Hobbyists and developers** who want persistent monitoring and automation systems without infrastructure complexity. Describe what you want, generate it, run it.

Both paths use the same framework and the same modules. Students work through the full sequence. Hobbyists skip to what they need.

## Learning Path

### Module 01: Describe and Build
*Your first distributed system in 10 minutes*

Tell Claude what you want. It generates a working app. You run it. Then walk through the generated code to understand the three building blocks (Source, Transform, Sink), how messages flow through a pipeline, and how filtering works (return `None` to drop a message). Every example includes a mock version (runs instantly, no API keys) and a real version (swap one line to use live data and AI).

### Module 02: Filtering
*Selective message processing*

Return `None` from any Transform to drop a message. Build conditional pipelines that pass only the data you care about — invalid entries, spam, low-priority items filtered out cleanly with no special syntax.

### Module 03: Fanout
*Broadcast to multiple destinations*

Send one message to many destinations simultaneously — file, email, dashboard, database. Build monitoring systems that alert through multiple channels at once.

### Module 04: Fanin
*Merge multiple sources*

Pull from multiple RSS feeds, social media streams, or APIs into one processor. Your app goes from "process one stream" to "aggregate from many" in a single module.

### Module 05: Split
*Route messages by content*

Route messages based on content: positive sentiment one way, negative another. Split streams by category. Send the right data to the right place.

### Module 06: Merge Synch
*Synchronize multiple streams*

Combine messages from multiple sources in lockstep — useful when you need paired data from different feeds before processing.

### Module 07: Complex Patterns
*Fork, join, diamond, general DAG*

Combine the building blocks into sophisticated topologies. Any acyclic graph is expressible. Match your network shape to your problem.

### Module 08: AI Agents
*Build transformers from plain-English prompts*

Swap mock components for real AI. Learn how a prompt defines behavior, JSON structures the output, and a Python function interprets the result. Build AI-powered transforms for sentiment analysis, content moderation, topic classification, entity extraction — or anything you can describe in a prompt. The gallery apps are all built on this pattern.

## Core Concepts

DisSysLab has three layers:
```
Layer 1: Python functions         (you write these — or Claude does)
Layer 2: Network nodes            (Source, Transform, Sink)
Layer 3: Distributed execution    (concurrent threads, message queues)
```

You work in Layers 1 and 2. DisSysLab handles Layer 3.

**Four node types:**

- **Source** — generates data (RSS feeds, APIs, sensors, databases)
- **Transform** — processes data (filter, analyze, enrich, classify)
- **Sink** — consumes data (save to file, send email, post to webhook)
- **Agent** — general node with multiple inputs and outputs (advanced)

**Network topologies:** pipeline, fanin, fanout, split, diamond, trees, arbitrary DAGs. Any acyclic graph.

**Mock and real:** Every component has a mock version (no API keys, instant results) and a real version (live data, AI analysis). Swap with one line change.

**Filtering:** Return `None` from any transform to drop a message. Simple, powerful, no special syntax.

## Installation
```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab

python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Verify it works:
```bash
python3 -m examples.module_01_basics.example
```

## What You Can Build

**Monitoring and alerts** — track social media mentions, watch for job opportunities, detect anomalies in data streams, monitor competitor activity.

**Content aggregation** — multi-source RSS readers with AI summaries, research paper monitors, market intelligence gathering, news digests filtered by topic and sentiment.

**AI pipelines** — sentiment tracking, content moderation, language translation chains, multi-agent analysis, automated summarization.

**Automation** — email categorization, scheduled report generation, multi-step workflows, data fusion from multiple APIs.

## Key Features

**No concurrency knowledge required.** Write ordinary Python functions. The framework handles threads, queues, message passing, and shutdown.

**AI-native.** Prompts are first-class components. Mock AI for learning, real AI for production. 40+ pre-built prompts included.

**Any topology.** Not just pipelines — fanin, fanout, split, diamond, trees, arbitrary DAGs. Match your network shape to your problem.

**Mock-first.** Every example runs without API keys or credentials. Add real data sources and AI when you're ready.

**Persistent.** Networks run continuously — monitoring, analyzing, alerting — until you stop them.

## Philosophy

**Excitement first.** Build something real before learning how it works. Motivation drives understanding, not the other way around.

**AI from the start.** Every module shows mock (keyword-based) and real (AI-powered) versions side by side. AI isn't an advanced topic — it's the point.

**Real applications, not toy examples.** You build news monitors, sentiment analyzers, content filters — systems you'd actually use.

**Describe, generate, understand.** Tell Claude what you want. Get working code. Then learn what it does and how to customize it.

## For Instructors

Teaching materials, course guides, and pedagogy notes are in the [for_instructors/](for_instructors/) directory.

## Contributing

We welcome contributions in connectors (new data sources and sinks), AI prompts, example applications, documentation, and course modules. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Citation
```bibtex
@software{dissyslab2025,
  title = {DisSysLab: Build Persistent Distributed Systems with Simple Python},
  author = {Chandy, K. Mani},
  year = {2025},
  url = {https://github.com/kmchandy/DisSysLab}
}
```

## Support

- **Issues:** [GitHub Issues](https://github.com/kmchandy/DisSysLab/issues)
- **Discussions:** [GitHub Discussions](https://github.com/kmchandy/DisSysLab/discussions)