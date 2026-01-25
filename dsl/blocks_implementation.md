# blocks/ - Implementation Guide

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

Generate messages from a generator function or iterable.

**Characteristics:**
- No inputs (inports = [])
- Single output (outports = ["out_"])
- Runs until generator exhausted
- Broadcasts STOP when complete

### Implementation

```python
from __future__ import annotations
from typing import Callable, Iterator, Any, Optional

from dsl.core import Agent, STOP


class Source(Agent):
    """
    Source agent: generates messages from a generator function.
    
    No inputs, single output. Produces messages by calling fn() which
    should return an iterable or generator.
    
    **Ports:**
    - Inports: [] (no inputs)
    - Outports: ["out_"]
    
    **Message Flow:**
    - Calls fn() to get iterable
    - Sends each item to "out_" port
    - Broadcasts STOP when exhausted
    
    **Examples:**
    
    From list:
        >>> source = Source(fn=lambda: [1, 2, 3], name="numbers")
    
    From generator:
        >>> def generate():
        ...     for i in range(10):
        ...         yield i * 2
        >>> source = Source(fn=generate, name="gen")
    
    With external data:
        >>> tweets = fetch_tweets()
        >>> source = Source(fn=lambda: tweets, name="twitter")
    """
    
    def __init__(
        self,
        *,
        fn: Callable[[], Iterator[Any]],
        name: str
    ):
        """
        Initialize Source agent.
        
        Args:
            fn: Callable that returns an iterable or generator.
                Called once when run() starts.
            name: Unique name for this agent (REQUIRED)
        
        Raises:
            ValueError: If name is empty
            TypeError: If fn is not callable
        """
        if not name:
            raise ValueError("Source agent requires a name")
        
        if not callable(fn):
            raise TypeError(
                f"Source fn must be callable, got {type(fn).__name__}"
            )
        
        super().__init__(name=name, inports=[], outports=["out_"])
        self._fn = fn
    
    @property
    def default_outport(self) -> str:
        """Default output port for edge syntax."""
        return "out_"
    
    def run(self) -> None:
        """
        Generate and send messages.
        
        Calls fn() once to get iterable, then sends each item.
        Broadcasts STOP when exhausted.
        """
        # Get iterable from function
        iterable = self._fn()
        
        # Send each item
        for item in iterable:
            self.send(item, "out_")
        
        # Signal completion
        self.broadcast_stop()
    
    def __repr__(self) -> str:
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"<Source name={self.name} fn={fn_name}>"
```

### Design Notes

**Why fn returns iterable instead of being a generator?**
- Flexibility: Can return list, generator, or any iterable
- Testability: Easy to pass simple lists
- Reusability: Function can be called multiple times if needed

**Why call fn() in run() instead of __init__()?**
- Lazy evaluation: Don't generate data until network runs
- Fresh data: Each run gets new data
- Resource management: File handles opened when needed

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