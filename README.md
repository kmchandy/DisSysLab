# DisSysLab

**Build persistent distributed systems by describing what you want.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What Is DisSysLab?

DisSysLab lets you build AI-powered distributed systems that run forever — monitoring news, analyzing social media, filtering content, sending alerts — using ordinary Python.

You don't need to know anything about threads, processes, locks, or message passing. You don't even need to write most of the code. Describe what you want to Claude, and it generates a working DisSysLab application. Then learn how it works, customize it, and make it yours.

## The Fastest Way to Start

Tell Claude (or any AI assistant):

> "Using the DisSysLab framework, build me an app that monitors an RSS feed for articles about AI, filters out irrelevant ones, analyzes sentiment, and saves the results to a file. Use mock components so I can run it without API keys."

Claude generates a complete working application. You run it. It works.

**That's Module 1.** The rest of the course teaches you what just happened and how to build your own.

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

### Module 1: Describe and Build
*Your first distributed system in 10 minutes*

Tell Claude what you want. It generates a working app. You run it. Then walk through the generated code to understand the three building blocks (Source, Transform, Sink), how messages flow through a pipeline, and how filtering works (return `None` to drop a message). Every example includes a mock version (runs instantly, no API keys) and a real version (swap one line to use live data and AI).

### Module 2: Multiple Sources, Multiple Destinations
*Build a real monitoring system*

Pull from multiple RSS feeds, social media streams, or APIs into one processor (fanin). Send results to multiple destinations — file, email, dashboard (fanout). Your app goes from "process one stream" to "aggregate and distribute" in a single module.

### Module 3: Smart Routing
*Send the right data to the right place*

Route messages based on content: positive sentiment one way, negative another. Split streams by category. Combine patterns into diamond networks and complex DAGs. Mock classifiers use keywords; real classifiers use AI prompts.

### Module 4: AI Integration
*The Prompt → JSON → Python pattern*

Swap mock components for real AI. Learn how a prompt defines behavior, JSON structures the output, and a Python function interprets the result. Build AI-powered transforms for sentiment analysis, content moderation, topic classification, entity extraction — or anything you can describe in a prompt.

### Module 5: Build Your Own App
*From idea to working system*

The systematic design process: draw your network, identify components, test each function independently, assemble incrementally, debug with network taps. Build the application you actually want — not a textbook exercise.

### Module 6+: Gallery
*Inspiration for what's possible*

Domain-specific examples: image processing pipelines, audio analysis, scientific computing, numeric processing with NumPy and pandas. Each is a complete working application you can run, study, and adapt.

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
python3 -m examples.module_01.example
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