# Basic Network Example: Distributed Social Media Analysis

## What This Example Does

This example builds a distributed system that processes social media posts from three platforms (X, Reddit, Facebook), cleans the text, and performs two types of analysis in parallel: sentiment analysis and urgency detection. The results are archived and displayed in real-time.

**The key insight:** You build this entire distributed system using ordinary Python functions—no threads, processes, locks, or explicit message passing required. The functions know nothing about distributed systems.

## Key Concepts Demonstrated

1. **Fanin**: Multiple data sources merge into a single processing node
2. **Fanout**: One node broadcasts its output to multiple downstream nodes  
3. **Message Passing**: Data flows automatically between nodes as dictionaries
4. **Parallel Processing**: Multiple analyzers process data simultaneously
5. **Ordinary Functions**: Vanilla Python functions become distributed system components

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