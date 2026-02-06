# Common Mistake: Recreating Stateful Objects

## The Problem

Students often write code like this:

```python
def get_items_from_list():
    """WRONG: Creates new source every time!"""
    source = ListSource(items=["hello", "world"])
    return source.run()

source = Source(fn=get_items_from_list, name="src")
```

**What happens:**
- Source agent calls `get_items_from_list()` repeatedly
- Each call creates a NEW `ListSource` with `count=0`
- Always returns `items[0]` → infinite loop!
- Network hangs forever returning "hello"

## The Fix

Create the stateful object **once**, then pass its method:

```python
# CORRECT: Create stateful object once
list_source = ListSource(items=["hello", "world"])

# Pass the bound method (not a function that creates it)
source = Source(fn=list_source.run, name="src")
```

**Why this works:**
- `list_source` is created once
- `list_source.run` is a bound method that maintains state
- Each call increments `count` properly
- Returns `None` when exhausted → network terminates correctly

## Pattern: Stateful vs Stateless

### ❌ Stateless Functions (Don't Need Instance)
```python
def double(x):
    return x * 2

transform = Transform(fn=double, name="doubler")
```

### ✅ Stateful Objects (Need Instance)
```python
# Create instance ONCE
counter = Counter(start=0, end=10)

# Pass the method
source = Source(fn=counter.run, name="counter")
```

## Teaching Point

**State must persist between calls:**
- Sources that iterate through data need state (index, position, etc.)
- Create the stateful object ONCE before wrapping in agent
- Pass the bound method, not a factory function

## Good Error Message

When network times out, it now shows:

```
⏱️  Network did not complete within 30 seconds

🔍 These agents are still running (may be hung):
   - list_source

💡 Common causes of hanging:
   1. Source not sending STOP signal when done
   2. Agent waiting forever on recv() with no data
   3. Infinite loop in agent logic  ← THIS ONE!
   4. Deadlock between agents
```

This helps students identify the issue quickly!

## Debug Technique

Add print statements to see what's happening:

```python
def get_items_from_list():
    result = list_source.run()
    print(f"Source returned: {result}")  # Shows the infinite loop
    return result
```

When you see the same value repeated forever, you know there's a state problem.

## Related Concepts

This teaches:
- **Closure** - Methods carry their object's state
- **State management** - Who owns the state?
- **Debugging** - How to spot infinite loops
- **Design patterns** - Factory vs instance methods