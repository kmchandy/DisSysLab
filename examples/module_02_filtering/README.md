# Module 02: Filtering - Conditional Message Processing

Learn how to selectively process messages by filtering out unwanted data using `None`.

## What You'll Learn

- How to filter messages by returning `None`
- Why returning `None` drops a message completely
- How to build conditional processing pipelines
- Common filtering patterns (keep/drop based on conditions)
- How filtering affects downstream nodes

## The Problem We're Solving

Not all data should be processed equally. Sometimes you want to:
- Skip invalid data (filter out malformed entries)
- Process only items meeting criteria (only process orders over $100)
- Remove noise (filter out spam messages)
- Sample data (process every 10th item)

In traditional programming, you'd use `if` statements throughout your code. In DisSysLab, you use **filter nodes** that return `None` to drop unwanted messages. This keeps your processing pipeline clean and modular.

## Network Topology

Our example filters numbers in a simple pipeline:
```
[1,2,3,4,5,6,7,8,9,10]
        ↓
   (source)
        ↓
  [filter_even] ← Returns None for odd numbers
        ↓
   [2,4,6,8,10] ← Only even numbers pass through
        ↓
  (collector)
```

**Key insight:** Numbers 1,3,5,7,9 are **dropped** by the filter - they never reach the collector.

## The Code Walkthrough

### Step 1: Write Ordinary Python Functions
```python
number_source = ListSource(items=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

def keep_only_even(number):
    """
    Filter function: keeps even numbers, drops odd numbers.
    
    Key insight: Returning None tells DisSysLab to DROP this message.
    """
    if number % 2 == 0:
        return number  # Pass even numbers through
    else:
        return None    # Drop odd numbers
```

**What's happening:**
- `keep_only_even()` is our **filter function**
- **Returns the value** if the condition is met (even number) → message passes through
- **Returns `None`** if condition fails (odd number) → message is **dropped**
- No other processing - we're focusing purely on the filtering concept

**The magic of `None`:** When a Transform node returns `None`, DisSysLab:
1. Does NOT send a message to downstream nodes
2. Does NOT create an empty/null message
3. Simply drops that message from the network

It's like the message never existed for downstream nodes!

### Step 2: Wrap Functions into Network Nodes

Using the same pattern from Module 01:
```python
source = Source(
    fn=number_source.run,
    name="number_source"
)

filter_even = Transform(
    fn=keep_only_even,
    name="filter_even"
)

results = []
collector = Sink(
    fn=results.append,
    name="collector"
)
```

**Key observation:** The filter is just a `Transform` node! There's no special "Filter" node type. Any Transform that returns `None` becomes a filter.

### Step 3: Define the Network Topology
```python
g = network([
    (source, filter_even),      # All numbers go to filter
    (filter_even, collector)    # Only even numbers continue
])
```

**What flows through each connection:**
- `source → filter_even`: [1,2,3,4,5,6,7,8,9,10] (all numbers)
- `filter_even → collector`: [2,4,6,8,10] (odd numbers dropped!)

**The simplicity is intentional:** We want to see filtering behavior clearly without other processing steps getting in the way.

### Step 4: Run the Network
```python
g.run_network()
```

**What happens during execution:**

**Source produces:** 1
- `filter_even` receives 1
- `keep_only_even(1)` returns `None` (odd)
- Message **dropped** - collector never sees it

**Source produces:** 2
- `filter_even` receives 2
- `keep_only_even(2)` returns 2 (even)
- Message passes to `collector`
- `collector` receives 2, appends to results

This repeats for all numbers:
- 1 → ❌ dropped
- 2 → ✓ collected
- 3 → ❌ dropped
- 4 → ✓ collected
- 5 → ❌ dropped
- 6 → ✓ collected
- 7 → ❌ dropped
- 8 → ✓ collected
- 9 → ❌ dropped
- 10 → ✓ collected

### Step 5: Verify Results
```python
print(f"Results: {results}")
# Output: Results: [2, 4, 6, 8, 10]

print(f"  Started with: 10 numbers")
print(f"  Filtered to: 5 even numbers")
print(f"  Dropped: 5 odd numbers")
```

## Running This Example

From the DisSysLab root directory:
```bash
python3 -m examples.module_02_filtering.example
```

**Expected output:**
```
Results: [2, 4, 6, 8, 10]
✓ Filtering completed successfully!
  Started with: 10 numbers
  Filtered to: 5 even numbers
  Dropped: 5 odd numbers
```

## Key Concepts

### Concept 1: The Power of `None`

**Returning `None` from a Transform means "drop this message":**
```python
def my_filter(value):
    if some_condition:
        return value      # ✓ Pass through
    else:
        return None       # ✗ Drop it
```

**What happens downstream:**
- Nodes after the filter only see messages that passed
- It's as if dropped messages never existed
- No empty/null/placeholder messages are created

**Why this is powerful:**
- Clean separation: filtering logic in one place
- Downstream nodes don't need to check conditions
- Easy to add/remove filters without changing other nodes

### Concept 2: Filters are Just Transforms

There's no special "Filter" node type. Any `Transform` that sometimes returns `None` is effectively a filter.

**Simple filter (always returns None or value):**
```python
def is_valid(data):
    if data > 0:
        return data
    return None  # Drop negative/zero values
```

**Enriching filter (returns modified value or None):**
```python
def validate_and_clean(text):
    if len(text) < 3:
        return None  # Drop short strings
    return text.strip().lower()  # Pass cleaned version
```

Both are `Transform` nodes!

### Concept 3: Multi-Stage Filtering

You can chain multiple filters:
```
source → filter1 → filter2 → filter3 → processor
```

Each filter drops some messages:
- filter1: keeps 80% of messages
- filter2: keeps 70% of what filter1 passed
- filter3: keeps 90% of what filter2 passed
- processor: receives 80% × 70% × 90% = 50.4% of original messages

**Best practice:** Put the most aggressive filter first (drops the most) to reduce work for downstream filters.

### Concept 4: Filtering vs. Branching

**Filtering (this module):** Drop messages completely
```python
def filter_spam(message):
    if is_spam(message):
        return None  # Gone forever
    return message
```

**Branching (Module 03: Fanout):** Send different messages to different paths
```python
# In fanout, ALL messages go somewhere
# Spam goes to spam_handler, valid messages go to processor
```

Use filtering when you want to **discard** data.  
Use branching when you want to **route** data differently.

### Concept 5: Conditional Processing Patterns

**Pattern 1: Threshold Filter**
```python
def above_threshold(value, threshold=100):
    if value > threshold:
        return value
    return None
```

**Pattern 2: Type Validator**
```python
def valid_emails_only(contact):
    if '@' in contact and '.' in contact:
        return contact
    return None
```

**Pattern 3: Deduplication**
```python
seen = set()
def deduplicate(item):
    if item in seen:
        return None  # Already seen, drop it
    seen.add(item)
    return item
```

**Pattern 4: Sampling**
```python
counter = [0]  # Using list to make it mutable in closure
def every_nth(item, n=10):
    counter[0] += 1
    if counter[0] % n == 0:
        return item  # Keep every 10th item
    return None
```

## Common Mistakes

### Mistake 1: Forgetting to Return the Value
```python
# ❌ Wrong - forgot to return the value!
def keep_positive(number):
    if number > 0:
        number  # This does nothing!
    return None

# All messages are dropped!
```
```python
# ✓ Correct - return the value
def keep_positive(number):
    if number > 0:
        return number  # Pass it through
    return None
```

**Why it fails:** Without `return`, the function returns `None` by default.  
**Fix:** Always explicitly `return` the value you want to pass through.

### Mistake 2: Returning Empty String/Zero Instead of None
```python
# ❌ Wrong - returns empty string, not None
def filter_short_strings(text):
    if len(text) > 5:
        return text
    return ""  # Empty string is NOT the same as None!

# Downstream gets empty strings, not dropped messages!
```
```python
# ✓ Correct - return None to drop
def filter_short_strings(text):
    if len(text) > 5:
        return text
    return None  # Actually drops the message
```

**Why it fails:** `""`, `0`, `False`, `[]` are all valid values, not "drop message" signals.  
**Fix:** Only `None` drops messages. Be explicit: `return None`.

### Mistake 3: Returning None Accidentally
```python
# ❌ Wrong - function returns None when it shouldn't
def add_prefix(text):
    text = "PREFIX_" + text
    # Forgot to return! Returns None by default

# All messages are dropped!
```
```python
# ✓ Correct - return the modified value
def add_prefix(text):
    text = "PREFIX_" + text
    return text
```

**Why it fails:** Python functions return `None` if you don't explicitly return something.  
**Fix:** Always end with `return <value>` for Transform nodes (unless intentionally filtering).

### Mistake 4: Trying to Filter in a Sink
```python
# ❌ Wrong - Sinks can't filter!
collector = Sink(
    fn=lambda x: results.append(x) if x > 10 else None,
    name="collector"
)

# This doesn't work - Sinks have no downstream nodes!
```
```python
# ✓ Correct - Filter before the Sink
filter_node = Transform(
    fn=lambda x: x if x > 10 else None,
    name="filter"
)

collector = Sink(
    fn=results.append,
    name="collector"
)

# Network: ... → filter_node → collector
```

**Why it fails:** Sinks are endpoints - they can't "drop" messages to nowhere.  
**Fix:** Put filtering logic in a Transform node **before** the Sink.

### Mistake 5: Modifying Without Returning
```python
# ❌ Wrong - modifies in place, doesn't return
def uppercase_filter(text):
    if len(text) > 3:
        text.upper()  # This creates a new string but doesn't return it!
    return None

# All messages dropped!
```
```python
# ✓ Correct - return the modified value
def uppercase_filter(text):
    if len(text) > 3:
        return text.upper()
    return None
```

**Why it fails:** `.upper()` doesn't modify the string, it returns a new one. You must return it!  
**Fix:** Remember that most Python operations return new values - you need to `return` them.

## Experiments to Try

Modify `example.py` to explore filtering behavior:

### Experiment 1: Reverse the Filter

**Modify:**
```python
def keep_only_odd(number):
    if number % 2 == 1:  # Changed from == 0
        return number
    return None
```

**What to observe:** Now you get [1, 3, 5, 7, 9] (odd numbers only)

### Experiment 2: Add a Second Filter

**Add after `filter_even`:**
```python
def keep_small(number):
    """Keep only numbers less than 7."""
    if number < 7:
        return number
    return None

filter_small = Transform(
    fn=keep_small,
    name="filter_small"
)
```

**Modify network:**
```python
g = network([
    (source, filter_even),
    (filter_even, filter_small),  # ← Second filter
    (filter_small, collector)
])
```

**What to observe:** Only [2, 4, 6] (even numbers that are also < 7)

### Experiment 3: Filter by Range

**Replace filter with:**
```python
def keep_in_range(number, min_val=3, max_val=7):
    if min_val <= number <= max_val:
        return number
    return None

filter_range = Transform(
    fn=keep_in_range,
    name="filter_range"
)
```

**What to observe:** Only [3, 4, 5, 6, 7] (numbers in range 3-7)

### Experiment 4: Add Print Statements

**Inside your filter function:**
```python
def keep_only_even(number):
    if number % 2 == 0:
        print(f"  ✓ Passing: {number}")
        return number
    else:
        print(f"  ✗ Dropping: {number}")
        return None
```

**What to observe:** See in real-time which messages pass and which are dropped.

### Experiment 5: Count Dropped Messages

**Add a counter:**
```python
dropped_count = [0]  # Use list to make it mutable

def keep_only_even(number):
    if number % 2 == 0:
        return number
    else:
        dropped_count[0] += 1
        return None

# After running:
print(f"Dropped {dropped_count[0]} messages")
```

**What to observe:** Track how many messages your filter removes.

## Real-World Use Cases

### Use Case 1: Data Cleaning Pipeline
```python
def remove_invalid_emails(email):
    if '@' in email and '.' in email.split('@')[1]:
        return email
    return None  # Drop malformed emails
```

### Use Case 2: Spam Filter
```python
SPAM_KEYWORDS = ['viagra', 'winner', 'click here']

def filter_spam(message):
    message_lower = message.lower()
    if any(word in message_lower for word in SPAM_KEYWORDS):
        return None  # Drop spam
    return message
```

### Use Case 3: Threshold-Based Processing
```python
def high_priority_only(order):
    if order['amount'] > 1000:  # Only process large orders
        return order
    return None
```

### Use Case 4: Sampling for Analysis
```python
import random

def sample_10_percent(data):
    if random.random() < 0.1:  # 10% chance
        return data
    return None  # Drop 90% of messages
```

## Next Steps

You now understand conditional processing with filters! This is a powerful pattern you'll use constantly.

**Next module:** [Module 03: Fanout](../module_03_fanout/) - Learn how to broadcast messages to multiple destinations simultaneously.

**Want more filtering examples?** Check `variations/` folder for:
- Text filtering (length, content, regex)
- Numeric filtering (ranges, conditions)
- Data validation patterns

**Want to go deeper?** Read [How It Works](../../docs/HOW_IT_WORKS.md) to understand message flow when filters drop messages.

## Quick Reference

**Basic filter pattern:**
```python
def my_filter(value):
    if condition:
        return value      # ✓ Pass through
    else:
        return None       # ✗ Drop it
```

**Filter with modification:**
```python
def clean_and_filter(text):
    if len(text) < 3:
        return None  # Drop short strings
    return text.strip().lower()  # Pass cleaned version
```

**Remember:**
- ✓ Return the value to pass it through
- ✗ Return `None` to drop the message
- Filters are just Transform nodes
- Downstream nodes only see messages that passed
- You can chain multiple filters

---

**Questions or stuck?** Review the "Common Mistakes" section or check [Troubleshooting](../../docs/troubleshooting.md).