# QUICKSTART.md - DisSysLab Cheat Sheet

**Copy these templates to start building your app immediately!**

This is your **quick reference** for the essential patterns. For more detailed templates with testing and examples, see [TEMPLATES.md](TEMPLATES.md).

---

## Table of Contents

1. [Source Template](#1-source-template) - Where data comes FROM
2. [Transform Template](#2-transform-template) - How to PROCESS data
3. [Sink Template](#3-sink-template) - Where data GOES TO
4. [Network Template](#4-network-template) - How to CONNECT everything
5. [Complete Example](#5-complete-example) - Putting it all together

---

## 1. Source Template

**A source produces data. It MUST have a `run()` method that returns items one at a time.**

```python
class MySource:
    """
    Where your data comes FROM.
    
    REQUIREMENTS:
    - Must have run() method
    - run() returns one item at a time
    - run() returns None when done
    """
    
    def __init__(self):
        """Setup: Load or prepare your data."""
        # TODO: Put your data here
        self.data = ["item1", "item2", "item3"]
        self.n = 0
    
    def run(self):
        """
        Return next item.
        
        MUST return None when finished!
        """
        if self.n < len(self.data):
            item = self.data[self.n]
            self.n += 1
            return item
        else:
            return None  # Signal: no more data
```

**Key Points:**
- ✅ `run()` is called repeatedly by the framework
- ✅ Return one item each time
- ✅ Return `None` when finished
- ✅ Track position with `self.n`

**Examples:** File reader, API caller, database query, sensor data

---

## 2. Transform Template

**A transform processes data. Just a regular Python function!**

```python
def my_transform(item):
    """
    Process one item.
    
    REQUIREMENTS:
    - Takes one parameter (the item)
    - Returns the transformed item
    - OR returns None to filter out
    """
    
    # TODO: Process the item
    # Examples:
    # - Add fields: item["new_field"] = "value"
    # - Modify fields: item["count"] = item["count"] * 2
    # - Filter: if item["status"] != "active": return None
    
    # Example: Add a computed field
    item["processed"] = True
    
    return item  # Pass item forward
    # return None  # Use this to filter out item
```

**Key Points:**
- ✅ Just a Python function
- ✅ Takes one parameter
- ✅ Returns modified item
- ✅ Return `None` to filter out

**Examples:** Filter, enrich, validate, aggregate, AI analysis

---

## 3. Sink Template

**A sink consumes data. It MUST have `run(item)` and `finalize()` methods.**

```python
class MySink:
    """
    Where your data GOES TO.
    
    REQUIREMENTS:
    - Must have run(item) method
    - Must have finalize() method
    - run() is called for each item
    - finalize() is called once at end
    """
    
    def __init__(self):
        """Setup: Open files, connect to APIs, etc."""
        # TODO: Initialize your output
        self.results = []
    
    def run(self, item):
        """
        Process one item.
        
        Called once for EACH item.
        """
        # TODO: Do something with the item
        # Examples:
        # - Collect: self.results.append(item)
        # - Write: self.file.write(json.dumps(item))
        # - POST: requests.post(url, json=item)
        
        self.results.append(item)
    
    def finalize(self):
        """
        Called once at the END.
        
        Use for cleanup: close files, flush buffers, etc.
        """
        # TODO: Final processing
        # Examples:
        # - Close files: self.file.close()
        # - Print summary: print(f"Processed {len(self.results)} items")
        # - Write batch: json.dump(self.results, file)
        
        print(f"Sink processed {len(self.results)} items")
```

**Key Points:**
- ✅ `run(item)` is called for EACH item
- ✅ `finalize()` is called ONCE at the end
- ✅ Use finalize() to close files, save batches, etc.

**Examples:** File writer, database inserter, API poster, dashboard display

---

## 4. Network Template

**A network connects sources, transforms, and sinks together.**

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink

# ============================================
# STEP 1: Create your components
# ============================================

# Create source
my_source = MySource()
source_node = Source(fn=my_source.run, name="my_source")

# Create transform(s)
transform_node = Transform(fn=my_transform, name="my_transform")

# Create sink
my_sink = MySink()
sink_node = Sink(fn=my_sink.run, name="my_sink")


# ============================================
# STEP 2: Define network (list of edges)
# ============================================

g = network([
    (source_node, transform_node),   # Source → Transform
    (transform_node, sink_node)       # Transform → Sink
])


# ============================================
# STEP 3: Run the network
# ============================================

g.run_network()

# Don't forget finalize!
my_sink.finalize()
```

**Key Points:**
- ✅ Wrap source with `Source(fn=source.run, ...)`
- ✅ Wrap transform with `Transform(fn=transform_func, ...)`
- ✅ Wrap sink with `Sink(fn=sink.run, ...)`
- ✅ Network is a list of edges (tuples)
- ✅ Call `finalize()` on sinks after running

**Network Patterns:**

```python
# Linear: A → B → C
[(A, B), (B, C)]

# Fanout: A → B → C
#              → D
[(A, B), (B, C), (B, D)]

# Fanin:  A → C
#         B → C
[(A, C), (B, C)]

# Complex: A → B → D
#          A → C → D
[(A, B), (A, C), (B, D), (C, D)]
```

---

## 5. Complete Example

**Here's a complete working app:**

```python
"""
Simple data processing pipeline:
Read data → Filter → Transform → Save
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
import json


# ============================================
# SOURCE: Read customer data
# ============================================

class CustomerSource:
    def __init__(self):
        self.customers = [
            {"id": 1, "name": "Alice", "age": 28, "status": "active"},
            {"id": 2, "name": "Bob", "age": 34, "status": "inactive"},
            {"id": 3, "name": "Carol", "age": 45, "status": "active"},
        ]
        self.n = 0
    
    def run(self):
        if self.n < len(self.customers):
            customer = self.customers[self.n]
            self.n += 1
            return customer
        return None


# ============================================
# TRANSFORM 1: Filter active customers
# ============================================

def filter_active(customer):
    if customer["status"] == "active":
        return customer
    return None  # Filter out inactive


# ============================================
# TRANSFORM 2: Add greeting
# ============================================

def add_greeting(customer):
    customer["greeting"] = f"Hello, {customer['name']}!"
    return customer


# ============================================
# SINK: Collect and display results
# ============================================

class DisplaySink:
    def __init__(self):
        self.results = []
    
    def run(self, item):
        self.results.append(item)
        print(f"  ✓ {item['greeting']}")
    
    def finalize(self):
        print(f"\nProcessed {len(self.results)} active customers")


# ============================================
# BUILD AND RUN NETWORK
# ============================================

# Create components
source = CustomerSource()
sink = DisplaySink()

# Create nodes
source_node = Source(fn=source.run, name="customers")
filter_node = Transform(fn=filter_active, name="filter")
greeting_node = Transform(fn=add_greeting, name="greeting")
sink_node = Sink(fn=sink.run, name="display")

# Define network
g = network([
    (source_node, filter_node),
    (filter_node, greeting_node),
    (greeting_node, sink_node)
])

# Run!
print("Running pipeline...")
g.run_network()
sink.finalize()
```

**Output:**
```
Running pipeline...
  ✓ Hello, Alice!
  ✓ Hello, Carol!

Processed 2 active customers
```

---

## Common Patterns Quick Reference

### **Multiple Transforms (Chain)**
```python
g = network([
    (source, transform1),
    (transform1, transform2),
    (transform2, transform3),
    (transform3, sink)
])
```

### **Multiple Outputs (Fanout)**
```python
g = network([
    (source, transform),
    (transform, sink1),
    (transform, sink2),
    (transform, sink3)
])

# Don't forget to finalize ALL sinks!
sink1.finalize()
sink2.finalize()
sink3.finalize()
```

### **Multiple Inputs (Fanin)**
```python
g = network([
    (source1, transform),
    (source2, transform),
    (transform, sink)
])
```

### **Conditional Flow**
```python
def route(item):
    if item["priority"] == "high":
        return item
    return None  # Filter out low priority

high_route = Transform(fn=route, name="high_filter")

g = network([
    (source, high_route),
    (high_route, urgent_sink),
    (source, all_sink)  # All items also go here
])
```

---

## Checklist for Building Your App

### **Before You Start:**
- [ ] What data do I need? (Source)
- [ ] What processing do I need? (Transforms)
- [ ] Where should results go? (Sink)
- [ ] Draw the network diagram on paper

### **While Building:**
- [ ] Start with source alone - does it return data?
- [ ] Add one transform - does it process correctly?
- [ ] Add sink - does it collect/save correctly?
- [ ] Test each piece individually before connecting

### **After Building:**
- [ ] Does the network run without errors?
- [ ] Are results correct?
- [ ] Did I call finalize() on all sinks?
- [ ] Did source return None at the end?

### **Common Mistakes:**
- ❌ Forgot to return None in source
- ❌ Forgot to call finalize() on sinks
- ❌ Transform returned nothing (should return item or None)
- ❌ Sink doesn't have finalize() method
- ❌ Network edges in wrong order

---

## Testing Your Code

### **Test Source Alone:**
```python
source = MySource()
while True:
    item = source.run()
    if item is None:
        break
    print(item)
```

### **Test Transform Alone:**
```python
test_item = {"id": 1, "name": "test"}
result = my_transform(test_item)
print(result)
```

### **Test Sink Alone:**
```python
sink = MySink()
sink.run({"test": "data"})
sink.run({"more": "data"})
sink.finalize()
```

### **Test Network:**
```python
# Start small, add complexity gradually
# Test with 2-3 items first, then scale up
```

---

## Where to Get Help

- **Examples:** See `examples/module_09/` for complete working apps
- **Templates:** See `TEMPLATES.md` for detailed templates with tests
- **Debugging:** See `DEBUGGING.md` (Module 10) for troubleshooting
- **Components:** See `components/sources/` and `components/sinks/` for real implementations

---

## Quick Start Recipes

### **Read File → Process → Save File**
```python
from components.sources.file_source import FileSource
from components.sinks.file_writer import FileWriter

source = FileSource("input.csv")
writer = FileWriter("output.json", format="json")

source_node = Source(fn=source.run, name="input")
transform_node = Transform(fn=my_process, name="process")
sink_node = Sink(fn=writer.run, name="output")

g = network([(source_node, transform_node), (transform_node, sink_node)])
g.run_network()
writer.finalize()
```

### **Stream Data → Filter → Alert**
```python
from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
from components.sinks.webhook_sink import Webhook

stream = BlueSkyJetstreamSource(max_posts=50)
webhook = Webhook(url="https://hooks.slack.com/...")

source_node = Source(fn=stream.run, name="stream")
filter_node = Transform(fn=my_filter, name="filter")
sink_node = Sink(fn=webhook.run, name="alerts")

g = network([(source_node, filter_node), (filter_node, sink_node)])
g.run_network()
webhook.finalize()
```

### **Multiple Sources → Combine → Output**
```python
source1 = FileSource("data1.csv")
source2 = FileSource("data2.csv")
sink = MySink()

s1 = Source(fn=source1.run, name="source1")
s2 = Source(fn=source2.run, name="source2")
transform = Transform(fn=combine, name="combine")
sink_node = Sink(fn=sink.run, name="output")

g = network([(s1, transform), (s2, transform), (transform, sink_node)])
g.run_network()
sink.finalize()
```

---

## Remember: The Pattern is Always the Same!

```
SOURCE → TRANSFORM → SINK
(where)   (process)   (where)
(from)    (how)       (to)
```

1. **Source:** `run()` returns items, then None
2. **Transform:** Function that takes item, returns item or None
3. **Sink:** `run(item)` processes each item, `finalize()` cleans up
4. **Network:** List of edges connecting them

**That's it! You now have everything you need to build distributed systems with DisSysLab!** 🚀

---

## Next Steps

1. **Try the complete example above** - make sure it works
2. **Modify it** - change the data, add transforms, try different sinks
3. **Build something new** - use your own data and logic
4. **See examples** - Check `examples/` for inspiration
5. **Read TEMPLATES.md** - For more detailed templates with testing

**Happy building!**