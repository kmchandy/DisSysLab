# Module 05: Split - Routing Messages to Multiple Outputs

Learn how to route messages to different outputs based on custom logic using the Split node.

## What You'll Learn

- How to route messages to specific outputs (split pattern)
- The difference between split and fanout
- How to use port references (`node.out_0`, `node.out_1`)
- How to implement routing logic (round-robin, conditional, etc.)
- How Split nodes use lists to specify which output gets each message

## The Problem We're Solving

Sometimes you need to send different messages to different destinations:
- Route high-priority tasks to fast workers, low-priority to slow workers
- Send errors to error handler, valid data to processor
- Distribute work across multiple parallel workers (load balancing)
- Separate data by category (users by region, products by type)

**Fanout** (Module 03) sends EVERY message to ALL destinations. **Split** sends EACH message to ONE specific destination based on your logic.

## Network Topology

Our example uses round-robin routing to distribute numbers across 3 outputs:
```
                    → out_0 → collector_0 → [0, 3, 6, 9]
                   ↗
[0,1,2,3,4,5,6,7,8,9] → splitter → out_1 → collector_1 → [1, 4, 7]
                   ↘
                    → out_2 → collector_2 → [2, 5, 8]
```

**Key insight:** Each number goes to EXACTLY ONE output. Number 0 goes to output 0, number 1 goes to output 1, number 2 goes to output 2, then it wraps around (number 3 goes to output 0).

## The Code Walkthrough

### Step 1: Write Ordinary Python Functions
```python
number_source = ListSource(items=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

class RoundRobinRouter:
    """Routes messages round-robin across N outputs."""
    
    def __init__(self, num_outputs=3):
        self.num_outputs = num_outputs
        self.counter = 0
    
    def run(self, msg):
        """
        Route message to one output based on counter.
        
        Returns a list of N messages where only one is non-None.
        """
        # Create result list with None for all positions
        results = [None] * self.num_outputs
        
        # Put message at current position
        output_index = self.counter % self.num_outputs
        results[output_index] = msg
        
        # Increment counter for next message
        self.counter += 1
        
        return results
```

**What's happening:**
- `RoundRobinRouter` is a class that maintains state (the counter)
- `run(msg)` receives ONE message and returns a LIST of outputs
- The list has `num_outputs` elements
- Only ONE element in the list is non-None (the message)
- Other elements are None (meaning "don't send to that output")

**Example execution:**
```python
router = RoundRobinRouter(3)
router.run(0)  # Returns [0, None, None]      ← 0 goes to output 0
router.run(1)  # Returns [None, 1, None]      ← 1 goes to output 1
router.run(2)  # Returns [None, None, 2]      ← 2 goes to output 2
router.run(3)  # Returns [3, None, None]      ← 3 goes to output 0 (wraps)
```

**The Split contract:**
- Input: ONE message
- Output: LIST of N messages (one per output port)
- Non-None elements get sent to their corresponding output
- None elements mean "skip this output"

### Step 2: Wrap Functions into Network Nodes
```python
source = Source(
    fn=number_source.run,
    name="number_source"
)

router = RoundRobinRouter(num_outputs=3)
splitter = Split(
    fn=router.run,
    num_outputs=3,  # MUST specify number of outputs
    name="round_robin_splitter"
)

results_0 = []
collector_0 = Sink(fn=results_0.append, name="collector_0")

results_1 = []
collector_1 = Sink(fn=results_1.append, name="collector_1")

results_2 = []
collector_2 = Sink(fn=results_2.append, name="collector_2")
```

**Critical detail:** `num_outputs=3` tells Split how many output ports to create. This MUST match the length of the list your function returns.

**What Split creates:**
- `splitter.out_0` - First output port
- `splitter.out_1` - Second output port
- `splitter.out_2` - Third output port

These are **port references** you use when building the network.

### Step 3: Define the Network Topology

**This is where Split's port references are used:**
```python
g = network([
    (source, splitter),
    (splitter.out_0, collector_0),  # Output port 0
    (splitter.out_1, collector_1),  # Output port 1
    (splitter.out_2, collector_2)   # Output port 2
])
```

**Notice the syntax difference:**
- Before: `(source, dest)` - simple node-to-node
- Split: `(splitter.out_0, dest)` - port reference to node

**What this means:**
- `splitter.out_0` is NOT a node - it's a reference to output port 0 of the splitter node
- Messages in position 0 of the returned list go to `splitter.out_0`
- Messages in position 1 go to `splitter.out_1`
- Messages in position 2 go to `splitter.out_2`

### Step 4: Run the Network
```python
g.run_network()
```

**What happens during execution:**

**Message 0:**
- Source produces 0
- Splitter receives 0
- Router returns [0, None, None]
- 0 goes to out_0 → collector_0
- Nothing goes to out_1 or out_2

**Message 1:**
- Source produces 1
- Splitter receives 1
- Router returns [None, 1, None]
- 1 goes to out_1 → collector_1
- Nothing goes to out_0 or out_2

**Message 2:**
- Source produces 2
- Splitter receives 2
- Router returns [None, None, 2]
- 2 goes to out_2 → collector_2
- Nothing goes to out_0 or out_1

**Message 3:**
- Source produces 3
- Splitter receives 3
- Router returns [3, None, None] (wraps back to 0)
- 3 goes to out_0 → collector_0

This continues for all 10 numbers.

### Step 5: Verify Results
```python
print("Output 0:", results_0)  # [0, 3, 6, 9]
print("Output 1:", results_1)  # [1, 4, 7]
print("Output 2:", results_2)  # [2, 5, 8]

assert results_0 == [0, 3, 6, 9]
assert results_1 == [1, 4, 7]
assert results_2 == [2, 5, 8]
```

**Verification:**
- Total messages: 10 (input)
- Output 0: 4 messages (0, 3, 6, 9)
- Output 1: 3 messages (1, 4, 7)
- Output 2: 3 messages (2, 5, 8)
- Total distributed: 4 + 3 + 3 = 10 ✓

## Running This Example

From the DisSysLab root directory:
```bash
python3 -m examples.module_05_split.example
```

**Expected output:**
```
Output 0: [0, 3, 6, 9]
Output 1: [1, 4, 7]
Output 2: [2, 5, 8]
✓ Split completed successfully!
  Input: 10 numbers (0-9)
  Output 0: 4 numbers (0 mod 3)
  Output 1: 3 numbers (1 mod 3)
  Output 2: 3 numbers (2 mod 3)
```

## Key Concepts

### Concept 1: Split vs. Fanout

**Split (this module):** Each message goes to ONE output
```
Message 0 → output 0
Message 1 → output 1
Message 2 → output 2
```

**Fanout (Module 03):** Each message goes to ALL outputs
```
Message 0 → [output 0, output 1, output 2]
Message 1 → [output 0, output 1, output 2]
```

**When to use each:**
- Use **Split** for routing/load balancing (distribute work)
- Use **Fanout** for broadcasting (everyone sees everything)

**Visual comparison:**
```
Split:     source ──→ router ──┬→ dest1  (gets msg 0, 3, 6)
                              ├→ dest2  (gets msg 1, 4, 7)
                              └→ dest3  (gets msg 2, 5, 8)

Fanout:    source ──┬→ dest1  (gets ALL messages)
                   ├→ dest2  (gets ALL messages)
                   └→ dest3  (gets ALL messages)
```

### Concept 2: The Split Function Contract

Your split function MUST:
1. **Accept one message** as input
2. **Return a list** of exactly `num_outputs` elements
3. **Put the message at ONE position**, rest are None
4. **Return None** for outputs that shouldn't receive this message
```python
# Correct split function
def my_router(msg):
    if condition:
        return [msg, None, None]  # Send to output 0
    else:
        return [None, msg, None]  # Send to output 1

# ❌ WRONG - returns single value instead of list
def bad_router(msg):
    return msg  # ERROR!

# ❌ WRONG - wrong list length
def bad_router(msg):
    return [msg, None]  # ERROR! Should be 3 elements if num_outputs=3
```

### Concept 3: Port References

Split creates **named output ports** you reference in the network definition:
```python
splitter = Split(fn=router, num_outputs=3, name="splitter")

# DisSysLab automatically creates:
# - splitter.out_0
# - splitter.out_1
# - splitter.out_2

# Use them in network definition:
network([
    (source, splitter),           # Connect to the splitter
    (splitter.out_0, dest1),      # Connect port 0
    (splitter.out_1, dest2),      # Connect port 1
    (splitter.out_2, dest3)       # Connect port 2
])
```

**Important:** Port numbers start at 0 and match list indices.

### Concept 4: Routing Strategies

**Round-Robin (our example):** Distribute evenly
```python
def round_robin(msg):
    output = counter % num_outputs
    counter += 1
    return [msg if i == output else None for i in range(num_outputs)]
```

**Conditional Routing:** Route based on message content
```python
def route_by_value(msg):
    if msg < 5:
        return [msg, None]  # Small numbers to output 0
    else:
        return [None, msg]  # Large numbers to output 1
```

**Hash-Based Routing:** Consistent routing for same keys
```python
def route_by_hash(msg):
    output = hash(msg) % num_outputs
    results = [None] * num_outputs
    results[output] = msg
    return results
```

**Load Balancing:** Track queue sizes and route to least busy
```python
class LoadBalancer:
    def __init__(self, num_outputs):
        self.queue_sizes = [0] * num_outputs
    
    def route(self, msg):
        # Send to least busy output
        output = min(range(len(self.queue_sizes)), 
                    key=lambda i: self.queue_sizes[i])
        results = [None] * len(self.queue_sizes)
        results[output] = msg
        self.queue_sizes[output] += 1
        return results
```

### Concept 5: Sending to Multiple Outputs

**Can you send ONE message to MULTIPLE outputs?** Yes!
```python
def broadcast_to_two(msg):
    if special_condition(msg):
        return [msg, msg, None]  # Send to BOTH output 0 AND output 1
    else:
        return [msg, None, None]  # Send only to output 0
```

**This creates selective broadcasting:**
- Normal messages: go to one output
- Special messages: go to multiple outputs

**Example use case:**
```python
def route_important_messages(msg):
    if msg.priority == "HIGH":
        return [msg, msg]  # Send to BOTH fast_processor AND logger
    else:
        return [msg, None]  # Send only to fast_processor
```

## Common Mistakes

### Mistake 1: Returning Single Value Instead of List
```python
# ❌ Wrong - returns message, not list
def bad_router(msg):
    return msg  # Split expects a list!

# ✓ Correct - returns list
def good_router(msg):
    return [msg, None, None]
```

**Why it fails:** Split expects a list to map to output ports.  
**Fix:** Always return a list of length `num_outputs`.

### Mistake 2: Wrong List Length
```python
# ❌ Wrong - list length doesn't match num_outputs
splitter = Split(fn=router, num_outputs=3, name="splitter")

def router(msg):
    return [msg, None]  # Only 2 elements! Should be 3!
```

**Why it fails:** DisSysLab can't map 2 elements to 3 outputs.  
**Fix:** Returned list length must equal `num_outputs`.

### Mistake 3: Forgetting Port References
```python
# ❌ Wrong - using splitter directly instead of its ports
network([
    (source, splitter),
    (splitter, collector)  # ERROR! Which output port?
])

# ✓ Correct - use port references
network([
    (source, splitter),
    (splitter.out_0, collector)  # Explicit port
])
```

**Why it fails:** Split has multiple outputs - you must specify which one.  
**Fix:** Use `splitter.out_N` to reference specific output ports.

### Mistake 4: All None in Returned List
```python
# ❌ Wrong - message gets lost!
def bad_router(msg):
    return [None, None, None]  # Message goes nowhere!
```

**Why it fails:** If all positions are None, the message is dropped.  
**Fix:** At least one position should have the message (unless you intend to drop it).

### Mistake 5: Port Number Mismatch
```python
# ❌ Wrong - accessing port that doesn't exist
splitter = Split(fn=router, num_outputs=2, name="splitter")

network([
    (source, splitter),
    (splitter.out_0, collector_0),
    (splitter.out_1, collector_1),
    (splitter.out_2, collector_2)  # ERROR! out_2 doesn't exist (only 0, 1)
])
```

**Why it fails:** Only created 2 output ports (0 and 1), but trying to use 3.  
**Fix:** Ensure `num_outputs` matches the number of ports you use.

## Experiments to Try

Modify `example.py` to explore split behavior:

### Experiment 1: Conditional Routing

**Replace round-robin with conditional:**
```python
def route_by_value(msg):
    if msg < 5:
        return [msg, None, None]  # Low numbers → output 0
    elif msg < 8:
        return [None, msg, None]  # Mid numbers → output 1
    else:
        return [None, None, msg]  # High numbers → output 2
```

**What to observe:** results_0 = [0,1,2,3,4], results_1 = [5,6,7], results_2 = [8,9]

### Experiment 2: Two Outputs Only

**Change to 2 outputs:**
```python
router = RoundRobinRouter(num_outputs=2)
splitter = Split(fn=router.run, num_outputs=2, name="splitter")

# Only need 2 collectors
network([
    (source, splitter),
    (splitter.out_0, collector_0),
    (splitter.out_1, collector_1)
])
```

**What to observe:** Even numbers to output 0, odd to output 1

### Experiment 3: Broadcast Important Messages

**Send some messages to multiple outputs:**
```python
def selective_broadcast(msg):
    if msg % 5 == 0:  # Multiples of 5 are "important"
        return [msg, msg, msg]  # Send to ALL outputs
    else:
        output = msg % 3
        results = [None, None, None]
        results[output] = msg
        return results
```

**What to observe:** 0 and 5 appear in all three result lists

### Experiment 4: Add Print Statements

**See routing decisions:**
```python
def route_with_logging(msg):
    results = [None] * num_outputs
    output = counter % num_outputs
    results[output] = msg
    print(f"Message {msg} → output {output}")
    counter += 1
    return results
```

**What to observe:** Real-time routing decisions as network runs

### Experiment 5: Uneven Distribution

**Route more to one output:**
```python
def weighted_router(msg):
    # 50% to output 0, 25% to output 1, 25% to output 2
    if msg % 4 < 2:
        return [msg, None, None]
    elif msg % 4 == 2:
        return [None, msg, None]
    else:
        return [None, None, msg]
```

**What to observe:** Uneven distribution across outputs

## Real-World Use Cases

### Use Case 1: Load Balancing
```python
# Distribute work across 5 worker nodes
network([
    (task_source, load_balancer),
    (load_balancer.out_0, worker_0),
    (load_balancer.out_1, worker_1),
    (load_balancer.out_2, worker_2),
    (load_balancer.out_3, worker_3),
    (load_balancer.out_4, worker_4)
])
```

### Use Case 2: Priority Routing
```python
def route_by_priority(msg):
    if msg['priority'] == 'HIGH':
        return [msg, None, None]  # Fast lane
    elif msg['priority'] == 'MEDIUM':
        return [None, msg, None]  # Normal lane
    else:
        return [None, None, msg]  # Slow lane
```

### Use Case 3: Geographic Routing
```python
def route_by_region(user_data):
    region = user_data['region']
    if region == 'US':
        return [user_data, None, None]
    elif region == 'EU':
        return [None, user_data, None]
    else:
        return [None, None, user_data]
```

### Use Case 4: Error Handling
```python
def route_valid_and_errors(msg):
    if is_valid(msg):
        return [msg, None]  # Valid → processor
    else:
        return [None, msg]  # Invalid → error handler
```

## Next Steps

You now understand how to route messages to specific outputs! Split is powerful for load balancing and conditional routing.

**Next module:** [Module 06: Merge with Synchronization](../module_06_merge_synch/) - Learn how to merge messages from multiple sources while maintaining synchronization.

**Try combining split with other patterns:**
- Split after fanout (broadcast, then route)
- Split before fanin (route, then merge)
- Multiple splits (hierarchical routing)

**Want to see split with real file I/O?** Check `variations/file_output.py` for the same pattern writing to actual files.

**Want to go deeper?** Read [How It Works](../../docs/HOW_IT_WORKS.md) to understand how DisSysLab manages multiple output ports.

## Quick Reference

**Basic split pattern:**
```python
router = MyRouter(num_outputs=3)
splitter = Split(fn=router.run, num_outputs=3, name="splitter")

network([
    (source, splitter),
    (splitter.out_0, dest1),
    (splitter.out_1, dest2),
    (splitter.out_2, dest3)
])
```

**Split function contract:**
```python
def my_router(msg):
    # Return list of num_outputs elements
    # Exactly one (or more) should be the message
    # Rest should be None
    return [msg, None, None]  # Send to output 0
```

**Remember:**
- Split sends each message to ONE (or more) specific outputs
- Your function returns a LIST matching num_outputs
- Use port references: `splitter.out_0`, `splitter.out_1`, etc.
- None in the list means "skip this output"
- Split ≠ Fanout (split routes, fanout broadcasts)

---

**Questions or stuck?** Review the "Common Mistakes" section or check [Troubleshooting](../../docs/troubleshooting.md).