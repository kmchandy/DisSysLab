# DisSysLab

**Mission**: DisSysLab (dsl) makes distributed systems accessible to anybody familiar with elementary programming. You build a distributed application by simply associating ordinary Python functions with nodes of a network. 


[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Persistent distributed applications** With dsl you can build persistent networks that include AI agents, streaming data sources such as social media feeds, and connections to services such as email and calendars.

**Teaching**: dsl is used as part of an online, self-study course in distributed algorithms for first-year undergraduates. Most distributed programming frameworks are based on concurrency concepts such as threads, processes, message-passing, and locks. You build a distributed app with dsl by assigning ordinary Python functions to nodes of a network. 

### Quick Start: An Example Network

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Step 1: Write ordinary Python functions
list_data = ListSource(items=["hello", "world"])

def make_uppercase(text):
    return text.upper()

# Step 2: Wrap functions into network nodes
source = Source(fn=list_data.run, name="source")
uppercase = Transform(fn=make_uppercase, name="uppercase")
results = []
collector = Sink(fn=results.append, name="collector")

# Step 3: Build and run the network
g = network([
    (source, uppercase),
    (uppercase, collector)
])

g.run_network()

print(results)  # ['HELLO', 'WORLD']
```

You just built a distributed system where nodes run concurrently.

## Core Idea

DisSysLab has three layers:

```
Layer 1: Plain Python Functions (your code)
    ↓
Layer 2: Network Nodes (Source, Transform, Agent, Sink)
    ↓  
Layer 3: Distributed Network (runs concurrently)
```

You write Layer 1. dsl handles Layers 2 & 3.

### Network

A network is specified by a directed graph. The nodes of a networks are called agents. We often use the following special cases of agents

- **Source** - Generates data (RSS feeds, sensors, databases)
- **Transform** - Processes data (filter spam, analyze sentiment, translate)
- **Sink** - Consumes data (save to file, send email, display)

This documentation discusses acyclic networks first and general networks later.

## A Persistent Network of Agents: AI News Monitor

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import RSSSource
from components.transformers.claude_agent import ClaudeAgent
from components.transformers.prompts import get_prompt

# Connect to real RSS feeds
hacker_news = Source(fn=RSSSource("https://news.ycombinator.com/rss").run, name="hn")
reddit = Source(fn=RSSSource("https://reddit.com/r/python/.rss").run, name="reddit")

# AI-powered spam filter
spam_filter = Transform(
    fn=ClaudeAgent(get_prompt("spam_detector")).run,
    name="spam_filter"
)

# AI sentiment analysis
sentiment = Transform(
    fn=ClaudeAgent(get_prompt("sentiment_analyzer")).run,
    name="sentiment"
)

# Build network with fanin and pipeline patterns
g = network([
    (hacker_news, spam_filter),  # Fanin: Two sources
    (reddit, spam_filter),        # merge automatically
    (spam_filter, sentiment),     # Pipeline: Filter then analyze
    (sentiment, archive)          # Save results
])

g.run_network()
```


## What You Can Build

### Data Processing
- Multi-source RSS aggregators
- Social media content monitors
- Log file analyzers
- Streaming data pipelines
- Multi-path processing networks

### AI Applications
- Sentiment analysis systems
- Content moderation pipelines
- Spam detection networks
- Multi-language translators
- Automated summarizers
- Topic classifiers

### Integrations
- Gmail → AI analysis → Calendar events
- Twitter → sentiment → alerts
- RSS feeds → translation → email digest
- Multiple APIs → data fusion → dashboard

## Installation

```bash
git clone https://github.com/yourusername/DisSysLab.git
cd DisSysLab

python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Run first example
python3 -m examples.module_01_basics.example
```

## Learning Path

**→ Start here:** [Module 01: The Lightning Strike](examples/module_01_basics/) (30 minutes)

**Module 1: The Lightning Strike** (30 minutes)
- First network in 5 minutes
- Understanding the three-layer model
- Immediate success experience

**Module 2: The Fundamental Patterns** (3-4 hours)
- Pipeline: Linear chains
- Fanout: Broadcasting to multiple destinations
- Fanin: Merging multiple sources
- Trees and DAGs: Complex topologies

**Module 3: Messages are Dictionaries** (2 hours)
- Structured data flow
- Field passing and enrichment
- Multi-path data combination

**Module 4: Filtering and Routing** (2 hours)
- Conditional message dropping
- Path-specific filtering
- Priority-based routing

**Module 5: The Component Library** (2 hours)
- Reusable sources, transforms, sinks
- Mock vs real components
- Rapid composition

**Module 6: Complex Network Design** (3 hours)
- Gather-process-distribute patterns
- Hierarchical processing
- Custom topology design

**Module 7: Your First Real App** (3-4 hours)
- Complete application project
- Sophisticated topologies
- Real-world problem solving

**Module 8: Prompts are Programs** (2 hours)
- AI agent basics
- Prompt library usage
- JSON output handling

**Module 9: AI Composition** (2-3 hours)
- Chaining AI agents
- Multi-AI pipelines
- AI + logic integration

**Module 10: Custom Prompts** (2 hours)
- Writing effective prompts
- Prompt engineering
- Creating custom AI agents

**Module 11: Production Ready** (3 hours)
- Mock to real service transition
- API integration
- Error handling and monitoring

**Module 12: Your Capstone** (4-6 hours)
- Student-designed project
- Application of all concepts
- Portfolio piece

## Key Features

### For Students
- ✅ No threading knowledge required
- ✅ Build real apps from day one
- ✅ Mock components for safe learning
- ✅ Any network topology supported
- ✅ Clear error messages and timeouts
- ✅ Progressive complexity

### For Developers
- ✅ Integrate AI services easily
- ✅ Connect to RSS, Gmail, Twitter APIs
- ✅ Reusable component library
- ✅ 40+ AI prompts ready to use
- ✅ Swap mocks for production seamlessly
- ✅ Design complex topologies naturally

## Documentation

- [Quick Start Tutorial](docs/quickstart.md) - Get started in 5 minutes
- [Core Concepts](docs/concepts.md) - How DisSysLab works
- [Network Topologies Guide](docs/topologies.md) - Designing network shapes
- [Prompt Library](components/transformers/prompts.py) - 40+ AI agent prompts
- [API Reference](docs/api.md) - Complete documentation
- [Examples](examples/) - Progressive tutorials
- [Teaching Guide](docs/teaching.md) - For instructors
- [Site Directory Structure](dev/README_Directory.md)

## Philosophy

**Simple First**: Write ordinary Python. No special syntax or complex APIs.

**Real Applications**: Build useful systems, not toy examples. Students stay engaged when they create things that matter.

**Any Topology**: Not just pipelines - build networks with any acyclic structure to match your problem.

**Progressive Learning**: Start with a 3-node pipeline. End with complex multi-agent AI systems. Add one concept at a time.

**Safe Exploration**: Mock components let students experiment without API costs or production complexity.

## Contributing

We welcome contributions:
- **Components** - Add sources (APIs, databases) or sinks (notifications, storage)
- **Prompts** - Expand the AI prompt library
- **Examples** - Real-world application networks
- **Network patterns** - Document common topologies
- **Documentation** - Tutorials and guides
- **Course modules** - Teaching materials

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE)

## Citation

```bibtex
@software{dissyslab2025,
  title = {DisSysLab: A Teaching Framework for Distributed Systems},
  author = {Chandy, K. Mani},
  year = {2025},
  url = {https://github.com/yourusername/DisSysLab}
}
```

## Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/DisSysLab/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/DisSysLab/discussions)

---

**Ready to build?** Start with [Quick Start Tutorial](docs/quickstart.md) →