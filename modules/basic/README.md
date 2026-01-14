# Basic Network Example: Distributed Social Media Analysis

## Key Insight
You build a distributed system by constructing a graph in which nodes call
ordinary Python functions that are often from widely-used libraries such as NumPy. 
These functions are independent of dsl and have no concurrency primitives such 
as threads, processes, locks, or message passing. 

## The Graph
The graph is specified as a list of directed edges where an edge from node u to
node v is written as (u, v). Each node in the graph has at least one incident edge.
The graph in this example is:

```python
    (hacker_data_source, discard_spam),
    (tech_data_source, discard_spam),
    (reddit_data_source, discard_spam),
    (discard_spam, analyze_sentiment),
    (discard_spam, discard_non_urgent),
    (discard_non_urgent, issue_alert),
    (analyze_sentiment, archive_recorder), 

RSS FEEDS (Sources)

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ hacker_data │    │ tech_data   │    │ reddit_data │
│   _source   │    │   _source   │    │   _source   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                 FANIN    ▼
                   ┌─────────────┐
                   │  discard_   │ (Transform: AI Spam Filter)
                   │    spam     │
                   └──────┬──────┘
                          │
                          │
                 FANOUT   ├──────────────────┐
                          │                  │
                          ▼                  ▼
                   ┌─────────────┐    ┌─────────────┐
                   │  analyze_   │    │  discard_   │ (Transform: Filter Urgent)
                   │  sentiment  │    │  non_urgent │
                   └──────┬──────┘    └──────┬──────┘
                          │                  │
                          │                  │
                          ▼                  ▼
                   ┌─────────────┐    ┌─────────────┐
                   │  archive_   │    │  issue_     │ (Sink: Email Alerts)
                   │  recorder   │    │  alert      │
                   └─────────────┘    └─────────────┘
                    (Sink: JSON)
```

## Nodes: Sources, Transformers and Sinks

Nodes without input edges are called **Source** nodes. Nodes without output edges are
called **Sink** nodes. Nodes with at least one input and one output edge are called **Transformers**. 


In this example, the nodes **hacker_data_source**, **tech_data_source**, and **reddit_data_source**  are souces; nodes **discard_spam**, **analyze_sentiment**, and **discard_non_urgent**, are transformers; and nodes **issue_alert** and **archive_recorder** are sinks.

## Streams
A message stream is a sequence of messages. Associated with each edge of the graph (u, v) is a stream created by u and sent to v. 

For example **discard_spam** receives streams from **hacker_data_source**, **tech_data_source**, and **reddit_data_source** while it sends streams to **issue_alert** and **archive_recorder**.

## Components Library
The components library is a library of ordinary Python functions that are independent of **dsl** and have no concurrency primitives such as threads, processes, locks, or message passing. We will often build distributed systems by using standard Python libraries such as those in NumPy.

In this example, we use functions in the library that are mockups of calls to AI services. For example, we use a mockup call to an AI service to determine the sentiment of a text. You can exeucte the code in this example without registering for services, getting keys, and downloading APIs. Later we will replace the mockups with AI services and APIs. 

# From Plain Python to a Node of a Distributed System Graph

### Sources ###
You build a source node of the graph by calling **Source(f)** where **f** is a function that returns a value. Look at
```python
hacker_data_source = Source(MockRSSSource(
    feed_name="hacker_news", max_articles=100).run)
```
**MockRSSSource** is a class, and **MockRSSSource(feed_name="hacker_news", max_articles=100)** is an object -- an instance of that class -- while **MockRSSSource(feed_name="hacker_news", max_articles=100).run** is a function. This function returns a new value, the next article, when it is called. The infrastructure calls the function repeatedyl to generate a stream of articles.

### Transformers ###
Similarly **Transform(f)**, where where **f** is a function, is a transformer node. Function **f** has a single argument and returns a single value.

In this example **MockAISentimentAnalyzer.run** is a function that has a single argument, a text, and that returns a single value which is a dict. When a message arrives at this node the contents of the message are passed to the function and the function's return value is sent as a message by the node.

### Merge Streams ###
A node may have input edges from multple nodes. In the example, the node **discard_spam** has inputs from all three source nodes. The streams from all edges feeding a node are merged nondeterministically and fairly. This means that the order in which messages are received is unknown; however, every message in every input stream of a node is received by the node eventually if the system runs forever. In the example, a hacker news article may be sent by a source before a tech article is sent by a different source but the tech article may be received before the hacker one. We also know that the hacker article will be received eventually.

### Broadcast ###
A node may have multiple edges leading from it. In the example, the node **discard_spam** has outputs to nodes **analyze_sentiment**, and **discard_non_urgent**. A stream output by a node is broadcast along all the output edges from that node. In the example, nodes **analyze_sentiment** and **discard_non_urgent** receive identical streams. The delay of messages on different streams is unknown. So, at a given instant, **analyze_sentiment** may have received more, or fewer, or the same number of messages as **discard_non_urgent**.

This example builds a distributed system that processes social media posts from three platforms (X, Reddit, Facebook), cleans the text, and performs two types of analysis in parallel: sentiment analysis and urgency detection. The results are archived and displayed in real-time.

**The key insight:** You build this entire distributed system using ordinary Python functions—no threads, processes, locks, or explicit message passing required. The functions know nothing about distributed systems.



## The Central Teaching Point

**Functions being wrapped are general-purpose and know nothing about DSL, messages, or distributed systems.**

Look at `simple_text_analysis.py`:
- `clean_text(text)` - just a string processing function
- `analyze_sentiment(text)` - returns a tuple `(sentiment, score)`
- `analyze_urgency(text)` - returns a tuple `(urgency, metrics)`
- `SourceOfSocialMediaPosts` - just iterates through a list of strings

These could be used in ANY Python program. The DSL decorators transform them into distributed agents.

## Network Topology
```
     from_X ────┐
                │
   from_Reddit ─┼──> clean ──┬──> sentiment_analyzer ──> archive_recorder
                │            │
 from_Facebook ─┘            └──> urgency_analyzer ───> display
 
 [FANIN]              [FANOUT]         [PARALLEL PROCESSING]
```

**Fanin Pattern**: Three independent social media sources (`from_X`, `from_Reddit`, `from_Facebook`) all send their posts to a single `clean` node that removes unwanted characters.

**Fanout Pattern**: The `clean` node broadcasts each cleaned post to TWO analyzers simultaneously—one checking sentiment, another checking urgency.

**Parallel Outputs**: Analysis results flow to different destinations—sentiment data goes to a JSON archive, urgency alerts go to the console.

## Code Walkthrough

Open `network_example.py` and follow these five steps:

### Step 1: Create Source Nodes (Lines 30-40)
```python
# Create ordinary Python objects
from_X_data = SourceOfSocialMediaPosts(posts=example_posts_from_X, name="from_X")

# Wrap into agents using source_map
from_X = source_map(output_keys=["text"])(from_X_data.run)
```

**What happens:**
- `from_X_data.run()` returns a string: `"Just got promoted at work!"`
- `source_map` wraps it into a message dict: `{"text": "Just got promoted at work!"}`
- The agent sends this dict downstream

**Key point:** The `SourceOfSocialMediaPosts` class knows nothing about messages or dicts. It just returns strings.

### Step 2: Wrap Vanilla Python Functions (Lines 46-67)
```python
clean = transform_map(
    input_keys=["text"],
    output_keys=["clean_text"]
)(clean_text)
```

**Translation:** 
1. Extract `text` from incoming message: `msg["text"]`
2. Call `clean_text("Just got promoted at work!")`
3. Get result: `"Just got promoted at work"`
4. Put in output message: `msg["clean_text"] = "Just got promoted at work"`
5. Send: `{"text": "...", "clean_text": "..."}`

**Key point:** `clean_text()` is just a string function. It doesn't know it's part of a distributed system.

**Multiple outputs:**
```python
sentiment_analyzer = transform_map(
    input_keys=["clean_text"],
    output_keys=["sentiment", "score"]
)(analyze_sentiment)
```

`analyze_sentiment()` returns a tuple `("POSITIVE", 2)`, which `transform_map` unpacks into:
```python
{"clean_text": "...", "sentiment": "POSITIVE", "score": 2}
```

### Step 3: Create Sink Nodes (Lines 73-85)
```python
display_handler = ConsoleRecorder()
display = Sink(fn=display_handler.run)
```

Sinks consume messages without producing downstream output. They print to console or save to files.

### Step 4: Define Network Topology (Lines 91-103)
```python
g = network([
    # Fanin: Three sources merge into clean
    (from_X, clean),
    (from_Reddit, clean),
    (from_Facebook, clean),
    
    # Fanout: clean broadcasts to two analyzers
    (clean, sentiment_analyzer),
    (clean, urgency_analyzer),
    
    # Route to different outputs
    (sentiment_analyzer, archive_recorder),
    (urgency_analyzer, display)
])
```

Each tuple `(node_a, node_b)` means "connect node_a's output to node_b's input."

**That's it.** This simple list of connections defines the entire distributed system topology.

### Step 5: Execute the Network (Lines 109-111)
```python
g.run_network()
```

The DSL handles all the complexity:
- Spawning processes/threads for each node
- Managing message queues between nodes
- Routing messages according to the topology
- Coordinating shutdown when sources are exhausted

## Running the Example
```bash
python -m modules.basic.network_example
```

**What you'll see:**
- Console output showing urgency alerts as they're detected
- A file `sentiment_archive.jsonl` containing all sentiment analysis results

**View the archived data:**
```bash
cat sentiment_archive.jsonl | jq '.'
```

## The Three Decorators

DisSysLab uses three decorators to wrap ordinary Python functions:

### `source_map(output_keys=[...])`
Wraps functions that generate data (no inputs, have outputs).
```python
# Function returns a string
def generate():
    return "hello"

# Wrap it
source = source_map(output_keys=["text"])(generate)
# Generates: {"text": "hello"}
```

### `transform_map(input_keys=[...], output_keys=[...])`
Wraps functions that process data (have inputs and outputs).
```python
# Function takes string, returns string
def process(text):
    return text.upper()

# Wrap it
transform = transform_map(
    input_keys=["text"],
    output_keys=["upper_text"]
)(process)
# Input:  {"text": "hello"}
# Output: {"text": "hello", "upper_text": "HELLO"}
```

### `sink_map(input_keys=[...])`
Wraps functions that consume data (have inputs, no outputs).
```python
# Function takes values and prints
def display(text, score):
    print(f"{text}: {score}")

# Wrap it
sink = sink_map(input_keys=["text", "score"])(display)
# Receives: {"text": "hello", "score": 42}
# Prints: "hello: 42"
```

## The Big Picture: Why This Matters

**You just built a distributed system where:**
- Three data sources run independently
- A cleaning pipeline processes messages from all sources
- Two parallel analyzers work simultaneously on cleaned data
- Results route to different outputs based on type

**And you did it by:**
1. Writing ordinary Python functions (`clean_text`, `analyze_sentiment`, etc.)
2. Wrapping them with decorators (`source_map`, `transform_map`, `sink_map`)
3. Listing connections as simple tuples

**No explicit:**
- Thread/process management
- Queue creation or message routing
- Synchronization primitives (locks, semaphores)
- Inter-process communication code

The DSL handles all the distributed systems complexity, letting you focus on the data processing logic.

## What's in `simple_text_analysis.py`?

This file contains:
- **Data**: Example posts from each social media platform (just lists of strings)
- **Functions**: Vanilla Python functions that know nothing about distributed systems
  - `clean_text()` - text preprocessing
  - `analyze_sentiment()` - basic sentiment detection
  - `analyze_urgency()` - keyword-based urgency scoring
- **Source class**: `SourceOfSocialMediaPosts` - iterates through a list of strings

**Note:** These functions use simple string operations and regex—nothing fancy. The point is to show that ANY Python function can become part of a distributed system.

## Next Steps

Once you understand this basic example:
1. Try modifying the network topology (add another analyzer, change routing)
2. Write your own processing functions and wrap them
3. Experiment with different fanin/fanout patterns
4. Move on to more advanced examples using NumPy, pandas, scikit-learn

**Key principle:** Start with working Python code, then distribute it using the DSL.