# blocks/ - Implementation Guide

## Overview

The `dsl/blocks/` directory contains pre-built agent types that provide common patterns for building distributed systems. These agents are the building blocks students use to construct networks.

**Available Agents:**
- **Source**: Generates messages (no inputs → one output)
- **Transform**: Processes messages (one input → one output)
- **Sink**: Consumes messages (one input → no outputs)
- **Split**: Routes messages to multiple outputs based on function
- **Broadcast**: Copies messages to all outputs (fanout pattern)
- **MergeAsynch**: Combines multiple inputs (fanin pattern)

**Design Philosophy:**
1. **Simple interface**: Students work with ordinary Python functions
2. **Uniform API**: All agents follow consistent patterns
3. **Fail-fast**: Errors are immediately visible for learning
4. **Flexible messages**: Support any Python type, not just dicts

---

## Directory Structure

```
dsl/blocks/
├── __init__.py          # Exports all agent types
├── source.py            # Source agent
├── transform.py         # Transform agent
├── sink.py              # Sink agent
├── split.py             # Split (routing) agent
├── fanout.py            # Broadcast agent
└── fanin.py             # MergeAsynch agent
```

---

## Common Patterns

### Pattern 1: Required Name Parameter

All block agents require a `name` parameter in `__init__`. This is enforced by validation.

```python
# Correct - name is required:
source = Source(fn=data.run, name="src")
transform = Transform(fn=process, name="trans")
sink = Sink(fn=save, name="sink")

# Incorrect - will raise ValueError:
source = Source(fn=data.run)  # ERROR: missing name
```

**Why required?**
- Debugging: Clear identification in error messages
- Visualization: Labeled nodes in network diagrams
- Inspection: Can identify agents in compiled network

**Implementation pattern:**
```python
def __init__(self, ..., *, name: str):
    if not name:
        raise ValueError("Agent name is required")
    super().__init__(name=name, inports=[...], outports=[...])
```

### Pattern 2: Simple Port Structure

**Agents with single ports:**
- Implicit default ports (`"in_"` and/or `"out_"`)
- Students can use agent directly in edges

**Agents with multiple ports:**
- Numbered ports (`"in_0"`, `"in_1"`, `"out_0"`, `"out_1"`)
- Students must use dot notation (`split.out_0`)

### Pattern 3: Callable Pattern with `run` Alias

All agents use `__call__` as the main method with `run` as an alias:

```python
def __call__(self) -> None:
    # Main processing logic
    ...

run = __call__  # Alias for consistency
```

This allows both `agent.run()` and `agent()` to work.

### Pattern 4: STOP Signal Handling

**Receivers (Transform, Sink, Split):**
```python
while True:
    msg = self.recv("in_")
    if msg is STOP:
        self.broadcast_stop()  # Forward to outputs
        return
    # ... process message ...
```

**Generators (Source):**
```python
while True:
    msg = self._fn()
    if msg is None:  # Exhausted
        self.broadcast_stop()
        return
    self.send(msg, "out_")
```

### Pattern 5: Error Handling (Fail-Fast)

All agents catch exceptions, log them, and stop the pipeline:

```python
try:
    result = self._fn(msg)
except Exception as e:
    print(f"[{AgentType}] Error in fn: {e}")
    print(traceback.format_exc())
    self.broadcast_stop()
    return
```

**Why fail-fast?**
- Students see errors immediately
- Clear which agent failed
- Easy to debug
- Better than silent failures

---

## source.py - Source Agent

### Purpose

Repeatedly calls a function to generate messages until it returns `None`.

### Key Characteristics

- **No inputs**: `inports = []`
- **Single output**: `outports = ["out_"]`
- **Pull-based**: Calls `fn()` repeatedly
- **Termination**: Stops when `fn()` returns `None`
- **Optional rate limiting**: `interval` parameter controls message pace

### Design Pattern

**Stateful instance with callable method:**

```python
class DataProvider:
    def __init__(self, items):
        self.items = items
        self.index = 0
    
    def run(self):
        if self.index >= len(self.items):
            return None  # Exhausted
        item = self.items[self.index]
        self.index += 1
        return {"value": item}

# Create instance
provider = DataProvider([1, 2, 3])

# Wrap in Source
source = Source(fn=provider.run, interval=0)
```

**Why this pattern?**
- Instance maintains state (index, counters, etc.)
- Method accesses instance variables naturally
- Same pattern as Transform/Sink (uniform API)
- No need to understand generators/yield

### Implementation

```python
from __future__ import annotations
import traceback
import time
from typing import Any, Callable, Optional
from dsl.core import Agent, STOP


class Source(Agent):
    """
    Source Agent: Repeatedly calls a function to generate messages.

    **Ports:**
    - Inports: [] (no inputs)
    - Outports: ["out_"]

    **Function Contract:**
    fn() must:
    - Return a message (any type) on each call
    - Return None when exhausted (no more messages)
    - Maintain its own state between calls

    **Message Flow:**
    1. Calls fn() repeatedly
    2. Sends each returned message to "out_"
    3. When fn() returns None → sends STOP and terminates
    4. Optional: delays interval seconds between messages

    **Rate Limiting:**
    - interval=0 (default): emit as fast as possible
    - interval=1.0: emit one message per second
    - Useful for simulating real-time streams

    **Error Handling:**
    - Exceptions during fn() are caught and logged
    - STOP signal sent to downstream agents
    - Pipeline terminates gracefully
    """

    def __init__(
        self, 
        fn: Callable[[], Optional[Any]],
        *,
        name: str,
        interval: float = 0
    ):
        """
        Initialize Source agent.

        Args:
            fn: Callable that returns messages or None when exhausted.
                Signature: fn() -> Optional[message]
            name: Unique name for this agent (REQUIRED)
            interval: Delay in seconds between messages (default: 0)

        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
        """
        if not name:
            raise ValueError("Source agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                "Source fn must be callable with signature: fn() -> Optional[message]"
            )

        super().__init__(name=name, inports=[], outports=["out_"])
        self._fn = fn
        self._interval = interval

    def __call__(self) -> None:
        """
        Main processing loop.

        Repeatedly calls fn() and emits messages until exhausted.
        """
        try:
            while True:
                # Get next message
                msg = self._fn()

                # None means source is exhausted
                if msg is None:
                    self.broadcast_stop()
                    return

                # Send message downstream
                self.send(msg, "out_")

                # Optional rate limiting
                if self._interval > 0:
                    time.sleep(self._interval)

        except Exception as e:
            print(f"[Source] Error in fn: {e}")
            print(traceback.format_exc())
            self.broadcast_stop()

    run = __call__

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        interval_str = f", interval={self._interval}" if self._interval > 0 else ""
        return f"<Source fn={fn_name}{interval_str}>"

    def __str__(self) -> str:
        return "Source"
```

### Usage Examples

**Simple list source:**
```python
class ListSource:
    def __init__(self, items):
        self.items = items
        self.index = 0
    
    def run(self):
        if self.index >= len(self.items):
            return None
        item = self.items[self.index]
        self.index += 1
        return item  # Return any type (int, str, dict, etc.)

data = ListSource([1, 2, 3])
source = Source(fn=data.run, name="list_src")
```

**Counter source:**
```python
class CounterSource:
    def __init__(self, max_count):
        self.count = 0
        self.max_count = max_count
    
    def run(self):
        if self.count >= self.max_count:
            return None
        result = self.count  # Just return the number
        self.count += 1
        return result

counter = CounterSource(max_count=10)
source = Source(fn=counter.run, name="counter")
```

**With rate limiting:**
```python
data = ListSource([1, 2, 3])
source = Source(fn=data.run, name="slow_src", interval=1.0)  # One message per second
```

**Using lambda (simple cases):**
```python
items = iter([1, 2, 3])
source = Source(fn=lambda: next(items, None), name="iter_src")
```

**When using dict messages (optional):**
```python
class DictSource:
    def __init__(self, items):
        self.items = items
        self.index = 0
    
    def run(self):
        if self.index >= len(self.items):
            return None
        item = self.items[self.index]
        self.index += 1
        return {"value": item, "index": self.index}

data = DictSource([1, 2, 3])
source = Source(fn=data.run, name="dict_src")
```

### Design Notes

**Q: Why `fn()` returns `None` instead of using generators?**

A: Simpler for beginners:
- `return None` when done vs understanding `yield`
- Instance methods maintain state naturally
- Uniform API with Transform/Sink
- Can use lambdas for simple cases

**Q: Why call `fn()` repeatedly instead of once?**

A: Pull-based control:
- Source controls generation pace
- Instance method maintains state between calls
- Easy to test (just call `fn()` and check result)
- Natural pattern for stateful data sources

---

## transform.py - Transform Agent

### Purpose

Applies a function to transform each message flowing through the network.

### Key Characteristics

- **Single input**: `inports = ["in_"]`
- **Single output**: `outports = ["out_"]`
- **Stateless or stateful**: Function can be pure or method on instance
- **Filtering**: Returning `None` drops the message
- **Fail-fast**: First error stops pipeline

### Design Pattern

**Stateless transformation (pure function):**

```python
def double(msg):
    return {"value": msg["value"] * 2}

transform = Transform(fn=double)
```

**Stateful transformation (instance method):**

```python
class Counter:
    def __init__(self):
        self.count = 0
    
    def add_index(self, msg):
        self.count += 1
        return {**msg, "index": self.count}

counter = Counter()
transform = Transform(fn=counter.add_index)
```

### Implementation

```python
from __future__ import annotations
import traceback
from typing import Any, Callable, Optional, Dict
from dsl.core import Agent, STOP


class Transform(Agent):
    """
    Transform Agent: Applies a function to transform messages.

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_"]

    **Function Contract:**
    fn(msg) must:
    - Take a single message argument
    - Return transformed message or None to filter
    - Signature: fn(msg) -> Optional[msg]

    **Message Flow:**
    1. Receives message from "in_"
    2. Applies fn(msg) to transform it
    3. Sends result to "out_"
    4. If fn returns None → message filtered (not sent)
    5. On STOP → broadcasts STOP and terminates

    **Filtering:**
    Returning None drops the message - it won't be sent downstream.
    This enables filter patterns within transforms.

    **Error Handling:**
    - Exceptions caught and logged
    - Pipeline stops immediately (fail-fast)
    - STOP broadcast to downstream agents
    - Helps students debug quickly

    **State:**
    Use instance methods for stateful transformations that need
    counters, caches, or other state between messages.
    """

    def __init__(
        self, 
        fn: Callable[..., Optional[Any]], 
        *, 
        name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize Transform agent.

        Args:
            fn: Callable that transforms messages.
                Signature: fn(msg, **params) -> Optional[msg]
                Returns None to filter message
            name: Unique name for this agent (REQUIRED)
            params: Optional dict of keyword arguments passed to fn

        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
        """
        if not name:
            raise ValueError("Transform agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                f"Transform fn must be callable. Got {type(fn).__name__}"
            )

        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self._fn = fn
        self._params = params or {}

    def __call__(self) -> None:
        """
        Main processing loop.

        Receives, transforms, and sends messages until STOP.
        """
        while True:
            msg = self.recv("in_")

            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return

            # Transform message
            try:
                result = self._fn(msg, **self._params)
            except Exception as e:
                print(f"[Transform] Error in fn: {e}")
                print(traceback.format_exc())
                self.broadcast_stop()
                return

            # Send result (None filtered automatically by send())
            self.send(result, "out_")

    run = __call__

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Transform fn={fn_name}>"

    def __str__(self) -> str:
        return "Transform"
```

### Usage Examples

**Simple stateless transform:**
```python
def double(msg):
    return msg * 2

transform = Transform(fn=double, name="doubler")
```

**Transform with parameters (simple functions):**
```python
def scale(msg, factor):
    return msg * factor

transform = Transform(fn=scale, params={"factor": 10}, name="scaler")
```

**Multiple parameters:**
```python
def linear(msg, m, b):
    return msg * m + b

transform = Transform(fn=linear, params={"m": 2, "b": 5}, name="linear")
```

**Stateful transform (class method when you need state):**
```python
class Counter:
    def __init__(self):
        self.count = 0
    
    def add_index(self, msg):
        self.count += 1
        return (msg, self.count)  # Return tuple with index

counter = Counter()
transform = Transform(fn=counter.add_index, name="counter")
```

**Filter pattern (None drops messages):**
```python
def filter_range(msg, min_val, max_val):
    if min_val <= msg <= max_val:
        return msg
    return None  # Filtered out

transform = Transform(
    fn=filter_range, 
    params={"min_val": 0, "max_val": 100},
    name="range_filter"
)
```

**Text processing (when using dict messages):**
```python
def clean_text(msg, pattern):
    import re
    text = msg["text"]
    cleaned = re.sub(pattern, '', text)
    return {**msg, "clean_text": cleaned}

transform = Transform(
    fn=clean_text,
    params={"pattern": r'[^\w\s.,!?-]'},
    name="cleaner"
)
```

### Design Notes

**Q: When to use params vs class methods?**

A: Choose based on complexity:

**Use `params` for simple configuration:**
```python
# Clean and simple - no state needed
def scale(msg, factor):
    return msg * factor

transform = Transform(fn=scale, params={"factor": 10}, name="scaler")
```

**Use class methods when you need state:**
```python
# State required - counter must persist
class Counter:
    def __init__(self):
        self.count = 0
    
    def add_index(self, msg):
        self.count += 1
        return (msg, self.count)

counter = Counter()
transform = Transform(fn=counter.add_index, name="counter")
```

**Both patterns work together:**
```python
# Stateful class with additional parameters
class Analyzer:
    def __init__(self):
        self.history = []
    
    def analyze(self, msg, threshold):
        self.history.append(msg)
        if msg > threshold:
            return (msg, len(self.history))
        return None

analyzer = Analyzer()
transform = Transform(
    fn=analyzer.analyze, 
    params={"threshold": 100},
    name="analyzer"
)
```

**Q: Why fail-fast on exceptions?**

A: Educational benefit:
- Students see errors immediately
- Clear which transform failed
- Easy to add breakpoints
- Better than silent failures

---

## sink.py - Sink Agent

### Purpose

Terminal node that consumes messages for side effects (printing, saving, collecting).

### Key Characteristics

- **Single input**: `inports = ["in_"]`
- **No outputs**: `outports = []`
- **Side effects only**: Return value ignored
- **Filters None**: None messages not passed to `fn`
- **Finalize support**: Calls `fn.finalize()` if present during shutdown

### Design Pattern

**Simple sink (built-in function):**
```python
sink = Sink(fn=print)
```

**Collector sink (closure):**
```python
results = []
sink = Sink(fn=results.append)
```

**Stateful sink (instance method):**
```python
class ResultCollector:
    def __init__(self):
        self.results = []
        self.count = 0
    
    def process(self, msg):
        self.count += 1
        self.results.append(msg)
        if self.count % 10 == 0:
            print(f"Processed {self.count} messages")

collector = ResultCollector()
sink = Sink(fn=collector.process)
```

### Implementation

```python
from __future__ import annotations
import traceback
from typing import Any, Callable, Dict, Optional
from dsl.core import Agent, STOP


class Sink(Agent):
    """
    Sink Agent: Terminal node that consumes messages.

    **Ports:**
    - Inports: ["in_"]
    - Outports: [] (terminal node)

    **Function Contract:**
    fn(msg) should:
    - Take a single message argument
    - Perform side effects (print, save, collect)
    - Return value is ignored

    **Message Flow:**
    1. Receives messages from "in_"
    2. Filters out None messages (doesn't call fn)
    3. Calls fn(msg) for each message
    4. On STOP → terminates (no broadcast, no outputs)

    **Finalize Support:**
    If fn has a finalize() method, it's called during shutdown.
    Useful for closing files, flushing buffers, etc.

    **Error Handling:**
    - Exceptions caught and logged
    - Pipeline terminates on errors
    - Clean termination guaranteed
    """

    def __init__(
        self, 
        fn: Callable[..., None], 
        *, 
        name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize Sink agent.

        Args:
            fn: Callable that processes messages.
                Signature: fn(msg, **params) -> None
                Return value ignored
            name: Unique name for this agent (REQUIRED)
            params: Optional dict of keyword arguments passed to fn

        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
        """
        if not name:
            raise ValueError("Sink agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                f"Sink fn must be callable. Got {type(fn).__name__}"
            )

        super().__init__(name=name, inports=["in_"], outports=[])
        self._fn = fn
        self._params = params or {}

    def __call__(self) -> None:
        """
        Main processing loop.

        Receives and processes messages until STOP.
        """
        try:
            while True:
                msg = self.recv("in_")

                # Terminate on STOP
                if msg is STOP:
                    return

                # Filter out None messages
                if msg is None:
                    continue

                # Process message
                try:
                    self._fn(msg, **self._params)
                except Exception as e:
                    print(f"[Sink] Error in fn: {e}")
                    print(traceback.format_exc())
                    return

        except Exception as e:
            print(f"[Sink] Error: {e}")
            print(traceback.format_exc())
            return

    def shutdown(self) -> None:
        """
        Cleanup after run() completes.

        Calls finalize() on wrapped function if it exists.
        Ensures files closed, connections cleaned up, etc.
        """
        if hasattr(self._fn, 'finalize') and callable(self._fn.finalize):
            try:
                print(f"[Sink] Finalizing {self._fn.__name__}...")
                self._fn.finalize()
            except Exception as e:
                print(f"[Sink] Error during finalize: {e}")

    run = __call__

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Sink fn={fn_name}>"

    def __str__(self) -> str:
        return "Sink"
```

### Usage Examples

**Print sink:**
```python
def print_msg(msg):
    print(f"Received: {msg}")

sink = Sink(fn=print_msg, name="printer")

# Or just use print directly:
sink = Sink(fn=print, name="console")
```

**Sink with parameters:**
```python
def save_to_file(msg, filename):
    with open(filename, "a") as f:
        f.write(str(msg) + "\n")

sink = Sink(fn=save_to_file, params={"filename": "output.txt"}, name="file_writer")
```

**Multiple parameters:**
```python
def log_message(msg, prefix, level):
    print(f"[{level}] {prefix}: {msg}")

sink = Sink(
    fn=log_message, 
    params={"prefix": "DATA", "level": "INFO"},
    name="logger"
)
```

**Collector sink:**
```python
results = []
sink = Sink(fn=results.append, name="collector")
```

**Stateful sink with finalize:**
```python
class FileHandler:
    def __init__(self, filename):
        self.filename = filename
        self.file = None
    
    def process(self, msg):
        if self.file is None:
            self.file = open(self.filename, "w")
        self.file.write(str(msg) + "\n")
    
    def finalize(self):
        if self.file:
            self.file.close()
            print(f"Closed {self.filename}")

handler = FileHandler("output.txt")
sink = Sink(fn=handler.process, name="file_sink")
# handler.finalize() called automatically during shutdown
```

### Design Notes

**Q: Why filter None messages?**

A: Prevents errors:
- Transforms can filter by returning None
- Sink shouldn't process None values
- Explicit: None means "no message"

**Q: Why finalize() support?**

A: Resource cleanup:
- Files need to be closed
- Network connections need cleanup
- Buffers need flushing
- Standard pattern for cleanup

**Q: Why no broadcast_stop()?**

A: Sinks have no outputs:
- Terminal nodes in graph
- Nothing downstream to notify
- Just return from run()

---

## split.py - Split Agent

### Purpose

Routes messages to N outputs based on a routing function that returns a list.

### Key Characteristics

- **Single input**: `inports = ["in_"]`
- **Multiple outputs**: `outports = ["out_0", "out_1", ..., "out_N-1"]`
- **List-based routing**: Function returns list of N messages
- **Flexible**: Supports routing, multicast, and transformation
- **Filtering**: None values in list are filtered (not sent to that output)

### Design Pattern

**Routing function returns list of N messages:**

```python
class ContentRouter:
    def route(self, msg):
        if is_spam(msg):
            return [msg, None, None]  # Route to out_0
        elif is_abuse(msg):
            return [None, msg, None]  # Route to out_1
        else:
            return [None, None, msg]  # Route to out_2

router = ContentRouter()
split = Split(fn=router.route, num_outputs=3)
```

**Why list-based routing?**
- Supports routing (one output)
- Supports multicast (multiple outputs)
- Supports filtering (None values)
- Supports transformation (modify message)
- All in one pattern!

### Implementation

```python
from __future__ import annotations
import traceback
from typing import Any, Callable, List, Optional
from dsl.core import Agent, STOP


class Split(Agent):
    """
    Split Agent: Route messages to N outputs based on function.

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1", ..., "out_{N-1}"]

    **Function Contract:**
    fn(msg) must:
    - Take a single message argument
    - Return a list of N messages (one per output)
    - None values filtered (not sent to that output)
    - Signature: fn(msg) -> List[Optional[msg]]

    **Capabilities:**
    This pattern supports:
    - Routing: [msg, None, None] → only out_0
    - Multicast: [msg, msg, None] → both out_0 and out_1
    - Transform: [enriched_msg, None, None] → modified message to out_0
    - Filter: [None, None, None] → drop message completely

    **Message Flow:**
    1. Receives message from "in_"
    2. Calls fn(msg) to get list of N messages
    3. Sends each non-None message to corresponding output
    4. On STOP → broadcasts STOP to all outputs and terminates

    **Error Handling:**
    - Validates fn returns list of correct length
    - Catches exceptions in routing logic
    - Broadcasts STOP on errors
    """

    def __init__(
        self, 
        fn: Callable[[Any], List[Optional[Any]]], 
        *,
        num_outputs: int,
        name: str
    ) -> None:
        """
        Initialize Split agent.

        Args:
            fn: Callable that routes messages.
                Signature: fn(msg) -> List[Optional[msg]]
                Must return list of num_outputs messages
            num_outputs: Number of output ports to create
            name: Unique name for this agent (REQUIRED)

        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
            ValueError: If num_outputs < 2
        """
        if not name:
            raise ValueError("Split agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                f"Split fn must be callable. Got {type(fn).__name__}"
            )

        if num_outputs < 2:
            raise ValueError(
                f"Split requires at least 2 outputs, got {num_outputs}"
            )

        super().__init__(
            name=name,
            inports=["in_"],
            outports=[f"out_{i}" for i in range(num_outputs)]
        )
        self._fn = fn
        self.num_outputs = num_outputs

    def __call__(self) -> None:
        """
        Main processing loop.

        Routes messages via fn and sends to outputs.
        """
        while True:
            msg = self.recv("in_")

            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return

            try:
                # Get routing decisions
                results = self._fn(msg)

                # Validate results
                if not isinstance(results, (list, tuple)):
                    raise TypeError(
                        f"Split fn must return a list of {self.num_outputs} messages. "
                        f"Got {type(results).__name__}: {results!r}"
                    )

                if len(results) != self.num_outputs:
                    raise ValueError(
                        f"Split fn must return exactly {self.num_outputs} messages. "
                        f"Got {len(results)} messages: {results!r}"
                    )

                # Send to each output
                # (None values filtered automatically by send())
                for i, out_msg in enumerate(results):
                    self.send(out_msg, f"out_{i}")

            except Exception as e:
                print(f"[Split] Error in fn: {e}")
                print(traceback.format_exc())
                self.broadcast_stop()
                return

    run = __call__

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Split fn={fn_name} num_outputs={self.num_outputs}>"

    def __str__(self) -> str:
        return f"Split({self.num_outputs} outputs)"
```

### Usage Examples

**Simple value routing:**
```python
class EvenOddRouter:
    def route(self, msg):
        if msg % 2 == 0:
            return [msg, None]  # Even → out_0
        else:
            return [None, msg]  # Odd → out_1

router = EvenOddRouter()
split = Split(fn=router.route, num_outputs=2, name="even_odd")

g = network([
    (source, split),
    (split.out_0, even_handler),
    (split.out_1, odd_handler)
])
```

**Range-based routing:**
```python
class RangeRouter:
    def route(self, msg):
        if msg < 0:
            return [msg, None, None]  # Negative
        elif msg < 100:
            return [None, msg, None]  # Mid-range
        else:
            return [None, None, msg]  # Large

router = RangeRouter()
split = Split(fn=router.route, num_outputs=3, name="range_split")
```

**Round-robin routing:**
```python
class RoundRobinRouter:
    def __init__(self, num_outputs):
        self.num_outputs = num_outputs
        self.counter = 0
    
    def route(self, msg):
        results = [None] * self.num_outputs
        results[self.counter % self.num_outputs] = msg
        self.counter += 1
        return results

router = RoundRobinRouter(num_outputs=3)
split = Split(fn=router.route, num_outputs=3, name="round_robin")
```

**Multicast (send to multiple outputs):**
```python
class DuplicateRouter:
    def route(self, msg):
        if msg > 100:
            return [msg, msg, msg]  # Send to all outputs
        elif msg > 50:
            return [msg, msg, None]  # Send to two outputs
        else:
            return [msg, None, None]  # Send to one output

router = DuplicateRouter()
split = Split(fn=router.route, num_outputs=3, name="duplicator")
```

**Transform while routing:**
```python
class EnrichingRouter:
    def __init__(self):
        self.count = 0
    
    def route(self, msg):
        self.count += 1
        # Add metadata as tuple
        enriched = (msg, self.count)
        
        if msg > 0:
            return [enriched, None]
        else:
            return [None, enriched]

router = EnrichingRouter()
split = Split(fn=router.route, num_outputs=2, name="enricher")
```

**When using dict messages (optional):**
```python
class ContentRouter:
    def route(self, msg):
        if is_spam(msg["text"]):
            return [msg, None, None]  # Route to spam handler
        elif is_abuse(msg["text"]):
            return [None, msg, None]  # Route to abuse handler
        else:
            return [None, None, msg]  # Route to safe handler

router = ContentRouter()
split = Split(fn=router.route, num_outputs=3, name="router")
```

### Design Notes

**Q: Why list-based routing instead of index-based?**

A: More powerful:
```python
# Old way (index-based):
def router(msg):
    if is_spam(msg):
        return 0  # Route to out_0
    else:
        return 1  # Route to out_1

# New way (list-based):
def router(msg):
    if is_spam(msg):
        return [msg, None]  # Route to out_0
    elif needs_both(msg):
        return [msg, msg]  # Multicast!
    else:
        return [None, msg]  # Route to out_1
```

Benefits:
- Supports multicast (send to multiple outputs)
- Supports filtering (all None = drop)
- Supports transformation (modify message)
- Explicit about what goes where

**Q: Why validate list length strictly?**

A: Clear errors:
- Student forgot an output → immediate error
- List too short → crash before confusion
- List too long → crash before silent drop
- Better than mysterious behavior

---

## fanout.py - Broadcast Agent

### Purpose

Copies messages from one input to all outputs (fanout pattern). Auto-inserted by framework when one agent connects to multiple receivers.

### Key Characteristics

- **Single input**: `inports = ["in_"]`
- **Multiple outputs**: `outports = ["out_0", "out_1", ..., "out_N-1"]`
- **Deep copy**: Each output gets independent copy (prevents shared state bugs)
- **Auto-inserted**: Framework creates automatically for fanout
- **Transparent**: Students usually don't create directly

### Design Pattern

**Automatic insertion by framework:**

```python
# Student writes:
g = network([
    (source, handler_a),
    (source, handler_b),  # Fanout detected!
    (source, handler_c)
])

# Framework automatically inserts:
# broadcast = Broadcast(num_outports=3)
# And rewires to:
#   source → broadcast → handler_a
#                     → handler_b
#                     → handler_c
```

### Implementation

```python
from dsl.core import Agent, STOP
from typing import Optional, Any, Callable
import copy


class Broadcast(Agent):
    """
    Broadcast Agent: Copies messages to all outputs (fanout).

    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1", ..., "out_{N-1}"]

    **Message Flow:**
    1. Receives message from "in_"
    2. Creates deep copy for each output (prevents shared state)
    3. Sends copies to all outputs
    4. On STOP → broadcasts STOP to all outputs and terminates

    **Deep Copy:**
    Each output gets an independent copy of the message to avoid
    shared state bugs when downstream agents modify messages.

    **Usage:**
    Automatically inserted by network() when one node fans out
    to multiple nodes. Students typically don't create directly.
    """

    def __init__(self, num_outports: int, *, name: str):
        """
        Initialize Broadcast agent.

        Args:
            num_outports: Number of output ports to create
            name: Unique name for this agent (REQUIRED)

        Raises:
            ValueError: If name is empty
            ValueError: If num_outports < 2
        """
        if not name:
            raise ValueError("Broadcast agent requires a name")
        
        if num_outports < 2:
            raise ValueError(
                f"Broadcast requires at least 2 outputs, got {num_outports}"
            )

        super().__init__(
            name=name,
            inports=["in_"],
            outports=[f"out_{i}" for i in range(num_outports)]
        )

    def __call__(self):
        """
        Main processing loop.

        Broadcasts each message to all outputs with deep copies.
        """
        while True:
            msg = self.recv("in_")

            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return

            # Broadcast to all outputs (with deep copies)
            for outport in self.outports:
                outport_msg = copy.deepcopy(msg)
                self.send(outport_msg, outport=outport)

    run = __call__

    def __repr__(self) -> str:
        return f"<Broadcast outputs={len(self.outports)}>"

    def __str__(self) -> str:
        return f"Broadcast({len(self.outports)} outputs)"
```

### Usage Examples

**Automatic insertion (typical):**
```python
source = Source(fn=data.run, name="src")
handler_a = Sink(fn=process_a, name="handler_a")
handler_b = Sink(fn=process_b, name="handler_b")
handler_c = Sink(fn=process_c, name="handler_c")

g = network([
    (source, handler_a),
    (source, handler_b),  # Framework inserts Broadcast automatically
    (source, handler_c)
])
```

**Explicit creation (rare):**
```python
source = Source(fn=data.run, name="src")
broadcast = Broadcast(num_outports=3, name="fanout")
handler_a = Sink(fn=process_a, name="handler_a")
handler_b = Sink(fn=process_b, name="handler_b")
handler_c = Sink(fn=process_c, name="handler_c")

g = network([
    (source, broadcast),
    (broadcast.out_0, handler_a),
    (broadcast.out_1, handler_b),
    (broadcast.out_2, handler_c)
])
```

### Design Notes

**Q: Why deep copy instead of shallow copy?**

A: Prevents shared state bugs:
```python
# Without deep copy:
msg = {"data": [1, 2, 3]}
# handler_a modifies: msg["data"].append(4)
# handler_b sees modified msg! Bug!

# With deep copy:
msg = {"data": [1, 2, 3]}
# Each handler gets independent copy
# No interference between handlers
```

**Q: Performance cost of deep copy?**

A: Worth it for correctness:
- Prevents subtle bugs
- Makes debugging easier
- Students learn message isolation
- Can optimize later if needed

**Q: Why auto-insert instead of requiring explicit Broadcast?**

A: Convenience:
```python
# Without auto-insert (tedious):
broadcast = Broadcast(num_outports=3)
g = network([
    (source, broadcast),
    (broadcast.out_0, handler_a),
    (broadcast.out_1, handler_b),
    (broadcast.out_2, handler_c)
])

# With auto-insert (natural):
g = network([
    (source, handler_a),
    (source, handler_b),
    (source, handler_c)
])
```

Students write natural connections, framework handles plumbing.

---

## fanin.py - MergeAsynch Agent

### Purpose

Asynchronously merges N inputs into one output (fanin pattern). Auto-inserted by framework when multiple senders connect to one receiver.

### Key Characteristics

- **Multiple inputs**: `inports = ["in_0", "in_1", ..., "in_N-1"]`
- **Single output**: `outports = ["out_"]`
- **Asynchronous**: Forwards messages as they arrive (non-deterministic order)
- **Thread-based**: One worker thread per input port
- **Coordinated STOP**: Waits for STOP from ALL inputs before sending final STOP
- **Auto-inserted**: Framework creates automatically for fanin

### Design Pattern

**Automatic insertion by framework:**

```python
# Student writes:
g = network([
    (source_a, handler),
    (source_b, handler),  # Fanin detected!
    (source_c, handler)
])

# Framework automatically inserts:
# merge = MergeAsynch(num_inports=3)
# And rewires to:
#   source_a → merge → handler
#   source_b →
#   source_c →
```

### Implementation

```python
from __future__ import annotations
from typing import Set
import threading

from dsl.core import Agent, STOP


class MergeAsynch(Agent):
    """
    MergeAsynch Agent: Asynchronous N→1 merge (fanin).

    **This is the recommended merge for most use cases.**
    Automatically inserted when multiple nodes feed into one node.

    **Ports:**
    - Inports: ["in_0", "in_1", ..., "in_{N-1}"]
    - Outports: ["out_"]

    **Message Flow:**
    1. Receives messages from any input as they arrive (async)
    2. Immediately forwards each message to output
    3. Waits for STOP from ALL inputs before sending final STOP
    4. Uses threading to handle multiple inputs concurrently

    **Key Feature:**
    Emits single STOP downstream only after receiving STOP from all inputs.
    This ensures proper shutdown coordination in complex graphs.

    **Ordering:**
    Non-deterministic - depends on which input produces messages fastest.
    For deterministic ordering, use round-robin Merge (not yet implemented).

    **Threading:**
    - One worker thread per input port
    - Thread-safe message forwarding
    - Clean shutdown coordination
    """

    def __init__(self, num_inports: int, *, name: str):
        """
        Initialize MergeAsynch agent.

        Args:
            num_inports: Number of input ports to create
            name: Unique name for this agent (REQUIRED)

        Raises:
            ValueError: If name is empty
            ValueError: If num_inports < 2
        """
        if not name:
            raise ValueError("MergeAsynch agent requires a name")
        
        if num_inports < 2:
            raise ValueError(
                f"MergeAsynch requires at least 2 inputs, got {num_inports}"
            )

        inports = [f"in_{i}" for i in range(num_inports)]
        super().__init__(name=name, inports=inports, outports=["out_"])

        # Threading for shutdown coordination
        self._stop_lock = threading.Lock()
        self._stopped_ports: Set[str] = set()
        self._all_stopped = threading.Event()

    def _worker(self, port: str) -> None:
        """
        Worker thread for one input port.

        Continuously receives messages from port and forwards them.
        Stops when STOP received, coordinates with other workers.
        """
        while True:
            msg = self.recv(port)  # Blocking read

            # Check for termination
            if msg is STOP:
                with self._stop_lock:
                    self._stopped_ports.add(port)
                    if len(self._stopped_ports) == len(self.inports):
                        self._all_stopped.set()
                break

            # Forward message immediately (asynchronous)
            self.send(msg, "out_")

    def __call__(self) -> None:
        """
        Main loop.

        Spawns worker threads for each input, waits for all to finish,
        then sends final STOP downstream.
        """
        # Spawn worker thread for each input
        threads = []
        for p in self.inports:
            t = threading.Thread(
                target=self._worker,
                args=(p,),
                name=f"merge_worker_{p}",
                daemon=False
            )
            t.start()
            threads.append(t)

        # Wait until all inputs delivered STOP
        self._all_stopped.wait()

        # Clean shutdown of workers
        for t in threads:
            t.join()

        # Emit single STOP downstream
        self.send(STOP, "out_")

    run = __call__

    def __repr__(self) -> str:
        return f"<MergeAsynch inputs={len(self.inports)}>"

    def __str__(self) -> str:
        return f"MergeAsynch({len(self.inports)} inputs)"
```

### Usage Examples

**Automatic insertion (typical):**
```python
source_a = Source(fn=data_a.run, name="src_a")
source_b = Source(fn=data_b.run, name="src_b")
source_c = Source(fn=data_c.run, name="src_c")
handler = Sink(fn=process, name="handler")

g = network([
    (source_a, handler),
    (source_b, handler),  # Framework inserts MergeAsynch automatically
    (source_c, handler)
])
```

**Explicit creation (rare):**
```python
source_a = Source(fn=data_a.run, name="src_a")
source_b = Source(fn=data_b.run, name="src_b")
source_c = Source(fn=data_c.run, name="src_c")
merge = MergeAsynch(num_inports=3, name="fanin")
handler = Sink(fn=process, name="handler")

g = network([
    (source_a, merge.in_0),
    (source_b, merge.in_1),
    (source_c, merge.in_2),
    (merge, handler)
])
```

### Design Notes

**Q: Why asynchronous (non-deterministic) instead of round-robin?**

A: Performance and simplicity:
- Faster: No waiting for slow inputs
- Simpler: No coordination needed
- Natural: Matches real distributed systems
- Educational: Shows non-determinism

For deterministic order, can implement round-robin Merge later.

**Q: Why wait for ALL inputs to send STOP?**

A: Correct shutdown:
```python
# Without waiting:
source_a → STOP (fast source)
source_b → still sending (slow source)
merge → sends STOP downstream
# BUT source_b still has messages! Lost data!

# With waiting:
source_a → STOP
source_b → still sending
merge → waits for source_b
source_b → STOP
merge → sends STOP downstream (all data forwarded)
```

**Q: Why one thread per input?**

A: Concurrent processing:
- Each input independent
- No blocking on slow inputs
- Natural threading model
- Matches distributed systems

---

## blocks/__init__.py

```python
"""Pre-built agent types for distributed systems."""

from .source import Source
from .transform import Transform
from .sink import Sink
from .split import Split
from .fanout import Broadcast
from .fanin import MergeAsynch

__all__ = [
    'Source',
    'Transform',
    'Sink',
    'Split',
    'Broadcast',
    'MergeAsynch',
]
```

---

## Common Patterns Summary

| Agent | Inports | Outports | Function Signature | Use Case |
|-------|---------|----------|-------------------|----------|
| Source | [] | ["out_"] | `fn() -> Optional[msg]` | Generate data |
| Transform | ["in_"] | ["out_"] | `fn(msg) -> Optional[msg]` | Process data |
| Sink | ["in_"] | [] | `fn(msg) -> None` | Consume data |
| Split | ["in_"] | ["out_0", ...] | `fn(msg) -> List[Optional[msg]]` | Route to N outputs |
| Broadcast | ["in_"] | ["out_0", ...] | (internal) | Copy to N outputs |
| MergeAsynch | ["in_0", ...] | ["out_"] | (internal) | Merge N inputs |

---

## Implementation Order

1. **Source** - Simplest pattern, no inputs
2. **Sink** - Simple pattern, no outputs
3. **Transform** - Core processing, most common
4. **Broadcast** - Framework needs for fanout
5. **MergeAsynch** - Framework needs for fanin
6. **Split** - Advanced routing
7. **__init__.py** - Export all agents


## Directory Purpose

`dsl/blocks/` contains pre-built agent types that students use to build networks:
- **Source**: Generates messages (no inputs, one output)
- **Transform**: Processes messages (one input, one output)
- **Sink**: Consumes messages (one input, no outputs)
- **Broadcast**: Copies messages to multiple outputs (fanout)
- **Merge/MergeAsynch**: Combines multiple inputs (fanin)
- **Split**: Routes messages based on function (one input, multiple outputs)

**Core Responsibilities:**
1. Provide common agent patterns
2. Hide STOP handling boilerplate
3. Support both simple and stateful operations
4. Work with any message type (not just dicts)

---

## File Organization

```
dsl/blocks/
├── __init__.py          # Export all blocks
├── source.py            # Source agent
├── transform.py         # Transform agent
├── sink.py              # Sink agent
├── broadcast.py         # Broadcast (fanout) agent
├── merge.py             # Merge and MergeAsynch (fanin) agents
└── split.py             # Split (routing) agent
```

---

## Common Patterns Across All Blocks

### Pattern 1: Require name parameter

All blocks require `name` in `__init__`:
```python
def __init__(self, *, name: str, ...):
    if not name:
        raise ValueError("Agent name is required")
    super().__init__(name=name, inports=[...], outports=[...])
```

### Pattern 2: Default port properties

Blocks with single ports define defaults:
```python
@property
def default_inport(self) -> Optional[str]:
    return "in_" if "in_" in self.inports else None

@property
def default_outport(self) -> Optional[str]:
    return "out_" if "out_" in self.outports else None
```

Blocks with multiple ports return None (ambiguous):
```python
@property
def default_outport(self) -> Optional[str]:
    return None  # Multiple outputs - must be explicit
```

### Pattern 3: STOP handling

All blocks handle STOP in run():
```python
def run(self):
    while True:
        msg = self.recv("in_")
        if msg is STOP:
            self.broadcast_stop()
            return
        # ... process message ...
```

Sources broadcast STOP when done:
```python
def run(self):
    for item in self._data:
        self.send(item, "out_")
    self.broadcast_stop()  # Signal completion
```

### Pattern 4: Type hints

All blocks use comprehensive type hints:
```python
from __future__ import annotations
from typing import Any, Callable, Optional, List
```

---

## source.py - Source Agent

### Purpose

Generate messages by repeatedly calling a function until it returns None.

**Characteristics:**
- No inputs (inports = [])
- Single output (outports = ["out_"])
- Calls fn() repeatedly, sends each result
- Stops when fn() returns None (exhausted)
- Optional rate limiting with interval parameter

**Pattern:**
```python
# 1. Create instance with stateful data
class ListSource:
    def __init__(self, items):
        self.items = items
        self.index = 0
    
    def run(self):
        if self.index >= len(self.items):
            return None  # Exhausted
        item = self.items[self.index]
        self.index += 1
        return {"value": item}

# 2. Pass instance method to Source
data = ListSource([1, 2, 3])
source = Source(fn=data.run, name="src")

# 3. When network runs, Source calls fn() repeatedly until it returns None
```

### Implementation

```python
from __future__ import annotations
import traceback
import time
from typing import Any, Callable, Optional
from dsl.core import Agent, STOP


class Source(Agent):
    """
    Source Agent: Repeatedly calls a function to generate messages.

    **Ports:**
    - Inports: [] (no inputs - sources generate data)
    - Outports: ["out_"] (emits generated messages)

    **Function Requirements:**
    The fn callable must:
    - Return a message (any type) on each call
    - Return None when exhausted (no more messages)
    - Maintain its own state between calls (if needed)

    **Message Flow:**
    1. Calls fn() repeatedly
    2. Sends returned messages to "out_" port
    3. When fn() returns None, sends STOP and terminates

    **Optional Rate Limiting:**
    The interval parameter adds a delay between messages:
    - interval=0 (default): emit as fast as possible
    - interval=1.0: emit one message per second
    - Useful for simulating real-time streams

    **Error Handling:**
    - Exceptions during fn() are caught and logged
    - STOP signal is sent to downstream agents
    - Pipeline terminates gracefully

    **Consistent Pattern:**
    All agents now use the same pattern:
        source = Source(fn=data_source.run, name="src")
        transform = Transform(fn=processor.run, name="proc")
        sink = Sink(fn=handler.run, name="sink")

    This makes the API uniform and easier to teach.

    **Examples:**

    Simple list source:
        >>> class ListSource:
        ...     def __init__(self, items):
        ...         self.items = items
        ...         self.index = 0
        ...     
        ...     def run(self):
        ...         if self.index >= len(self.items):
        ...             return None  # Exhausted
        ...         item = self.items[self.index]
        ...         self.index += 1
        ...         return {"value": item}
        >>> 
        >>> data = ListSource([1, 2, 3])
        >>> source = Source(fn=data.run, name="numbers")

    Counter source:
        >>> class CounterSource:
        ...     def __init__(self, max_count):
        ...         self.count = 0
        ...         self.max_count = max_count
        ...     
        ...     def run(self):
        ...         if self.count >= self.max_count:
        ...             return None
        ...         result = {"count": self.count}
        ...         self.count += 1
        ...         return result
        >>> 
        >>> counter = CounterSource(max_count=5)
        >>> source = Source(fn=counter.run, name="counter")

    With rate limiting:
        >>> data = ListSource([1, 2, 3])
        >>> source = Source(fn=data.run, interval=1.0, name="slow_src")

    Using a lambda:
        >>> items = iter([1, 2, 3])
        >>> source = Source(fn=lambda: next(items, None), name="iter_src")
    """

    def __init__(
        self, 
        *,
        fn: Callable[[], Optional[Any]], 
        name: str,
        interval: float = 0
    ):
        """
        Initialize a Source agent.

        Args:
            fn: Callable that returns messages or None when exhausted.
                Should have signature: fn() -> Optional[message]
            name: Unique name for this agent (REQUIRED)
            interval: Optional delay in seconds between messages (default: 0)

        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable

        Examples:
            >>> data = ListSource([1, 2, 3])
            >>> source = Source(fn=data.run, name="src")
            >>> 
            >>> # With rate limiting
            >>> source = Source(fn=data.run, interval=1.0, name="slow")
        """
        if not name:
            raise ValueError("Source agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                "Source fn must be callable with signature: fn() -> Optional[message]"
            )

        super().__init__(name=name, inports=[], outports=["out_"])
        self._fn = fn
        self._interval = interval

    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"

    def run(self) -> None:
        """
        Main processing loop for the Source agent.

        Repeatedly calls self._fn() to get messages and emits them.
        Stops when fn() returns None or an exception occurs.
        """
        try:
            while True:
                # Get next message from function
                msg = self._fn()

                # None means the source is exhausted
                if msg is None:
                    self.broadcast_stop()
                    return

                # Send the message downstream
                self.send(msg, "out_")

                # Optional rate limiting
                if self._interval > 0:
                    time.sleep(self._interval)

        except Exception as e:
            # Log error and terminate gracefully
            print(f"[Source '{self.name}'] Error in fn: {e}")
            print(traceback.format_exc())
            self.broadcast_stop()

    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        interval_str = f", interval={self._interval}" if self._interval > 0 else ""
        return f"<Source name={self.name} fn={fn_name}{interval_str}>"

    def __str__(self) -> str:
        return "Source"
```

### Design Notes

**Why fn() returns None instead of being a generator?**
- **Simpler for students**: `return None` when done vs `yield` + understanding generators
- **Stateful instances**: Instance maintains state (index, count) between calls
- **Uniform API**: Same pattern as Transform/Sink (all take callables)
- **Flexible**: Can use lambdas, methods, or standalone functions

**Why call fn() repeatedly instead of once?**
- **Pull-based**: Source controls generation pace
- **State management**: Instance method maintains state naturally
- **Testing**: Easy to test - just call fn() and check result

**Example from codebase:**
```python
class SourceOfSocialMediaPosts:
    def __init__(self, posts):
        self.posts = posts
        self.index = 0
    
    def run(self):
        if self.index >= len(self.posts):
            return None
        post = self.posts[self.index]
        self.index += 1
        return {"text": post}

# Create instance
from_X_data = SourceOfSocialMediaPosts(posts=example_posts_from_X)

# Wrap in Source agent
from_X = Source(fn=from_X_data.run, name="from_X")
```

**Why include interval parameter?**
- **Rate limiting**: Simulate real-time data streams
- **Backpressure**: Control message flow rate
- **Testing**: Slow down for debugging/observation

**Critical difference from generators:**
- **Generator pattern**: `for item in fn(): yield item`
- **Callable pattern**: `while (msg := fn()) is not None: send(msg)`

The callable pattern is simpler for beginners and more explicit about termination.

---

## transform.py - Transform Agent

### Purpose

Apply a function to each message flowing through.

**Characteristics:**
- Single input (inports = ["in_"])
- Single output (outports = ["out_"])
- Stateless or stateful (fn can be method)
- Filters messages if fn returns None

### Implementation

```python
from __future__ import annotations
from typing import Any, Callable, Optional, Dict
import traceback

from dsl.core import Agent, STOP


class Transform(Agent):
    """
    Transform agent: applies a function to each message.
    
    Single input, single output. Processes each message by calling
    fn(msg, **params) and sending the result.
    
    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_"]
    
    **Message Flow:**
    - Receives msg from "in_" port
    - Calls fn(msg, **params)
    - Sends result to "out_" port
    - If fn returns None, message is filtered (not sent)
    - Forwards STOP and terminates
    
    **Error Handling:**
    - Exceptions caught, logged, pipeline stopped
    - Fail-fast for educational clarity
    
    **Examples:**
    
    Simple transform:
        >>> def double(x):
        ...     return x * 2
        >>> transform = Transform(fn=double, name="doubler")
    
    With parameters:
        >>> def scale(x, factor):
        ...     return x * factor
        >>> transform = Transform(fn=scale, params={"factor": 10}, name="scaler")
    
    Stateful transform (instance method):
        >>> class Counter:
        ...     def __init__(self):
        ...         self.count = 0
        ...     def process(self, msg):
        ...         self.count += 1
        ...         return {"value": msg, "index": self.count}
        >>> counter = Counter()
        >>> transform = Transform(fn=counter.process, name="counter")
    
    Filter pattern:
        >>> def filter_positive(x):
        ...     return x if x > 0 else None
        >>> transform = Transform(fn=filter_positive, name="filter")
    """
    
    def __init__(
        self,
        *,
        fn: Callable[..., Optional[Any]],
        name: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Transform agent.
        
        Args:
            fn: Callable that transforms messages.
                Signature: fn(msg, **params) -> result
                - Takes message and optional keyword arguments
                - Returns transformed message, or None to filter
            name: Unique name for this agent (REQUIRED)
            params: Optional dict of keyword arguments passed to fn
        
        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
        """
        if not name:
            raise ValueError("Transform agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                f"Transform fn must be callable, got {type(fn).__name__}"
            )
        
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self._fn = fn
        self._params = params or {}
    
    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"
    
    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"
    
    def run(self) -> None:
        """
        Process messages in loop.
        
        Receives messages, transforms them, sends results.
        Stops on STOP signal or exception.
        """
        while True:
            # Receive message
            msg = self.recv("in_")
            
            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return
            
            # Transform message
            try:
                result = self._fn(msg, **self._params)
            except Exception as e:
                # Fail-fast: log error and stop pipeline
                print(f"[Transform '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                self.broadcast_stop()
                return
            
            # Send result (None filtered automatically by send())
            self.send(result, "out_")
    
    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Transform name={self.name} fn={fn_name}>"
```

### Design Notes

**Why params dict instead of *args, **kwargs?**
- Explicit: Clear what parameters are being passed
- Testable: Easy to see configuration
- Debuggable: Can inspect params

**Why fail-fast on exceptions?**
- Educational: Students see errors immediately
- Debugging: Clear which transform failed
- Production: Different error handling can be added later

**Why allow None to filter?**
- Common pattern: Filter while transforming
- Simple: No separate Filter agent needed
- Explicit: None means "don't send"

---

## sink.py - Sink Agent

### Purpose

Consume messages without producing output.

**Characteristics:**
- Single input (inports = ["in_"])
- No outputs (outports = [])
- Terminal node in network
- Calls function for side effects

### Implementation

```python
from __future__ import annotations
from typing import Any, Callable, Optional, Dict
import traceback

from dsl.core import Agent, STOP


class Sink(Agent):
    """
    Sink agent: consumes messages for side effects.
    
    Single input, no outputs. Terminal node that calls fn(msg, **params)
    for each message. Used for actions like printing, saving, or sending.
    
    **Ports:**
    - Inports: ["in_"]
    - Outports: [] (no outputs)
    
    **Message Flow:**
    - Receives msg from "in_" port
    - Calls fn(msg, **params)
    - No outputs (terminal node)
    - Terminates on STOP
    
    **Error Handling:**
    - Exceptions caught, logged, pipeline stopped
    - Fail-fast for educational clarity
    
    **Examples:**
    
    Print to console:
        >>> sink = Sink(fn=print, name="printer")
    
    Collect results:
        >>> results = []
        >>> sink = Sink(fn=results.append, name="collector")
    
    Save to file:
        >>> def save_to_file(msg):
        ...     with open("output.txt", "a") as f:
        ...         f.write(str(msg) + "\\n")
        >>> sink = Sink(fn=save_to_file, name="writer")
    
    With parameters:
        >>> def save_json(msg, filename):
        ...     with open(filename, "a") as f:
        ...         json.dump(msg, f)
        ...         f.write("\\n")
        >>> sink = Sink(fn=save_json, params={"filename": "data.jsonl"}, name="saver")
    """
    
    def __init__(
        self,
        *,
        fn: Callable[..., None],
        name: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Sink agent.
        
        Args:
            fn: Callable that processes messages for side effects.
                Signature: fn(msg, **params) -> None
                - Takes message and optional keyword arguments
                - Return value ignored (side effects only)
            name: Unique name for this agent (REQUIRED)
            params: Optional dict of keyword arguments passed to fn
        
        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
        """
        if not name:
            raise ValueError("Sink agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                f"Sink fn must be callable, got {type(fn).__name__}"
            )
        
        super().__init__(name=name, inports=["in_"], outports=[])
        self._fn = fn
        self._params = params or {}
    
    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"
    
    def run(self) -> None:
        """
        Process messages until STOP.
        
        Calls fn for each message, terminates on STOP.
        """
        while True:
            # Receive message
            msg = self.recv("in_")
            
            # Check for termination
            if msg is STOP:
                # No outputs to broadcast to
                return
            
            # Process message for side effects
            try:
                self._fn(msg, **self._params)
            except Exception as e:
                # Fail-fast: log error and stop
                print(f"[Sink '{self.name}'] Error in fn: {e}")
                print(traceback.format_exc())
                # No broadcast_stop() - we have no outputs
                return
    
    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Sink name={self.name} fn={fn_name}>"
```

### Design Notes

**Why no broadcast_stop() in Sink?**
- Sinks have no outputs
- STOP doesn't need to propagate further
- Just return from run()

**Why catch exceptions if we're just logging?**
- Prevents thread from dying silently
- Shows clear error to student
- Consistent with Transform behavior

---

## broadcast.py - Broadcast Agent (Fanout)

### Purpose

Copy input to multiple outputs (fanout pattern).

**Characteristics:**
- Single input (inports = ["in_"])
- Multiple outputs (outports = ["out_0", "out_1", ...])
- Copies messages to all outputs
- Auto-inserted by framework for fanout

### Implementation

```python
from __future__ import annotations
from typing import Optional

from dsl.core import Agent, STOP


class Broadcast(Agent):
    """
    Broadcast agent: copies messages to multiple outputs (fanout).
    
    Single input, multiple outputs. Receives message and sends copy
    to each output port.
    
    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1", ..., "out_{n-1}"]
    
    **Message Flow:**
    - Receives msg from "in_" port
    - Sends msg to ALL output ports
    - Forwards STOP to all outputs and terminates
    
    **Usage:**
    Usually auto-inserted by framework when one agent sends to multiple
    receivers. Can also be created explicitly for control.
    
    **Examples:**
    
    Explicit broadcast:
        >>> broadcast = Broadcast(num_outputs=3, name="fanout")
        >>> g = network([
        ...     (source, broadcast),
        ...     (broadcast.out_0, sink_a),
        ...     (broadcast.out_1, sink_b),
        ...     (broadcast.out_2, sink_c)
        ... ])
    
    Auto-inserted (framework creates broadcast automatically):
        >>> g = network([
        ...     (source, sink_a),
        ...     (source, sink_b),  # Broadcast auto-inserted here
        ...     (source, sink_c)
        ... ])
    """
    
    def __init__(self, *, num_outputs: int, name: str):
        """
        Initialize Broadcast agent.
        
        Args:
            num_outputs: Number of output ports to create
            name: Unique name for this agent (REQUIRED)
        
        Raises:
            ValueError: If name is empty
            ValueError: If num_outputs < 1
        """
        if not name:
            raise ValueError("Broadcast agent requires a name")
        
        if num_outputs < 1:
            raise ValueError(
                f"Broadcast requires at least 1 output, got {num_outputs}"
            )
        
        # Create output ports: out_0, out_1, ..., out_{n-1}
        outports = [f"out_{i}" for i in range(num_outputs)]
        
        super().__init__(name=name, inports=["in_"], outports=outports)
        self.num_outputs = num_outputs
    
    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"
    
    @property
    def default_outport(self) -> Optional[str]:
        """No default output (multiple outputs - ambiguous)."""
        return None
    
    def run(self) -> None:
        """
        Broadcast messages to all outputs.
        
        Receives from "in_", sends to all "out_*" ports.
        """
        while True:
            # Receive message
            msg = self.recv("in_")
            
            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return
            
            # Send to all outputs
            for i in range(self.num_outputs):
                self.send(msg, f"out_{i}")
    
    def __repr__(self) -> str:
        return f"<Broadcast name={self.name} outputs={self.num_outputs}>"
```

### Design Notes

**Why numbered ports (out_0, out_1) instead of custom names?**
- Consistent: Predictable port naming
- Auto-insertable: Framework can create without knowing semantics
- Simple: No configuration needed

**Why no default_outport?**
- Multiple outputs - ambiguous which one to use
- Forces explicit: `broadcast.out_0`
- Clear intent: Student sees which output

---

## merge.py - Merge Agents (Fanin)

### Purpose

Combine multiple inputs into single output (fanin pattern).

**Two variants:**
- **Merge**: Round-robin (deterministic, fair)
- **MergeAsynch**: First-available (non-deterministic, faster)

### Implementation

```python
from __future__ import annotations
from typing import Optional, List
from queue import Queue, Empty

from dsl.core import Agent, STOP


class MergeAsynch(Agent):
    """
    MergeAsynch agent: combines multiple inputs (fanin, non-deterministic).
    
    Multiple inputs, single output. Receives from whichever input has
    a message available first. Fast but non-deterministic order.
    
    **Ports:**
    - Inports: ["in_0", "in_1", ..., "in_{n-1}"]
    - Outports: ["out_"]
    
    **Message Flow:**
    - Receives from any "in_*" port (whichever is ready first)
    - Sends to "out_" port
    - Terminates when ALL inputs send STOP
    
    **Ordering:**
    Non-deterministic - depends on which input produces messages fastest.
    Use Merge for deterministic round-robin.
    
    **Examples:**
    
    Explicit merge:
        >>> merge = MergeAsynch(num_inputs=3, name="combine")
        >>> g = network([
        ...     (source_a, merge.in_0),
        ...     (source_b, merge.in_1),
        ...     (source_c, merge.in_2),
        ...     (merge, sink)
        ... ])
    
    Auto-inserted (framework creates merge automatically):
        >>> g = network([
        ...     (source_a, sink),
        ...     (source_b, sink),  # Merge auto-inserted here
        ...     (source_c, sink)
        ... ])
    """
    
    def __init__(self, *, num_inputs: int, name: str):
        """
        Initialize MergeAsynch agent.
        
        Args:
            num_inputs: Number of input ports to create
            name: Unique name for this agent (REQUIRED)
        
        Raises:
            ValueError: If name is empty
            ValueError: If num_inputs < 1
        """
        if not name:
            raise ValueError("MergeAsynch agent requires a name")
        
        if num_inputs < 1:
            raise ValueError(
                f"MergeAsynch requires at least 1 input, got {num_inputs}"
            )
        
        # Create input ports: in_0, in_1, ..., in_{n-1}
        inports = [f"in_{i}" for i in range(num_inputs)]
        
        super().__init__(name=name, inports=inports, outports=["out_"])
        self.num_inputs = num_inputs
    
    @property
    def default_inport(self) -> Optional[str]:
        """No default input (multiple inputs - ambiguous)."""
        return None
    
    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"
    
    def run(self) -> None:
        """
        Merge messages from multiple inputs (non-deterministic).
        
        Uses select-like pattern: receive from whichever input is ready.
        Terminates when all inputs have sent STOP.
        """
        # Track which inputs are still active
        active_inputs = set(range(self.num_inputs))
        
        while active_inputs:
            # Try each active input (non-blocking)
            for i in list(active_inputs):
                try:
                    # Non-blocking get (with small timeout)
                    msg = self.in_q[f"in_{i}"].get(timeout=0.001)
                    
                    if msg is STOP:
                        # This input is done
                        active_inputs.remove(i)
                    else:
                        # Forward message
                        self.send(msg, "out_")
                    
                    break  # Got a message, check all inputs again
                    
                except Empty:
                    # This input has no message ready, try next
                    continue
        
        # All inputs finished
        self.broadcast_stop()
    
    def __repr__(self) -> str:
        return f"<MergeAsynch name={self.name} inputs={self.num_inputs}>"


class Merge(Agent):
    """
    Merge agent: combines multiple inputs (fanin, round-robin).
    
    Multiple inputs, single output. Receives from inputs in round-robin
    order. Deterministic but may block waiting for slow inputs.
    
    **Ports:**
    - Inports: ["in_0", "in_1", ..., "in_{n-1}"]
    - Outports: ["out_"]
    
    **Message Flow:**
    - Receives from "in_0", "in_1", "in_2", ... in order
    - Sends to "out_" port
    - Terminates when ALL inputs send STOP
    
    **Ordering:**
    Deterministic round-robin. Input 0, then input 1, then input 2, etc.
    Slower than MergeAsynch but predictable.
    
    **Examples:**
    
    Round-robin merge:
        >>> merge = Merge(num_inputs=2, name="combine")
        >>> g = network([
        ...     (source_a, merge.in_0),  # Alternates: a, b, a, b, ...
        ...     (source_b, merge.in_1),
        ...     (merge, sink)
        ... ])
    """
    
    def __init__(self, *, num_inputs: int, name: str):
        """
        Initialize Merge agent.
        
        Args:
            num_inputs: Number of input ports to create
            name: Unique name for this agent (REQUIRED)
        
        Raises:
            ValueError: If name is empty
            ValueError: If num_inputs < 1
        """
        if not name:
            raise ValueError("Merge agent requires a name")
        
        if num_inputs < 1:
            raise ValueError(
                f"Merge requires at least 1 input, got {num_inputs}"
            )
        
        # Create input ports: in_0, in_1, ..., in_{n-1}
        inports = [f"in_{i}" for i in range(num_inputs)]
        
        super().__init__(name=name, inports=inports, outports=["out_"])
        self.num_inputs = num_inputs
    
    @property
    def default_inport(self) -> Optional[str]:
        """No default input (multiple inputs - ambiguous)."""
        return None
    
    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"
    
    def run(self) -> None:
        """
        Merge messages from multiple inputs (round-robin).
        
        Reads from inputs in order: 0, 1, 2, ..., n-1, 0, 1, ...
        Terminates when all inputs have sent STOP.
        """
        # Track which inputs are still active
        active_inputs = set(range(self.num_inputs))
        
        while active_inputs:
            # Try each input in order
            for i in range(self.num_inputs):
                if i not in active_inputs:
                    continue  # This input already finished
                
                msg = self.recv(f"in_{i}")
                
                if msg is STOP:
                    # This input is done
                    active_inputs.remove(i)
                else:
                    # Forward message
                    self.send(msg, "out_")
        
        # All inputs finished
        self.broadcast_stop()
    
    def __repr__(self) -> str:
        return f"<Merge name={self.name} inputs={self.num_inputs}>"
```

### Design Notes

**Why two merge variants?**
- MergeAsynch: Faster, non-deterministic (good default)
- Merge: Slower, deterministic (for when order matters)

**Why track active_inputs?**
- Can't use simple while True loop
- Need to know when ALL inputs finished
- Each input might finish at different times

**Why MergeAsynch uses timeout?**
- Check all inputs in round-robin
- Don't block on one slow input
- Balance fairness with responsiveness

---

## split.py - Split Agent (Routing)

### Purpose

Route messages to different outputs based on function.

**Characteristics:**
- Single input (inports = ["in_"])
- Multiple outputs (outports = ["out_0", "out_1", ...])
- Calls router function to determine output
- Used for conditional routing

### Implementation

```python
from __future__ import annotations
from typing import Callable, Any, Optional

from dsl.core import Agent, STOP


class Split(Agent):
    """
    Split agent: routes messages based on function (conditional routing).
    
    Single input, multiple outputs. Calls router function to determine
    which output port to send each message to.
    
    **Ports:**
    - Inports: ["in_"]
    - Outports: ["out_0", "out_1", ..., "out_{n-1}"]
    
    **Message Flow:**
    - Receives msg from "in_" port
    - Calls router(msg) to get output index
    - Sends msg to "out_{index}" port
    - Forwards STOP to all outputs and terminates
    
    **Router Function:**
    - Takes message, returns integer 0 to (num_outputs-1)
    - Determines which output receives the message
    - Invalid index logs error and drops message
    
    **Examples:**
    
    Even/odd split:
        >>> def even_odd(value):
        ...     return 0 if value % 2 == 0 else 1
        >>> splitter = Split(router=even_odd, num_outputs=2, name="split")
        >>> g = network([
        ...     (source, splitter),
        ...     (splitter.out_0, even_sink),
        ...     (splitter.out_1, odd_sink)
        ... ])
    
    Priority routing:
        >>> def priority(msg):
        ...     if msg["urgent"]:
        ...         return 0
        ...     elif msg["important"]:
        ...         return 1
        ...     else:
        ...         return 2
        >>> splitter = Split(router=priority, num_outputs=3, name="router")
    """
    
    def __init__(
        self,
        *,
        router: Callable[[Any], int],
        num_outputs: int,
        name: str
    ):
        """
        Initialize Split agent.
        
        Args:
            router: Function that maps messages to output indices.
                    Signature: router(msg) -> int (0 to num_outputs-1)
            num_outputs: Number of output ports to create
            name: Unique name for this agent (REQUIRED)
        
        Raises:
            ValueError: If name is empty
            ValueError: If num_outputs < 1
            TypeError: If router is not callable
        """
        if not name:
            raise ValueError("Split agent requires a name")
        
        if num_outputs < 1:
            raise ValueError(
                f"Split requires at least 1 output, got {num_outputs}"
            )
        
        if not callable(router):
            raise TypeError(
                f"Split router must be callable, got {type(router).__name__}"
            )
        
        # Create output ports: out_0, out_1, ..., out_{n-1}
        outports = [f"out_{i}" for i in range(num_outputs)]
        
        super().__init__(name=name, inports=["in_"], outports=outports)
        self._router = router
        self.num_outputs = num_outputs
    
    @property
    def default_inport(self) -> str:
        """Default input port for edge syntax."""
        return "in_"
    
    @property
    def default_outport(self) -> Optional[str]:
        """No default output (multiple outputs - ambiguous)."""
        return None
    
    def run(self) -> None:
        """
        Route messages to outputs based on router function.
        
        Calls router(msg) to determine output, sends to that port.
        """
        while True:
            # Receive message
            msg = self.recv("in_")
            
            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return
            
            # Determine output
            try:
                index = self._router(msg)
            except Exception as e:
                print(f"[Split '{self.name}'] Router error: {e}")
                # Drop message, continue processing
                continue
            
            # Validate index
            if not isinstance(index, int):
                print(
                    f"[Split '{self.name}'] Router returned non-integer: "
                    f"{type(index).__name__}. Message dropped."
                )
                continue
            
            if not (0 <= index < self.num_outputs):
                print(
                    f"[Split '{self.name}'] Router returned invalid index {index}. "
                    f"Valid range: 0-{self.num_outputs-1}. Message dropped."
                )
                continue
            
            # Send to selected output
            self.send(msg, f"out_{index}")
    
    def __repr__(self) -> str:
        router_name = getattr(self._router, "__name__", repr(self._router))
        return f"<Split name={self.name} router={router_name} outputs={self.num_outputs}>"
```

### Design Notes

**Why drop invalid messages instead of raising?**
- Robustness: One bad message doesn't stop pipeline
- Educational: Student sees error, network keeps running
- Debugging: Can see pattern of errors

**Why log router errors instead of propagating?**
- Router is student code - may have bugs
- Show error clearly to student
- Continue processing other messages

---

## blocks/__init__.py

```python
"""Pre-built agent types for common patterns."""

from .source import Source
from .transform import Transform
from .sink import Sink
from .broadcast import Broadcast
from .merge import Merge, MergeAsynch
from .split import Split

__all__ = [
    'Source',
    'Transform',
    'Sink',
    'Broadcast',
    'Merge',
    'MergeAsynch',
    'Split',
]
```

---

## Testing Strategy

### Unit Tests for Each Block

```python
# test_source.py
def test_source_from_list():
    """Source generates messages from list."""
    source = Source(fn=lambda: [1, 2, 3], name="src")
    source.out_q["out_"] = SimpleQueue()
    
    source.run()
    
    assert source.out_q["out_"].get() == 1
    assert source.out_q["out_"].get() == 2
    assert source.out_q["out_"].get() == 3
    assert source.out_q["out_"].get() is STOP


def test_source_from_generator():
    """Source works with generator functions."""
    def gen():
        for i in range(3):
            yield i * 10
    
    source = Source(fn=gen, name="src")
    source.out_q["out_"] = SimpleQueue()
    
    source.run()
    
    assert source.out_q["out_"].get() == 0
    assert source.out_q["out_"].get() == 10
    assert source.out_q["out_"].get() == 20
    assert source.out_q["out_"].get() is STOP


# test_transform.py
def test_transform_simple():
    """Transform applies function to messages."""
    transform = Transform(fn=lambda x: x * 2, name="trans")
    transform.in_q["in_"] = SimpleQueue()
    transform.out_q["out_"] = SimpleQueue()
    
    transform.in_q["in_"].put(5)
    transform.in_q["in_"].put(STOP)
    
    transform.run()
    
    assert transform.out_q["out_"].get() == 10
    assert transform.out_q["out_"].get() is STOP


def test_transform_with_params():
    """Transform passes params to function."""
    def scale(x, factor):
        return x * factor
    
    transform = Transform(fn=scale, params={"factor": 10}, name="trans")
    transform.in_q["in_"] = SimpleQueue()
    transform.out_q["out_"] = SimpleQueue()
    
    transform.in_q["in_"].put(5)
    transform.in_q["in_"].put(STOP)
    
    transform.run()
    
    assert transform.out_q["out_"].get() == 50


def test_transform_filter():
    """Transform filters None results."""
    def filter_positive(x):
        return x if x > 0 else None
    
    transform = Transform(fn=filter_positive, name="trans")
    transform.in_q["in_"] = SimpleQueue()
    transform.out_q["out_"] = SimpleQueue()
    
    transform.in_q["in_"].put(-5)
    transform.in_q["in_"].put(10)
    transform.in_q["in_"].put(STOP)
    
    transform.run()
    
    assert transform.out_q["out_"].get() == 10
    assert transform.out_q["out_"].get() is STOP


# test_sink.py
def test_sink_processes_messages():
    """Sink calls function for each message."""
    results = []
    sink = Sink(fn=results.append, name="sink")
    sink.in_q["in_"] = SimpleQueue()
    
    sink.in_q["in_"].put(1)
    sink.in_q["in_"].put(2)
    sink.in_q["in_"].put(STOP)
    
    sink.run()
    
    assert results == [1, 2]


# test_broadcast.py
def test_broadcast_copies_to_all():
    """Broadcast sends message to all outputs."""
    broadcast = Broadcast(num_outputs=3, name="bc")
    broadcast.in_q["in_"] = SimpleQueue()
    broadcast.out_q["out_0"] = SimpleQueue()
    broadcast.out_q["out_1"] = SimpleQueue()
    broadcast.out_q["out_2"] = SimpleQueue()
    
    broadcast.in_q["in_"].put(42)
    broadcast.in_q["in_"].put(STOP)
    
    broadcast.run()
    
    assert broadcast.out_q["out_0"].get() == 42
    assert broadcast.out_q["out_1"].get() == 42
    assert broadcast.out_q["out_2"].get() == 42


# test_split.py
def test_split_routes_by_function():
    """Split routes messages based on router function."""
    def router(x):
        return 0 if x % 2 == 0 else 1
    
    split = Split(router=router, num_outputs=2, name="split")
    split.in_q["in_"] = SimpleQueue()
    split.out_q["out_0"] = SimpleQueue()
    split.out_q["out_1"] = SimpleQueue()
    
    split.in_q["in_"].put(2)  # Even → 0
    split.in_q["in_"].put(3)  # Odd → 1
    split.in_q["in_"].put(4)  # Even → 0
    split.in_q["in_"].put(STOP)
    
    split.run()
    
    assert split.out_q["out_0"].get() == 2
    assert split.out_q["out_0"].get() == 4
    assert split.out_q["out_1"].get() == 3
```

### Integration Tests

```python
def test_source_transform_sink_pipeline():
    """Test complete pipeline execution."""
    results = []
    
    source = Source(fn=lambda: [1, 2, 3], name="src")
    transform = Transform(fn=lambda x: x * 2, name="trans")
    sink = Sink(fn=results.append, name="sink")
    
    g = network([
        (source, transform),
        (transform, sink)
    ])
    
    g.run_network()
    
    assert results == [2, 4, 6]


def test_fanout_with_broadcast():
    """Test fanout pattern."""
    results_a = []
    results_b = []
    
    source = Source(fn=lambda: [1, 2], name="src")
    sink_a = Sink(fn=results_a.append, name="sink_a")
    sink_b = Sink(fn=results_b.append, name="sink_b")
    
    g = network([
        (source, sink_a),
        (source, sink_b)
    ])
    
    g.run_network()
    
    assert results_a == [1, 2]
    assert results_b == [1, 2]


def test_split_routing():
    """Test split routing pattern."""
    evens = []
    odds = []
    
    source = Source(fn=lambda: [1, 2, 3, 4], name="src")
    split = Split(
        router=lambda x: 0 if x % 2 == 0 else 1,
        num_outputs=2,
        name="split"
    )
    even_sink = Sink(fn=evens.append, name="evens")
    odd_sink = Sink(fn=odds.append, name="odds")
    
    g = network([
        (source, split),
        (split.out_0, even_sink),
        (split.out_1, odd_sink)
    ])
    
    g.run_network()
    
    assert evens == [2, 4]
    assert odds == [1, 3]
```

---

## Implementation Order

1. **Source** - Simplest, no inputs
2. **Sink** - Simple, no outputs
3. **Transform** - Core processing agent
4. **Broadcast** - Fanout (used by framework)
5. **MergeAsynch** - Fanin (used by framework)
6. **Merge** - Round-robin variant
7. **Split** - Routing agent
8. **__init__.py** - Export all blocks

---

## Common Patterns Summary

| Block | Inports | Outports | Use Case |
|-------|---------|----------|----------|
| Source | [] | ["out_"] | Generate data |
| Transform | ["in_"] | ["out_"] | Process data |
| Sink | ["in_"] | [] | Consume data |
| Broadcast | ["in_"] | ["out_0", ...] | Fanout |
| Merge | ["in_0", ...] | ["out_"] | Fanin (round-robin) |
| MergeAsynch | ["in_0", ...] | ["out_"] | Fanin (fast) |
| Split | ["in_"] | ["out_0", ...] | Routing |