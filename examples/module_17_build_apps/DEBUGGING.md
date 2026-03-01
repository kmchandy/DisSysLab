# DEBUGGING.md - Troubleshooting Your DisSysLab Apps

**When things don't work, this guide helps you fix them.**

Debugging distributed systems is different from debugging sequential programs. This guide shows you systematic strategies for finding and fixing problems in your DisSysLab networks.

---

## Table of Contents

1. [The Debugging Mindset](#the-debugging-mindset)
2. [Quick Diagnostic Checklist](#quick-diagnostic-checklist)
3. [Common Error Messages](#common-error-messages)
4. [Debugging by Component](#debugging-by-component)
5. [Testing Strategies](#testing-strategies)
6. [Debugging Tools & Techniques](#debugging-tools--techniques)
7. [Performance Issues](#performance-issues)
8. [When to Ask for Help](#when-to-ask-for-help)

---

## The Debugging Mindset

### **Rule 1: Build and Test Incrementally**

**Never build the whole network at once!** Add one piece at a time, test after each addition.

```python
# Step 1: Source only
g = network([])
source = MySource()
# Test source...

# Step 2: Source → Transform
g = network([(source_node, transform_node)])
g.run_network()
# Test this...

# Step 3: Source → Transform → Sink
g = network([
    (source_node, transform_node),
    (transform_node, sink_node)
])
g.run_network()
# Test this...
```

### **Rule 2: Isolate, Don't Integrate**

When something breaks, **test each piece separately before debugging the network.**

✅ **Do this:** Test each piece separately
```python
# Test source alone
source = MySource()
for i in range(5):
    item = source.run()
    print(f"Got: {item}")
    if item is None:
        break
```

❌ **Don't do this:** Try to debug the whole network
```python
# Too complex - can't tell what's broken
g = network([
    (source1, transform1), (source2, transform1),
    (transform1, transform2), (transform2, transform3),
    (transform3, sink1), (transform3, sink2)
])
g.run_network()  # Something's wrong... but what?
```

### **Rule 3: Monitor Edges, Not Everything**

**Don't add print statements everywhere!** This creates overwhelming log output when you have many agents running concurrently.

Instead, **monitor specific edges** where you suspect problems.

✅ **Do this:** Add a logger node to monitor specific connections
```python
from dsl.blocks import Transform

def create_logger(log_file="debug.log", max_messages=100, label=""):
    """
    Create a logger transform that logs messages passing through.
    
    Args:
        log_file: Where to write logs
        max_messages: Stop logging after this many (prevents huge logs)
        label: Prefix for log messages
    """
    count = [0]  # Use list to modify in nested function
    
    def logger(item):
        if count[0] < max_messages:
            count[0] += 1
            with open(log_file, 'a') as f:
                f.write(f"[{label}] Message {count[0]}: {item}\n")
        return item  # Pass through unchanged
    
    return Transform(fn=logger, name=f"logger_{label}")

# Monitor the edge between source and transform
logger_node = create_logger(
    log_file="edge_debug.log",
    max_messages=50,
    label="source→transform"
)

# Original network (suspected problem):
# g = network([
#     (source, transform),
#     (transform, sink)
# ])

# Modified network with logger:
g = network([
    (source, logger_node),      # ← Add logger here
    (logger_node, transform),   # ← Continue to transform
    (transform, sink)
])

g.run_network()

# Check edge_debug.log to see what passed through
```

**Why this is better:**
- Logs only specific edges you care about
- Limits output (max_messages prevents GB of logs)
- Doesn't clutter your code with print statements
- Easy to add/remove for different edges
- All agents can run without overwhelming output

**Monitor multiple edges:**
```python
logger1 = create_logger(log_file="edge1.log", label="source→filter")
logger2 = create_logger(log_file="edge2.log", label="filter→sink")

g = network([
    (source, logger1),
    (logger1, filter_node),
    (filter_node, logger2),
    (logger2, sink)
])
```

**After debugging, remove the loggers:**
```python
# Back to original network
g = network([
    (source, filter_node),
    (filter_node, sink)
])
```

❌ **Don't do this:** Add print statements everywhere
```python
def transform1(item):
    print(f"transform1 got: {item}")  # ← Too much output!
    result = process(item)
    print(f"transform1 returns: {result}")
    return result

def transform2(item):
    print(f"transform2 got: {item}")  # ← More output!
    # ... 10 more transforms all printing ...
```

**Problem:** With 10 agents each processing 100 messages, you get 1000+ log lines. Impossible to read!

### **Rule 4: Check Your Assumptions**

Common assumptions that are often wrong:
- "The source is definitely producing data" (is it?)
- "The transform is definitely being called" (is it?)
- "The file path is correct" (is it?)
- "The API credentials work" (do they?)

**Always verify!** Add print statements to check.

---

## Quick Diagnostic Checklist

**Start here when something's not working:**

### ☐ **Is the network running at all?**

**Note:** Some networks are **persistent** - they run forever and never finish. Examples:
- Social media sentiment analysis (continuous stream)
- Real-time monitoring systems
- Server applications
- Event processing systems

For **terminating networks** (file processing, batch jobs):
```python
print("Starting network...")
g.run_network()
print("Network finished!")  # ← You'll see this when done
```
- If you don't see "Network finished!" → network hung or crashed
- If you see both messages immediately → network ran but did nothing

For **persistent networks** (streams, monitors):
```python
print("Starting network...")
g.run_network()
# This line may never execute! Network runs forever.
```
- Monitor the output/logs to verify the network is processing data
- Use Ctrl+C to stop when done
- Or set a `max_items` or `lifetime` limit for testing

**How to tell if your network should terminate:**
- **Terminates:** File sources, fixed lists, batch processing
- **Persistent:** WebSocket streams (BlueSky Jetstream), monitoring, servers

**Testing persistent networks:**
```python
# Add limits for testing
source = BlueSkyJetstream(
    max_posts=10,      # ← Stop after 10 posts
    lifetime=30        # ← Or stop after 30 seconds
)
```

### ☐ **Is the source producing data?**
```python
# Test source alone
source = MySource()
count = 0
while True:
    item = source.run()
    if item is None:
        break
    print(f"{count}: {item}")
    count += 1
print(f"Source produced {count} items")
```
- If count is 0 → source isn't working
- If source never returns None → infinite loop

### ☐ **Are transforms being called?**
```python
def my_transform(item):
    print(f"Transform called with: {item}")  # ← Add this
    return process(item)
```
- If you don't see "Transform called" → transform not connected properly
- If you see it → transform is working, check the logic

### ☐ **Is the sink receiving data?**
```python
def my_sink(item):
    print(f"Sink received: {item}")  # ← Add this
    save(item)
```
- If you don't see "Sink received" → data not reaching sink
- If you see it → sink is working, check finalize()

### ☐ **Did you call finalize()?**
```python
g.run_network()
my_sink.finalize()  # ← Don't forget this!
```
- Many sinks buffer data and write in finalize()
- Without finalize(), you won't see output

### ☐ **Are edges in the right direction?**
```python
# ❌ Wrong
network([(sink, source)])  # Backwards!

# ✅ Correct
network([(source, sink)])  # Data flows forward
```

---

## Common Error Messages

### **Error: "NameError: name 'network' is not defined"**

**Problem:** Forgot to import

**Solution:**
```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
```

---

### **Error: "TypeError: ... missing 1 required positional argument"**

**Problem:** Your function needs parameters you didn't provide

**Example:**
```python
def add_suffix(text, suffix):  # Needs 2 args
    return text + suffix

# ❌ Wrong
transform = Transform(fn=add_suffix, name="add")
# Error: missing argument 'suffix'
```

**Solution:** Use `params` to provide extra arguments
```python
# ✅ Correct
transform = Transform(
    fn=add_suffix,
    params={"suffix": "!!"},  # ← Provide the extra argument
    name="add"
)
```

---

### **Error: "AttributeError: 'NoneType' object has no attribute..."**

**Problem:** A transform returned `None` when it shouldn't, or a source/sink is None

**Common causes:**
1. Transform filtered out an item by returning `None`, but next node expected data
2. Forgot to create a source/sink object
3. Source returned `None` too early

**Solution 1:** Check your transform logic
```python
def my_transform(item):
    if item['value'] > 10:
        return item
    # ❌ Implicit return None for values <= 10
    # Next node will get None and crash!
```

**Solution 2:** Make sure objects are created
```python
# ❌ Wrong
source = None  # Forgot to create it
source_node = Source(fn=source.run, name="source")  # Crash!

# ✅ Correct
source = MySource()  # Create the object first
source_node = Source(fn=source.run, name="source")
```

---

### **Error: "FileNotFoundError: No such file or directory"**

**Problem:** File path is wrong

**Solution:** Check the path, use absolute paths, or verify file exists
```python
import os

filepath = "data.csv"
if not os.path.exists(filepath):
    print(f"File not found: {filepath}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Files here: {os.listdir('.')}")
```

---

### **Error: Network runs but produces no output**

**Problem:** Multiple possible causes

**Diagnostic steps:**

**1. Check if source is producing:**
```python
source = MySource()
print(f"First item: {source.run()}")
print(f"Second item: {source.run()}")
```

**2. Check if transforms are filtering everything:**
```python
def my_filter(item):
    print(f"Filter got: {item}")
    result = item if item['status'] == 'active' else None
    print(f"Filter returned: {result}")
    return result
```

**3. Check if sink is collecting:**
```python
class MySink:
    def __init__(self):
        self.items = []
    
    def run(self, item):
        print(f"Sink got: {item}")  # ← Add this
        self.items.append(item)
    
    def finalize(self):
        print(f"Sink collected {len(self.items)} items")  # ← Add this
```

**4. Verify you called finalize:**
```python
g.run_network()
sink.finalize()  # ← Must call this!
print(f"Results: {sink.items}")
```

---

### **Error: "ImportError: cannot import name..."**

**Problem:** Trying to import something that doesn't exist

**Common causes:**
1. Typo in import name
2. File doesn't exist in that location
3. Circular import

**Solution:**
```python
# Check what's available
import components.sources
print(dir(components.sources))

# Check file exists
import os
print(os.path.exists("components/sources/my_source.py"))
```

---

### **Error: Network hangs (never finishes)**

**Problem:** Source never returns `None`, or infinite loop somewhere

**Diagnostic:**
```python
# Add timeout
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Network took too long!")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)  # 10 second timeout

try:
    g.run_network()
    signal.alarm(0)  # Cancel timeout
except TimeoutError:
    print("Network hung! Check if source returns None.")
```

**Common causes:**
```python
# ❌ Source never returns None
class BrokenSource:
    def run(self):
        return "data"  # Always returns something - never stops!

# ✅ Source returns None eventually
class WorkingSource:
    def __init__(self):
        self.count = 0
    
    def run(self):
        if self.count < 10:
            self.count += 1
            return f"item {self.count}"
        return None  # ← Stops after 10 items
```

---

## Debugging by Component

### Debugging Sources

**Symptom:** No data flowing through network

**Test the source alone:**
```python
source = MySource()

print("Testing source...")
items = []
for i in range(20):  # Safety limit
    item = source.run()
    if item is None:
        print(f"✓ Source stopped after {len(items)} items")
        break
    items.append(item)
    print(f"  {i+1}. {item}")
else:
    print("⚠️ Source didn't stop after 20 items!")

if len(items) == 0:
    print("❌ Source produced no data!")
```

**Common source problems:**

**Problem 1: Source returns None immediately**
```python
class BrokenSource:
    def __init__(self):
        self.data = ["a", "b", "c"]
        self.n = len(self.data)  # ❌ Starts at end!
    
    def run(self):
        if self.n < len(self.data):
            item = self.data[self.n]
            self.n += 1
            return item
        return None  # Returns None immediately!

# ✅ Fix: Start at 0
self.n = 0
```

**Problem 2: Source never returns None**
```python
class BrokenSource:
    def run(self):
        return "data"  # ❌ Always returns something

# ✅ Fix: Add stopping condition
class FixedSource:
    def __init__(self):
        self.count = 0
    
    def run(self):
        if self.count < 10:
            self.count += 1
            return f"item {self.count}"
        return None  # ← Stops
```

**Problem 3: Source crashes**
```python
# Add error handling
class RobustSource:
    def run(self):
        try:
            # Your source logic
            return fetch_data()
        except Exception as e:
            print(f"Source error: {e}")
            return None  # Stop on error
```

---

### Debugging Transforms

**Symptom:** Data enters but doesn't come out correctly

**Test the transform alone:**
```python
def my_transform(item):
    return item.upper()

# Test with sample data
test_items = ["hello", "world", None]
for item in test_items:
    result = my_transform(item) if item else None
    print(f"{item} → {result}")
```

**Common transform problems:**

**Problem 1: Transform returns None accidentally**
```python
def broken_transform(item):
    item['new_field'] = "value"
    # ❌ Forgot to return item!

# ✅ Fix
def fixed_transform(item):
    item['new_field'] = "value"
    return item  # ← Must return!
```

**Problem 2: Transform crashes on unexpected data**
```python
def broken_transform(item):
    return item['field'].upper()  # ❌ Crashes if 'field' missing

# ✅ Fix: Add error handling
def fixed_transform(item):
    try:
        return item['field'].upper()
    except KeyError:
        print(f"Warning: 'field' missing in {item}")
        return None  # Filter out bad items
    except Exception as e:
        print(f"Transform error: {e}")
        return None
```

**Problem 3: Transform modifies shared state incorrectly**
```python
# ❌ Wrong: Modifying shared list
results = []
def broken_transform(item):
    results.append(item)  # Side effect!
    return item

# ✅ Better: Each item is independent
def fixed_transform(item):
    # Just transform and return
    return item.upper()
```

---

### Debugging Sinks

**Symptom:** Data reaches sink but isn't saved/displayed

**Test the sink alone:**
```python
sink = MySink()

# Send test data
sink.run({"test": 1})
sink.run({"test": 2})
sink.run({"test": 3})

# Finalize
sink.finalize()

# Check results
print(f"Sink collected: {sink.items}")
```

**Common sink problems:**

**Problem 1: Forgot to call finalize()**
```python
class BufferingSink:
    def __init__(self):
        self.buffer = []
    
    def run(self, item):
        self.buffer.append(item)  # Buffered
    
    def finalize(self):
        save_to_file(self.buffer)  # ← Only writes here!

# ❌ Wrong
g.run_network()
# File is empty! Forgot finalize()

# ✅ Correct
g.run_network()
sink.finalize()  # ← Now file has data
```

**Problem 2: Sink crashes silently**
```python
class BrokenSink:
    def run(self, item):
        self.file.write(item)  # ❌ Crashes if file not open
    
    def finalize(self):
        pass

# ✅ Fix: Add error handling and logging
class FixedSink:
    def __init__(self):
        self.errors = 0
    
    def run(self, item):
        try:
            self.file.write(json.dumps(item))
        except Exception as e:
            print(f"Sink error: {e}")
            self.errors += 1
    
    def finalize(self):
        if self.errors > 0:
            print(f"⚠️ Sink had {self.errors} errors")
```

**Problem 3: File sink creates empty files**
```python
class BrokenFileSink:
    def __init__(self, filepath):
        self.file = open(filepath, 'w')  # Opens immediately
    
    def run(self, item):
        self.file.write(json.dumps(item))
        # ❌ Forgot to flush or newline!
    
    def finalize(self):
        self.file.close()

# ✅ Fix: Flush and add newlines
class FixedFileSink:
    def run(self, item):
        self.file.write(json.dumps(item) + '\n')  # ← Add newline
        self.file.flush()  # ← Force write
```

---

### Debugging Networks

**Symptom:** Edges not connecting properly, data not flowing

**Visualize your network:**
```python
def print_network(edges):
    print("Network topology:")
    for from_node, to_node in edges:
        print(f"  {from_node.name} → {to_node.name}")

edges = [
    (source_node, transform_node),
    (transform_node, sink_node)
]

print_network(edges)
# Output:
#   source → transform
#   transform → sink
```

**Common network problems:**

**Problem 1: Edges in wrong direction**
```python
# ❌ Wrong: Backwards
network([
    (sink, transform),     # ← Backwards!
    (transform, source)    # ← Backwards!
])

# ✅ Correct: Forward flow
network([
    (source, transform),
    (transform, sink)
])
```

**Problem 2: Disconnected nodes**
```python
# ❌ Wrong: transform2 is not connected
network([
    (source, transform1),
    (transform1, sink)
    # transform2 exists but isn't in the network!
])

# ✅ Correct: All nodes connected
network([
    (source, transform1),
    (transform1, transform2),  # ← Add this
    (transform2, sink)
])
```

**Problem 3: Forgot to create nodes**
```python
# ❌ Wrong: Passing functions instead of nodes
network([
    (source.run, transform)  # ← source.run is a function!
])

# ✅ Correct: Wrap in nodes first
source_node = Source(fn=source.run, name="source")
transform_node = Transform(fn=transform, name="transform")
network([(source_node, transform_node)])
```

---

## Testing Strategies

### Strategy 1: Unit Test Each Component

Test sources, transforms, and sinks independently before connecting.

```python
def test_source():
    """Test source produces expected data."""
    source = MySource()
    items = []
    while True:
        item = source.run()
        if item is None:
            break
        items.append(item)
    
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    assert items[0]['id'] == 1, "First item should have id=1"
    print("✓ Source test passed")

def test_transform():
    """Test transform processes correctly."""
    result = my_transform({"value": 10})
    assert result['value'] == 20, "Should double the value"
    
    result = my_transform({"value": -5})
    assert result is None, "Should filter negative values"
    print("✓ Transform test passed")

def test_sink():
    """Test sink collects data."""
    sink = MySink()
    sink.run({"test": 1})
    sink.run({"test": 2})
    sink.finalize()
    
    assert len(sink.items) == 2, "Should collect 2 items"
    print("✓ Sink test passed")

# Run all tests
test_source()
test_transform()
test_sink()
```

### Strategy 2: Test with Small Data First

Start with 2-3 items, not 1000.

```python
# ❌ Don't start with this
source = BigDataSource(items=range(10000))

# ✅ Start with this
source = SmallDataSource(items=["a", "b", "c"])
```

### Strategy 3: Add Assertions

Verify your assumptions with assertions.

```python
def my_transform(item):
    assert isinstance(item, dict), f"Expected dict, got {type(item)}"
    assert 'id' in item, f"Item missing 'id': {item}"
    
    result = process(item)
    
    assert result is not None, "Process returned None!"
    return result
```

### Strategy 4: Use Mock Data

Create fake data that's easy to verify.

```python
# ✅ Good test data: predictable, easy to check
test_data = [
    {"id": 1, "value": 10},
    {"id": 2, "value": 20},
    {"id": 3, "value": 30}
]

# After processing, you know what to expect:
# If transform doubles values:
#   → [{"id": 1, "value": 20}, ...]
```

---

## Debugging Tools & Techniques

### Technique 1: Add Print Statements Everywhere

```python
def logged_transform(item):
    print(f"→ IN:  {item}")
    result = process(item)
    print(f"← OUT: {result}")
    return result
```

### Technique 2: Count Messages

```python
class CountingSink:
    def __init__(self):
        self.count = 0
        self.items = []
    
    def run(self, item):
        self.count += 1
        print(f"Received item #{self.count}")
        self.items.append(item)
    
    def finalize(self):
        print(f"Total received: {self.count}")
```

### Technique 3: Use Python Debugger

```python
def my_transform(item):
    import pdb; pdb.set_trace()  # ← Pause here
    result = process(item)
    return result

# When network runs, it will pause at this transform
# Commands:
#   n - next line
#   s - step into
#   p variable - print variable
#   c - continue
#   q - quit
```

### Technique 4: Log to File

```python
import logging

logging.basicConfig(
    filename='network.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(message)s'
)

def my_transform(item):
    logging.info(f"Processing: {item}")
    result = process(item)
    logging.info(f"Result: {result}")
    return result

# After running, check network.log
```

### Technique 5: Verify Data Types

```python
def type_checking_transform(item):
    print(f"Type: {type(item)}")
    print(f"Value: {item}")
    
    if not isinstance(item, dict):
        print(f"⚠️ Expected dict, got {type(item)}")
        return None
    
    return process(item)
```

---

## Performance Issues

### Issue: Network is slow

**Diagnostic:**
```python
import time

def timed_transform(item):
    start = time.time()
    result = process(item)
    elapsed = time.time() - start
    
    if elapsed > 0.1:  # Slow!
        print(f"⚠️ Slow transform: {elapsed:.2f}s for {item}")
    
    return result
```

**Common causes:**
1. Transform doing too much work
2. Network I/O in transform (API calls, database)
3. Large data being copied

**Solutions:**
- Break complex transform into simpler steps
- Move I/O to sources/sinks
- Process in batches
- Add caching

---

### Issue: Network uses too much memory

**Diagnostic:**
```python
import sys

class MemorySink:
    def __init__(self):
        self.items = []
    
    def run(self, item):
        self.items.append(item)
        
        if len(self.items) % 1000 == 0:
            size = sys.getsizeof(self.items)
            print(f"Collected {len(self.items)} items, {size} bytes")
```

**Common causes:**
1. Collecting all data in memory (sink with huge list)
2. Not releasing resources
3. Circular references

**Solutions:**
- Write to file incrementally instead of buffering
- Use generators instead of lists
- Clear data after processing

---

## When to Ask for Help

**Ask for help if:**
1. ✅ You've tested each component separately
2. ✅ You've added print statements
3. ✅ You've checked the common mistakes
4. ✅ You've been stuck for >30 minutes

**When asking, provide:**
1. The error message (full traceback)
2. Minimal code that reproduces the problem
3. What you've already tried
4. What you expected vs. what happened

**Good question:**
> "I'm getting 'TypeError: missing argument' when running my transform. I tested the function alone and it works. Here's my code: [code]. I expected it to process the items, but it crashes immediately. I tried adding params={} but still get the error."

**Bad question:**
> "My code doesn't work. Help?"

---

## Debugging Checklist

Before asking for help, check:

**Imports:**
- [ ] Imported `network` from `dsl`
- [ ] Imported `Source`, `Transform`, `Sink` from `dsl.blocks`
- [ ] Imported any custom components

**Source:**
- [ ] Source returns items
- [ ] Source returns `None` eventually
- [ ] Tested source alone
- [ ] Source produces expected data

**Transforms:**
- [ ] Transform returns item or None
- [ ] Transform doesn't crash on valid data
- [ ] Tested transform with sample data
- [ ] Used `params={}` for extra arguments

**Sink:**
- [ ] Sink has `run(item)` method
- [ ] Sink has `finalize()` method
- [ ] Called `finalize()` after network runs
- [ ] Tested sink alone

**Network:**
- [ ] Edges in correct direction (source → sink)
- [ ] All nodes are connected
- [ ] Wrapped functions in nodes (Source, Transform, Sink)
- [ ] Called `g.run_network()`

**Output:**
- [ ] Checked if source produced data
- [ ] Checked if transforms filtered everything
- [ ] Checked if sink collected data
- [ ] Called finalize()

---

## Quick Reference: Common Fixes

| Problem | Solution |
|---------|----------|
| "name 'network' not defined" | Add: `from dsl import network` |
| "missing argument" | Add: `params={"arg": value}` |
| No output | Check: source producing? transforms filtering? finalize called? |
| Network hangs | Check: source returns None? |
| "NoneType has no attribute" | Check: transform returning None when it shouldn't? |
| File not found | Check: path correct? file exists? |
| Transform not called | Check: edges connected? node wrapped? |
| Sink empty | Check: finalize() called? |

---

## Remember

**The debugging process:**
1. Isolate the problem (which component?)
2. Test that component alone
3. Add logging/print statements
4. Fix one thing at a time
5. Test again

**Most problems are simple:**
- Forgot to import
- Forgot to return
- Forgot to call finalize()
- Edge in wrong direction
- Typo in variable name

**Take breaks!** Sometimes stepping away helps you see the problem.

**You'll get better at this!** Every bug you fix makes you a better programmer.

---

**Next Steps:**
- Review [QUICKSTART.md](QUICKSTART.md) for templates
- Review [BUILD_APP.md](BUILD_APP.md) for the systematic process
- Check the examples in `examples/` for working code

**Happy debugging!** 🐛🔍
