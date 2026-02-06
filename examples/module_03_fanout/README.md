# Module 03: Fanout - Broadcasting Messages to Multiple Destinations

Learn how to send the same message to multiple processing paths that run independently and concurrently.

## What You'll Learn

- How to broadcast one message to multiple destinations (fanout pattern)
- How fanout creates independent processing paths
- Why each destination gets a COPY of the message
- How to build parallel processing pipelines
- The difference between fanout and filtering

## The Problem We're Solving

Sometimes you need to process the same data in multiple different ways:
- Analyze text for sentiment AND extract keywords
- Save data to database AND send notification email
- Process image for thumbnail AND for full-size display
- Log activity AND trigger business logic

In traditional programming, you'd call each function sequentially. In DisSysLab, you use **fanout** to send each message to multiple destinations that process it concurrently and independently.

## Network Topology

Our example broadcasts each word to two different processing paths:
```
                    → uppercase → collector_upper → ["HELLO", "WORLD", "PYTHON"]
                   ↗
["hello", "world"] 
                   ↘
                    → reverse → collector_reverse → ["olleh", "dlrow", "nohtyp"]
```

**Key insight:** Each word goes to BOTH paths. "hello" becomes "HELLO" in one path and "olleh" in the other path - simultaneously!

## The Code Walkthrough

### Step 1: Write Ordinary Python Functions
```python
word_source = ListSource(items=["hello", "world", "python"])

def to_uppercase(text):
    """Convert text to uppercase."""
    return text.upper()

def reverse_text(text):
    """Reverse the text."""
    return text[::-1]
```

**What's happening:**
- Two completely different processing functions
- `to_uppercase()` transforms to uppercase
- `reverse_text()` reverses the string
- Neither function knows about the other - they're independent

**The beauty of fanout:** We can apply BOTH transformations to the same data without either function knowing about the other.

### Step 2: Wrap Functions into Network Nodes
```python
source = Source(
    fn=word_source.run,
    name="word_source"
)

uppercase = Transform(
    fn=to_uppercase,
    name="uppercase"
)

reverse = Transform(
    fn=reverse_text,
    name="reverse"
)

results_upper = []
collector_upper = Sink(
    fn=results_upper.append,
    name="collector_upper"
)

results_reverse = []
collector_reverse = Sink(
    fn=results_reverse.append,
    name="collector_reverse"
)
```

**Key observation:** We have TWO separate result lists because we have TWO independent processing paths. Each path collects its own results.

### Step 3: Define the Network Topology

**This is where fanout happens:**
```python
g = network([
    (source, uppercase),          # Path 1: source → uppercase
    (source, reverse),            # Path 2: source → reverse (FANOUT!)
    (uppercase, collector_upper),
    (reverse, collector_reverse)
])
```

**The fanout magic:**
- `(source, uppercase)` - source sends to uppercase
- `(source, reverse)` - source ALSO sends to reverse

**Notice:** We mention `source` TWICE as the starting point of edges. This is fanout!

**What flows through the network:**
```
source produces "hello":
  → Copy 1 goes to uppercase: "hello" → "HELLO" → collector_upper
  → Copy 2 goes to reverse: "hello" → "olleh" → collector_reverse

source produces "world":
  → Copy 1 goes to uppercase: "world" → "WORLD" → collector_upper
  → Copy 2 goes to reverse: "world" → "dlrow" → collector_reverse

source produces "python":
  → Copy 1 goes to uppercase: "python" → "PYTHON" → collector_upper
  → Copy 2 goes to reverse: "python" → "nohtyp" → collector_reverse
```

### Step 4: Run the Network
```python
g.run_network()
```

**What happens during execution:**

**Concurrent processing:** When source produces "hello":
- Thread 1 (uppercase path): receives "hello", processes it immediately
- Thread 2 (reverse path): receives "hello", processes it immediately
- Both happen AT THE SAME TIME - not sequentially!

**Each message is copied:** The original "hello" isn't moved - it's COPIED to each destination. This means:
- `uppercase` can't affect what `reverse` sees
- Each path is completely independent
- If one path is slow, the other continues normally

### Step 5: Verify Results
```python
print("Uppercase path results:", results_upper)
# Output: Uppercase path results: ['HELLO', 'WORLD', 'PYTHON']

print("Reverse path results:", results_reverse)
# Output: Reverse path results: ['olleh', 'dlrow', 'nohtyp']

print(f"  Source produced: 3 words")
print(f"  Each word went to 2 destinations")
print(f"  Total messages processed: 6 (3 words × 2 paths)")
```

## Running This Example

From the DisSysLab root directory:
```bash
python3 -m examples.module_03_fanout.example
```

**Expected output:**
```
Uppercase path results: ['HELLO', 'WORLD', 'PYTHON']
Reverse path results: ['olleh', 'dlrow', 'nohtyp']
✓ Fanout completed successfully!
  Source produced: 3 words
  Each word went to 2 destinations
  Total messages processed: 6 (3 words × 2 paths)
```

## Key Concepts

### Concept 1: Fanout Creates Copies

When a node fans out to multiple destinations, **each destination gets its own copy** of the message:
```python
# Network with fanout
network([
    (source, process1),
    (source, process2),
    (source, process3)
])
```

**What happens:**
- source produces message M
- M is COPIED to process1, process2, AND process3
- Each processes its own copy independently
- Changes in one path don't affect others

**Why copies matter:**
```python
def modify_list(lst):
    lst.append("modified")
    return lst

# If we didn't copy, all paths would see the modifications!
# But with copies, each path has its own independent data
```

### Concept 2: Independent Parallel Processing

Each fanout path runs **independently and concurrently**:
```
Path 1: source → fast_process → collector1    (finishes quickly)
Path 2: source → slow_process → collector2    (takes longer)
```

**Key insights:**
- Fast paths don't wait for slow paths
- Each path has its own thread and queue
- One path failing doesn't stop other paths
- Order of completion is not guaranteed

**Example timing:**
```
t=0: source produces "hello"
t=1: fast_process finishes "HELLO"
t=2: fast_process gets "world"
t=3: slow_process still working on "hello"
t=4: fast_process finishes "WORLD"
t=5: slow_process finishes "olleh"
```

### Concept 3: Fanout Degree (How Many Destinations)

**Fanout degree** = number of destinations from one source
```python
# Fanout degree 2
network([
    (source, dest1),
    (source, dest2)
])

# Fanout degree 4
network([
    (source, dest1),
    (source, dest2),
    (source, dest3),
    (source, dest4)
])
```

**Performance consideration:**
- Higher fanout = more copies = more memory
- But processing happens in parallel, so total time ≈ slowest path

**Typical use cases:**
- Fanout 2-3: Common (parallel processing paths)
- Fanout 4-10: Reasonable (broadcast to multiple services)
- Fanout 100+: Rare but possible (mass notifications)

### Concept 4: Fanout vs. Filtering

**Fanout (this module):** ALL messages go to ALL destinations
```python
def process_a(data):
    return data.upper()

def process_b(data):
    return data[::-1]

# BOTH see EVERY message
network([
    (source, process_a),
    (source, process_b)
])
```

**Filtering (Module 02):** SOME messages are dropped
```python
def only_even(data):
    if data % 2 == 0:
        return data
    return None  # Odd numbers dropped

# Only even numbers continue
network([
    (source, only_even),
    (only_even, collector)
])
```

**Combined fanout + filtering:**
```python
network([
    (source, filter_even),     # First path: only evens
    (source, filter_odd),      # Second path: only odds
    (filter_even, collector_even),
    (filter_odd, collector_odd)
])
# Now evens go one way, odds go another - perfect routing!
```

### Concept 5: Common Fanout Patterns

**Pattern 1: Process and Log**
```python
network([
    (source, business_logic),      # Main processing
    (source, logger)               # Logging (doesn't affect main flow)
])
```

**Pattern 2: Multiple Transformations**
```python
network([
    (source, extract_keywords),    # Extract keywords
    (source, analyze_sentiment),   # Analyze sentiment
    (source, count_words),         # Count words
    # All three analyses happen in parallel!
])
```

**Pattern 3: Save and Notify**
```python
network([
    (source, database_saver),      # Save to database
    (source, email_notifier)       # Send notification
])
```

**Pattern 4: Different Formats**
```python
network([
    (source, generate_thumbnail),  # Create small image
    (source, generate_full_size),  # Create full image
    (source, generate_metadata)    # Extract metadata
])
```

## Common Mistakes

### Mistake 1: Expecting Sequential Processing
```python
# ❌ Wrong assumption - thinking paths run in order
network([
    (source, process1),  # "This runs first"
    (source, process2)   # "Then this runs"
])

# Reality: BOTH run concurrently!
```

**Why it fails:** In fanout, all paths run simultaneously. There's no guaranteed order.  
**Fix:** If you need sequential processing, use a pipeline: source → process1 → process2

### Mistake 2: Modifying Shared State
```python
# ❌ Wrong - modifying shared state from multiple paths
counter = [0]

def increment_a(data):
    counter[0] += 1  # Race condition!
    return data

def increment_b(data):
    counter[0] += 1  # Race condition!
    return data

network([
    (source, increment_a),
    (source, increment_b)
])
# Counter value is unpredictable due to race conditions!
```

**Why it fails:** Multiple threads accessing shared state without locks causes race conditions.  
**Fix:** Each path should have its own independent state, or use thread-safe structures.

### Mistake 3: Using Same Sink for Multiple Paths
```python
# ❌ Wrong - can cause interleaving
results = []

collector1 = Sink(fn=results.append, name="c1")
collector2 = Sink(fn=results.append, name="c2")

network([
    (source, process1),
    (source, process2),
    (process1, collector1),  # Both append to same list!
    (process2, collector2)   # Results will be interleaved
])
```

**Why it fails:** Results from both paths mix together, and you can't tell which came from which path.  
**Fix:** Use separate result lists for each path.
```python
# ✓ Correct - separate results
results1 = []
results2 = []

collector1 = Sink(fn=results1.append, name="c1")
collector2 = Sink(fn=results2.append, name="c2")
```

### Mistake 4: Forgetting Fanout is Copies
```python
# ❌ Wrong - expecting modifications to propagate
def modify_and_pass(data_dict):
    data_dict['modified'] = True
    return data_dict

network([
    (source, modify_and_pass),
    (source, check_modified)  # Won't see modification!
])
```

**Why it fails:** Each path gets a COPY (for immutable types) or reference (for mutable types). For safety, treat them as independent.  
**Fix:** Don't rely on side effects between paths. Each path should be self-contained.

### Mistake 5: Creating Fanout by Mistake
```python
# ❌ Accidental fanout - typo creates two connections
network([
    (source, processor),
    (source, processor)  # Oops! Same destination twice
])
# Now processor gets DUPLICATE messages!
```

**Why it fails:** Listing the same edge twice creates actual duplicate messages.  
**Fix:** Each connection should be listed only once. Check your network definition carefully.

## Experiments to Try

Modify `example.py` to explore fanout behavior:

### Experiment 1: Add a Third Path

**Add another processing function:**
```python
def word_length(text):
    return len(text)

length_counter = Transform(
    fn=word_length,
    name="length_counter"
)

results_length = []
collector_length = Sink(
    fn=results_length.append,
    name="collector_length"
)
```

**Add to network:**
```python
g = network([
    (source, uppercase),
    (source, reverse),
    (source, length_counter),  # Third path!
    (uppercase, collector_upper),
    (reverse, collector_reverse),
    (length_counter, collector_length)
])
```

**What to observe:** Three independent results: uppercase, reverse, and lengths [5, 5, 6]

### Experiment 2: Add Print Statements

**In each transform:**
```python
def to_uppercase(text):
    print(f"[UPPERCASE] Processing: {text}")
    return text.upper()

def reverse_text(text):
    print(f"[REVERSE] Processing: {text}")
    return text[::-1]
```

**What to observe:** See that both paths process the same messages concurrently

### Experiment 3: Different Speed Paths

**Add delays:**
```python
import time

def fast_process(text):
    return text.upper()

def slow_process(text):
    time.sleep(1)  # Simulate slow processing
    return text[::-1]
```

**What to observe:** Fast path finishes quickly while slow path is still working

### Experiment 4: Fanout with Filtering

**Add filters to each path:**
```python
def keep_long_words(text):
    if len(text) > 5:
        return text
    return None

filter_long = Transform(
    fn=keep_long_words,
    name="filter_long"
)

network([
    (source, filter_long),       # Path 1: long words only
    (source, uppercase),          # Path 2: all words
    (filter_long, collector_long),
    (uppercase, collector_upper)
])
```

**What to observe:** Path 1 only gets "python", Path 2 gets all three words

### Experiment 5: Count Total Messages

**Track processing:**
```python
processed_count = [0, 0]  # [uppercase_count, reverse_count]

def count_uppercase(text):
    processed_count[0] += 1
    return text.upper()

def count_reverse(text):
    processed_count[1] += 1
    return text[::-1]

# After running:
print(f"Total messages: {sum(processed_count)}")
print(f"Uppercase path: {processed_count[0]}")
print(f"Reverse path: {processed_count[1]}")
```

**What to observe:** Each path processes all 3 messages = 6 total

## Real-World Use Cases

### Use Case 1: Data Pipeline with Backup
```python
network([
    (source, primary_database),      # Main storage
    (source, backup_database)        # Backup storage
])
# Same data goes to both databases
```

### Use Case 2: Multi-Format Output
```python
network([
    (source, generate_json),         # JSON format
    (source, generate_xml),          # XML format
    (source, generate_csv)           # CSV format
])
# Create three different formats from same data
```

### Use Case 3: Analytics and Processing
```python
network([
    (source, business_logic),        # Main processing
    (source, analytics_tracker),     # Track metrics
    (source, audit_logger)           # Compliance logging
])
```

### Use Case 4: Notification System
```python
network([
    (order_source, process_order),   # Process the order
    (order_source, email_customer),  # Send confirmation email
    (order_source, notify_warehouse),# Alert warehouse
    (order_source, update_inventory) # Update stock
])
```

## Next Steps

You now understand how to broadcast messages to multiple destinations! Fanout lets you create parallel processing pipelines.

**Next module:** [Module 04: Fanin](../module_04_fanin/) - Learn how to merge multiple sources into one processor (the opposite of fanout!).

**Want to combine fanout with other patterns?** Try:
- Fanout + filtering in each path (route different messages different ways)
- Fanout + pipelines (each path is a multi-stage pipeline)
- Fanout + fanout (tree-like broadcast structure)

**Want to go deeper?** Read [How It Works](../../docs/HOW_IT_WORKS.md) to understand how DisSysLab copies messages and manages concurrent processing.

## Quick Reference

**Basic fanout pattern:**
```python
network([
    (source, dest1),  # Same source...
    (source, dest2),  # ...to multiple destinations
    (source, dest3)
])
```

**Fanout with processing:**
```python
network([
    (source, process1),
    (source, process2),
    (process1, sink1),
    (process2, sink2)
])
```

**Remember:**
- Each destination gets a COPY of the message
- All paths run independently and concurrently
- One slow path doesn't block fast paths
- Use separate result collectors for each path
- Fanout = one source appears multiple times as edge start

---

**Questions or stuck?** Review the "Common Mistakes" section or check [Troubleshooting](../../docs/troubleshooting.md).