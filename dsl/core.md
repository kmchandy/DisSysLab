# core.py - Core Abstractions

## Purpose

Defines the fundamental building blocks for the DSL:
- `STOP`: Sentinel object for end-of-stream signaling
- `Agent`: Abstract base class for all processing nodes
- Message passing primitives: `send()`, `recv()`, `broadcast_stop()`

## Design Principles

1. **Minimal Surface Area**: Only essential abstractions
2. **Clear Lifecycle**: startup → run → shutdown
3. **Thread-Per-Agent**: Each agent runs independently
4. **Type Agnostic**: Messages can be any Python object (dicts recommended)

---

## STOP Sentinel

### Purpose
Signal end-of-stream to trigger graceful termination.

### Implementation
```python
class _Stop:
    """Sentinel object for end-of-stream signaling."""
    def __repr__(self):
        return "STOP"

STOP = _Stop()
```

### Usage Pattern
```python
def run(self):
    while True:
        msg = self.recv("in_")
        if msg is STOP:
            self.broadcast_stop()  # Forward to downstream
            return                 # Terminate this agent
        # ... process message ...
```

### Why Sentinel vs Boolean?
- **Type Safety**: Can't confuse with `False` or `None`
- **Explicit**: Clear intent (not just "no data")
- **Debuggable**: `repr()` shows "STOP" in logs
- **Propagation**: Can be passed through network

### Why Not Exception?
- STOP is normal control flow, not an error
- Exceptions are for unexpected failures
- Clearer separation of concerns

---

## Agent Base Class

### Conceptual Model

An Agent is an **independent processing unit** that:
- Receives messages on **named input ports**
- Processes messages in its **run() method**
- Sends results to **named output ports**
- Runs in **its own thread** for concurrency

**Key Insight**: Agents are like functions, but concurrent and communicating via message passing instead of function calls.

### Class Signature

```python
class Agent(ABC):
    """
    Abstract base class for all agents in the network.
    
    Subclasses must:
    1. Call super().__init__(name=..., inports=..., outports=...)
    2. Implement run() method
    3. Optionally override startup() and shutdown()
    """
    
    def __init__(self, *, name: str, inports: List[str] = None, 
                 outports: List[str] = None):
        """
        Initialize agent with name and port configuration.
        
        Args:
            name: Unique identifier for this agent (REQUIRED)
            inports: List of input port names (default: [])
            outports: List of output port names (default: [])
        
        Raises:
            ValueError: If name is None or empty
            ValueError: If any port names are duplicated
        
        Example:
            >>> class MyAgent(Agent):
            ...     def __init__(self):
            ...         super().__init__(
            ...             name="my_processor",
            ...             inports=["in_"],
            ...             outports=["out_", "error_"]
            ...         )
        """
```

### Port Configuration

**Inports**: Named inputs that receive messages
- Example: `["in_"]` for simple agents
- Example: `["in_0", "in_1", "in_2"]` for merge agents
- Must be unique within the agent

**Outports**: Named outputs that send messages
- Example: `["out_"]` for simple agents
- Example: `["out_0", "out_1", "out_2"]` for split agents
- Must be unique within the agent

**Invariant**: All port names must be unique across inports and outports
- Valid: `inports=["data"], outports=["out"]`
- Invalid: `inports=["port"], outports=["port"]`  # Duplicate!

### Agent Lifecycle

```
Construction → Validation → Startup → Run → Shutdown
     ↓             ↓           ↓        ↓        ↓
__init__()     check()    startup()  run()  shutdown()
```

#### 1. Construction (__init__)
- Define ports (inports, outports)
- Store configuration parameters
- Initialize instance variables
- **DO NOT**: Open files, create connections, start threads

#### 2. Validation (Network.check)
- Network validates all ports are connected
- Checks for dangling ports
- Verifies no duplicate connections
- **Agent doesn't participate** - this is Network's job

#### 3. Startup (startup)
- Open files, database connections, network sockets
- Initialize resources that depend on network structure
- Called **once** before threading starts
- **Optional**: Override only if needed

```python
def startup(self):
    """One-time initialization before run()."""
    self.file = open(self.filename, 'w')
    self.db_conn = database.connect(self.connection_string)
```

#### 4. Run (run) - **REQUIRED**
- Main processing loop
- Runs in dedicated thread
- Continues until STOP received or source exhausted
- **Must implement** in every subclass

```python
def run(self):
    """Main processing loop - MUST be implemented."""
    while True:
        msg = self.recv("in_")
        if msg is STOP:
            self.broadcast_stop()
            return
        result = self.process(msg)
        self.send(result, "out_")
```

#### 5. Shutdown (shutdown)
- Close files, connections, release resources
- Called **once** after all threads complete
- **Optional**: Override only if needed

```python
def shutdown(self):
    """Cleanup after run() completes."""
    if self.file:
        self.file.close()
    if self.db_conn:
        self.db_conn.close()
```

### Message Passing API

#### send(msg, outport)
Send a message to an output port (non-blocking).

```python
def send(self, msg: Any, outport: str) -> None:
    """
    Send message to output port.
    
    Args:
        msg: Message to send (any Python object, typically dict)
        outport: Name of output port (must exist on this agent)
    
    Behavior:
        - None messages are filtered (dropped, not sent)
        - STOP messages propagate
        - All other messages sent immediately
        - Non-blocking (queue.put with no timeout)
    
    Raises:
        ValueError: If outport doesn't exist on this agent
        ValueError: If outport is not connected (network validation failed)
    
    Example:
        >>> self.send({"value": 42}, "out_")
        >>> self.send(STOP, "out_")  # Signal termination
        >>> self.send(None, "out_")  # Dropped, not sent
    """
```

**None Filtering**: 
```python
# None messages are automatically filtered
result = compute_result(msg)
self.send(result, "out_")  # If result is None, nothing sent

# This pattern enables filtering:
def filter_positive(msg):
    if msg["value"] > 0:
        return msg
    return None  # Message filtered out
```

#### recv(inport)
Receive a message from an input port (blocking).

```python
def recv(self, inport: str) -> Any:
    """
    Receive message from input port (blocking).
    
    Args:
        inport: Name of input port (must exist on this agent)
    
    Returns:
        Message received (any Python object, typically dict or STOP)
    
    Behavior:
        - Blocks until message available
        - Returns message immediately once received
        - No timeout (blocks forever if no message)
    
    Raises:
        ValueError: If inport doesn't exist on this agent
        ValueError: If inport is not connected (network validation failed)
    
    Example:
        >>> msg = self.recv("in_")
        >>> if msg is STOP:
        ...     return
        >>> # Process msg
    """
```

**Blocking Behavior**:
- Waits until message arrives
- No busy-waiting (efficient thread sleep)
- Uses queue.get() internally (thread-safe)

#### broadcast_stop()
Send STOP to all output ports (convenience method).

```python
def broadcast_stop(self) -> None:
    """
    Send STOP signal to all downstream agents.
    
    Call this when:
    - Receiving STOP from upstream (forward it)
    - Source exhausted (no more data to send)
    - Error requiring pipeline shutdown
    
    Equivalent to:
        for outport in self.outports:
            self.send(STOP, outport)
    
    Example:
        >>> msg = self.recv("in_")
        >>> if msg is STOP:
        ...     self.broadcast_stop()  # Forward to all downstream
        ...     return
    """
```

### Properties for Default Ports

Subclasses can override to provide sensible defaults:

```python
@property
def default_inport(self) -> Optional[str]:
    """
    Default input port for edge syntax without explicit port.
    
    Override in subclasses to enable: (source, self)
    
    Returns:
        Port name or None if no default
    
    Example:
        >>> class Transform(Agent):
        ...     @property
        ...     def default_inport(self):
        ...         return "in_"
    """
    return "in_" if "in_" in self.inports else None

@property
def default_outport(self) -> Optional[str]:
    """
    Default output port for edge syntax without explicit port.
    
    Override in subclasses to enable: (self, sink)
    
    Returns:
        Port name or None if no default
    
    Example:
        >>> class Source(Agent):
        ...     @property
        ...     def default_outport(self):
        ...         return "out_"
    """
    return "out_" if "out_" in self.outports else None
```

### Threading Model

**One Thread Per Agent**:
- Each agent's `run()` executes in dedicated thread
- Created by Network during compilation
- Started when network.run() called
- Joined when all agents complete

**Thread Safety**:
- Communication via thread-safe queues (SimpleQueue)
- No shared mutable state between agents
- No locks needed in agent code
- Queues handle all synchronization

**Termination**:
- Agent returns from run() → thread exits
- Network waits for all threads to complete
- Shutdown called after all threads joined

### Internal State (Set by Network)

These attributes are managed by Network, not Agent:

```python
self.name: str              # Set during construction (required)
self.in_q: Dict[str, Queue]  # Set during Network.compile()
self.out_q: Dict[str, Queue] # Set during Network.compile()
```

**Do Not Access Directly**:
- Use `send()` and `recv()` instead of queue operations
- Network manages queue creation and wiring
- Queues are implementation detail

---

## Common Patterns

### Source Pattern (No Inputs)
```python
class MySource(Agent):
    def __init__(self, data):
        super().__init__(name="source", inports=[], outports=["out_"])
        self.data = data
    
    def run(self):
        for item in self.data:
            self.send({"value": item}, "out_")
        self.broadcast_stop()  # Signal completion
```

### Transform Pattern (Input → Output)
```python
class MyTransform(Agent):
    def __init__(self, fn):
        super().__init__(name="transform", inports=["in_"], outports=["out_"])
        self.fn = fn
    
    def run(self):
        while True:
            msg = self.recv("in_")
            if msg is STOP:
                self.broadcast_stop()
                return
            result = self.fn(msg)
            self.send(result, "out_")
```

### Sink Pattern (Input Only)
```python
class MySink(Agent):
    def __init__(self, fn):
        super().__init__(name="sink", inports=["in_"], outports=[])
        self.fn = fn
    
    def run(self):
        while True:
            msg = self.recv("in_")
            if msg is STOP:
                return  # No downstream, just stop
            self.fn(msg)
```

### Filter Pattern (Conditional Forwarding)
```python
class MyFilter(Agent):
    def run(self):
        while True:
            msg = self.recv("in_")
            if msg is STOP:
                self.broadcast_stop()
                return
            if self.predicate(msg):
                self.send(msg, "out_")
            # Else: drop message (don't send)
```

### Multi-Port Pattern (Routing)
```python
class MySplit(Agent):
    def __init__(self, num_outputs):
        super().__init__(
            name="split",
            inports=["in_"],
            outports=[f"out_{i}" for i in range(num_outputs)]
        )
    
    def run(self):
        while True:
            msg = self.recv("in_")
            if msg is STOP:
                self.broadcast_stop()
                return
            route = self.determine_route(msg)
            self.send(msg, f"out_{route}")
```

---

## Error Handling

### Construction Errors
```python
# Missing name
Agent(name=None)  # ValueError: Agent name is required

# Duplicate ports
Agent(name="x", inports=["p"], outports=["p"])  # ValueError: Duplicate port 'p'
```

### Runtime Errors
```python
# Invalid port
self.send(msg, "invalid")  # ValueError: Port 'invalid' is not a valid outport

# Unconnected port
self.recv("in_")  # ValueError: Inport 'in_' is not connected
```

### Exception Handling in run()
```python
def run(self):
    try:
        while True:
            msg = self.recv("in_")
            if msg is STOP:
                self.broadcast_stop()
                return
            result = self.risky_operation(msg)
            self.send(result, "out_")
    except Exception as e:
        print(f"Agent {self.name} failed: {e}")
        self.broadcast_stop()  # Notify downstream
        raise  # Re-raise for Network to catch
```

---

## Testing Agents

### Unit Testing
```python
def test_transform_agent():
    # Create agent
    transform = Transform(fn=lambda msg: {"value": msg["value"] * 2})
    
    # Mock queues
    transform.in_q["in_"] = SimpleQueue()
    transform.out_q["out_"] = SimpleQueue()
    
    # Send test message
    transform.in_q["in_"].put({"value": 5})
    transform.in_q["in_"].put(STOP)
    
    # Run agent
    transform.run()
    
    # Check output
    result = transform.out_q["out_"].get()
    assert result == {"value": 10}
    
    stop_signal = transform.out_q["out_"].get()
    assert stop_signal is STOP
```

### Integration Testing
Use Network to test agent in realistic scenario:
```python
def test_agent_in_network():
    source = Source(fn=lambda: [{"value": i} for i in range(3)])
    transform = MyTransform(fn=lambda msg: msg)
    sink = Sink(fn=collector.append)
    
    g = network([
        (source, transform),
        (transform, sink)
    ])
    g.run_network()
    
    assert len(collector) == 3
```

---

## Design Rationale

### Why Abstract Base Class?
- Enforces run() implementation (compile-time check)
- Provides uniform interface for Network
- Enables type checking: `isinstance(x, Agent)`
- Clear contract for subclasses

### Why Named Ports?
- Multiple inputs/outputs need identification
- Explicit routing for split/merge patterns
- Self-documenting: port names describe purpose
- Enables validation (check all ports connected)

### Why Thread-Per-Agent?
- **Pedagogical**: Easiest to understand (one agent = one thread)
- **Isolation**: Agents truly independent
- **Debugging**: Stack traces show agent execution
- **Simplicity**: No event loop, no async/await

Trade-off: Not scalable (100s of agents OK, 1000s not)

### Why SimpleQueue?
- Thread-safe (no locks needed)
- Unbounded (no backpressure complexity)
- Simple interface (get/put only)
- Standard library (no dependencies)

Trade-off: No flow control, can consume unbounded memory

---

## Future Enhancements

### Possible Additions
1. **Async Support**: `async def run()` for async agents
2. **Backpressure**: Bounded queues with flow control
3. **Monitoring**: Built-in metrics (throughput, latency)
4. **Debugging**: Message tracing, step-through execution
5. **Serialization**: Save/restore agent state

### Non-Goals
- **Performance**: Thread-per-agent is intentionally simple
- **Distribution**: Single-machine only (for teaching)
- **Fault Tolerance**: No automatic restart/recovery
- **Load Balancing**: No work stealing or redistribution

These are production concerns; this is a teaching tool.