# BUILD_APP.md - How to Build Your Distributed App

**A systematic process for going from idea to working application.**

This guide walks you through building any distributed app with DisSysLab by answering 3 key questions, then implementing the answers step-by-step.

---

## The Big Picture

Every distributed app follows the same pattern:

```
SOURCES → TRANSFORMS → SINKS
(where     (what         (where
 from)      happens)      to)
```

**Your job:** Answer 3 questions, then build it.

---

## The 3 Essential Questions

### **Question 1: Where does data come FROM?**
*What are the data streams that are sources for the application?*

### **Question 2: Where does data go TO?**
*What data streams does the app produce and which sinks do they go to?*

### **Question 3: What happens in BETWEEN?**
*What are the transformations between sources and sinks? Can you break them into smaller pieces?*

**That's it!** Answer these three questions and you have your design.

---

## Step-by-Step Process

### Phase 1: Define Your App (10-15 minutes)

**Start with the problem, not the code.**

#### Write Your "App Statement"

Fill in this template:

```
My app [DOES WHAT] by reading from [SOURCES],
processing it with [TRANSFORMS], and sending results to [SINKS].
```

**Examples:**

✅ "My app **monitors customer feedback** by reading from **BlueSky and email**, 
   filtering for **negative sentiment**, and sending **alerts to Slack**."

✅ "My app **aggregates tech news** by reading from **RSS feeds**, 
   extracting **AI-related articles**, and **emailing me a daily digest**."

✅ "My app **tracks inventory** by reading from **CSV files**, 
   identifying **low stock items**, and **updating a dashboard and database**."

---

### Phase 2: Answer the 3 Questions (15-20 minutes)

**Now get specific. Use this worksheet:**

---

#### **Question 1: What are your SOURCES?**

*Where does data come FROM?*

List each data source:

| Source # | Type | What Data? | Format | How Often? |
|----------|------|------------|--------|------------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

**Example:**
| Source # | Type | What Data? | Format | How Often? |
|----------|------|------------|--------|------------|
| 1 | BlueSky Stream | Customer mentions | JSON posts | Real-time |
| 2 | Email (IMAP) | Support tickets | Email text | Every 5 min |

**Available source types:**
- Files (CSV, JSON, text)
- APIs (REST, webhooks)
- Streams (BlueSky Jetstream, WebSocket)
- Databases
- Email (IMAP)
- Custom (build your own!)

**For each source, decide:**
- [ ] Do I need demo version or real version?
- [ ] What credentials/setup do I need?
- [ ] How much data will I process? (all, last 100, last hour?)

---

#### **Question 2: What are your SINKS?**

*Where does data go TO?*

List each output:

| Sink # | Type | What Data? | Format | Purpose |
|--------|------|------------|--------|---------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

**Example:**
| Sink # | Type | What Data? | Format | Purpose |
|--------|------|------------|--------|---------|
| 1 | Slack Webhook | Negative feedback alerts | JSON | Notify team |
| 2 | JSON File | All processed posts | JSON | Archive |
| 3 | Dashboard | Live stats | Display | Monitor |

**Available sink types:**
- Files (JSON, CSV, text)
- APIs (POST, webhooks)
- Email (SMTP)
- Databases
- Display/Dashboard
- Custom (build your own!)

**For each sink, decide:**
- [ ] What format does it need?
- [ ] Should I write everything or just some items?
- [ ] Do I need batching or real-time?

---

#### **Question 3: What are your TRANSFORMS?**

*What happens BETWEEN sources and sinks?*

**Think step-by-step:** Start → ... → ... → End

List the transformations in order:

| Step # | Transform Name | Input | Output | Purpose |
|--------|----------------|-------|--------|---------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

**Example:**
| Step # | Transform Name | Input | Output | Purpose |
|--------|----------------|-------|--------|---------|
| 1 | Filter English | Raw posts | English posts | Remove non-English |
| 2 | Spam Filter | English posts | Non-spam posts | Remove spam |
| 3 | Sentiment Analysis | Non-spam posts | Posts + sentiment | Detect negative |
| 4 | Extract Negatives | Posts + sentiment | Negative posts only | Filter for alerts |

**Common transform types:**
- **Filter:** Keep only items matching criteria (return item or None)
- **Enrich:** Add new fields to items (return modified item)
- **Extract:** Pull out specific fields (return subset)
- **Aggregate:** Combine multiple items (return summary)
- **Route:** Send different items to different places (multiple transforms)
- **AI Analysis:** Use LLM to analyze (add AI results)

**Key principle: Break complex transforms into simple steps**

❌ **Don't do this:** One big function that does everything
```python
def process_everything(item):
    # 50 lines of code doing many things
    ...
```

✅ **Do this:** Chain of simple functions
```python
def filter_english(item): ...
def remove_spam(item): ...
def analyze_sentiment(item): ...
def extract_negative(item): ...
```

**Each transform should do ONE thing clearly.**

---

### Phase 3: Draw Your Network (5 minutes)

**Visualize the flow on paper or whiteboard.**

Use simple boxes and arrows:

```
┌─────────────┐
│ BlueSky     │──┐
│ Stream      │  │
└─────────────┘  │    ┌──────────┐    ┌──────────┐    ┌──────────┐
                 ├───→│  Filter  │───→│Sentiment │───→│ Extract  │──┐
┌─────────────┐  │    │ English  │    │ Analysis │    │ Negative │  │
│ Email       │──┘    └──────────┘    └──────────┘    └──────────┘  │
│ Support     │                                                       │
└─────────────┘                                                       ├──→ Slack
                                                                      │
                                                                      ├──→ File
                                                                      │
                                                                      └──→ Dashboard
```

**This diagram is your blueprint!**

Check:
- [ ] All sources connect to something
- [ ] All transforms connect in logical order
- [ ] All sinks receive from somewhere
- [ ] Flow makes sense left-to-right

---

### Network Patterns: Beyond Simple Pipelines

**DisSysLab supports ANY network topology - not just linear pipelines!**

Here are the most common patterns:

#### **Pattern 1: Linear Pipeline** (Simplest)

```
Source → Transform → Transform → Sink
```

```python
g = network([
    (source, transform1),
    (transform1, transform2),
    (transform2, sink)
])
```

**Use when:** Simple sequential processing

---

#### **Pattern 2: Fanout (Branching)** ⭐

One source/transform sends to MULTIPLE destinations.

```
              ┌──→ Sink 1 (urgent alerts)
              │
Source → Transform ──→ Sink 2 (file archive)
              │
              └──→ Sink 3 (dashboard)
```

```python
g = network([
    (source, transform),
    (transform, sink1),    # Same transform, 3 outputs!
    (transform, sink2),
    (transform, sink3)
])
```

**Use when:** 
- Multiple outputs for same data
- Different destinations based on content
- Parallel processing

**Real examples:**
- Alert system (Slack + Email + File)
- Multi-format export (JSON + CSV + Database)
- Monitoring (Dashboard + Log + Archive)

---

#### **Pattern 3: Fanin (Joining)** ⭐

MULTIPLE sources feed into one transform/sink.

```
Source 1 ──┐
           ├──→ Transform → Sink
Source 2 ──┘
```

```python
g = network([
    (source1, transform),   # Multiple sources, one transform!
    (source2, transform),
    (transform, sink)
])
```

**Use when:**
- Combining data from multiple sources
- Aggregating streams
- Merging datasets

**Real examples:**
- News aggregator (multiple RSS feeds → one digest)
- Multi-channel monitoring (Twitter + Reddit + News → analysis)
- Data warehouse (multiple databases → combined report)

---

#### **Pattern 4: Conditional Routing** ⭐⭐

Route items to different paths based on content.

```
              ┌─→ Filter High ──→ Urgent Sink
              │
Source ──────┤
              │
              └─→ Filter Low ──→ Normal Sink
```

```python
def filter_high_priority(item):
    if item.get('priority') == 'high':
        return item
    return None  # Filter out

def filter_low_priority(item):
    if item.get('priority') == 'low':
        return item
    return None

g = network([
    (source, high_filter),
    (source, low_filter),      # Source feeds BOTH filters
    (high_filter, urgent_sink),
    (low_filter, normal_sink)
])
```

**Use when:**
- Different processing for different item types
- Priority-based routing
- Category-based workflows

---

#### **Pattern 5: Diamond (Branch then Join)** ⭐⭐

Split, process differently, then combine.

```
              ┌─→ Transform A ──┐
              │                 │
Source ──────┤                 ├──→ Combine ──→ Sink
              │                 │
              └─→ Transform B ──┘
```

```python
g = network([
    (source, transformA),
    (source, transformB),
    (transformA, combine),
    (transformB, combine),
    (combine, sink)
])
```

**Use when:**
- Parallel processing then aggregation
- A/B testing
- Multi-model AI comparison

---

#### **Pattern 6: Multi-Stage Pipeline with Fanout** ⭐⭐⭐

Complex real-world pattern combining multiple patterns.

```
Source 1 ──┐
           ├──→ Filter ──→ AI Analysis ──┬──→ Dashboard
Source 2 ──┘                              │
                                          ├──→ Alert (if negative)
                                          │
                                          └──→ Archive (all)
```

```python
g = network([
    # Fanin: Multiple sources
    (source1, filter_node),
    (source2, filter_node),
    
    # Processing
    (filter_node, ai_node),
    
    # Fanout: Multiple sinks
    (ai_node, dashboard),
    (ai_node, alert),
    (ai_node, archive)
])
```

**This is Example 2 from Module 09!**

---

#### **Pattern 7: Feedback Loop** ⭐⭐⭐⭐ (Advanced)

Output feeds back as input (requires careful design to avoid infinite loops).

```
Source ──→ Process ──→ Sink
            ↑    │
            └────┘ (filtered feedback)
```

**Use when:**
- Iterative refinement
- Batch processing with retries
- State machines

**⚠️ Advanced:** Requires careful termination logic!

---

### Choosing Your Network Pattern

**Ask yourself:**

1. **One source or many?**
   - One → Linear or Fanout
   - Many → Fanin or Diamond

2. **One output or many?**
   - One → Linear or Fanin
   - Many → Fanout

3. **Different processing paths?**
   - Yes → Conditional Routing or Diamond
   - No → Linear

4. **Combine results later?**
   - Yes → Diamond
   - No → Fanout

**Examples:**

| Your App | Pattern | Why |
|----------|---------|-----|
| Read file → Process → Save file | Linear | Simple pipeline |
| Monitor Twitter → Alert Slack + Email | Fanout | One input, multiple outputs |
| Aggregate 3 RSS feeds → Digest | Fanin | Multiple inputs, one output |
| Incoming requests → Route by type → Different handlers | Conditional | Different paths by content |
| Source → Process A + B → Compare | Diamond | Parallel processing then combine |

---

### Building Complex Networks

**The process is the same - just more edges!**

1. **Answer the 3 questions** (still works!)
   - List ALL sources
   - List ALL sinks
   - List ALL transforms

2. **Draw the diagram** (critical for complex networks!)
   - Use boxes and arrows
   - Show all connections
   - Label each edge

3. **Build layer by layer** (same strategy!)
   - Start with one source → one transform
   - Add one connection at a time
   - Test after each addition

**Example: Building a complex network incrementally**

```python
# Layer 1: Just one source
g = network([
    (source1, transform)
])
g.run_network()

# Layer 2: Add second source
g = network([
    (source1, transform),
    (source2, transform)  # Added fanin
])
g.run_network()

# Layer 3: Add fanout
g = network([
    (source1, transform),
    (source2, transform),
    (transform, sink1),   # Added first output
    (transform, sink2)    # Added second output
])
g.run_network()

# Keep adding one edge at a time, testing each step!
```

---

### Phase 4: Build Incrementally (30-60 minutes)

**Never build the whole thing at once!**

Build in layers, testing each layer before adding the next.

#### **Layer 1: Source Only**

Build and test JUST the source.

```python
# Test source alone
source = MySource()

count = 0
while True:
    item = source.run()
    if item is None:
        break
    print(f"{count + 1}. {item}")
    count += 1

print(f"\n✓ Source works! Got {count} items")
```

**Verify:**
- [ ] Source returns items
- [ ] Items have expected format
- [ ] Source returns None at end
- [ ] No errors

**Don't move on until this works!**

---

#### **Layer 2: Source → First Transform**

Add ONE transform.

```python
from dsl import network
from dsl.blocks import Source, Transform

# Source (already tested)
source = MySource()
source_node = Source(fn=source.run, name="source")

# First transform
def my_transform(item):
    # Your processing here
    print(f"Processing: {item}")
    return item

transform_node = Transform(fn=my_transform, name="transform")

# Simple network: Source → Transform
g = network([(source_node, transform_node)])
g.run_network()
```

**Verify:**
- [ ] Transform receives items
- [ ] Transform returns correct output
- [ ] No errors

---

#### **Layer 3: Source → Transforms → Sink**

Add remaining transforms and sink.

```python
from dsl.blocks import Sink

# Add more transforms
transform1_node = Transform(fn=transform1, name="step1")
transform2_node = Transform(fn=transform2, name="step2")

# Add sink
sink = MySink()
sink_node = Sink(fn=sink.run, name="sink")

# Complete network
g = network([
    (source_node, transform1_node),
    (transform1_node, transform2_node),
    (transform2_node, sink_node)
])

g.run_network()
sink.finalize()

print(f"✓ Complete! Processed {len(sink.results)} items")
```

**Verify:**
- [ ] All transforms work in sequence
- [ ] Sink receives correct items
- [ ] finalize() is called
- [ ] Results are correct

---

#### **Layer 4: Multiple Outputs (if needed)**

Add fanout if you have multiple sinks.

```python
# Add more sinks
sink1 = FileSink()
sink2 = WebhookSink()
sink3 = DashboardSink()

sink1_node = Sink(fn=sink1.run, name="file")
sink2_node = Sink(fn=sink2.run, name="webhook")
sink3_node = Sink(fn=sink3.run, name="dashboard")

# Network with fanout
g = network([
    (source_node, transform_node),
    (transform_node, sink1_node),
    (transform_node, sink2_node),
    (transform_node, sink3_node)
])

g.run_network()

# Finalize ALL sinks
sink1.finalize()
sink2.finalize()
sink3.finalize()
```

---

### Phase 5: Test & Refine (15-30 minutes)

**Now that it works, make it better.**

#### **Test with Different Data**

- [ ] Small dataset (10 items)
- [ ] Medium dataset (100 items)
- [ ] Large dataset (1000+ items)
- [ ] Edge cases (empty, malformed, duplicates)

#### **Check Performance**

```python
import time

start = time.time()
g.run_network()
elapsed = time.time() - start

print(f"Processed {count} items in {elapsed:.2f}s")
print(f"Rate: {count/elapsed:.1f} items/second")
```

#### **Add Error Handling**

```python
def safe_transform(item):
    try:
        # Your processing
        return process(item)
    except Exception as e:
        print(f"Error processing {item}: {e}")
        return None  # Filter out bad items
```

#### **Add Logging**

```python
def transform_with_logging(item):
    print(f"[Transform] Processing item {item.get('id')}")
    result = process(item)
    print(f"[Transform] Result: {result}")
    return result
```

---

## Complete Example: Building a News Aggregator

Let's walk through the complete process.

### **Step 1: App Statement**

```
My app aggregates tech news by reading from RSS feeds,
filtering for AI-related articles, and emailing me a daily digest.
```

---

### **Step 2: Answer the 3 Questions**

#### **Question 1: Sources**

| Source # | Type | What Data? | Format | How Often? |
|----------|------|------------|--------|------------|
| 1 | RSS Feed | TechCrunch articles | XML/JSON | Daily |
| 2 | RSS Feed | Hacker News | XML/JSON | Daily |

#### **Question 2: Sinks**

| Sink # | Type | What Data? | Format | Purpose |
|--------|------|------------|--------|---------|
| 1 | Email (SMTP) | Digest of AI articles | HTML email | Daily summary |
| 2 | JSON File | All articles | JSON | Archive |

#### **Question 3: Transforms**

| Step # | Transform Name | Input | Output | Purpose |
|--------|----------------|-------|--------|---------|
| 1 | Filter AI Keywords | Raw articles | AI articles | Keep only AI-related |
| 2 | Extract Summary | AI articles | Title + summary | Pull key fields |
| 3 | Format HTML | Summaries | HTML digest | Prepare for email |

---

### **Step 3: Draw Network**

**This shows BOTH fanin (multiple sources) and fanout (multiple sinks)!**

```
┌─────────────┐
│ TechCrunch  │──┐
│ RSS         │  │    ┌──────────┐    ┌──────────┐    ┌──────────┐
└─────────────┘  ├───→│  Filter  │───→│ Extract  │───→│  Format  │──┬──→ Email
                 │    │    AI    │    │ Summary  │    │   HTML   │  │
┌─────────────┐  │    └──────────┘    └──────────┘    └──────────┘  └──→ JSON File
│ Hacker News │──┘
│ RSS         │
└─────────────┘

FANIN: 2 sources → 1 filter
FANOUT: 1 formatter → 2 sinks
```

**This is a real-world pattern: aggregate from multiple sources, output to multiple destinations!**

---

### **Step 4: Build Layer by Layer**

#### **Layer 1: Test Source**

```python
from components.sources.rss_source import RSSSource

# Test RSS source
rss = RSSSource(url="https://techcrunch.com/feed/")

count = 0
while True:
    article = rss.run()
    if article is None:
        break
    print(f"{count + 1}. {article['title']}")
    count += 1

print(f"✓ Got {count} articles from TechCrunch")
```

#### **Layer 2: Add Filter**

```python
from dsl import network
from dsl.blocks import Source, Transform

source = RSSSource(url="https://techcrunch.com/feed/")
source_node = Source(fn=source.run, name="rss")

def filter_ai(article):
    """Keep only AI-related articles."""
    text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
    
    keywords = ['ai', 'artificial intelligence', 'machine learning', 
                'llm', 'chatgpt', 'openai', 'claude']
    
    for keyword in keywords:
        if keyword in text:
            return article
    
    return None  # Filter out

filter_node = Transform(fn=filter_ai, name="filter_ai")

g = network([(source_node, filter_node)])
g.run_network()

print("✓ Filter works!")
```

#### **Layer 3: Complete Pipeline with Fanin & Fanout**

**Now add the second source (fanin) and second sink (fanout):**

```python
from dsl.blocks import Sink
from components.sinks.email_sender import EmailSender
from components.sinks.file_writer import FileWriter

# TWO SOURCES (fanin)
source1 = RSSSource(url="https://techcrunch.com/feed/")
source2 = RSSSource(url="https://news.ycombinator.com/rss")

source1_node = Source(fn=source1.run, name="techcrunch")
source2_node = Source(fn=source2.run, name="hackernews")

# All transforms
def filter_ai(article): ...  # From above

def extract_summary(article):
    """Pull out key fields."""
    return {
        'title': article.get('title'),
        'summary': article.get('summary', '')[:200],
        'link': article.get('link')
    }

# Build HTML digest
html_parts = []

def format_html(article):
    """Add to HTML digest."""
    html = f"""
    <div style="margin-bottom: 20px;">
        <h3><a href="{article['link']}">{article['title']}</a></h3>
        <p>{article['summary']}</p>
    </div>
    """
    html_parts.append(html)
    return article  # Pass through for file sink too!

# TWO SINKS (fanout)
email = EmailSender(
    to_email="your.email@gmail.com",
    subject="AI News Digest"
)

file_sink = FileWriter(filepath="ai_articles.json", format="json")

# Transform nodes
filter_node = Transform(fn=filter_ai, name="filter")
extract_node = Transform(fn=extract_summary, name="extract")
format_node = Transform(fn=format_html, name="format")

# Sink nodes
email_node = Sink(fn=email.run, name="email")
file_node = Sink(fn=file_sink.run, name="file")

# COMPLEX NETWORK: 2 sources → processing → 2 sinks
g = network([
    # FANIN: Both sources feed the filter
    (source1_node, filter_node),
    (source2_node, filter_node),
    
    # Processing pipeline
    (filter_node, extract_node),
    (extract_node, format_node),
    
    # FANOUT: One formatter feeds both sinks
    (format_node, email_node),
    (format_node, file_node)
])

print("Running network with:")
print("  - 2 sources (TechCrunch + Hacker News)")
print("  - 3 transforms (filter + extract + format)")
print("  - 2 sinks (email + file)")
print()

g.run_network()

# Send digest email
digest_html = '<html><body>' + ''.join(html_parts) + '</body></html>'
email.run({'body': digest_html})

# Finalize BOTH sinks
email.finalize()
file_sink.finalize()

print("✓ Email sent!")
print("✓ Articles saved to ai_articles.json")
```

**See how fanin and fanout work?**
- **Fanin:** Both RSS sources feed into the same filter
- **Fanout:** The formatter sends results to both email AND file

**This is the power of networks - not just pipelines!**

---

## Debugging Checklist

**When things don't work:**

### **Source Issues**

- [ ] Does `run()` return items?
- [ ] Does `run()` return `None` at end?
- [ ] Are items in the right format (dict)?
- [ ] Check credentials/file paths

### **Transform Issues**

- [ ] Does transform receive items?
- [ ] Does transform return something (item or None)?
- [ ] Test transform alone with sample data
- [ ] Add print statements to see what's happening

### **Sink Issues**

- [ ] Does `run(item)` receive items?
- [ ] Is `finalize()` being called?
- [ ] Check file paths/credentials
- [ ] Test sink alone before network

### **Network Issues**

- [ ] Are edges in the right order?
- [ ] Did you wrap components correctly?
  - Source: `Source(fn=source.run, ...)`
  - Transform: `Transform(fn=func, ...)`
  - Sink: `Sink(fn=sink.run, ...)`
- [ ] Are all variables defined?
- [ ] Run each layer separately

---

## Common Patterns & Tips

### **Pattern: Filter Early**

Put filters near the source to reduce processing.

✅ **Good:** Source → Filter → Heavy Processing → Sink
❌ **Bad:** Source → Heavy Processing → Filter → Sink

### **Pattern: One Transform = One Job**

Break complex logic into simple steps.

✅ **Good:** 
```python
filter → extract → enrich → format
```

❌ **Bad:**
```python
do_everything()  # 100 lines
```

### **Pattern: Test Small First**

Start with 10 items, then scale up.

```python
# Limit for testing
source = MySource(max_items=10)  

# When it works, remove limit
source = MySource()
```

### **Pattern: Add Logging**

See what's happening at each step.

```python
def logged_transform(item):
    print(f"→ {item}")
    result = process(item)
    print(f"← {result}")
    return result
```

---

## Quick Reference: The Build Process

```
1. Write App Statement
   ↓
2. Answer 3 Questions
   - Sources?
   - Sinks?
   - Transforms?
   ↓
3. Draw Network Diagram
   ↓
4. Build Layer by Layer
   - Source only
   - Source → Transform
   - Source → Transforms → Sink
   - Add multiple outputs
   ↓
5. Test & Refine
   - Different data sizes
   - Edge cases
   - Error handling
   ↓
6. Done! ✓
```

---

## What's Next?

**You now have a systematic process for building any distributed app!**

Next steps:
- **Try it:** Build the news aggregator above
- **Guided builds:** See detailed walkthroughs in guided_build_*.md files
- **Debug:** See DEBUGGING.md for troubleshooting
- **Templates:** See QUICKSTART.md for code templates

**Remember: Every app is just Sources → Transforms → Sinks!**

Answer the 3 questions, build layer by layer, and you'll succeed. 🚀
