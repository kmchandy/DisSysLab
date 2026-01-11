# DisSysLab Teaching Plan v2.0

## Core Vision

**Goal:** Teach distributed systems by building concurrent agent networks

**Philosophy:**
- Students build apps they care about
- AI generates functions, students build networks  
- Learn theory when they hit real problems
- Focus on network observability and message flow

---

## Teaching Approach: Component Library Pattern

### Key Innovation: Module 2 as "Catalog"

**Module 2** shows a complete, realistic network that students will build toward.
- Students see the endpoint first (motivation!)
- Provides "component library" for later modules
- Each subsequent module picks components from Module 2
- Homework naturally leads to next concept

---

## Module Sequence

### **Module 1: Introduction** (15 minutes)
**Status:** Needs README.md

**Content:**
- What is DisSysLab?
- What are distributed systems?
- Concurrent agents and message passing
- Persistent vs sequential systems
- Overview of module sequence
- Installation instructions

**Student Activity:**
- Read overview
- Install DisSysLab
- Verify installation

**Deliverable:** Understanding of course structure

---

### **Module 2: The Big Picture** (30 minutes, READ ONLY)
**Status:** Needs creation - THIS IS THE LINCHPIN

**Format:** Descriptive walkthrough - students READ but cannot RUN (no API keys yet)

**Content:**
Complete, realistic network showing:
- **Real sources:** Twitter, Reddit, RSS feeds
- **Interesting transforms:** Sentiment analysis, urgency detection, spam filtering, text cleaning
- **Real sinks:** Database writer, file logger, dashboard, email alerts
- **Complex topology:** Fanin, fanout, routing
- **Persistent execution:** Runs forever processing streams

**Example Network:**
```python
# THIS IS SHOWN, NOT RUN (students don't have keys)

# Real sources
twitter = TwitterSource(api_key=TWITTER_KEY)
reddit = RedditSource(credentials=REDDIT_CREDS)
rss = RSSFeedSource(urls=NEWS_FEEDS)

# Transforms
clean = Transform(fn=text_cleaner.run)
spam = Transform(fn=spam_detector.run)
sentiment = Transform(fn=claude_sentiment.run)  # Uses Claude API
urgency = Transform(fn=urgency_analyzer.run)

# Sinks
db = DatabaseWriter(connection=DB_CONN)
dashboard = RealTimeDashboard(port=8080)
alert = EmailAlerter(smtp_config=SMTP)
file_log = FileWriter(path="logs/")

# Complex network with fanin, fanout, routing
g = network([
    (twitter, clean),
    (reddit, clean),          # Fanin at clean
    (rss, clean),
    (clean, spam),            # Fanout from clean
    (clean, sentiment),
    (clean, urgency),
    (spam, file_log),
    (sentiment, db),
    (sentiment, dashboard),   # Fanout from sentiment
    (urgency, alert),
    (urgency, dashboard)      # Fanin at dashboard
])

# This runs FOREVER, processing streams in real-time
g.run_network()
```

**Key Teaching Points:**
1. **Persistent vs Sequential:** This doesn't process a file and exit - it runs continuously
2. **Concurrent Execution:** Each agent runs in its own thread
3. **Message Flow:** Data flows as dicts between agents
4. **Real Applications:** This is what you'll build!

**Component Catalog Introduced:**
Students see all components they'll use in later modules:

**Sources:**
- `TwitterSource` (real) / `MockTwitterSource` (for exercises)
- `RedditSource` (real) / `MockRedditSource` (for exercises)  
- `RSSFeedSource`
- `ListSource` (simple, for learning)

**Transforms:**
- `TextCleaner` - Remove emojis, clean whitespace
- `SpamFilter` - Detect and filter spam (returns None)
- `SentimentAnalyzer` - Analyze sentiment (Claude API or simple)
- `UrgencyAnalyzer` - Detect urgent messages

**Sinks:**
- `ConsoleLogger` - Print to console
- `FileWriter` - Write to file
- `DatabaseWriter` - Save to database (real)
- `Dashboard` - Real-time web display (real)
- `EmailAlerter` - Send email alerts (real)

**Student Activity:**
- Read guided tour of network
- Identify components (sources, transforms, sinks)
- Understand network topology
- See visualization of network
- **Cannot run it** (needs API keys)
- Understand persistent vs sequential
- Get excited about what they'll build!

**Deliverable:** 
- Understanding of complete system
- Component catalog for later modules
- Motivation to learn!

**Critical Implementation Notes:**
- Provide BOTH real and mock versions of each component
- Mock versions work without API keys (for Modules 3-8)
- Real versions shown in Module 2, used in Module 9
- Excellent README with guided tour
- Topology diagram/visualization

---

### **Module 3: Your First Pipeline** (30 minutes)
**Status:** Needs creation

**Format:** Hands-on, executable

**Content:**
Build simple pipeline using components from Module 2

**Example:**
```python
# Components from Module 2 catalog
from module2.components.sources import ListSource
from module2.components.transforms import TextCleaner
from module2.components.sinks import ConsoleLogger

# Sample data
sample_posts = [
    {"text": "I love this product! 😊"},
    {"text": "Terrible service 😠"},
    {"text": "It's okay I guess"}
]

# Create agents
list_source = ListSource(sample_posts)
text_cleaner = TextCleaner()
console_logger = ConsoleLogger()

# Build network
g = network([
    (Source(fn=list_source.run), 
     Transform(fn=text_cleaner.run)),
    (Transform(fn=text_cleaner.run),
     Sink(fn=console_logger.run))
])

# Visualize
visualize(g)

# Run!
g.run_network()
```

**Key Teaching:**
- Source → Transform → Sink pattern
- Message passing (dicts)
- Concurrent execution
- Using visualize()

**Homework:**
"Add `SpamFilter` from Module 2 between `text_cleaner` and `console_logger`"

**Deliverable:** Working pipeline + homework solution

**Leads to:** Module 4 (Filtering)

---

### **Module 4: Filtering with None** (20 minutes)
**Status:** Needs creation (current drop_None/ can be adapted)

**Format:** Hands-on

**Content:**
- Explain homework solution from Module 3
- How None messages are dropped
- Filter pattern
- Observing filtered messages

**Example:**
```python
# Solution to Module 3 homework
from module2.components.transforms import SpamFilter

spam_filter = SpamFilter()

g = network([
    (source, text_cleaner),
    (text_cleaner, Transform(fn=spam_filter.run)),  # Returns None for spam
    (spam_filter, console_logger)  # Only non-spam reaches here
])

visualize(g)  # See the pipeline
g.run_network()  # See spam being filtered
```

**Key Teaching:**
- Returning None drops messages
- Automatic filtering (no special logic needed)
- Downstream doesn't know about dropped messages

**Homework:**
"Add `MockTwitterSource` and `MockRedditSource` from Module 2. Both should feed into `text_cleaner`"

**Deliverable:** Understanding of filtering

**Leads to:** Module 5 (Fanin)

---

### **Module 5: Fanin (Multiple Sources)** (30 minutes)
**Status:** Needs creation

**Format:** Hands-on

**Content:**
- Explain homework solution from Module 4
- Multiple sources → one processor
- Automatic Merge insertion
- Message interleaving from concurrent streams

**Example:**
```python
# Solution to Module 4 homework
from module2.components.sources import MockTwitterSource, MockRedditSource

twitter = MockTwitterSource()
reddit = MockRedditSource()

g = network([
    (Source(fn=twitter.run), text_cleaner),
    (Source(fn=reddit.run), text_cleaner),  # Fanin!
    (text_cleaner, spam_filter),
    (spam_filter, console_logger)
])

visualize(g)  # See automatic Merge agent inserted!
g.run_network()
```

**Key Teaching:**
- Fanin pattern
- Automatic Merge insertion
- Messages from multiple sources interleave
- See Merge in visualization

**Homework:**
"Add `FileWriter` sink from Module 2. Both `spam_filter` and existing sink should receive output"

**Deliverable:** Understanding of fanin

**Leads to:** Module 6 (Fanout)

---

### **Module 6: Fanout (Multiple Destinations)** (30 minutes)
**Status:** Needs creation

**Format:** Hands-on

**Content:**
- Explain homework solution from Module 5
- One source → multiple processors
- Automatic Broadcast insertion
- Message copying

**Example:**
```python
# Solution to Module 5 homework
from module2.components.sinks import FileWriter

file_writer = FileWriter(path="output.log")

g = network([
    (twitter_source, text_cleaner),
    (reddit_source, text_cleaner),
    (text_cleaner, spam_filter),
    (spam_filter, console_logger),
    (spam_filter, Sink(fn=file_writer.run))  # Fanout!
])

visualize(g)  # See automatic Broadcast agent inserted!
g.run_network()
```

**Key Teaching:**
- Fanout pattern
- Automatic Broadcast insertion
- Same message copied to multiple destinations
- See Broadcast in visualization

**Homework:**
"Add `SentimentAnalyzer` from Module 2 in parallel with `spam_filter`"

**Deliverable:** Understanding of fanout

**Leads to:** Module 7 (Stateful Transforms)

---

### **Module 7: Stateful Transforms** (30 minutes)
**Status:** Needs creation

**Format:** Hands-on

**Content:**
- Transforms that maintain state
- When to use state (counters, moving averages, caches)
- Pattern: accumulate → process → output

**Example:**
```python
# Stateful sentiment analyzer that counts
class StatefulSentiment:
    def __init__(self):
        self.positive_count = 0
        self.negative_count = 0
    
    def run(self, msg):
        sentiment = analyze_sentiment(msg['text'])
        if sentiment == "POSITIVE":
            self.positive_count += 1
        else:
            self.negative_count += 1
        
        return {
            "text": msg['text'],
            "sentiment": sentiment,
            "total_positive": self.positive_count,
            "total_negative": self.negative_count
        }

analyzer = StatefulSentiment()
g = network([
    (source, Transform(fn=analyzer.run)),
    (transform, logger)
])
```

**Key Teaching:**
- State persists between messages
- Each agent instance maintains its own state
- Use for: counters, caches, aggregations, moving averages

**Homework:**
"Add urgency analyzer that maintains urgency counts"

**Deliverable:** Understanding of stateful vs stateless

**Leads to:** Module 8 (Content Routing)

---

### **Module 8: Content Routing (Split)** (45 minutes)
**Status:** Needs creation (current split/ can be adapted)

**Format:** Hands-on

**Content:**
- Split agent with router function
- Explicit port references (split.out_0)
- Different handlers for different message types
- Pattern: classify → route → handle

**Example:**
```python
from dsl.blocks.split import Split

# Router function
def classify_message(msg):
    if msg.get('spam'):
        return [msg, None, None]     # Route to spam handler
    elif msg.get('urgent'):
        return [None, msg, None]     # Route to urgent handler
    else:
        return [None, None, msg]     # Route to normal handler

# Create Split agent
splitter = Split(router=classify_message, num_outputs=3)

# Network with explicit ports
g = network([
    (source, splitter),
    (splitter.out_0, spam_handler),    # Explicit port!
    (splitter.out_1, urgent_handler),
    (splitter.out_2, normal_handler)
])

visualize(g)
```

**Key Teaching:**
- Content-based routing
- Router function pattern
- Explicit port references
- Different processing paths

**Homework:**
"Build complete network combining fanin, fanout, filtering, and routing"

**Deliverable:** Understanding of routing

**Leads to:** Module 9 (The Real Thing)

---

### **Module 9: Build the Real Thing** (2 hours)
**Status:** Needs creation - THE CULMINATION

**Format:** Hands-on (with API keys)

**Content:**
- Get API keys (Anthropic, optionally Twitter/Reddit)
- Swap mock components → real components
- Run the Module 2 network for real!
- Observe persistent execution
- **Achievement unlocked:** Built a real distributed system!

**Two Paths:**

**Path A: Full Real APIs** (for students with all API access)
```python
# Use real Twitter, Reddit, Claude AI
twitter = TwitterSource(api_key=TWITTER_KEY)
reddit = RedditSource(credentials=REDDIT_CREDS)
sentiment = Transform(fn=claude_sentiment.run)

# Same network structure as Module 2!
g = network([...])
g.run_network()  # Runs forever!
```

**Path B: Partial Real APIs** (for students with limited access)
```python
# Use RSS (no API) + Claude AI (free tier)
rss = RSSFeedSource(urls=NEWS_FEEDS)
mock_reddit = MockRedditSource()
sentiment = Transform(fn=claude_sentiment.run)

# Same network structure!
g = network([...])
g.run_network()
```

**Key Teaching:**
- Mock → real is just swapping components
- Network structure stays identical
- Persistent vs sequential (see it run forever!)
- Real-time distributed processing
- This is what you came here to learn!

**Deliverable:** Working real-world distributed system

**Leads to:** Module 10 (Build Your Own)

---

### **Module 10: Build Your Own** (Open-ended)
**Status:** Needs creation

**Format:** Project-based

**Content:**
- Design your own network
- Use AI to generate custom components
- Combine all learned patterns
- Build something you care about!

**Project Ideas:**
- Personal news aggregator
- Multi-source price monitor
- Social media sentiment dashboard
- Game statistics analyzer
- Email/notification router
- Research paper monitor
- Stock/crypto alert system

**Guidance:**
- Start with network topology design
- Ask AI to generate components you need
- Test with mock data first
- Deploy with real APIs
- Share your project!

**Key Teaching:**
- You now know distributed systems!
- You can build real applications
- AI helps with implementation
- Network patterns are what you learned

**Deliverable:** Student's own distributed application

---

## Two-Path Approach Throughout

### **Path A: AI-Powered (Recommended)**
- Module 9+: Use Claude AI for sentiment/classification
- Generate components with AI assistance
- Real-world applications
- More motivating

### **Path B: Simple Helpers (Alternative)**
- Use helpers/sentiment.py, helpers/spam.py
- Simple keyword-based implementations
- Works without API keys
- Can upgrade to Path A later

**Both paths teach the same distributed systems concepts!**

---

## Directory Structure

```
examples/
├── module1_intro/
│   └── README.md
│
├── module2_big_picture/              # THE LINCHPIN
│   ├── README.md                      # Guided tour
│   ├── complete_network.py            # Full example (can't run without keys)
│   ├── topology_diagram.png           # Visualization
│   └── components/                    # Component catalog
│       ├── sources/
│       │   ├── twitter_source.py      # Real
│       │   ├── mock_twitter.py        # Mock (for exercises)
│       │   ├── reddit_source.py       # Real
│       │   ├── mock_reddit.py         # Mock
│       │   ├── rss_source.py
│       │   └── list_source.py
│       ├── transforms/
│       │   ├── text_cleaner.py
│       │   ├── spam_filter.py
│       │   ├── sentiment_simple.py    # Keyword-based
│       │   ├── sentiment_claude.py    # AI-powered
│       │   └── urgency_analyzer.py
│       └── sinks/
│           ├── console_logger.py
│           ├── file_writer.py
│           ├── database_writer.py     # Real
│           ├── dashboard.py           # Real
│           └── email_alerter.py       # Real
│
├── module3_first_pipeline/
│   ├── README.md
│   ├── example.py
│   └── homework.md
│
├── module4_filtering/
│   ├── README.md
│   ├── solution.py
│   └── homework.md
│
├── module5_fanin/
│   ├── README.md
│   ├── solution.py
│   └── homework.md
│
├── module6_fanout/
│   ├── README.md
│   ├── solution.py
│   └── homework.md
│
├── module7_stateful/
│   ├── README.md
│   ├── solution.py
│   └── homework.md
│
├── module8_routing/
│   ├── README.md
│   ├── solution.py
│   └── homework.md
│
├── module9_real_thing/
│   ├── README.md
│   ├── setup_apis.md
│   ├── path_a_full_real.py
│   └── path_b_partial_real.py
│
└── module10_build_your_own/
    ├── README.md
    ├── project_ideas.md
    └── templates/
```

---

## Success Criteria

### **After Module 2:**
✅ Students understand what they're building toward
✅ Students are excited/motivated
✅ Students know all components they'll use

### **After Module 6:**
✅ Students can build networks with fanin/fanout
✅ Students understand message filtering
✅ Students can visualize networks

### **After Module 9:**
✅ Students have built a real distributed system
✅ Students understand persistent vs sequential
✅ Students can swap mock → real components

### **After Module 10:**
✅ Students can design their own networks
✅ Students can use AI to generate components
✅ Students have built something they care about
✅ Students are ready for distributed systems theory

---

## What Makes This Approach Work

1. **Motivation First:** Module 2 shows the endpoint before teaching details
2. **Component Reuse:** Same components throughout (from Module 2 catalog)
3. **Incremental Complexity:** Each module adds ONE concept
4. **Natural Progression:** Homework drives next module
5. **Concrete Examples:** Real components, not abstract
6. **Clear Culmination:** Module 9 = run Module 2 network!
7. **Observable Networks:** visualize() in every module
8. **Two Paths:** AI or helpers - both teach same concepts

---

## Next Steps for Implementation

### **Priority 1: Create Module 2** (The Linchpin)
- Write excellent README (guided tour)
- Create component catalog with mock versions
- Design network topology
- Create visualization
- This is the foundation!

### **Priority 2: Create Modules 3-6** (Core Learning)
- Each builds on Module 2 components
- Each has clear homework
- Each teaches one concept

### **Priority 3: Create Modules 7-8** (Advanced Patterns)
- Stateful transforms
- Content routing

### **Priority 4: Create Module 9** (Culmination)
- API setup guide
- Two paths (full/partial real)
- Run Module 2 network!

### **Priority 5: Create Module 10** (Student Projects)
- Project ideas
- Templates
- Guidance

---

## Timeline Estimate

- **Module 2:** 1 week (critical - get it right!)
- **Modules 3-6:** 1 week (building on Module 2)
- **Modules 7-8:** 3 days
- **Module 9:** 3 days (API setup guides)
- **Module 10:** 2 days (templates/ideas)

**Total: ~3 weeks to complete all modules**

---

## Alignment with Original Roadmap

This teaching plan is **Sprint 2** from the original roadmap:
- Focus on student learning
- Create diverse examples
- Tutorial structure

After this, proceed with:
- **Sprint 1:** Core documentation (graph.py, core.py)
- **Sprint 3:** Patterns and troubleshooting
- **Sprint 4:** Polish and package