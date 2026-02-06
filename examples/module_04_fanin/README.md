# Module 04: Fanin - Merging Multiple Sources into One Destination

Learn how to merge messages from multiple independent sources into a single processing node.

## What You'll Learn

- How to merge multiple sources into one destination (fanin pattern)
- How messages from different sources are interleaved
- Why message order from fanin is non-deterministic
- How to build data aggregation pipelines
- The difference between fanin and fanout

## The Problem We're Solving

Sometimes you need to collect data from multiple independent sources:
- Aggregate data from multiple sensors
- Merge log files from different services
- Combine user inputs from multiple forms
- Collect results from parallel workers
- Monitor multiple social media feeds

In traditional programming, you'd manually poll each source or use complex callbacks. In DisSysLab, you use **fanin** to automatically merge multiple sources into one processing node.

## Network Topology

Our example merges two independent sources into one processor:
```
source_A: ["A1", "A2", "A3"] ───┐
                                ├──→ merger → collector → results
source_B: ["B1", "B2", "B3"] ───┘
```

**Key insight:** Both sources send to the SAME destination (merger). The merger receives messages from BOTH sources, interleaved based on timing.

## The Code Walkthrough

### Step 1: Write Ordinary Python Functions
```python
source_A_data = ListSource(items=["A1", "A2", "A3"])
source_B_data = ListSource(items=["B1", "B2", "B3"])

def add_label(text, label="merged"):
    """Add a label to the text."""
    return f"[{label}] {text}"
```

**What's happening:**
- Two independent data sources (A and B)
- Each produces its own sequence of messages
- `add_label()` processes merged messages - it doesn't know or care which source sent them

**The power of fanin:** The processing function (`add_label`) treats all messages the same, regardless of which source they came from.

### Step 2: Wrap Functions into Network Nodes
```python
source_A = Source(
    fn=source_A_data.run,
    name="source_A"
)

source_B = Source(
    fn=source_B_data.run,
    name="source_B"
)

merger = Transform(
    fn=add_label,
    name="merger"
)

results = []
collector = Sink(
    fn=results.append,
    name="collector"
)
```

**Key observation:** We have TWO source nodes but only ONE transform node. The transform will receive messages from both sources.

### Step 3: Define the Network Topology

**This is where fanin happens:**
```python
g = network([
    (source_A, merger),     # Source A → merger
    (source_B, merger),     # Source B → merger (FANIN!)
    (merger, collector)
])
```

**The fanin magic:**
- `(source_A, merger)` - source_A sends to merger
- `(source_B, merger)` - source_B ALSO sends to merger

**Notice:** We mention `merger` TWICE as the destination of edges. This is fanin!

**What flows through the network:**
```
source_A produces "A1" → goes to merger → "[merged] A1" → collector
source_B produces "B1" → goes to merger → "[merged] B1" → collector
source_A produces "A2" → goes to merger → "[merged] A2" → collector
source_B produces "B2" → goes to merger → "[merged] B2" → collector
... (messages interleave based on timing)
```

### Step 4: Run the Network
```python
g.run_network()
```

**What happens during execution:**

**Concurrent sources:** Both sources run simultaneously:
- `source_A` produces A1, A2, A3 in its own thread
- `source_B` produces B1, B2, B3 in its own thread
- Both send to `merger` which has ONE input queue

**Message interleaving:** Messages arrive at `merger` in the order they're produced:
- If source_A is faster: might get A1, A2, A3, B1, B2, B3
- If source_B is faster: might get B1, B2, B3, A1, A2, A3
- If they're similar speed: might get A1, B1, A2, B2, A3, B3
- **The order is non-deterministic!**

**Key insight:** Fanin creates a **single queue** that receives messages from multiple sources. The order depends on timing.

### Step 5: Verify Results
```python
print(f"Results: {results}")
# Output might be: ['[merged] A1', '[merged] B1', '[merged] A2', ...]
# Order varies by timing!

assert len(results) == 6  # All 6 messages present
# We have messages from both sources
a_messages = [r for r in results if 'A' in r]
b_messages = [r for r in results if 'B' in r]

assert len(a_messages) == 3  # 3 from source A
assert len(b_messages) == 3  # 3 from source B

print(f"  Messages may be interleaved (order depends on timing)")
```

**Important:** We verify that ALL messages are present, but we DON'T verify the order because it's non-deterministic.

## Running This Example

From the DisSysLab root directory:
```bash
python3 -m examples.module_04_fanin.example
```

**Expected output (order may vary):**
```
Results: ['[merged] A1', '[merged] B1', '[merged] A2', '[merged] B2', '[merged] A3', '[merged] B3']
✓ Fanin completed successfully!
  Source A produced: 3 messages
  Source B produced: 3 messages
  Merger received: 6 messages total
  Messages may be interleaved (order depends on timing)
```

## Key Concepts

### Concept 1: Fanin Merges into One Queue

When multiple sources fan into one destination, **they share a single input queue**:
```
source_A → ─┐
            ├→ [queue] → merger
source_B → ─┘
```

**What this means:**
- Messages from all sources go into ONE queue
- The destination processes messages in queue order
- Queue order = arrival order (which depends on timing)

**Why one queue:**
- Simplifies the destination node (it just reads from one queue)
- Natural load balancing (fast sources don't overwhelm the destination)
- Automatic buffering if destination is slower than sources

### Concept 2: Message Order is Non-Deterministic

**You cannot predict the order** messages arrive when multiple sources fan in:
```python
# Run 1: ['A1', 'A2', 'B1', 'A3', 'B2', 'B3']
# Run 2: ['B1', 'A1', 'B2', 'A2', 'B3', 'A3']
# Run 3: ['A1', 'B1', 'A2', 'B2', 'A3', 'B3']
```

**Why order varies:**
- Sources run in independent threads
- Thread scheduling is non-deterministic
- Network delays, processing speeds vary
- System load affects timing

**Designing for non-deterministic order:**
- ✓ DO: Ensure your logic works regardless of message order
- ✓ DO: Include source information in messages if needed
- ✓ DO: Use timestamps if chronological order matters
- ✗ DON'T: Assume source A always comes before source B

### Concept 3: Fanin Degree (How Many Sources)

**Fanin degree** = number of sources merging into one destination
```python
# Fanin degree 2
network([
    (source1, dest),
    (source2, dest)
])

# Fanin degree 4
network([
    (source1, dest),
    (source2, dest),
    (source3, dest),
    (source4, dest)
])
```

**Considerations:**
- Higher fanin = more sources competing for one queue
- All sources contribute equally (no prioritization by default)
- Destination processing speed becomes the bottleneck

**Typical use cases:**
- Fanin 2-3: Common (merging parallel data streams)
- Fanin 5-10: Reasonable (aggregating from multiple services)
- Fanin 100+: Possible but consider if bottleneck at destination

### Concept 4: Fanin vs. Fanout (The Opposites)

**Fanin (this module):** Multiple sources → One destination
```
source1 ──┐
source2 ──┤→ destination
source3 ──┘
```

**Fanout (Module 03):** One source → Multiple destinations
```
          ┌→ dest1
source ───┤→ dest2
          └→ dest3
```

**When to use each:**
- Use **fanin** when aggregating/collecting from multiple sources
- Use **fanout** when broadcasting to multiple processors

**Combined patterns:**
```
         ┌→ process1 ──┐
source ──┤             ├→ aggregator
         └→ process2 ──┘
         
Fanout then Fanin: Split processing, then merge results
```

### Concept 5: Preserving Source Identity

If you need to know which source a message came from, **add source information to the message**:

**Pattern 1: Tag in source**
```python
def source_A_tagged():
    for item in data_A:
        return {"source": "A", "data": item}

def source_B_tagged():
    for item in data_B:
        return {"source": "B", "data": item}
```

**Pattern 2: Tag in transform before fanin**
```python
network([
    (source_A, tag_A),
    (source_B, tag_B),
    (tag_A, merger),
    (tag_B, merger)
])

def tag_with_A(data):
    return {"source": "A", "data": data}

def tag_with_B(data):
    return {"source": "B", "data": data}
```

**Pattern 3: Use different processing based on source**
```python
# Instead of fanin, use separate paths:
network([
    (source_A, process_A_data),
    (source_B, process_B_data)
])
```

## Common Mistakes

### Mistake 1: Assuming Message Order
```python
# ❌ Wrong - assuming A messages come before B messages
network([
    (source_A, merger),
    (source_B, merger)
])

# Later in code:
first_half = results[:3]  # "These must be from A"
second_half = results[3:]  # "These must be from B"
# WRONG! Order is non-deterministic!
```

**Why it fails:** Sources run concurrently, order depends on timing.  
**Fix:** Don't assume order. Tag messages with source if you need to distinguish them.

### Mistake 2: Not Accounting for All Sources
```python
# ❌ Wrong - expecting only 3 results when there are 2 sources
assert len(results) == 3  # Fails! There are 6 messages (3 from each source)
```

**Why it fails:** Fanin merges ALL messages from ALL sources.  
**Fix:** Count total messages from all sources: 3 + 3 = 6

### Mistake 3: Race Conditions with Shared State
```python
# ❌ Wrong - sources modifying shared state
counter = [0]

def source_A_increment():
    for item in data:
        counter[0] += 1  # Race condition!
        return item

def source_B_increment():
    for item in data:
        counter[0] += 1  # Race condition!
        return item
```

**Why it fails:** Multiple sources modifying shared state without synchronization.  
**Fix:** Keep sources independent, or use thread-safe structures (locks, queues).

### Mistake 4: Trying to Synchronize Sources
```python
# ❌ Wrong - trying to alternate messages from sources
# "I want A1, then B1, then A2, then B2..."
# This is fighting against fanin's natural behavior!
```

**Why it fails:** Fanin doesn't synchronize - it just merges in arrival order.  
**Fix:** If you need synchronized alternation, don't use fanin. Use explicit control logic.

### Mistake 5: Bottleneck at Destination
```python
# ❌ Wrong - slow destination with many fast sources
def slow_processor(data):
    time.sleep(1)  # Very slow!
    return data

# 10 fast sources → 1 slow destination
network([
    (fast_source1, slow_processor),
    (fast_source2, slow_processor),
    # ... (10 total sources)
])
# Queue fills up, sources wait
```

**Why it fails:** Destination becomes a bottleneck if sources are much faster.  
**Fix:** Either speed up the destination, or add multiple parallel destinations.

## Experiments to Try

Modify `example.py` to explore fanin behavior:

### Experiment 1: Add a Third Source

**Add another source:**
```python
source_C_data = ListSource(items=["C1", "C2", "C3"])

source_C = Source(
    fn=source_C_data.run,
    name="source_C"
)
```

**Add to network:**
```python
g = network([
    (source_A, merger),
    (source_B, merger),
    (source_C, merger),  # Third source!
    (merger, collector)
])
```

**What to observe:** Now 9 messages total (3 from each source), all interleaved

### Experiment 2: Different Source Speeds

**Add delays to sources:**
```python
import time

class SlowSource:
    def __init__(self, items):
        self.items = items
        self.index = 0
    
    def run(self):
        if self.index >= len(self.items):
            return None
        time.sleep(0.5)  # Slow!
        item = self.items[self.index]
        self.index += 1
        return item

slow_source = SlowSource(["SLOW1", "SLOW2"])
fast_source = ListSource(items=["FAST1", "FAST2", "FAST3"])
```

**What to observe:** Fast source messages arrive first, slow source messages come later

### Experiment 3: Tag Messages with Source

**Modify sources to tag data:**
```python
class TaggedSource:
    def __init__(self, items, tag):
        self.items = items
        self.tag = tag
        self.index = 0
    
    def run(self):
        if self.index >= len(self.items):
            return None
        item = self.items[self.index]
        self.index += 1
        return f"[{self.tag}] {item}"

source_A = Source(
    fn=TaggedSource(["A1", "A2"], "SOURCE_A").run,
    name="source_A"
)
```

**What to observe:** Can clearly see which source each message came from

### Experiment 4: Count Messages by Source

**Track source counts:**
```python
from collections import Counter

# After running:
source_counts = Counter()
for msg in results:
    if 'A' in msg:
        source_counts['A'] += 1
    elif 'B' in msg:
        source_counts['B'] += 1

print(f"Source A: {source_counts['A']} messages")
print(f"Source B: {source_counts['B']} messages")
```

**What to observe:** Each source contributed equally

### Experiment 5: Fanin with Different Data Types

**Mix different types:**
```python
source_numbers = ListSource(items=[1, 2, 3])
source_strings = ListSource(items=["a", "b", "c"])

def process_mixed(data):
    return f"Processed: {data} (type: {type(data).__name__})"
```

**What to observe:** Fanin works with heterogeneous data types

## Real-World Use Cases

### Use Case 1: Multi-Sensor Aggregation
```python
network([
    (temperature_sensor, data_aggregator),
    (humidity_sensor, data_aggregator),
    (pressure_sensor, data_aggregator)
])
# Collect readings from all sensors
```

### Use Case 2: Log Aggregation
```python
network([
    (web_server_logs, log_processor),
    (database_logs, log_processor),
    (application_logs, log_processor)
])
# Merge logs from multiple services
```

### Use Case 3: Social Media Monitoring
```python
network([
    (twitter_feed, sentiment_analyzer),
    (facebook_feed, sentiment_analyzer),
    (reddit_feed, sentiment_analyzer)
])
# Analyze sentiment across platforms
```

### Use Case 4: Parallel Worker Results
```python
network([
    (worker1_results, result_collector),
    (worker2_results, result_collector),
    (worker3_results, result_collector)
])
# Collect results from parallel workers
```

## Next Steps

You now understand how to merge multiple sources! Combined with fanout (Module 03), you can build complex network topologies.

**Next module:** [Module 05: Complex Patterns](../module_05_complex_patterns/) - Learn how to combine fanin, fanout, filtering, and pipelines into sophisticated networks.

**Try combining patterns:**
- Fanout then fanin (split processing, merge results)
- Multiple fanins (several merge points in one network)
- Fanin with filtering (merge, then filter)

**Want to go deeper?** Read [How It Works](../../docs/HOW_IT_WORKS.md) to understand how DisSysLab manages the shared queue when multiple sources fan in.

## Quick Reference

**Basic fanin pattern:**
```python
network([
    (source1, dest),  # Multiple sources...
    (source2, dest),  # ...to same destination
    (source3, dest)
])
```

**Fanin with processing:**
```python
network([
    (source1, merger),
    (source2, merger),
    (merger, sink)
])
```

**Remember:**
- Multiple sources share ONE input queue at destination
- Message order is non-deterministic (depends on timing)
- All messages from all sources are processed
- Tag messages if you need to know which source sent them
- Fanin = same destination appears multiple times as edge end

---

**Questions or stuck?** Review the "Common Mistakes" section or check [Troubleshooting](../../docs/troubleshooting.md).