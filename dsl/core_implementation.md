# core.py - Implementation Guide

## File Purpose

`dsl/core.py` contains the fundamental building blocks:
1. `STOP` - Sentinel for end-of-stream signaling
2. `Agent` - Abstract base class for all network nodes
3. Supporting infrastructure (ExceptionThread, type hints)

## What Goes in core.py

**Include:**
- `STOP` sentinel object
- `Agent` base class
- `ExceptionThread` (for capturing exceptions from agent threads)
- Type definitions and protocols

**Do NOT include:**
- Network class (goes in `network.py`)
- Concrete agent types like Source/Transform/Sink (go in `blocks/`)
- Network builder function (goes in `builder.py`)
- PortReference (goes in `builder.py`)

---

## Implementation Checklist

### 1. STOP Sentinel
```python
class _Stop:
    """Sentinel object for end-of-stream signaling."""
    def __repr__(self):
        return "STOP"

STOP = _Stop()
```

**Requirements:**
- ✅ Simple class with just `__repr__`
- ✅ Single global instance
- ✅ Identity comparison works: `msg is STOP`

### 2. ExceptionThread
```python
class ExceptionThread(Thread):
    """Thread that captures exceptions from target function for debugging."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exception: Optional[Exception] = None
        self.exc_info: Optional[tuple] = None
    
    def run(self):
        try:
            super().run()
        except Exception as e:
            self.exception = e
            self.exc_info = sys.exc_info()
```

**Requirements:**
- ✅ Captures exception without stopping other threads
- ✅ Stores both exception object and full traceback info
- ✅ Used by Network to report agent failures

### 3. Agent Base Class

#### 3.1 Class Structure
```python
class Agent(ABC):
    """Base class for all agents in the network."""
    
    def __init__(self, *, name: str, inports: List[str] = None, 
                 outports: List[str] = None):
        """Initialize agent with required name and ports."""
        
    # Lifecycle methods
    def startup(self) -> None: ...
    
    @abstractmethod
    def run(self) -> None: ...
    
    def shutdown(self) -> None: ...
    
    # Message passing
    def send(self, msg: Any, outport: str) -> None: ...
    def recv(self, inport: str) -> Any: ...
    def broadcast_stop(self) -> None: ...
    
    # Default ports (for builder.py to use)
    @property
    def default_inport(self) -> Optional[str]: ...
    
    @property
    def default_outport(self) -> Optional[str]: ...
    
    # Port reference support (for builder.py)
    def __getattr__(self, name: str): ...
```

#### 3.2 Initialization Requirements

**Name parameter:**
- ✅ REQUIRED (no default, no auto-generation)
- ✅ Must be provided as keyword argument: `name="my_agent"`
- ✅ Validation: must be non-empty string
- ✅ Store in `self.name`

**Port parameters:**
- ✅ Default to empty lists if not provided
- ✅ Convert to lists (avoid mutable default trap)
- ✅ Store in `self.inports` and `self.outports`
- ✅ Validate: all port names must be strings
- ✅ Validate: all port names must be unique within agent

**Queue dictionaries:**
- ✅ Create `self.in_q: Dict[str, Optional[Queue]]` with None values
- ✅ Create `self.out_q: Dict[str, Optional[Queue]]` with None values
- ✅ Network will populate these during compilation

**Example:**
```python
def __init__(self, *, name: str, inports: List[str] = None, 
             outports: List[str] = None):
    # Validate name
    if not name:
        raise ValueError("Agent name is required and cannot be empty")
    if not isinstance(name, str):
        raise TypeError(f"Agent name must be string, got {type(name)}")
    
    self.name = name
    
    # Avoid mutable default trap
    self.inports = list(inports) if inports is not None else []
    self.outports = list(outports) if outports is not None else []
    
    # Validate ports
    for port in self.inports + self.outports:
        if not isinstance(port, str):
            raise TypeError(f"Port names must be strings, got {type(port)}")
    
    # Check uniqueness
    all_ports = self.inports + self.outports
    if len(set(all_ports)) != len(all_ports):
        raise ValueError(f"Duplicate port names in agent '{name}'")
    
    # Queue dictionaries (wired by Network during compilation)
    self.in_q = {p: None for p in self.inports}
    self.out_q = {p: None for p in self.outports}
```

#### 3.3 Lifecycle Methods

**startup() - Optional Override**
```python
def startup(self) -> None:
    """
    One-time initialization before run() is called.
    
    Override to open files, connections, initialize resources.
    Called once per agent before threading starts.
    """
    pass  # Default: do nothing
```

**run() - REQUIRED Override**
```python
@abstractmethod
def run(self) -> None:
    """
    Main processing loop - MUST be implemented by subclasses.
    
    Runs in its own thread. Should loop until STOP received or 
    processing complete.
    """
    raise NotImplementedError("Subclasses must implement run()")
```

**shutdown() - Optional Override**
```python
def shutdown(self) -> None:
    """
    Cleanup after run() completes.
    
    Override to close files, connections, release resources.
    Called once per agent after all threads joined.
    """
    pass  # Default: do nothing
```

#### 3.4 Message Passing Methods

**send() - Send to Output Port**
```python
def send(self, msg: Any, outport: str) -> None:
    """
    Send message to output port.
    
    Args:
        msg: Any pickleable Python object (or STOP)
        outport: Name of output port
    
    Behavior:
        - None messages are filtered (not sent)
        - STOP and all other messages are sent
        - Non-blocking (uses queue.put)
    
    Raises:
        ValueError: If outport doesn't exist or not connected
    """
    # Validate outport exists
    if outport not in self.outports:
        raise ValueError(
            f"Port '{outport}' is not a valid outport of agent '{self.name}'. "
            f"Valid outports: {self.outports}"
        )
    
    # Get queue
    q = self.out_q[outport]
    if q is None:
        raise ValueError(
            f"Outport '{outport}' of agent '{self.name}' is not connected. "
            f"This should not happen if network was validated."
        )
    
    # Filter None messages
    if msg is None:
        return
    
    # Send message
    q.put(msg)
```

**recv() - Receive from Input Port**
```python
def recv(self, inport: str) -> Any:
    """
    Receive message from input port (blocking).
    
    Args:
        inport: Name of input port
    
    Returns:
        Message (any Python object or STOP)
    
    Blocks until message available.
    
    Raises:
        ValueError: If inport doesn't exist or not connected
    """
    # Validate inport exists
    if inport not in self.inports:
        raise ValueError(
            f"Port '{inport}' is not a valid inport of agent '{self.name}'. "
            f"Valid inports: {self.inports}"
        )
    
    # Get queue
    q = self.in_q[inport]
    if q is None:
        raise ValueError(
            f"Inport '{inport}' of agent '{self.name}' is not connected. "
            f"This should not happen if network was validated."
        )
    
    # Receive message (blocking)
    return q.get()
```

**broadcast_stop() - Signal Termination**
```python
def broadcast_stop(self) -> None:
    """Send STOP to all output ports."""
    for outport in self.outports:
        self.send(STOP, outport)
```

#### 3.5 Default Port Properties

**Purpose:** Enable `(agent, agent)` syntax without explicit ports

**Implementation:**
```python
@property
def default_inport(self) -> Optional[str]:
    """
    Default input port for edge syntax without explicit port.
    
    Override in subclasses to enable: (source, self)
    
    Returns:
        Port name or None if no default
    """
    # Base implementation: return "in_" if it exists
    return "in_" if "in_" in self.inports else None

@property
def default_outport(self) -> Optional[str]:
    """
    Default output port for edge syntax without explicit port.
    
    Override in subclasses to enable: (self, sink)
    
    Returns:
        Port name or None if no default
    """
    # Base implementation: return "out_" if it exists
    return "out_" if "out_" in self.outports else None
```

**Subclass Overrides:**
- Source: only override `default_outport` (no inputs)
- Transform: use base implementation (both "in_" and "out_")
- Sink: only override `default_inport` (no outputs)
- Split: override `default_outport` to return None (ambiguous)
- Merge: override `default_inport` to return None (ambiguous)

#### 3.6 Port Reference Support (__getattr__)

**Purpose:** Enable `agent.port_name` syntax

**Implementation:**
```python
def __getattr__(self, name: str):
    """
    Enable dot notation for ports: agent.port_name
    
    Creates PortReference objects for use in network() edges.
    
    Example:
        >>> source.out_  # Returns PortReference(source, "out_")
        >>> sink.in_     # Returns PortReference(sink, "in_")
    
    Raises:
        AttributeError: If name is not a valid port
    """
    # Import here to avoid circular dependency
    from dsl.builder import PortReference
    
    # Check if it's a valid port
    if name in self.inports or name in self.outports:
        return PortReference(agent=self, port_name=name)
    
    # Not a port - raise standard AttributeError
    raise AttributeError(
        f"'{type(self).__name__}' object has no attribute '{name}'. "
        f"Valid ports: inports={self.inports}, outports={self.outports}"
    )
```

**Note:** This creates a circular dependency issue (Agent needs PortReference, PortReference needs Agent). We solve this with lazy import inside the method.

---

## Implementation Order

1. **STOP sentinel** - Simple, no dependencies
2. **ExceptionThread** - Simple, no dependencies  
3. **Agent.__init__** - Validation and initialization
4. **Agent.send/recv/broadcast_stop** - Message passing
5. **Agent.default_inport/default_outport** - Properties
6. **Agent.startup/run/shutdown** - Lifecycle (run is abstract)
7. **Agent.__getattr__** - Port reference support (last, has dependency)

---

## Testing Strategy

### Unit Tests for STOP
```python
def test_stop_singleton():
    """STOP is a singleton."""
    assert STOP is STOP
    
def test_stop_repr():
    """STOP has readable repr."""
    assert repr(STOP) == "STOP"
    
def test_stop_identity():
    """Can use 'is' for comparison."""
    msg = STOP
    assert msg is STOP
```

### Unit Tests for Agent
```python
def test_agent_requires_name():
    """Agent requires name parameter."""
    with pytest.raises(ValueError):
        Agent(name="", inports=[], outports=[])
    
    with pytest.raises(ValueError):
        Agent(name=None, inports=[], outports=[])

def test_agent_name_must_be_string():
    """Agent name must be string."""
    with pytest.raises(TypeError):
        Agent(name=123, inports=[], outports=[])

def test_agent_port_defaults():
    """Ports default to empty lists."""
    class TestAgent(Agent):
        def run(self): pass
    
    agent = TestAgent(name="test")
    assert agent.inports == []
    assert agent.outports == []

def test_agent_duplicate_ports():
    """Duplicate port names raise error."""
    class TestAgent(Agent):
        def run(self): pass
    
    with pytest.raises(ValueError, match="Duplicate"):
        TestAgent(name="test", inports=["p"], outports=["p"])

def test_send_filters_none():
    """send() filters None messages."""
    class TestAgent(Agent):
        def run(self): pass
    
    agent = TestAgent(name="test", outports=["out_"])
    agent.out_q["out_"] = SimpleQueue()
    
    agent.send(None, "out_")
    assert agent.out_q["out_"].empty()  # Nothing sent

def test_send_passes_stop():
    """send() passes STOP messages."""
    class TestAgent(Agent):
        def run(self): pass
    
    agent = TestAgent(name="test", outports=["out_"])
    agent.out_q["out_"] = SimpleQueue()
    
    agent.send(STOP, "out_")
    assert agent.out_q["out_"].get() is STOP

def test_default_ports():
    """Default port properties work correctly."""
    class TestAgent(Agent):
        def __init__(self):
            super().__init__(name="test", inports=["in_"], outports=["out_"])
        def run(self): pass
    
    agent = TestAgent()
    assert agent.default_inport == "in_"
    assert agent.default_outport == "out_"

def test_no_default_ports():
    """Agents without standard ports return None."""
    class TestAgent(Agent):
        def __init__(self):
            super().__init__(name="test", inports=["x"], outports=["y"])
        def run(self): pass
    
    agent = TestAgent()
    assert agent.default_inport is None
    assert agent.default_outport is None

def test_port_reference_valid():
    """__getattr__ creates PortReference for valid ports."""
    class TestAgent(Agent):
        def __init__(self):
            super().__init__(name="test", inports=["in_"], outports=["out_"])
        def run(self): pass
    
    agent = TestAgent()
    
    ref = agent.out_
    assert ref.agent is agent
    assert ref.port_name == "out_"

def test_port_reference_invalid():
    """__getattr__ raises AttributeError for invalid ports."""
    class TestAgent(Agent):
        def __init__(self):
            super().__init__(name="test", inports=["in_"], outports=["out_"])
        def run(self): pass
    
    agent = TestAgent()
    
    with pytest.raises(AttributeError, match="no attribute 'invalid'"):
        _ = agent.invalid
```

---

## Common Pitfalls

### 1. Circular Import (Agent ↔ PortReference)
**Problem:** Agent.__getattr__ needs PortReference, but PortReference needs Agent
**Solution:** Lazy import inside __getattr__ method

### 2. Mutable Default Arguments
**Problem:** `def __init__(self, inports=[])` shares list across instances
**Solution:** Use None and create new list: `inports = inports or []`

### 3. Queue None Check
**Problem:** Accessing `self.in_q[port]` before Network wires queues
**Solution:** Check if queue is None and raise helpful error

### 4. STOP Comparison
**Problem:** Using `==` instead of `is`
**Solution:** Always use `if msg is STOP:` for identity check

### 5. Abstract Method Enforcement
**Problem:** Forgetting `@abstractmethod` on run()
**Solution:** Use ABC and @abstractmethod decorator

---

## Questions to Resolve Before Implementing

1. **Should Agent.close() exist?**
   - Currently a no-op in the reference code
   - Probably not needed - can remove
   
2. **Should we include type hints throughout?**
   - Recommended: Yes, helps with IDE support
   - Use `from __future__ import annotations` for forward references
   
3. **Error message verbosity?**
   - Current approach: Detailed messages with suggestions
   - Keep this - very helpful for students

4. **Should default_inport/default_outport be in Agent or only in subclasses?**
   - Recommended: Base implementation in Agent (returns "in_"/"out_" if exists)
   - Subclasses can override when needed (Split, Merge return None)

---

## Ready to Implement?

Once you've reviewed this implementation guide, we can:
1. Write the actual `core.py` code
2. Write comprehensive tests
3. Verify it works as documented

Any questions or changes to this implementation plan before we proceed?