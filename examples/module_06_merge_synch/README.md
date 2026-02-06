# Module 06: Merge Synch - Synchronized Message Merging

Learn how to merge messages from multiple parallel paths while maintaining synchronization and message pairing.

# What You'll Learn

- How to merge results from parallel processing paths(merge_synch pattern)
- The difference between merge_synch and fanin
- How to maintain message synchronization across paths
- How to use input port references(`merger.in_0`, `merger.in_1`)
- How MergeSynch waits for all inputs before producing output

# The Problem We're Solving

Sometimes you need to process the same data in multiple different ways and then recombine the results:
- Process an image for thumbnail AND extract metadata, then pair them together
- Analyze text for sentiment AND extract keywords, then combine insights
- Validate data AND enrich it, then merge validated + enriched versions
- Run multiple ML models on same input, then ensemble the predictions

**Fanin ** (Module 04) merges messages from different sources - messages aren't related.  
**MergeSynch** merges results from the SAME original message - they must stay paired!

## Network Topology

Our example processes each word in two ways, then merges the results:
```
                    → uppercase → "HELLO" ──┐
                   ↗                        │
"hello" ──────────┤                         ├──→ merge_synch → ("hello", "HELLO", 5)
                   ↘                        │
                    → length → 5 ───────────┘
```

**Key insight:** The original "hello" fans out to two processing paths. MergeSynch waits for BOTH results, then combines them: original + uppercase + length = one merged output.

## The Code Walkthrough

### Step 1: Write Ordinary Python Functions
```python
word_source = ListSource(items=["hello", "world", "python"])

def to_uppercase(text):
    """Convert text to uppercase."""
    return text.upper()

def get_length(text):
    """Get length of text."""
    return len(text)

def format_result(merged_data):
    """
    Format the merged data into a tuple.
    
    Args:
        merged_data: List of [original, uppercase, length]
    
    Returns:
        Tuple of (original, uppercase, length)
    """
    return tuple(merged_data)
```

**What's happening:**
- Two independent processing functions: `to_uppercase` and `get_length`
- Neither function knows about the other
- `format_result` receives the merged data as a list and formats it

**The power of merge_synch:** Process data multiple ways in parallel, then automatically recombine results in the correct order.

### Step 2: Wrap Functions into Network Nodes
```python
source = Source(
    fn=word_source.run,
    name="word_source"
)

uppercase_transform = Transform(
    fn=to_uppercase,
    name="uppercase"
)

length_transform = Transform(
    fn=get_length,
    name="length"
)

merger = MergeSynch(
    num_inputs=3,  # Will receive: original + uppercase + length
    name="merge_synch"
)

formatter = Transform(
    fn=format_result,
    name="formatter"
)

results = []
collector = Sink(
    fn=results.append,
    name="collector"
)
```

**Critical detail:** `num_inputs=3` tells MergeSynch to wait for 3 inputs before producing output. This MUST match the number of connections to the merger.

**What MergeSynch creates:**
- `merger.in_0` - First input port
- `merger.in_1` - Second input port
- `merger.in_2` - Third input port

These are **input port references** you use when building the network.

### Step 3: Define the Network Topology

**This is where MergeSynch's port references are used:**
```python
g = network([
    # Source fans out to two transforms
    (source, uppercase_transform),
    (source, length_transform),
    
    # Both transforms AND original connect to merger
    (source, merger.in_0),                    # Original text
    (uppercase_transform, merger.in_1),       # Uppercase result
    (length_transform, merger.in_2),          # Length result
    
    # Merger output goes to formatter, then collector
    (merger, formatter),
    (formatter, collector)
])
```

**The topology explained:**

1. **Fanout from source:** Source sends to uppercase_transform, length_transform, AND merger.in_0
2. **Parallel processing:** Both transforms process independently
3. **Fanin to merger:** All three results (original, uppercase, length) go to merger inputs
4. **Synchronized merge:** Merger waits for all 3, then outputs a list
5. **Format and collect:** Formatter converts list to tuple, collector stores it

**Visual flow for "hello":**
```
source produces "hello"
  ├→ merger.in_0 receives "hello" (waits...)
  ├→ uppercase processes → "HELLO" → merger.in_1 receives "HELLO" (waits...)
  └→ length processes → 5 → merger.in_2 receives 5 (all inputs ready!)
  
merger outputs ["hello", "HELLO", 5]
formatter converts to ("hello", "HELLO", 5)
collector stores ("hello", "HELLO", 5)
```

### Step 4: Run the Network
```python
g.run_network()
```

**What happens during execution:**

**Message 1: "hello"**
- Source produces "hello"
- Splits 3 ways: → uppercase, → length, → merger.in_0
- merger.in_0 receives "hello" immediately, WAITS for other inputs
- uppercase processes: "hello" → "HELLO" → merger.in_1
- length processes: "hello" → 5 → merger.in_2
- merger now has all 3 inputs for message 1: ["hello", "HELLO", 5]
- merger outputs the list
- formatter converts to tuple: ("hello", "HELLO", 5)
- collector stores it

**Message 2: "world"**
- Same process repeats
- merger waits for all 3 inputs for this message
- Outputs ["world", "WORLD", 5]

**Message 3: "python"**
- Same process
- Outputs ["python", "PYTHON", 6]

**Key behavior:** MergeSynch WAITS until it receives a message on ALL input ports for the same original message before producing output. This maintains synchronization.

### Step 5: Verify Results
```python
print("Results:", results)
# Output: Results: [('hello', 'HELLO', 5), ('world', 'WORLD', 5), ('python', 'PYTHON', 6)]

expected = [
    ("hello", "HELLO", 5),
    ("world", "WORLD", 5),
    ("python", "PYTHON", 6)
]

assert results == expected

print("✓ Merge Synch completed successfully!")
for original, upper, length in results:
    print(f"    '{original}' → '{upper}' (length: {length})")
```

## Running This Example

From the DisSysLab root directory:
```bash
python3 -m examples.module_06_merge_synch.example
```

**Expected output:**
```
Results: [('hello', 'HELLO', 5), ('world', 'WORLD', 5), ('python', 'PYTHON', 6)]
✓ Merge Synch completed successfully!
  Each word was processed in parallel:
    'hello' → 'HELLO' (length: 5)
    'world' → 'WORLD' (length: 5)
    'python' → 'PYTHON' (length: 6)
```

## Key Concepts

### Concept 1: MergeSynch vs. Fanin

**MergeSynch (this module):** Merges results from SAME original message
```
Message M splits:
  → process_A(M) → result_A ──┐
  → process_B(M) → result_B ──┤→ merge → [result_A, result_B]
  → original M ────────────────┘

All three are paired together for the SAME message M
```

**Fanin (Module 04):** Merges messages from DIFFERENT sources
```
Source A → msg_A1, msg_A2 ──┐
                            ├→ merge → [msg_A1, msg_B1, msg_A2, msg_B2, ...]
Source B → msg_B1, msg_B2 ──┘

Messages are independent, no pairing
```

**When to use each:**
- Use **MergeSynch** when results must stay paired (same input, multiple processes)
- Use **Fanin** when merging independent streams (different sources)

### Concept 2: Synchronization - Waiting for All Inputs

MergeSynch **blocks** until it receives messages on ALL input ports for the same original message:
```python
# MergeSynch with 3 inputs

Time 0: merger.in_0 receives "hello" → WAITS
Time 1: merger.in_1 receives "HELLO" → WAITS (still need in_2)
Time 2: merger.in_2 receives 5 → ALL READY!
Time 3: merger outputs ["hello", "HELLO", 5]
```

**Why this matters:**
- Ensures results from all parallel paths are combined
- Prevents incomplete data from passing through
- Maintains message integrity across paths

**What if one path is slow?**
- Merger waits for the slowest path
- Output rate = rate of slowest input
- This is intentional - we need ALL results before proceeding

### Concept 3: Input Port References

MergeSynch creates **numbered input ports** you reference in the network definition:
```python
merger = MergeSynch(num_inputs=3, name="merger")

# DisSysLab automatically creates:
# - merger.in_0
# - merger.in_1
# - merger.in_2

# Use them in network definition:
network([
    (source1, merger.in_0),      # Connect to port 0
    (source2, merger.in_1),      # Connect to port 1
    (source3, merger.in_2)       # Connect to port 2
])
```

**Important:** 
- Port numbers start at 0
- Must have exactly `num_inputs` connections
- Order matters: in_0 is first in the output list, in_1 is second, etc.

### Concept 4: Output Format

MergeSynch outputs a **list** containing one element from each input port, in order:
```python
# With num_inputs=3:
merger.in_0 receives: "hello"
merger.in_1 receives: "HELLO"
merger.in_2 receives: 5

# MergeSynch outputs:
["hello", "HELLO", 5]
# Index 0 = in_0, Index 1 = in_1, Index 2 = in_2
```

**Processing the merged output:**
```python
def process_merged(data):
    original = data[0]    # From in_0
    uppercase = data[1]   # From in_1
    length = data[2]      # From in_2
    return f"{original} -> {uppercase} ({length} chars)"
```

Or unpack it:
```python
def process_merged(data):
    original, uppercase, length = data
    return f"{original} -> {uppercase} ({length} chars)"
```

### Concept 5: Common Network Patterns with MergeSynch

**Pattern 1: Fanout → Process → MergeSynch**
```
source ──┬→ process_A ──┐
         │              ├→ merger
         └→ process_B ──┘
```

**Pattern 2: Preserve Original + Processed**
```
source ──┬→ merger.in_0 (original) ──┐
         │                           ├→ merger
         └→ process → merger.in_1 ───┘
```

**Pattern 3: Multiple Processing Stages**
```
source ──┬→ process_A → merger.in_0 ──┐
         │                            ├→ merger
         ├→ process_B → merger.in_1 ──┤
         │                            │
         └→ process_C → merger.in_2 ──┘
```

**Pattern 4: Ensemble ML Models**
```
data ──┬→ model_A ──┐
       ├→ model_B ──┤
       ├→ model_C ──┤→ merger → average_predictions
       └→ model_D ──┘
```

## Common Mistakes

### Mistake 1: Wrong Number of Inputs
```python
# ❌ Wrong - declared 3 inputs but only connected 2
merger = MergeSynch(num_inputs=3, name="merger")

network([
    (source, merger.in_0),
    (process, merger.in_1)
    # Missing merger.in_2 connection!
])
```

**Why it fails:** MergeSynch waits forever for the missing third input.  
**Fix:** Ensure `num_inputs` matches the number of connections to merger ports.

### Mistake 2: Connecting to Merger Without Port Reference
```python
# ❌ Wrong - trying to connect directly to merger
network([
    (source, merger)  # ERROR! Which input port?
])

# ✓ Correct - use port reference
network([
    (source, merger.in_0)
])
```

**Why it fails:** MergeSynch has multiple input ports - you must specify which one.  
**Fix:** Always use `merger.in_N` to reference specific input ports.

### Mistake 3: Expecting Immediate Output
```python
# ❌ Wrong assumption - thinking merger outputs as soon as in_0 receives
merger = MergeSynch(num_inputs=2)

# After in_0 receives message, expecting output
# But merger WAITS for in_1!
```

**Why it fails:** MergeSynch blocks until ALL inputs are ready.  
**Fix:** Design expecting delays - merger is as fast as slowest input path.

### Mistake 4: Wrong Port Order
```python
# Setup expects: [original, processed]
network([
    (source, merger.in_0),      # Original
    (processor, merger.in_1)    # Processed
])

# ❌ Wrong - processing merged data in wrong order
def handle_merged(data):
    processed = data[0]   # WRONG! This is original
    original = data[1]    # WRONG! This is processed
```

**Why it fails:** Port order matters - in_0 is first in list, in_1 is second.  
**Fix:** Remember that `data[i]` corresponds to `merger.in_i`.

### Mistake 5: Not Handling Slow Paths
```python
# ❌ Wrong - not considering path speed differences
network([
    (source, fast_process),       # Completes in 0.1s
    (source, slow_process),       # Completes in 10s
    (fast_process, merger.in_0),
    (slow_process, merger.in_1)
])

# Merger outputs at 10s intervals (limited by slow_process)
```

**Why it fails:** Not necessarily wrong, but might not be what you expected. Merger waits for slowest path.  
**Fix:** Be aware of path speeds. Consider optimizing slow paths or using different topology if speed matters.

## Experiments to Try

Modify `example.py` to explore merge_synch behavior:

### Experiment 1: Add Another Processing Path

**Add a third transform:**
```python
def count_vowels(text):
    return sum(1 for c in text.lower() if c in 'aeiou')

vowel_counter = Transform(
    fn=count_vowels,
    name="vowel_counter"
)

merger = MergeSynch(num_inputs=4, name="merger")  # Now 4 inputs!

network([
    (source, uppercase_transform),
    (source, length_transform),
    (source, vowel_counter),
    (source, merger.in_0),
    (uppercase_transform, merger.in_1),
    (length_transform, merger.in_2),
    (vowel_counter, merger.in_3)
])
```

**What to observe:** Now get (original, uppercase, length, vowel_count)

### Experiment 2: Different Input Speeds

**Add delays to simulate slow processing:**
```python
import time

def slow_uppercase(text):
    time.sleep(0.5)  # Simulate slow processing
    return text.upper()

def fast_length(text):
    return len(text)
```

**What to observe:** Merger waits for slow_uppercase before outputting

### Experiment 3: Preserve Multiple Originals

**Send original to multiple ports:**
```python
network([
    (source, merger.in_0),      # Original copy 1
    (source, process),
    (source, merger.in_2),      # Original copy 2
    (process, merger.in_1)
])
```

**What to observe:** Can have duplicates in the merged output

### Experiment 4: Add Print Statements

**Track synchronization:**
```python
def uppercase_with_log(text):
    result = text.upper()
    print(f"  Uppercase done: {text} -> {result}")
    return result

def length_with_log(text):
    result = len(text)
    print(f"  Length done: {text} -> {result}")
    return result
```

**What to observe:** See when each path completes and when merger outputs

### Experiment 5: Chain Multiple MergeSynch Nodes

**Create hierarchical merging:**
```python
merger1 = MergeSynch(num_inputs=2, name="merger1")
merger2 = MergeSynch(num_inputs=2, name="merger2")
final_merger = MergeSynch(num_inputs=2, name="final")

network([
    (source, process_A),
    (source, process_B),
    (process_A, merger1.in_0),
    (process_B, merger1.in_1),
    
    (source, process_C),
    (source, process_D),
    (process_C, merger2.in_0),
    (process_D, merger2.in_1),
    
    (merger1, final_merger.in_0),
    (merger2, final_merger.in_1)
])
```

**What to observe:** Nested merging for complex combinations

## Real-World Use Cases

### Use Case 1: Image Processing Pipeline
```python
network([
    (image_source, create_thumbnail),
    (image_source, extract_metadata),
    (image_source, merger.in_0),         # Original
    (create_thumbnail, merger.in_1),      # Thumbnail
    (extract_metadata, merger.in_2)       # Metadata
])
# Output: [original_image, thumbnail, metadata] all paired together
```

### Use Case 2: Text Analysis
```python
network([
    (text_source, sentiment_analyzer),
    (text_source, keyword_extractor),
    (text_source, language_detector),
    (sentiment_analyzer, merger.in_0),
    (keyword_extractor, merger.in_1),
    (language_detector, merger.in_2)
])
# Output: [sentiment, keywords, language] for each text
```

### Use Case 3: ML Model Ensemble
```python
network([
    (data_source, model_A),
    (data_source, model_B),
    (data_source, model_C),
    (model_A, merger.in_0),
    (model_B, merger.in_1),
    (model_C, merger.in_2),
    (merger, ensemble_predictor)  # Combines all predictions
])
```

### Use Case 4: Data Validation + Enrichment
```python
network([
    (raw_data, validator),
    (raw_data, enricher),
    (raw_data, merger.in_0),      # Original data
    (validator, merger.in_1),      # Validation result
    (enricher, merger.in_2),       # Enriched data
    (merger, final_processor)      # Process all together
])
```

## Next Steps

You now understand how to synchronize and merge results from parallel processing paths! MergeSynch is essential for ensemble processing and maintaining data integrity.

**What's next:** You've learned all the fundamental patterns (basics, filtering, fanout, fanin, split, merge_synch). The next modules will combine these patterns to build complex, real-world networks.

**Try combining merge_synch with other patterns:**
- Fanout → MergeSynch (parallel processing then recombine)
- Split → MergeSynch (route to different processors, merge results)
- Multiple MergeSynch nodes (hierarchical merging)

**Want to go deeper?** Read [How It Works](../../docs/HOW_IT_WORKS.md) to understand how DisSysLab implements synchronization across parallel paths.

## Quick Reference

**Basic merge_synch pattern:**
```python
merger = MergeSynch(num_inputs=3, name="merger")

network([
    (source, process1),
    (source, process2),
    (source, merger.in_0),
    (process1, merger.in_1),
    (process2, merger.in_2)
])

# Merger outputs: [msg_from_in_0, msg_from_in_1, msg_from_in_2]
```

**Processing merged output:**
```python
def handle_merged(merged_list):
    original, result1, result2 = merged_list
    # Process the synchronized results
    return combined_result
```

**Remember:**
- MergeSynch waits for ALL inputs before producing output
- Use input port references: `merger.in_0`, `merger.in_1`, etc.
- Output is a list in port order: [in_0, in_1, in_2, ...]
- MergeSynch ≠ Fanin (synch merges related messages, fanin merges independent streams)
- Number of connections must equal `num_inputs`

---

**Questions or stuck?** Review the "Common Mistakes" section or check [Troubleshooting](../../docs/troubleshooting.md).