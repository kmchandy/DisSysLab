# DisSysLab Teaching Module Plan

## Overview

This document outlines the complete module progression for teaching distributed systems to first-year undergraduate CS students using the DisSysLab framework.

**Core Philosophy:**
- Start with **ordinary Python functions** (no concurrency primitives)
- Progress to **distributed networks** using simple decorator patterns
- Integrate **AI agents** for real-world relevance
- Build toward **production-ready systems** with identical interfaces

**Success Metric:** Students progress from simple mock components to production-ready systems using identical interfaces and network topologies.

---

## Module Sequence

### **Module 1: Building Your First Network**
**Status:** ✅ Implemented  
**Location:** `modules/ch01_networks/`

#### Learning Objectives
- Understand the concept of dataflow networks
- Build simple linear pipelines: Source → Transform → Sink
- Use `@msg_map` decorator to wrap ordinary Python functions
- Understand message passing with dictionaries

#### Key Concepts
- Sources yield data (generators)
- Transforms process messages (pure functions)
- Sinks consume results (side effects)
- Messages are dictionaries
- `None` return values filter/drop messages

#### Examples
- `sentiment_network.py` - Social media sentiment analysis
- `simple_filter.py` - Message filtering by returning None

#### Deliverable
Students build a 3-4 node linear pipeline processing text data.

---

### **Module 2: Component Library & Patterns**
**Status:** ✅ Implemented  
**Location:** `modules/ch02_components/`

#### Learning Objectives
- Understand fanout (broadcast) and fanin (merge) patterns
- Use pre-built components from the library
- Distinguish between mock and production components
- Build more complex network topologies

#### Key Concepts
- **Fanout:** One source feeds multiple transforms
- **Fanin:** Multiple sources merge into one transform
- Component reusability
- Mock components for learning vs. production components

#### Component Categories
1. **Sources:** `SourceOfSocialMediaPosts`, generators, file readers
2. **Transforms:** `clean_text`, `analyze_sentiment`, `analyze_urgency`
3. **Sinks:** `ConsoleRecorder`, `JSONLRecorder`

#### Examples
- `network_example.py` - Multi-source, multi-sink network
- `fanout_fanin_example.py` - Complex routing patterns

#### Deliverable
Students build a network with 3+ sources, 2+ transforms, 2+ sinks.

---

### **Module 3: Sources - Data Generation Patterns**
**Status:** 🔨 Planned

#### Learning Objectives
- Understand different source patterns
- Build custom sources from scratch
- Handle finite vs. infinite data streams
- Implement rate limiting and backpressure

#### Key Concepts
- **Generator pattern:** `yield {"key": value}`
- **Iterator pattern:** Classes with `__iter__` and `__next__`
- **Finite sources:** Lists, files, API queries
- **Infinite sources:** Streams, sensors, live feeds
- When to return `None` (exhaustion signal)

#### Topics Covered
1. **Simple generators** - Lists, ranges, static data
2. **File-based sources** - CSV, JSON, JSONL readers
3. **Stateful sources** - Classes that maintain position/state
4. **Rate-limited sources** - Throttling, delays, batching
5. **Error handling** - Retry logic, graceful degradation

#### Examples
```python
# Simple generator
def from_list(items):
    for item in items:
        yield {"value": item}

# Stateful file reader
class CSVSource:
    def __init__(self, filepath):
        self.filepath = filepath
        self.file = None
        
    def run(self):
        with open(self.filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row

# Rate-limited source
def throttled_source(items, delay=1.0):
    for item in items:
        yield {"value": item}
        time.sleep(delay)
```

#### Deliverable
Students build 3 different source types: static data, file-based, and rate-limited.

---

### **Module 4: Transforms - Data Processing Patterns**
**Status:** 🔨 Planned

#### Learning Objectives
- Build stateless and stateful transforms
- Implement filtering, mapping, and enrichment patterns
- Handle errors in transform functions
- Understand when to use classes vs. functions

#### Key Concepts
- **Stateless transforms:** Pure functions with no memory
- **Stateful transforms:** Classes that maintain counters, caches, history
- **Filter pattern:** Return `None` to drop messages
- **Enrichment pattern:** Add fields to messages
- **Multi-output transforms:** Return tuples for multiple output keys

#### Topics Covered
1. **Simple mappings** - Field transformations
2. **Filters** - Conditional message dropping
3. **Enrichment** - Adding computed or lookup fields
4. **Stateful transforms** - Counters, running averages, deduplication
5. **Error handling** - Try/catch, logging, fallback values

#### Examples
```python
# Stateless filter
def filter_positive(msg):
    if msg["score"] > 0:
        return msg
    return None  # Drop negative scores

# Stateless enrichment
def add_timestamp(msg):
    return {**msg, "timestamp": time.time()}

# Stateful transform
class RunningAverage:
    def __init__(self):
        self.values = []
    
    def process(self, msg):
        self.values.append(msg["value"])
        avg = sum(self.values) / len(self.values)
        return {**msg, "running_avg": avg}
```

#### Deliverable
Students build a pipeline with 2 stateless and 1 stateful transform.

---

### **Module 5: Sinks - Output & Side Effects**
**Status:** 🔨 Planned

#### Learning Objectives
- Understand different sink patterns
- Handle resources (files, databases, APIs)
- Implement batching and buffering
- Proper cleanup with `finalize()`

#### Key Concepts
- **Sinks have side effects** - Write files, update databases, send alerts
- **Resource management** - Open in `__init__`, close in `finalize()`
- **Batching** - Collect N messages before writing
- **Flushing** - Force write after timeout or on finalize

#### Topics Covered
1. **Console/Print sinks** - Debugging and development
2. **File sinks** - JSONL, CSV, plain text
3. **Database sinks** - SQLite, PostgreSQL
4. **API sinks** - POST requests, webhooks
5. **Batching strategies** - Count-based, time-based, hybrid

#### Examples
```python
# Simple console sink
def print_sink(msg):
    print(f"Received: {msg}")

# File sink with batching
class BatchedJSONLSink:
    def __init__(self, path, batch_size=10):
        self.path = path
        self.batch_size = batch_size
        self.buffer = []
        self.file = open(path, 'w')
    
    def run(self, msg):
        self.buffer.append(msg)
        if len(self.buffer) >= self.batch_size:
            self._flush()
    
    def _flush(self):
        for msg in self.buffer:
            self.file.write(json.dumps(msg) + '\n')
        self.buffer.clear()
    
    def finalize(self):
        self._flush()
        self.file.close()
```

#### Deliverable
Students build a network with 3 different sink types (console, file, API).

---

### **Module 6: Blocks - Beyond Simple Nodes**
**Status:** 🔨 Planned

#### Learning Objectives
- Understand the full Agent/Block API
- Build custom Agents with explicit ports
- Use advanced patterns (Broadcast, Split, MergeAsynch)
- Understand when to use blocks vs. decorated functions

#### Key Concepts
- **Agent base class** - Manual control over ports and message handling
- **Multiple ports** - Named inputs and outputs
- **Broadcast block** - Send to all downstream nodes
- **Split block** - Route based on conditions
- **Merge block** - Combine from multiple sources

#### Topics Covered
1. **Agent lifecycle** - `startup()`, `run()`, `shutdown()`
2. **Explicit message passing** - `recv()`, `send()`, `broadcast_stop()`
3. **Multi-port agents** - Multiple ins and outs
4. **Routing logic** - Split by field value, round-robin, priority
5. **Complex patterns** - Broadcast-fanout, merge-fanin

#### Examples
```python
# Custom agent with multiple ports
class PriorityRouter(Agent):
    def __init__(self):
        super().__init__(
            inports=["in"],
            outports=["high", "medium", "low"]
        )
    
    def run(self):
        while True:
            msg = self.recv("in")
            if msg is STOP:
                self.broadcast_stop()
                return
            
            priority = msg.get("priority", "medium")
            if priority == "high":
                self.send(msg, "high")
            elif priority == "low":
                self.send(msg, "low")
            else:
                self.send(msg, "medium")
```

#### Deliverable
Students build a network using at least 2 custom Agent classes with multiple ports.

---

### **Module 7: Nested Networks & Composition**
**Status:** 🔨 Planned

#### Learning Objectives
- Build reusable network components
- Understand nested network compilation
- Design modular, composable architectures
- Debug complex nested structures

#### Key Concepts
- **Networks are blocks** - Can be embedded in other networks
- **External ports** - Connect inner network to outer network
- **Flattening** - Compilation resolves all nesting
- **Modularity** - Encapsulate complex logic in sub-networks

#### Topics Covered
1. **Creating sub-networks** - Define with external ports
2. **Composing networks** - Embed networks as blocks
3. **Path naming** - Understand `root.subnet.agent` naming
4. **Debugging nested structures** - Trace message flow
5. **Design patterns** - When to nest, when to flatten

#### Examples
```python
# Reusable text analysis sub-network
def create_text_analyzer():
    """Returns a network that analyzes text."""
    clean = Transform(fn=clean_text, name="clean")
    sentiment = Transform(fn=analyze_sentiment, name="sentiment")
    urgency = Transform(fn=analyze_urgency, name="urgency")
    
    return Network(
        name="text_analyzer",
        inports=["in"],
        outports=["out"],
        blocks={"clean": clean, "sentiment": sentiment, "urgency": urgency},
        connections=[
            ("external", "in", "clean", "in"),
            ("clean", "out", "sentiment", "in"),
            ("sentiment", "out", "urgency", "in"),
            ("urgency", "out", "external", "out")
        ]
    )

# Use in larger network
analyzer = create_text_analyzer()
main_network = Network(
    blocks={"source": source, "analyzer": analyzer, "sink": sink},
    connections=[
        ("source", "out", "analyzer", "in"),
        ("analyzer", "out", "sink", "in")
    ]
)
```

#### Deliverable
Students build a 3-level nested network (main → 2 subnets → leaf agents).

---

### **Module 8: AI Integration - Prompts to Python**
**Status:** ✅ Implemented  
**Location:** `modules/ch08_ai_integration/tutorial_prompts_to_python.md`

#### Learning Objectives
- Write effective prompts for structured output
- Parse JSON responses from AI
- Combine AI analysis with Python logic
- Use AI agents in distributed networks

#### Key Concepts
- **Prompt → JSON → Python pattern**
- Structured output for composability
- Error handling for AI calls
- Cost awareness and mock testing
- Chaining AI agents

#### Topics Covered
1. **Writing prompts** - Clear, specific, requesting JSON
2. **JSON parsing** - Extract fields, handle missing data
3. **Integration patterns** - Filter, classify, score, extract
4. **Prompt library** - Browse, search, use pre-built prompts
5. **Custom prompts** - Build domain-specific analyzers

#### Examples
- Sentiment analysis with AI
- Spam filtering with confidence thresholds
- Chaining multiple AI agents (sentiment + urgency)

#### Deliverable
Students build an AI-powered network with at least 2 AI agents and custom Python logic.

---

### **Module 9: Building Complete Applications**
**Status:** 🔨 Planned (NEW - Your Idea!)

#### Learning Objectives
- Follow systematic workflow for building DSL applications
- Test components independently before integration
- Use debugging tools to inspect message flow
- Build production-ready distributed systems

#### Key Concepts
- **Systematic workflow:** Design → Test → Integrate → Debug
- **Component testing:** Validate functions and prompts in isolation
- **Network tapping:** Inspect messages at any edge
- **Iterative development:** Start simple, add complexity gradually

#### Workflow Steps

##### **Step 1: Design - Draw the Network**
- Sketch network topology on paper/whiteboard
- Identify sources, transforms, sinks
- Label edges with message schemas
- Plan for error handling

**Example Exercise:**
```
Task: Build a content moderation system

Sketch:
    [RSS Feed] → [Extract Text] → [AI: Spam?] → [Filter] → [AI: Sentiment] → [Database]
                                      ↓
                                  [Spam Log]
```

##### **Step 2: Identify Components**
- List all pure Python functions needed
- List all AI prompts needed
- Determine which are stateful vs. stateless
- Plan test cases for each

**Example:**
```python
# Pure Python Functions:
# 1. extract_text(html) -> str
# 2. format_for_db(msg) -> dict

# AI Prompts:
# 1. spam_detector - Returns: {"is_spam": bool, "confidence": float}
# 2. sentiment_analyzer - Returns: {"sentiment": str, "score": float}

# Test Cases:
# - extract_text: HTML with tags, empty HTML, malformed HTML
# - spam_detector: Clear spam, clear legitimate, borderline
```

##### **Step 3: Test Pure Python Functions**
- Write unit tests for each function
- Test edge cases (empty input, None, errors)
- Verify return types match expected schema

**Example:**
```python
# test_extract_text.py
def test_extract_text_basic():
    html = "<p>Hello world</p>"
    result = extract_text(html)
    assert result == "Hello world"

def test_extract_text_empty():
    result = extract_text("")
    assert result == ""

def test_extract_text_nested():
    html = "<div><p>Nested <b>bold</b> text</p></div>"
    result = extract_text(html)
    assert "Nested" in result and "bold" in result
```

##### **Step 4: Test AI Prompts**
- Test prompts interactively with sample inputs
- Verify JSON schema matches expectations
- Check edge cases (ambiguous input, empty strings)
- Validate all required fields are present

**Example:**
```python
# test_prompts.py
from components.transformers.claude_agent import ClaudeAgent
from components.transformers.prompts import get_prompt

def test_spam_prompt():
    agent = ClaudeAgent(get_prompt("spam_detector"))
    
    # Clear spam
    result = agent.run("BUY NOW! FREE MONEY!")
    assert result["is_spam"] == True
    assert result["confidence"] > 0.8
    assert "confidence" in result
    assert "reason" in result
    
    # Clear legitimate
    result = agent.run("Meeting at 3pm in room 405")
    assert result["is_spam"] == False
    
    # Borderline
    result = agent.run("Great deal on laptops")
    assert "is_spam" in result
    print(f"Borderline confidence: {result['confidence']}")
```

##### **Step 5: Wrap Components**
- Apply decorators: `@msg_map`, `source_map`, `sink_map`
- Or create Agent classes for complex logic
- Ensure consistent message schemas

**Example:**
```python
# Before: Pure function
def extract_text(html):
    # ... parsing logic ...
    return clean_text

# After: Wrapped for network
text_extractor = msg_map(
    input_keys=["html"],
    output_keys=["text"]
)(extract_text)

# AI agent wrapped
spam_detector_agent = ClaudeAgent(get_prompt("spam_detector"))

def spam_checker(text):
    result = spam_detector_agent.run(text)
    return result["is_spam"], result["confidence"]

spam_checker_node = msg_map(
    input_keys=["text"],
    output_keys=["is_spam", "confidence"]
)(spam_checker)
```

##### **Step 6: Test Individual Agents**
- Test each agent in isolation (not in network)
- Mock inputs with sample messages
- Verify outputs match schema

**Example:**
```python
# test_agents.py

def test_text_extractor_standalone():
    """Test wrapped agent without network."""
    msg_in = {"html": "<p>Test content</p>"}
    msg_out = text_extractor(msg_in)
    
    assert "text" in msg_out
    assert msg_out["text"] == "Test content"
    assert "html" in msg_out  # Original field preserved

def test_spam_checker_standalone():
    """Test AI agent wrapper."""
    msg_in = {"text": "CLICK HERE FOR FREE PRIZE"}
    msg_out = spam_checker_node(msg_in)
    
    assert "is_spam" in msg_out
    assert "confidence" in msg_out
    assert msg_out["is_spam"] == True
    
def test_end_to_end_message_flow():
    """Simulate message passing through multiple nodes."""
    # Start
    msg = {"html": "<p>BUY NOW!</p>"}
    
    # Step 1: Extract
    msg = text_extractor(msg)
    assert "text" in msg
    
    # Step 2: Check spam
    msg = spam_checker_node(msg)
    assert "is_spam" in msg
    
    # Step 3: Filter (returns None if spam)
    if msg["is_spam"]:
        msg = None
    
    assert msg is None  # Message filtered
```

##### **Step 7: Build Minimal Network**
- Start with 2-3 nodes (source → transform → sink)
- Test basic connectivity
- Verify messages flow correctly

**Example:**
```python
# minimal_network.py

def test_data_source():
    """Test source with known data."""
    items = ["<p>Test 1</p>", "<p>Test 2</p>"]
    for item in items:
        yield {"html": item}

# Simple console sink for debugging
def debug_sink(msg):
    print(f"Received: {msg}")

# Minimal network
g = network([
    (test_data_source, text_extractor),
    (text_extractor, debug_sink)
])

g.run_network()
# Should print: Received: {html: ..., text: ...}
```

##### **Step 8: Add Complexity Incrementally**
- Add one component at a time
- Test after each addition
- Use tapping/debugging tools (see Step 9)

**Example progression:**
```python
# Version 1: Just extraction and printing
(source, extract, print_sink)

# Version 2: Add spam detection
(source, extract, spam_check, print_sink)

# Version 3: Add filtering
(source, extract, spam_check, filter, print_sink)

# Version 4: Add sentiment analysis
(source, extract, spam_check, filter, sentiment, print_sink)

# Version 5: Split to multiple sinks
(source, extract, spam_check, filter, sentiment, db_sink)
                                         ↓
                                    (spam_log_sink)
```

##### **Step 9: Debug with Network Tapping**
- Insert tap nodes to inspect messages at edges
- Log message counts, schemas, values
- Identify bottlenecks and failures

**Example (Future DSL Feature):**
```python
from dsl.debug import TapNode, MessageInspector

# Create taps
tap_after_extract = TapNode(name="after_extract")
tap_after_spam = TapNode(name="after_spam")

# Insert into network
g = network([
    (source, extract),
    (extract, tap_after_extract),      # TAP HERE
    (tap_after_extract, spam_check),
    (spam_check, tap_after_spam),      # TAP HERE
    (tap_after_spam, filter),
    (filter, sink)
])

g.run_network()

# Review tap data
print(tap_after_extract.get_sample_messages(n=5))
print(f"Messages passed: {tap_after_spam.message_count}")
print(f"Average spam confidence: {tap_after_spam.avg('confidence')}")
```

##### **Step 10: Production Deployment**
- Replace mock sources with production sources
- Add error handling and logging
- Implement monitoring and alerting
- Document the system

**Example:**
```python
# Development
source = MockRSSFeed(items=test_data)

# Production
source = LiveRSSFeed(
    url="https://news.example.com/feed",
    poll_interval=60,
    error_handler=log_and_continue
)
```

#### Complete Example Project
**Task:** Build a news article content moderation system

**Files:**
- `design.md` - Network diagram and component list
- `test_functions.py` - Tests for pure Python functions
- `test_prompts.py` - Interactive prompt testing
- `test_agents.py` - Standalone agent tests
- `minimal_network.py` - 3-node proof of concept
- `full_network.py` - Complete production system
- `debug_taps.py` - Network with debugging taps

**Deliverable:**
Students follow this workflow to build a complete application of their choosing (social media monitor, email classifier, log analyzer, etc.)

---

### **Module 10: Capstone Project**
**Status:** 🔨 Planned

#### Learning Objectives
- Apply all learned concepts to a real-world problem
- Design, implement, test, and deploy a complete system
- Present work to peers
- Reflect on distributed systems concepts

#### Project Requirements
1. **Minimum complexity:**
   - 3+ sources (at least one production source)
   - 5+ transforms (mix of Python and AI)
   - 3+ sinks (at least one persistent storage)
   - At least one nested network
   
2. **Must demonstrate:**
   - Fanout and fanin patterns
   - Filtering (returning None)
   - Stateful processing
   - AI integration
   - Error handling
   - Testing strategy

3. **Deliverables:**
   - Complete working code
   - Test suite
   - Network diagram
   - 5-minute presentation
   - Written reflection

#### Example Projects
- **Twitter Sentiment Dashboard** - Monitor hashtags, analyze sentiment, store in DB, generate reports
- **Email Triage System** - Classify emails, route by priority, auto-respond to simple queries
- **Log Analysis Pipeline** - Parse logs, detect anomalies, alert on errors, generate statistics
- **Content Recommendation Engine** - Fetch articles, analyze topics, match to user preferences, rank results
- **Academic Paper Processor** - Extract papers from arXiv, summarize with AI, categorize by topic, store metadata

#### Assessment Rubric
- **Correctness** (30%) - Does it work? Are tests passing?
- **Design** (25%) - Is the architecture clean? Good separation of concerns?
- **Complexity** (20%) - Appropriate use of advanced features?
- **Testing** (15%) - Comprehensive test coverage?
- **Presentation** (10%) - Clear explanation of design and trade-offs?

---

## Cross-Cutting Themes

### Testing Strategy (All Modules)
Every module emphasizes testing:
1. **Unit tests** - Individual functions in isolation
2. **Integration tests** - Full network execution
3. **Test-driven development** - Write tests before code when appropriate

### Error Handling (Progressive)
- **Modules 1-2:** Basic error messages
- **Modules 3-5:** Try/catch, logging, fallbacks
- **Modules 6-7:** Graceful degradation, retry logic
- **Modules 8-9:** AI error handling, monitoring
- **Module 10:** Production-grade error handling

### Performance Awareness (Progressive)
- **Modules 1-3:** Understand message flow
- **Modules 4-6:** Identify bottlenecks
- **Modules 7-9:** Optimize critical paths
- **Module 10:** Measure and optimize

### Documentation Practices (All Modules)
- Clear function docstrings
- Network diagrams
- README files
- Code comments for complex logic

---

## Pedagogical Progression Summary

| Module | Complexity | Focus | Key Skill |
|--------|-----------|-------|-----------|
| 1 | ⭐ | Linear pipelines | Basic message passing |
| 2 | ⭐⭐ | Network patterns | Fanout/fanin, component reuse |
| 3 | ⭐⭐ | Data sources | Generators, state management |
| 4 | ⭐⭐ | Data processing | Stateful transforms, filtering |
| 5 | ⭐⭐ | Outputs | Resource management, batching |
| 6 | ⭐⭐⭐ | Advanced blocks | Multi-port agents, custom routing |
| 7 | ⭐⭐⭐ | Composition | Nested networks, modularity |
| 8 | ⭐⭐⭐ | AI Integration | Prompts, JSON, AI-Python bridge |
| 9 | ⭐⭐⭐⭐ | Application dev | Systematic workflow, debugging |
| 10 | ⭐⭐⭐⭐⭐ | Capstone | End-to-end system design |

---

## Module Dependencies

```
Module 1 (Basics)
    ↓
Module 2 (Patterns) ←-------------------┐
    ↓                                   |
Module 3 (Sources) ────┐                |
    ↓                   |                |
Module 4 (Transforms) ─┤                |
    ↓                   |                |
Module 5 (Sinks) ──────┴─→ Module 6 (Blocks)
                              ↓
                         Module 7 (Nested)
                              ↓
                         Module 8 (AI)
                              ↓
    ┌─────────────────────────┴─────────────────┐
    ↓                                           ↓
Module 9 (Building Apps)                  Module 10 (Capstone)
    ↓                                           ↓
    └───────────────────→ (Both feed into) ────┘
```

**Key insight:** Modules 3-5 can be taught in parallel or in any order, as they focus on different node types. Module 6 requires all of them. Module 9 synthesizes everything before the capstone.

---

## Estimated Timeline

**10-week semester:**
- Week 1: Module 1
- Week 2: Module 2
- Week 3: Module 3
- Week 4: Module 4
- Week 5: Module 5
- Week 6: Module 6
- Week 7: Module 7
- Week 8: Module 8
- Week 9: Module 9 (Building Apps Workflow)
- Week 10: Module 10 (Capstone project)

**15-week semester:**
- Weeks 1-2: Modules 1-2
- Weeks 3-5: Modules 3-5 (one per week)
- Weeks 6-7: Module 6-7
- Weeks 8-9: Module 8
- Week 10: Module 9 (Building Apps)
- Weeks 11-15: Module 10 (Extended capstone with presentations)

---

## Implementation Priorities

### High Priority (Core Learning Path)
1. ✅ Module 1 - Implemented
2. ✅ Module 2 - Implemented
3. ✅ Module 8 - Implemented
4. 🔨 Module 9 - **NEXT** (Building Apps Workflow)

### Medium Priority (Depth)
5. Module 3 - Sources
6. Module 4 - Transforms
7. Module 5 - Sinks

### Lower Priority (Advanced Concepts)
8. Module 6 - Blocks
9. Module 7 - Nested Networks
10. Module 10 - Capstone (depends on all others)

**Rationale:** Modules 1, 2, 8, and 9 form the **critical path** for students to build interesting AI-powered applications. The depth modules (3-5) can be developed as needed, and advanced concepts (6-7) can wait until students have mastered the basics.

---

## Next Steps

1. **Develop Module 9** (Building Apps) with:
   - Detailed workflow documentation
   - Step-by-step example project
   - Testing templates
   - Debugging tools (tap nodes, inspectors)

2. **Create Module 10 scaffold:**
   - Project requirements
   - Assessment rubric
   - Example projects
   - Presentation guidelines

3. **Fill in Modules 3-5** as needed based on student questions and common patterns

4. **Build debugging infrastructure:**
   - TapNode implementation
   - MessageInspector utilities
   - Logging decorators
   - Visualization tools

---

## Success Metrics

Students successfully complete the course if they can:

1. ✅ Build a 5+ node network from scratch
2. ✅ Write effective prompts that return structured JSON
3. ✅ Test components independently before integration
4. ✅ Debug issues using systematic approaches
5. ✅ Design appropriate network topologies for given problems
6. ✅ Integrate AI and Python logic seamlessly
7. ✅ Deploy a working distributed system

**Ultimate goal:** Students leave the course able to build production-ready distributed systems that solve real problems, using AI where appropriate, with confidence in their testing and debugging skills.