# How DisSysLab Works

*A student-friendly guide to understanding the entire system*

---

## 1. Introduction - What is DisSysLab?

DisSysLab is a framework for building distributed systems from ordinary Python functions. You write simple functions that know nothing about threads, processes, queues, or message passing. DisSysLab automatically connects them into a network where each function runs in parallel, processing messages as they flow through the system. Think of it like building with LEGO blocks: each function is a block, and DisSysLab handles all the wiring between them.

---

## 2. The Big Picture - Three Simple Layers
```
┌─────────────────────────────────────────────────┐
│  Layer 1: Your Python Functions                │
│  (Regular functions that know nothing about DSL)│
│                                                 │
│  def clean_text(text): ...                     │
│  def analyze_sentiment(text): ...              │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Layer 2: Decorators Wrap Your Functions       │
│  (You add @source_map, @transform_map, etc.)   │
│                                                 │
│  @transform_map(input_keys=['text'],           │
│                 output_keys=['clean'])          │
│  def clean_text(text): ...                     │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Layer 3: Network Runs Everything in Parallel  │
│  (DisSysLab creates threads, queues, agents)   │
│                                                 │
│  network([(source, clean),                     │
│           (clean, sentiment)])                  │
└─────────────────────────────────────────────────┘
```

**Key Insight:** You only write Layer 1. DisSysLab handles everything else.

---

## 3. Step-by-Step: From Code to Running System

Let's trace what happens when you build and run a network.

### Step 1: What You Write
```python
# 1. Import the framework
from dsl import network
from dsl.decorators import source_map, transform_map, sink_map

# 2. Write ordinary Python functions
def generate_numbers():
    for i in range(5):
        return i  # Just returns a number

def double(x):
    return x * 2  # Just doubles a number

def print_result(x):
    print(f"Result: {x}")  # Just prints

# 3. Wrap functions with decorators
@source_map(output_keys=['number'])
def wrapped_generator():
    return generate_numbers()

@transform_map(input_keys=['number'], output_keys=['doubled'])
def wrapped_double(x):
    return double(x)

@sink_map(input_keys=['doubled'])
def wrapped_printer(x):
    print_result(x)

# 4. Define the network topology
g = network([
    (wrapped_generator, wrapped_double),
    (wrapped_double, wrapped_printer)
])

# 5. Run the network
g.run_network()
```

**That's it!** Now let's see what happens under the hood.

---

### Step 2: What `network()` Does - Building the Graph

When you call `network([...])`, DisSysLab:

1. **Parses the topology**
   - Sees: `(wrapped_generator, wrapped_double)` means "connect generator to doubler"
   - Sees: `(wrapped_double, wrapped_printer)` means "connect doubler to printer"

2. **Identifies node types**
   - `wrapped_generator` - Source (produces data)
   - `wrapped_double` - Transform (processes data)
   - `wrapped_printer` - Sink (consumes data)

3. **Detects patterns**
   - Checks for fanin (multiple sources → one destination)
   - Checks for fanout (one source → multiple destinations)
   - Validates the graph is acyclic (no loops... yet!)

4. **Returns a Network object**
   - Contains all topology information
   - Ready to be compiled into agents

**At this point:** Nothing is running yet. You just have a blueprint.

---

### Step 3: What `compile()` Does - Creating the Infrastructure

When you call `g.run_network()`, it internally calls `compile()` first. This is where the magic happens:
```
Your Topology          →    Compiled Network
━━━━━━━━━━━━━━━━━━         ━━━━━━━━━━━━━━━━━━

(generator, doubler)   →    Agent 1 ─[queue]─→ Agent 2
(doubler, printer)          Agent 2 ─[queue]─→ Agent 3

Each agent has:
- Its own thread
- Input queue(s)
- Output queue(s)  
- The wrapped function to call
```

**For each node, DisSysLab creates:**

1. **An Agent** - Python object managing one node
   - Knows which function to call
   - Knows which queues to read from / write to
   - Will run in its own thread

2. **Queues for communication**
   - Each connection gets a `queue.Queue`
   - Messages flow through these queues
   - Thread-safe (no race conditions!)

3. **Port mappings**
   - Maps message keys to function parameters
   - "Extract 'number' from message, pass as `x`"
   - "Take return value, put in message as 'doubled'"

**After compilation:** You have a complete runtime system, ready to execute.

---

### Step 4: What `run_network()` Does - Execution

Now the network actually runs:

1. **Starts all threads**
```
   Thread 1: running wrapped_generator
   Thread 2: running wrapped_double  
   Thread 3: running wrapped_printer
```

2. **Source agent (generator) starts producing**
```
   wrapped_generator() returns 0
   → Create message: {"number": 0}
   → Put in queue to wrapped_double
```

3. **Transform agent (doubler) processes**
```
   Reads from input queue: {"number": 0}
   → Extract 0 (from key "number")
   → Call wrapped_double(0)
   → Returns 0
   → Create message: {"doubled": 0}
   → Put in queue to wrapped_printer
```

4. **Sink agent (printer) consumes**
```
   Reads from input queue: {"doubled": 0}
   → Extract 0 (from key "doubled")
   → Call wrapped_printer(0)
   → Prints "Result: 0"
```

5. **Repeat for all data**
   - Generator produces 0, 1, 2, 3, 4
   - Each flows through the pipeline
   - All running concurrently!

6. **Termination**
   - Generator finishes, sends STOP signal
   - STOP propagates through network
   - All agents shut down cleanly

**Result:** Your network processed data in parallel without you writing any threading code.

---

## 4. How Messages Flow - Detailed Trace

Let's trace a single message through a more complex network:
```
Network topology:
  source1 ─┐
           ├─→ merge ─→ process ─→ sink
  source2 ─┘
```

### Message Journey:

**T=0:** `source1` produces
```
source1.run() returns "hello"
→ Decorator wraps: {"text": "hello"}
→ Goes into source1→merge queue
```

**T=1:** `merge` receives from source1
```
merge has 2 input queues (source1 and source2)
→ Reads from source1 queue: {"text": "hello"}
→ Calls merge("hello")
→ Returns "HELLO"  
→ Decorator wraps: {"merged": "HELLO"}
→ Goes into merge→process queue
```

**T=2:** `process` transforms
```
Reads from merge→process queue: {"merged": "HELLO"}
→ Calls process("HELLO")
→ Returns "PROCESSED: HELLO"
→ Decorator wraps: {"result": "PROCESSED: HELLO"}
→ Goes into process→sink queue
```

**T=3:** `sink` consumes
```
Reads from process→sink queue: {"result": "PROCESSED: HELLO"}
→ Calls sink("PROCESSED: HELLO")
→ Prints to console
→ No output (sink ends the flow)
```

**Meanwhile:** `source2` is running the same process in parallel!

---

## 5. Common Questions

### Q: Why do messages have to be dictionaries?

**A:** Consistency and extensibility. Dict messages:
- Work for all node types
- Can carry multiple values (`{"text": "hi", "score": 0.8}`)
- Can be enriched as they flow (`original_text`, `cleaned_text`, `sentiment`)
- Are easy to debug (just print the dict!)

### Q: What if I return `None` from a function?

**A:** The message is **dropped** - it doesn't get sent downstream. This is how you implement filtering:
```python
@transform_map(input_keys=['number'], output_keys=['even'])
def keep_only_even(n):
    if n % 2 == 0:
        return n
    else:
        return None  # Message dropped!
```

### Q: How does DisSysLab know what order to run things?

**A:** It doesn't! Everything runs in parallel. The network topology defines **dependencies** (what connects to what), not execution order. Messages flow when data is available.

### Q: What if one agent is slower than others?

**A:** Queues buffer messages automatically. Fast producers can keep going while slow consumers catch up. If queues get too large, you might see memory issues - that's a sign you need to optimize the slow agent.

### Q: Can I have multiple outputs from one node?

**A:** Yes! That's **fanout**:
```python
network([
    (source, processor1),  # Same source goes to both
    (source, processor2)
])
```

### Q: Can I merge multiple sources?

**A:** Yes! That's **fanin**:
```python
network([
    (source1, merger),  # Both sources merge into one
    (source2, merger)
])
```

### Q: How do I debug when things go wrong?

**A:** Add print statements inside your functions to trace message flow:
```python
def my_transform(x):
    print(f"Received: {x}")  # Debug print
    result = x * 2
    print(f"Sending: {result}")  # Debug print
    return result
```

### Q: What happens if there's an exception?

**A:** The agent thread crashes and you'll see the error. DisSysLab doesn't currently have automatic error recovery (that's version 2.0!). Best practice: handle exceptions inside your functions.

---

## 6. Where to Go Next

Now that you understand how it works:

### To Build Applications:
- **Start with `modules/basic/`** - See a complete example
- **Read module READMEs** - Learn patterns progressively
- **Check `docs/PATTERNS.md`** - Common design patterns

### To Understand the API:
- **`docs/API_REFERENCE.md`** - Complete function documentation
- **`docs/DECORATOR_REFERENCE.md`** - All three decorators explained

### To Go Deeper:
- **`docs/ARCHITECTURE.md`** - System internals
- **`docs/GRAPH_INTERNALS.md`** - How topology compilation works

### If You're Stuck:
- **`TROUBLESHOOTING.md`** - Common errors and fixes
- **Module `README.md` files** - Each has a "Common issues" section

### For Teaching:
- **`docs/TEACHING_GUIDE.md`** - Instructor resources *(to be written)*
- **Module examples** - Use as course material

---

## Summary

**The big picture:**
1. You write ordinary Python functions
2. You wrap them with decorators (`source_map`, `transform_map`, `sink_map`)
3. You define the network topology as a list of connections
4. DisSysLab compiles this into agents, queues, and threads
5. When you run the network, messages flow through automatically

**Key insight:** You never see threads, queues, or message passing. You just write functions and define connections. DisSysLab handles all the distributed systems complexity!

**Next step:** Try building your own network! Start with `modules/basic/` and modify it to do something different.

---

*Last updated: January 2026*
*For questions or issues, see TROUBLESHOOTING.md (to be written)*