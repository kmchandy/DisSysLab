# DisSysLab

**Build persistent monitoring and automation systems with simple Python.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**No threading knowledge required.** Write ordinary Python functions. Connect them in a network. Run persistent applications that monitor, analyze, and alert—forever.

---

## Who Uses DisSysLab?

### **For Developers & Researchers**
Build "set and forget" monitoring systems:
- 📡 Monitor social media for job opportunities or market trends
- 📰 Aggregate news from multiple sources with AI analysis
- 🔔 Get alerts when specific events happen
- 🤖 Create AI-powered data pipelines
- 📊 Track competitors and analyze sentiment

### **For Students**
Learn distributed systems by building real applications:
- ✅ No threading or async/await required
- ✅ Build useful apps from day one
- ✅ Progressive tutorials from simple to complex
- ✅ Complete self-study course included

---

## Quick Example: Social Media Monitor

Monitor BlueSky for mentions of "distributed systems" → AI sentiment analysis → Slack alerts:

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import BlueSkyJetstreamSource
from components.sinks import Webhook

# 1. Stream live posts from BlueSky
bluesky = BlueSkyJetstreamSource(
    search_keywords=["distributed systems"],
    max_posts=100
)

# 2. Filter and analyze with simple functions
def filter_relevant(post):
    # Your logic here
    return post if is_interesting(post) else None

def analyze_sentiment(post):
    # Add AI analysis
    post['sentiment'] = get_sentiment(post['text'])
    return post

# 3. Send alerts
slack = Webhook(url="https://hooks.slack.com/...")

# 4. Build the network
source = Source(fn=bluesky.run, name="bluesky")
filter_node = Transform(fn=filter_relevant, name="filter")
sentiment_node = Transform(fn=analyze_sentiment, name="sentiment")
alerts = Sink(fn=slack.run, name="alerts")

g = network([
    (source, filter_node),
    (filter_node, sentiment_node),
    (sentiment_node, alerts)
])

# 5. Run forever
g.run_network()
```

**That's it!** Your monitor runs 24/7 in ~30 lines of Python.

---

## Why DisSysLab?

**🎯 Simple**
- Write ordinary Python functions
- No threading, processes, or locks
- No async/await required
- No cluster setup or infrastructure

**⚡ Powerful**
- Persistent networks that run forever
- Any network topology (not just pipelines)
- Concurrent execution automatic
- Built-in error handling

**🤖 AI-Ready**
- Integrate ChatGPT/Claude with simple prompts
- 40+ pre-built AI agent templates
- No API boilerplate needed

**📚 Complete Learning Path**
- Self-study course from basics to advanced
- Build real apps, not toy examples
- Mock components for safe learning

---

## Core Concept: Three Simple Layers

DisSysLab separates **what** (your code) from **how** (the execution):

```
Layer 1: Plain Python Functions (you write these)
    ↓
Layer 2: Network Nodes (Source, Transform, Sink)
    ↓  
Layer 3: Distributed Network (runs concurrently)
```

**You write Layer 1.** DisSysLab handles Layers 2 & 3.

### Network Building Blocks

- **Source** - Generates data (RSS feeds, APIs, streams, databases)
- **Transform** - Processes data (filter, analyze, enrich, route)
- **Sink** - Consumes data (files, webhooks, email, databases)

Connect them in **any topology:** pipelines, trees, DAGs, fanout, fanin.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Verify Installation (5 Minutes)

Run your first network:

```bash
python3 -m examples.module_01_basics.example
```

**Expected output:**
```
Results: ['HELLO!!', 'WORLD!!']
✓ Pipeline completed successfully!
```

**✅ Success!** You just ran a distributed network.  
**❌ Error?** See [Installation Help](docs/getting-started.md)

---

## What You Can Build

### **Personal Automation**
- Monitor job boards for opportunities → Slack notifications
- Track news for specific topics → Daily email digest
- Watch competitor activity → Real-time dashboard
- Aggregate RSS feeds → AI-powered summaries

### **Data Processing**
- Multi-source data aggregation
- Streaming data pipelines
- Real-time analytics
- ETL workflows

### **AI Applications**
- Sentiment analysis systems
- Content moderation pipelines
- Multi-agent AI workflows
- Automated summarization
- Topic classification

### **Integrations**
- Social media → AI analysis → Alerts
- RSS feeds → Translation → Email
- Multiple APIs → Data fusion → Dashboard
- Email → Categorization → Auto-filing

---

## Learning Path

### **For Quick Start (Power Users)**

**1. Run the first example** (5 min)
```bash
python3 -m examples.module_01_basics.example
```

**2. Read the quick reference** (10 min)
- [QUICKSTART.md](examples/module_10_build_apps/QUICKSTART.md) - Copy-paste templates

**3. Build your app** (30 min)
- [BUILD_APP.md](examples/module_10_build_apps/BUILD_APP.md) - Systematic process

**4. When stuck**
- [DEBUGGING.md](examples/module_10_build_apps/DEBUGGING.md) - Troubleshooting guide

---

### **For Complete Course (Students)**

**Start here:** [Module 01: Basics](examples/module_01_basics/) (30 minutes)

#### **Core Sequence** (Required - 6-8 hours)
Build foundation by completing these in order:

1. **[Module 01: Basics](examples/module_01_basics/)** - Your first network (30 min) ⭐ START
2. **[Module 02: Filtering](examples/module_02_filtering/)** - Conditional processing (1 hour)
3. **[Module 03: Fanout](examples/module_03_fanout/)** - Broadcasting (1 hour)
4. **[Module 04: Fanin](examples/module_04_fanin/)** - Merging sources (1 hour)
5. **[Module 09: Connectors](examples/module_09_connectors/)** - Real-world data (2 hours)
6. **[Module 10: Build Apps](examples/module_10_build_apps/)** - Systematic development (2-3 hours)

#### **Advanced Topics** (Optional)
Explore after completing core modules:

- **[Module 05: Split](examples/module_05_split/)** - Stream splitting
- **[Module 06: Merge Synch](examples/module_06_merge_synch/)** - Synchronous merging
- **[Module 07: Complex Patterns](examples/module_07_complex_patterns/)** - Advanced topologies
- **[Module 08: Prompts](examples/module_08_prompts/)** - AI integration
- **[Module 11: Numeric](examples/module_11_numeric/)** - NumPy and pandas

**Complete learning sequence:** [Module Order Guide](docs/module-order.md)

---

## Example: Your First Network

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Step 1: Write ordinary Python functions
data = ListSource(items=["hello", "world"])

def make_uppercase(text):
    return text.upper()

def add_emphasis(text):
    return text + "!!"

# Step 2: Wrap into network nodes
source = Source(fn=data.run, name="source")
uppercase = Transform(fn=make_uppercase, name="uppercase")
emphasize = Transform(fn=add_emphasis, name="emphasize")
results = []
collector = Sink(fn=results.append, name="collector")

# Step 3: Define network topology
g = network([
    (source, uppercase),
    (uppercase, emphasize),
    (emphasize, collector)
])

# Step 4: Run the network
g.run_network()

print(results)  # ['HELLO!!', 'WORLD!!']
```

**You just built a concurrent distributed system!**

---

## Real-World Example: News Aggregator

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import RSSSource
from components.sinks import EmailSender, FileWriter

# Multiple RSS sources (fanin)
tech_crunch = Source(fn=RSSSource("https://techcrunch.com/feed/").run, name="tc")
hacker_news = Source(fn=RSSSource("https://news.ycombinator.com/rss").run, name="hn")

# Filter for AI-related articles
def filter_ai_news(article):
    keywords = ['ai', 'artificial intelligence', 'machine learning', 'llm']
    text = article.get('title', '').lower()
    return article if any(k in text for k in keywords) else None

# Format as email
def format_email(article):
    return {
        'subject': 'AI News Digest',
        'body': f"{article['title']}\n{article['link']}"
    }

# Build network (fanin → filter → fanout)
filter_node = Transform(fn=filter_ai_news, name="filter")
formatter = Transform(fn=format_email, name="format")
email_sink = Sink(fn=EmailSender(...).run, name="email")
file_sink = Sink(fn=FileWriter("news.json").run, name="file")

g = network([
    # Fanin: Multiple sources merge
    (tech_crunch, filter_node),
    (hacker_news, filter_node),
    
    # Process
    (filter_node, formatter),
    
    # Fanout: Multiple outputs
    (formatter, email_sink),
    (formatter, file_sink)
])

g.run_network()
```

---

## Documentation

### **Quick References**
- [Quick Start Templates](examples/module_10_build_apps/QUICKSTART.md) - Copy-paste to get started
- [Building Apps Guide](examples/module_10_build_apps/BUILD_APP.md) - Systematic process
- [Debugging Guide](examples/module_10_build_apps/DEBUGGING.md) - Troubleshooting

### **Learning**
- [Examples Directory](examples/) - Progressive tutorials
- [Module Order](docs/module-order.md) - Learning sequence
- [How It Works](docs/how-it-works.md) - Under the hood

### **For Instructors**
- [Teaching Materials](for_instructors/) - Course guides and pedagogy

---

## Key Features

### **Simplicity**
- ✅ No threading knowledge required
- ✅ No async/await needed
- ✅ Write ordinary Python functions
- ✅ Clear error messages

### **Flexibility**
- ✅ Any network topology
- ✅ Mock components for learning
- ✅ Real components for production
- ✅ Easy AI integration

### **Production-Ready**
- ✅ Persistent networks (run forever)
- ✅ Concurrent execution
- ✅ Error handling built-in
- ✅ Real-world connectors (RSS, email, webhooks, APIs)

---

## Philosophy

**Simple First**  
Write ordinary Python. No special syntax or complex APIs.

**Real Applications**  
Build useful systems, not toy examples. Stay engaged by creating things that matter.

**Any Topology**  
Not just pipelines—build networks with any structure to match your problem.

**Progressive Learning**  
Start with a 3-node pipeline. End with complex multi-agent AI systems. One concept at a time.

**Safe Exploration**  
Mock components let you experiment without API costs or credentials.

---

## Common Use Cases

### **Monitoring & Alerts**
- Track social media mentions
- Monitor competitor activity  
- Watch for job opportunities
- Detect anomalies in data streams

### **Content Aggregation**
- Multi-source RSS readers
- News aggregators with AI summaries
- Research paper monitors
- Market intelligence gathering

### **Automation**
- Email auto-categorization
- Automated data pipelines
- Scheduled report generation
- Multi-step workflows

### **AI Workflows**
- Multi-agent analysis pipelines
- Sentiment tracking systems
- Content moderation
- Language translation chains

---

## Contributing

We welcome contributions! Areas of interest:

- **Connectors** - New data sources and sinks (APIs, databases, services)
- **Examples** - Real-world application networks
- **Documentation** - Tutorials, guides, use cases
- **Course Modules** - Teaching materials for educators

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Support

- **Issues & Bugs:** [GitHub Issues](https://github.com/kmchandy/DisSysLab/issues)
- **Discussions:** [GitHub Discussions](https://github.com/kmchandy/DisSysLab/discussions)
- **Documentation:** [Getting Started Guide](docs/getting-started.md)

---

## Citation

If you use DisSysLab in research or teaching:

```bibtex
@software{dissyslab2025,
  title = {DisSysLab: Build Persistent Systems with Simple Python},
  author = {Chandy, K. Mani},
  year = {2025},
  url = {https://github.com/kmchandy/DisSysLab}
}
```

---

**Ready to build?**

→ **Power Users:** [Quick Start Templates](examples/module_10_build_apps/QUICKSTART.md)  
→ **Students:** [Module 01: Basics](examples/module_01_basics/)  
→ **Everyone:** Run your first network: `python3 -m examples.module_01_basics.example`

**Build persistent systems with simple Python.** 🚀
