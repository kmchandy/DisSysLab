# Module 01: Basics - Your First dsl Network

Build distributed systems using ordinary Python functions.

## The Problem that We're Solving

You may have developed applications that have the form: get data; process the data; save results and terminate. You may have written a sequential program which executes one step at a time to implement the application. dsl is different from sequential programming in two ways: (1) dsl applications are persistent: they run forever, or (2) steps of the applications are executed concurrently.

Many of the example apps in the initial modules terminate; apps that are persistent are described later.

## What You'll Learn in this Module

- Types of nodes: Source, Transform, Sink, and Agent.
- How to build a node of a network from an ordinary Python function
- How to define a network topology as a directed graph.
- How to run a network where nodes execute concurrently
- Patterns you use in most dsl programs



## Network Topology

Our first example is a simple **pipeline** - a linear chain of processing steps:
```
["hello", "world"] → UPPERCASE → ADD "!!" → results
      ↓                 ↓            ↓           ↓
   (source)        (uppercase)  (add_emphasis) (collector)
```

Each arrow represents a connection where data flows from one node to the next. All nodes run concurrently - as soon as `source` produces "hello", `uppercase` can start processing it while `source` is producing "world".

## The Code Walkthrough

Let's build this network step by step, following the file `example.py`.

### Step 1: Write Ordinary Python Functions

**Key insight:** Start with plain Python functions that know nothing about distributed systems, networks, or concurrency.
```python
list_source = ListSource(items=["hello", "world"])

def convert_to_upper_case(text):
    """Function used in a transform node."""
    return text.upper()

def add_suffix(text, suffix):
    """Function used in a transform node."""
    return text + suffix
```

**What's happening:**
- `ListSource` is a helper class that generates items from a list
- `convert_to_upper_case` is just a normal function - it takes a string, returns uppercase
- `add_suffix` is also just a normal function - it takes a string and suffix, returns concatenated result
- **None of these functions know they'll be used in a distributed system!**

**Common question:** "Do my functions need special decorators or imports?"  
**Answer:** No! That's the whole point. Write normal Python, wrap it later.

### Step 2: Wrap Functions into Network Nodes

**The General Pattern:**

To create any node, you use this pattern:
```python
node = NodeType(
    fn=your_function,      # The Python function to wrap
    name="node_name",      # A name for debugging
    params={...}           # Optional: extra parameters (if needed)
)
```

Where `NodeType` is one of:
- **`Source`** - for functions that generate data
- **`Transform`** - for functions that process data
- **`Sink`** - for functions that consume data

**That's it!** You're telling DisSysLab: "Take this ordinary function and turn it into a network node."

Later we describe the **agent** class in which you can write programs that explicitly send and receive messages.

---

**Now let's apply this pattern to create our four nodes:**

#### Creating the Source Node
```python
source = Source(
    fn=list_source.run,
    name="list_source"
)
```

**What we're doing:**
- Using `Source(...)` because this node generates data
- `fn=list_source.run` - the function that produces items
- `name="list_source"` - helps with debugging

**Mental model:** "Create a Source node that runs `list_source.run()` to generate data."

#### Creating the First Transform Node
```python
uppercase = Transform(
    fn=convert_to_upper_case,
    name="uppercase"
)
```

**What we're doing:**
- Using `Transform(...)` because this node processes data
- `fn=convert_to_upper_case` - the function that does the processing
- No `params` needed because `convert_to_upper_case(text)` only needs one argument (the input message)

**Mental model:** "Create a Transform node that runs `convert_to_upper_case()` on each message."

#### Creating the Second Transform Node (with Parameters)
```python
add_emphasis = Transform(
    fn=add_suffix,
    params={"suffix": "!!"},
    name="add_emphasis"
)
```

**What we're doing:**
- Using `Transform(...)` because this node processes data
- `fn=add_suffix` - the function to run
- `params={"suffix": "!!"}` - extra parameters the function needs
- Remember: `add_suffix(text, suffix)` needs TWO arguments, but messages only provide `text`, so we supply `suffix` via `params`

**Mental model:** "Create a Transform node that runs `add_suffix(text, suffix="!!")` on each message."

**Key insight:** When your function needs extra parameters beyond the input message, use `params={}` to provide them.

#### Creating the Sink Node
```python
results = []
collector = Sink(
    fn=results.append,
    name="collector"
)
```

**What we're doing:**
- Using `Sink(...)` because this node consumes data (no output to other nodes)
- `fn=results.append` - the function that stores/consumes the data
- We're using Python's built-in `list.append` method - it's just a function!

**Mental model:** "Create a Sink node that runs `results.append()` on each message."

---

**Summary of our four nodes:**

| Variable | Type | Function | Purpose |
|----------|------|----------|---------|
| `source` | Source | `list_source.run` | Generate "hello", "world" |
| `uppercase` | Transform | `convert_to_upper_case` | text → TEXT |
| `add_emphasis` | Transform | `add_suffix` | TEXT → TEXT!! |
| `collector` | Sink | `results.append` | Store in list |

**The pattern is always the same:**
1. Choose the right `NodeType` (Source, Transform, or Sink)
2. Pass your function with `fn=...`
3. Add a `name=...` for debugging
4. If needed, add `params={...}` for extra arguments

---

**About the three node types:**

**Source** - Produces data, has no inputs
```python
Source(fn=generating_function, name="my_source")
```
- Your function should generate or fetch data
- Examples: reading files, API calls, sensor data, database queries, generating sequences

**Transform** - Processes data, has one input and one output  
```python
Transform(fn=processing_function, name="my_transform", params={...})
```
- Your function takes input, returns processed output
- Examples: filtering, formatting, calculations, validation, text processing
- Use `params` if your function needs extra arguments

**Sink** - Consumes data, has input but no output
```python
Sink(fn=consuming_function, name="my_sink")
```
- Your function receives data and does something with it (but doesn't pass it on)
- Examples: saving to file, printing, sending email, database writes, collecting results

---

**Common questions at this step:**

**Q: "Can I use any Python function?"**  
A: Yes! As long as it matches the node type:
- Source functions: no parameters (or use `params` to provide them)
- Transform functions: one parameter for the input (or use `params` for extras)
- Sink functions: one parameter for the input

**Q: "What if my function has 3 parameters?"**  
A: Use `params` to provide the extra ones. For example:
```python
def my_function(data, threshold, scale):
    return data * scale if data > threshold else 0

node = Transform(
    fn=my_function,
    params={"threshold": 10, "scale": 2.5},
    name="my_transform"
)
# DisSysLab will call: my_function(data=<from_message>, threshold=10, scale=2.5)
```

**Q: "Why do I need to provide a name?"**  
A: When something goes wrong, error messages will show the node name. Compare:
- ❌ "Error in node at position 2" (hard to debug)
- ✓ "Error in node 'uppercase'" (immediately clear)

**Q: "Can I reuse the same function in multiple nodes?"**  
A: Absolutely! You might have three Transform nodes that all use the same function but with different `params`.


### Step 3: Define the Network Topology

Now we specify how nodes connect:
```python
g = network([
    (source, uppercase),          # hello → HELLO
    (uppercase, add_emphasis),    # HELLO → HELLO!!
    (add_emphasis, collector)     # HELLO!! → results list
])
```

**What's happening:**
- `network([...])` takes a **list of edges**
- Each edge is a tuple `(from_node, to_node)` meaning "connect output of `from_node` to input of `to_node`"
- Our network: `source → uppercase → add_emphasis → collector`

**Key insight:** You're describing the **topology** (shape) of your network, not the execution order. DisSysLab figures out how to run it.

### Step 4: Run the Network
```python
g.run_network()
```

**What's happening when you call `run_network()`:**

1. **DisSysLab creates threads** - One thread per node (4 threads total)
2. **Creates queues** - Message queues between connected nodes
3. **Starts all threads** - All nodes start running simultaneously
4. **Source produces data:**
   - `source` generates "hello", puts it in queue to `uppercase`
   - `source` generates "world", puts it in queue to `uppercase`
   - `source` finishes, sends STOP signal
5. **Transforms process data:**
   - `uppercase` reads "hello" from queue, converts to "HELLO", puts in queue to `add_emphasis`
   - `uppercase` reads "world" from queue, converts to "WORLD", puts in queue to `add_emphasis`
   - `uppercase` receives STOP, sends STOP to `add_emphasis`
6. **Sink consumes data:**
   - `collector` reads "HELLO!!" and "WORLD!!", appends to `results` list
   - `collector` receives STOP, exits
7. **Network shuts down cleanly** - All threads terminate

**The amazing part:** All of this happens automatically! You just wrote functions and defined connections. DisSysLab handled:
- Threading
- Message passing
- Queue management
- Synchronization
- Clean shutdown

### Step 5: Verify Results
```python
if __name__ == "__main__":
    print(f"Results: {results}")
    assert results == ["HELLO!!", "WORLD!!"], f"Expected ['HELLO!!', 'WORLD!!'], got {results}"
    print("✓ Pipeline completed successfully!")
```

**What you'll see:**
```
Results: ['HELLO!!', 'WORLD!!']
✓ Pipeline completed successfully!
```

## Running This Example

From the DisSysLab root directory:
```bash
python3 -m examples.module_01_basics.example
```

**Expected output:**
```
Results: ['HELLO!!', 'WORLD!!']
✓ Pipeline completed successfully!
```

## Key Concepts

### Concept 1: Separation of Concerns

DisSysLab separates **what** (your functions) from **how** (the distributed execution):

- **What:** Your Python functions define the logic
- **How:** DisSysLab handles threads, queues, message-passing

This means you can:
- Write functions without thinking about concurrency
- Test functions in isolation (they're just Python!)
- Reuse functions in different networks
- Focus on the problem, not the infrastructure

### Concept 2: Network as a Graph

Your network is a **directed graph**:
- **Nodes** are your wrapped functions (Source, Transform, Sink)
- **Edges** are connections where data flows
- **Direction** matters: `(A, B)` means A → B, not B → A
```
     source
       ↓
    uppercase
       ↓
  add_emphasis
       ↓
   collector
```

This is a **pipeline** - the simplest topology. Later modules cover more complex shapes.

### Concept 3: Messages Flow Automatically

Once you define the topology:
1. Source nodes **produce** messages
2. Messages **flow** through queues
3. Transform nodes **process** messages
4. Sink nodes **consume** messages
5. STOP signals propagate to shut down cleanly

You never explicitly send or receive messages - DisSysLab does it based on your topology.

### Concept 4: Concurrent Execution

**All nodes run at the same time** in their own threads. This means:
- Fast nodes don't wait for slow nodes (queues buffer messages)
- Multiple messages can be in the network simultaneously
- Processing happens in parallel when possible

In our example:
- While `uppercase` is processing "hello" → "HELLO"
- `source` can already be producing "world"
- And `add_emphasis` might be processing a previous message

**This is why DisSysLab is powerful:** You get parallelism for free.

### Concept 5: The Three Basic Node Types (Agents described later)

Every DisSysLab network uses these three building blocks:

| Node Type | Inputs | Outputs | Purpose | Examples |
|-----------|--------|---------|---------|----------|
| **Source** | None | One | Generate data | Read file, API call, sensor |
| **Transform** | One | One | Process data | Filter, convert, calculate |
| **Sink** | One | None | Consume data | Save file, print, send email |

**Question:** "What if I need multiple inputs or outputs?"  
**Answer:** Module 04 (fanin) and Module 03 (fanout) cover those patterns!

## Common Mistakes

### Mistake 1: Forgetting to Import
```python
# ❌ Wrong - forgot imports
g = network([(source, transform)])  # NameError: 'network' is not defined
```
```python
# ✓ Correct
from dsl import network
from dsl.blocks import Source, Transform, Sink
```

**Why it fails:** Python can't find the classes and functions.  
**Fix:** Always import what you need at the top of the file.

### Mistake 2: Edges in Wrong Order
```python
# ❌ Wrong - edges backwards
g = network([
    (collector, add_emphasis),    # ← Wrong direction!
    (add_emphasis, uppercase),
    (uppercase, source)
])
```
```python
# ✓ Correct - data flows forward
g = network([
    (source, uppercase),
    (uppercase, add_emphasis),
    (add_emphasis, collector)
])
```

**Why it fails:** Data can't flow backwards. Source produces data, Sink consumes it.  
**Fix:** Think about data flow direction: where does data come FROM → where does it go TO?

### Mistake 3: Forgetting `params` for Functions with Arguments
```python
# ❌ Wrong - add_suffix needs a suffix argument
add_emphasis = Transform(
    fn=add_suffix,
    name="add_emphasis"
)
# Error: add_suffix() missing 1 required positional argument: 'suffix'
```
```python
# ✓ Correct - provide params
add_emphasis = Transform(
    fn=add_suffix,
    params={"suffix": "!!"},
    name="add_emphasis"
)
```

**Why it fails:** Your function `add_suffix(text, suffix)` needs both arguments, but messages only provide `text`.  
**Fix:** Use `params={}` to provide the extra arguments.

### Mistake 4: Not Running the Network
```python
# ❌ Wrong - just defined network, never ran it
g = network([...])
print(results)  # Prints: [] (empty!)
```
```python
# ✓ Correct - must call run_network()
g = network([...])
g.run_network()  # ← This actually executes!
print(results)   # Now has data
```

**Why it fails:** `network([...])` just creates the structure. It doesn't execute until you call `run_network()`.  
**Fix:** Always call `g.run_network()` to actually run your network.

### Mistake 5: Using Wrong Node Type
```python
# ❌ Wrong - trying to use Transform for a source
source = Transform(  # ← Should be Source!
    fn=list_source.run,
    name="source"
)
```
```python
# ✓ Correct - use Source for data generation
source = Source(
    fn=list_source.run,
    name="source"
)
```

**Why it fails:** Transform expects input from another node, but Sources generate their own data.  
**Fix:** Match the node type to its role: Source (generates), Transform (processes), Sink (consumes).

## Experiments to Try

Modify `example.py` to explore how DisSysLab works:

### Experiment 1: Change the Data

**Modify:**
```python
list_source = ListSource(items=["python", "distributed", "systems"])
```

**What to observe:** Three items flow through, each getting processed.

### Experiment 2: Add Another Transform

**Add after `add_emphasis`:**
```python
reverse = Transform(
    fn=lambda x: x[::-1],
    name="reverse"
)
```

**Modify network:**
```python
g = network([
    (source, uppercase),
    (uppercase, add_emphasis),
    (add_emphasis, reverse),      # ← New step
    (reverse, collector)
])
```

**What to observe:** Strings get reversed: "HELLO!!" → "!!OLLEH"

### Experiment 3: Add Print Statements

**Inside your functions:**
```python
def convert_to_upper_case(text):
    print(f"Converting: {text}")
    return text.upper()
```

**What to observe:** See messages flowing through the network in real-time.

### Experiment 4: Try Different Functions

Replace `add_suffix` with something else:
```python
def count_letters(text):
    return f"{text} ({len(text)} letters)"
```

**What to observe:** Same network structure, different processing logic.

### Experiment 5: Multiple Transforms

Create a longer pipeline with 5-6 transform nodes. Each one does something simple (lowercase, capitalize, strip, etc.). 

**What to observe:** The pipeline pattern scales naturally to any length.

## Next Steps

You've learned the fundamental pattern! Every DisSysLab program follows these same four steps:

1. Write functions
2. Wrap into nodes
3. Define topology
4. Run network

**Next module:** [Module 02: Filtering](../module_02_filtering/) - Learn how to drop messages by returning `None`, enabling conditional processing.

**Want to understand more deeply?** Read [How It Works](../../docs/HOW_IT_WORKS.md) to see what happens inside DisSysLab when you run a network.

## Quick Reference

**Import what you need:**
```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource  # or other helpers
```

**The pattern:**
```python
# 1. Functions
def my_function(data):
    return data.upper()

# 2. Nodes
node = Transform(fn=my_function, name="my_node")

# 3. Network
g = network([(node1, node2), (node2, node3)])

# 4. Run
g.run_network()
```

**Node types:**
- `Source(fn=..., name=...)` - Generates data
- `Transform(fn=..., name=..., params={})` - Processes data
- `Sink(fn=..., name=...)` - Consumes data

---

**Questions or stuck?** Check [Troubleshooting](../../docs/troubleshooting.md) or review this README again. The concepts are simple once you see them work!# Module 01 Basics

Introduction to DisSysLab - First network, basic patterns

## Topics Covered

- Source, Transform, Sink nodes
- Simple pipeline
- Message flow


## Examples

[To be added]

## Running the Examples
```bash
python3 -m examples.module_01_basics.example_name
```

## Key Concepts

[To be documented]

## Exercises

[To be added]

---

*See [MODULE_ORDER.md](../../MODULE_ORDER.md) for the complete learning sequence.*
