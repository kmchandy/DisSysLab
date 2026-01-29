# dsl/network.py
"""
Network class for building, validating, compiling, and executing distributed dataflow networks.

This module provides:
- Network: Container for interconnected agents
- Compilation pipeline (flatten → insert fanout/fanin → resolve → wire → thread)
- Execution management (startup → run → shutdown)
- Component composition (as_component method)
"""

from __future__ import annotations
from typing import Optional, List, Dict, Tuple, Any, Union
from queue import SimpleQueue
from collections import deque

from dsl.core import Agent, ExceptionThread


# ============================================================================
# Network Class
# ============================================================================

class Network:
    """
    Container of interconnected agents forming a dataflow network.

    A Network:
    - Contains blocks (Agents or nested Networks)
    - Defines connections between block ports
    - Can have external input/output ports for composition
    - Validates structure and connectivity
    - Compiles into executable graph with threads and queues
    - Manages agent lifecycle (startup → run → shutdown)

    **Network Structure:**
    - Blocks: Dictionary mapping names to Agent/Network instances
    - Connections: List of 4-tuples (from_block, from_port, to_block, to_port)
    - External ports: Allow networks to be composed hierarchically

    **Connection Rules:**
    - Block names must be unique, strings, no '::', not 'external'
    - 'external' is reserved for network's own external ports
    - Network automatically handles fanout (one → many) and fanin (many → one)

    **Compilation Process:**
    1. Insert fanout/fanin: Add Broadcast/Merge agents to maintain 1-to-1 invariant
    2. Flatten: Recursively expand nested networks into leaf agents
    3. Resolve: Collapse external port chains into agent↔agent edges
    4. Wire: Create queues and connect agent ports
    5. Thread: Create one thread per agent
    6. Validate: Verify compilation succeeded

    **External Ports:**
    Networks can have their own inports/outports for composition:
    - Connect to 'external' as the block name
    - Used when embedding networks inside other networks
    - Must be fully connected (validated during check)
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        blocks: Optional[Dict[str, Union[Agent, 'Network']]] = None,
        connections: Optional[List[Tuple[str, str, str, str]]] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None
    ):
        """
        Initialize a Network.

        Args:
            name: Optional name for this network
            blocks: Dictionary mapping block names to Agent/Network instances
            connections: List of (from_block, from_port, to_block, to_port) tuples
            inports: External input ports (for nested networks)
            outports: External output ports (for nested networks)

        The network structure is validated immediately via check().
        """
        # Store configuration
        self.name = name
        self.inports: List[str] = list(inports) if inports is not None else []
        self.outports: List[str] = list(
            outports) if outports is not None else []
        self.blocks: Dict[str, Union[Agent, Network]] = blocks or {}
        self.connections: List[Tuple[str, str, str, str]] = connections or []

        # Assign names to blocks (for debugging/errors)
        # Only set name for Agents, not Networks (Networks keep their own names)
        for block_name, block_object in self.blocks.items():
            if isinstance(block_object, Agent):
                block_object.name = block_name

        # Validate immediately
        self.check()

        # Compilation state (populated by compile())
        self.compiled: bool = False
        self.agents: Dict[str, Agent] = {}
        self.graph_connections: List[Tuple[str, str, str, str]] = []
        self.queues: List[SimpleQueue] = []
        self.threads: List[ExceptionThread] = []
        self.unresolved_connections: List[Tuple[str, str, str, str]] = []

    # ========== Validation ==========

    def check(self) -> None:
        """
        Validate basic network structure before compilation.

        Ensures:
        - Block names are valid strings (no '::', not 'external')
        - All blocks are Agent or Network instances
        - All connections reference existing blocks and ports
        - External ports, if declared, are properly connected

        Note: Does NOT check 1-to-1 port connectivity - that happens
        after fanout/fanin insertion during compilation.

        Raises:
            TypeError: Invalid block or port structure
            ValueError: Invalid names, missing connections, or duplicate connections
        """
        # ========== Validate Block Names ==========
        if not self.blocks:
            raise ValueError(
                f"Network '{self.name or '(unnamed)'}' must have at least one block. "
                f"Empty networks are not allowed."
            )

        for block_name in self.blocks:
            # Must be string
            if not isinstance(block_name, str):
                raise TypeError(
                    f"Block name must be string, got {type(block_name).__name__}: {block_name!r}"
                )

            # Cannot contain '::' (reserved for nested paths)
            if "::" in block_name:
                raise ValueError(
                    f"Block name '{block_name}' cannot contain '::' "
                    f"(reserved for nested network paths)"
                )

            # Cannot be 'external' (reserved)
            if block_name == "external":
                raise ValueError(
                    "'external' is reserved and cannot be used as block name"
                )

        # ========== Validate Block Types ==========
        for block_name, block_object in self.blocks.items():
            if not isinstance(block_object, (Agent, Network)):
                raise TypeError(
                    f"Block '{block_name}' must be Agent or Network, "
                    f"got {type(block_object).__name__}"
                )

        # ========== Validate Port Structure ==========
        for block_name, block_object in self.blocks.items():
            # Inports must be list
            if not isinstance(block_object.inports, list):
                raise TypeError(
                    f"Inports of block '{block_name}' must be list, "
                    f"got {type(block_object.inports).__name__}"
                )

            # Outports must be list
            if not isinstance(block_object.outports, list):
                raise TypeError(
                    f"Outports of block '{block_name}' must be list, "
                    f"got {type(block_object.outports).__name__}"
                )

            # No duplicate inport names
            if len(set(block_object.inports)) != len(block_object.inports):
                raise ValueError(
                    f"Block '{block_name}' has duplicate inport names: "
                    f"{block_object.inports}"
                )

            # No duplicate outport names
            if len(set(block_object.outports)) != len(block_object.outports):
                raise ValueError(
                    f"Block '{block_name}' has duplicate outport names: "
                    f"{block_object.outports}"
                )

        # ========== Validate Connection Endpoints ==========
        for conn in self.connections:
            from_block, from_port, to_block, to_port = conn

            # From-block must exist
            if from_block != "external" and from_block not in self.blocks:
                raise ValueError(
                    f"Connection references unknown from_block '{from_block}': "
                    f"{self._format_connection(conn)}\n"
                    f"Valid blocks: {list(self.blocks.keys()) + ['external']}"
                )

            # To-block must exist
            if to_block != "external" and to_block not in self.blocks:
                raise ValueError(
                    f"Connection references unknown to_block '{to_block}': "
                    f"{self._format_connection(conn)}\n"
                    f"Valid blocks: {list(self.blocks.keys()) + ['external']}"
                )

            # From-port must exist on from-block (unless external)
            if from_block != "external":
                if from_port not in self.blocks[from_block].outports:
                    raise ValueError(
                        f"Unknown from_port in connection: {self._format_connection(conn)}\n"
                        f"Block '{from_block}' has no outport '{from_port}'.\n"
                        f"Valid outports: {self.blocks[from_block].outports}"
                    )

            # To-port must exist on to-block (unless external)
            if to_block != "external":
                if to_port not in self.blocks[to_block].inports:
                    raise ValueError(
                        f"Unknown to_port in connection: {self._format_connection(conn)}\n"
                        f"Block '{to_block}' has no inport '{to_port}'.\n"
                        f"Valid inports: {self.blocks[to_block].inports}"
                    )

        # ========== Validate External Port Connectivity ==========
        # Each declared external inport must be connected
        for p in self.inports:
            matches = [
                c for c in self.connections
                if c[0] == "external" and c[1] == p
            ]
            if len(matches) == 0:
                raise ValueError(
                    f"External inport '{p}' is not connected. "
                    f"All declared external ports must be connected."
                )

        # Each declared external outport must be connected
        for p in self.outports:
            matches = [
                c for c in self.connections
                if c[2] == "external" and c[3] == p
            ]
            if len(matches) == 0:
                raise ValueError(
                    f"External outport '{p}' is not connected. "
                    f"All declared external ports must be connected."
                )

    # ========== Compilation Pipeline ==========

    def compile(self) -> None:
        """
        Compile network into executable form.

        Pipeline:
        1. Insert fanout/fanin agents (maintain 1-to-1 invariant)
        2. Flatten nested networks to leaf agents
        3. Resolve external connections (collapse chains)
        4. Wire queues between agents
        5. Create execution threads
        6. Validate compiled structure

        After compilation:
        - self.agents: Dict mapping full path names to Agent instances
        - self.graph_connections: List of direct agent→agent connections
        - self.queues: All inter-agent SimpleQueues
        - self.threads: One ExceptionThread per agent

        Raises:
            ValueError: If external connections cannot be fully resolved
        """
        if self.compiled:
            return  # Already compiled

        # Step 0: Maintain 1-to-1 invariant
        self._insert_fanout_fanin()

        # Step 1: Flatten to leaf agents
        self._flatten_networks()

        # Step 2: Resolve external port chains
        self._resolve_external_connections()

        # Step 3: Wire communication channels
        self._wire_queues()

        # Step 4: Create execution threads
        self._create_threads()

        # Step 5: Validate compilation succeeded
        self._validate_compiled()

        self.compiled = True

    def _insert_fanout_fanin(self) -> None:
        """
        Insert Broadcast and Merge agents for multiple connections.

        Detects:
        - Fanout: One outport → multiple inports (insert Broadcast)
        - Fanin: Multiple outports → one inport (insert Merge)

        Modifies self.connections and self.blocks in place.
        """
        # Lazy import to avoid circular dependency
        from dsl.blocks.fanout import Broadcast
        from dsl.blocks.fanin import MergeAsynch

        # Step 1: Compute in-degree and out-degree for each (block, port)
        out_degree: Dict[Tuple[str, str], int] = {}
        in_degree: Dict[Tuple[str, str], int] = {}

        for (fb, fp, tb, tp) in self.connections:
            out_degree[(fb, fp)] = out_degree.get((fb, fp), 0) + 1
            in_degree[(tb, tp)] = in_degree.get((tb, tp), 0) + 1

        # Step 2: Find fanout cases (out-degree > 1)
        fanout_cases = [(b, p)
                        for (b, p), deg in out_degree.items() if deg > 1]

        # Step 3: For each fanout, insert Broadcast
        broadcast_count = 0
        for (block, port) in fanout_cases:
            # Find all connections from this port
            outgoing = [
                c for c in self.connections
                if c[0] == block and c[1] == port
            ]

            # Create broadcast agent
            num_outputs = len(outgoing)
            broadcast_name = f"broadcast_{broadcast_count}"
            broadcast = Broadcast(
                num_outputs=num_outputs,
                name=broadcast_name
            )
            self.blocks[broadcast_name] = broadcast
            broadcast_count += 1

            # Rewire connections:
            # Before: (block, port) → [(dest1, port1), (dest2, port2), ...]
            # After:  (block, port) → (broadcast, in_)
            #         (broadcast, out_0) → (dest1, port1)
            #         (broadcast, out_1) → (dest2, port2)

            # Remove old connections (iterate over copy)
            for c in outgoing:
                self.connections.remove(c)

            # Add new connections
            self.connections.append((block, port, broadcast_name, "in_"))
            for i, (_, _, dest_block, dest_port) in enumerate(outgoing):
                self.connections.append(
                    (broadcast_name, f"out_{i}", dest_block, dest_port)
                )

        # Step 4: Recompute in-degree (connections changed)
        in_degree = {}
        for (fb, fp, tb, tp) in self.connections:
            in_degree[(tb, tp)] = in_degree.get((tb, tp), 0) + 1

        # Step 5: Find fanin cases (in-degree > 1)
        fanin_cases = [(b, p) for (b, p), deg in in_degree.items() if deg > 1]

        # Step 6: For each fanin, insert Merge
        merge_count = 0
        for (block, port) in fanin_cases:
            # Find all connections to this port
            incoming = [
                c for c in self.connections
                if c[2] == block and c[3] == port
            ]

            # Create merge agent
            num_inputs = len(incoming)
            merge_name = f"merge_{merge_count}"
            merge = MergeAsynch(
                num_inputs=num_inputs,
                name=merge_name
            )
            self.blocks[merge_name] = merge
            merge_count += 1

            # Rewire connections:
            # Before: [(src1, port1), (src2, port2), ...] → (block, port)
            # After:  (src1, port1) → (merge, in_0)
            #         (src2, port2) → (merge, in_1)
            #         ...
            #         (merge, out_) → (block, port)

            # Remove old connections (iterate over copy)
            for c in incoming:
                self.connections.remove(c)

            # Add new connections
            for i, (src_block, src_port, _, _) in enumerate(incoming):
                self.connections.append(
                    (src_block, src_port, merge_name, f"in_{i}")
                )
            self.connections.append((merge_name, "out_", block, port))

    def _flatten_networks(self) -> None:
        """
        Flatten nested networks to leaf agents.

        Traverses network hierarchy breadth-first, collecting:
        - Leaf agents in self.agents dict (with full paths using :: separator)
        - Lifted connections in self.unresolved_connections

        Example:
            Network 'root' contains Network 'component' contains Agent 'processor'
            Results in: self.agents['root::component::processor'] = processor

        Modifies:
            - self.agents: Populated with leaf agents
            - self.unresolved_connections: Populated with lifted connections
        """
        class PathNode:
            """Helper for tracking blocks during traversal."""

            def __init__(self, block: Union[Agent, Network], path: str):
                self.block = block
                self.path = path

        # Breadth-first traversal starting from this network
        # Use network's actual name, or "root" if no name provided
        root_name = self.name if self.name else "root"
        root = PathNode(self, root_name)
        pending = deque([root])

        while pending:
            node = pending.popleft()
            blk, path = node.block, node.path

            # Leaf agent - add to agents dict
            if isinstance(blk, Agent):
                self.agents[path] = blk
                continue

            # Network - expand children
            assert isinstance(blk, Network)
            for child_name, child_block in blk.blocks.items():
                child_path = f"{path}::{child_name}" if path else child_name
                pending.append(PathNode(child_block, child_path))

            # Lift connections to full paths
            for (fb, fp, tb, tp) in blk.connections:
                fpath = path if fb == "external" else f"{path}::{fb}"
                tpath = path if tb == "external" else f"{path}::{tb}"
                self.unresolved_connections.append((fpath, fp, tpath, tp))

    def _resolve_external_connections(self) -> None:
        """
        Resolve external port chains to direct agent→agent connections.

        Uses fixpoint iteration to collapse chains like:
            (A, p) → (external, x) and (external, x) → (B, q)
            Becomes: (A, p) → (B, q)

        Two patterns:
        1. External-out: (A, p) → (B, q) where (B, q) → (C, r)
           Collapse to: (A, p) → (C, r)

        2. External-in: (A, p) → (B, q) where (C, r) → (A, p)
           Collapse to: (C, r) → (B, q)

        Preconditions:
            - self.agents populated with leaf agents
            - self.unresolved_connections has lifted connections

        Modifies:
            - self.graph_connections: Populated with direct agent→agent edges
            - self.unresolved_connections: Emptied (all resolved)

        Raises:
            ValueError: If external connections cannot be fully resolved
        """
        # Fixpoint iteration - repeat until no changes
        changed = True
        while changed:
            changed = False

            for conn in self.unresolved_connections[:]:
                fb, fp, tb, tp = conn

                # Pattern 1: External-out collapse
                # (A, p) → (B, q) where (B, q) → (C, r)
                match = next(
                    (v for v in self.unresolved_connections
                     if v[0] == tb and v[1] == tp and v != conn),
                    None
                )
                if match:
                    new_conn = (fb, fp, match[2], match[3])
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True
                    continue

                # Pattern 2: External-in collapse
                # (A, p) → (B, q) where (C, r) → (A, p)
                match = next(
                    (v for v in self.unresolved_connections
                     if v[2] == fb and v[3] == fp and v != conn),
                    None
                )
                if match:
                    new_conn = (match[0], match[1], tb, tp)
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True

        # Extract direct agent→agent connections
        for (fb, fp, tb, tp) in self.unresolved_connections[:]:
            if fb in self.agents and tb in self.agents:
                self.unresolved_connections.remove((fb, fp, tb, tp))
                self.graph_connections.append((fb, fp, tb, tp))

        # Verify all external connections resolved
        if self.unresolved_connections:
            raise ValueError(
                f"Network has unresolved external connections:\n"
                f"{self._format_connections(self.unresolved_connections)}\n"
                f"All external ports must be fully connected to agents."
            )

    def _wire_queues(self) -> None:
        """
        Wire communication queues between agents.

        For each agent:
        - Creates SimpleQueue for each inport
        - Connects sender outports to receiver inport queues

        After this step:
        - All agent.in_q[port] have queue objects
        - All agent.out_q[port] have queue objects (shared with receivers)
        - Agents can call send() and recv()

        Preconditions:
            - self.agents populated
            - self.graph_connections has direct agent→agent edges

        Modifies:
            - agent.in_q: Populated with SimpleQueue objects
            - agent.out_q: Populated with references to receiver queues
            - self.queues: List of all queues (for cleanup/inspection)
        """
        # Create input queue for each agent inport
        for agent in self.agents.values():
            for port in agent.inports:
                agent.in_q[port] = SimpleQueue()
                self.queues.append(agent.in_q[port])

        # Connect sender outports to receiver inport queues
        for (fb, fp, tb, tp) in self.graph_connections:
            sender = self.agents[fb]
            receiver = self.agents[tb]
            sender.out_q[fp] = receiver.in_q[tp]

    def _create_threads(self) -> None:
        """
        Create execution thread for each agent.

        Each thread:
        - Runs the agent's run() method
        - Captures exceptions via ExceptionThread
        - Named with agent's full path for debugging

        Threads are created but NOT started - use run() to start them.

        Preconditions:
            - self.agents populated

        Modifies:
            - self.threads: Populated with ExceptionThread objects
        """
        for full_name, agent in self.agents.items():
            t = ExceptionThread(
                target=agent.run,
                name=f"{full_name}_thread",
                daemon=False
            )
            self.threads.append(t)

    def _validate_compiled(self) -> None:
        """
        Validate compiled network structure (deep validation).

        Called at end of compile() to ensure compilation succeeded.
        Validates the fully flattened, resolved, wired network.

        Checks:
        - All agent inports have queues
        - All agent outports have queues
        - No unresolved external connections remain
        - All graph connections reference valid agents

        Raises:
            ValueError: If validation fails
        """
        # Verify all agent ports are wired
        for agent_name, agent in self.agents.items():
            # Check all inports connected
            for inport in agent.inports:
                if agent.in_q[inport] is None:
                    raise ValueError(
                        f"Compilation failed: Agent '{agent_name}' inport '{inport}' "
                        f"is not connected to any queue."
                    )

            # Check all outports connected
            for outport in agent.outports:
                if agent.out_q[outport] is None:
                    raise ValueError(
                        f"Compilation failed: Agent '{agent_name}' outport '{outport}' "
                        f"is not connected to any queue."
                    )

        # Verify no unresolved connections remain
        if self.unresolved_connections:
            raise ValueError(
                f"Compilation failed: Unresolved external connections remain:\n"
                f"{self._format_connections(self.unresolved_connections)}"
            )

        # Verify all graph connections reference valid agents
        for conn in self.graph_connections:
            fb, fp, tb, tp = conn
            if fb not in self.agents:
                raise ValueError(
                    f"Compilation failed: Connection references unknown agent '{fb}' "
                    f"in: {self._format_connection(conn)}"
                )
            if tb not in self.agents:
                raise ValueError(
                    f"Compilation failed: Connection references unknown agent '{tb}' "
                    f"in: {self._format_connection(conn)}"
                )

    # ========== Execution Methods ==========

    def startup(self) -> None:
        """
        Call startup() on all agents before running.

        Allows agents to initialize resources (open files, connections, etc.)
        before their run() methods are called.

        Raises:
            RuntimeError: If any agent's startup() fails
        """
        errors = []
        for name, agent in self.agents.items():
            try:
                agent.startup()
            except Exception as e:
                errors.append((name, e))

        if errors:
            msgs = "; ".join(f"{n}: {repr(e)}" for n, e in errors)
            raise RuntimeError(f"Startup failed for agent(s): {msgs}")

    def run(self, timeout: Optional[float] = 30.0) -> None:
        """
        Start all agent threads and wait for completion.

        Each agent runs in its own thread, executing its run() method.
        This method blocks until all threads have joined or timeout occurs.

        Args:
            timeout: Maximum seconds to wait for completion (default 30s, None = no timeout)

        If any agent thread raises an exception, it's captured and reported
        after all threads complete, then re-raised for debugging.

        Raises:
            RuntimeError: If any agent thread failed with an exception
            TimeoutError: If network doesn't complete within timeout
        """
        import time

        # Start all threads
        start_time = time.time()
        for t in self.threads:
            t.start()

        # Wait for all to complete with timeout
        failed_threads = []
        hung_threads = []

        for t in self.threads:
            if timeout is not None:
                elapsed = time.time() - start_time
                remaining = max(0.1, timeout - elapsed)
                t.join(timeout=remaining)

                if t.is_alive():
                    hung_threads.append(t)
            else:
                t.join()

            if hasattr(t, 'exception') and t.exception:
                failed_threads.append(t)

        # Report hung threads (timeout)
        if hung_threads:
            print("\n" + "="*70)
            print("NETWORK TIMEOUT - AGENTS STILL RUNNING:")
            print("="*70)
            print(f"\n⏱️  Network did not complete within {timeout} seconds")
            print(f"\n🔍 These agents are still running (may be hung):")
            for t in hung_threads:
                agent_name = t.name.replace("_thread", "")
                print(f"   - {agent_name}")

            print(f"\n💡 Common causes of hanging:")
            print(f"   1. Source not sending STOP signal when done")
            print(f"   2. Agent waiting forever on recv() with no data")
            print(f"   3. Infinite loop in agent logic")
            print(f"   4. Deadlock between agents")

            print(f"\n🔧 Debug tips:")
            print(f"   - Check that sources send STOP: self.broadcast_stop()")
            print(f"   - Verify agents handle STOP: if msg is STOP: return")
            print(f"   - Add print() statements to see where agents hang")
            print(f"   - Run with timeout=None to wait indefinitely")
            print("="*70)
            raise TimeoutError(
                f"Network timed out after {timeout}s. "
                f"Agents still running: {[t.name for t in hung_threads]}"
            )

        # Report failures
        if failed_threads:
            print("\n" + "="*70)
            print("AGENT FAILURES DETECTED:")
            print("="*70)
            for t in failed_threads:
                print(f"\nThread: {t.name}")
                import traceback
                traceback.print_exception(*t.exc_info)
            print("="*70)
            raise RuntimeError(
                f"{len(failed_threads)} agent(s) failed. See traceback above."
            )

    def shutdown(self) -> None:
        """
        Call shutdown() on all agents after running.

        Allows agents to cleanup resources (close files, connections, etc.)
        after their run() methods complete.

        Errors during shutdown are collected but don't prevent other shutdowns.

        Raises:
            RuntimeError: If any agent's shutdown() fails
        """
        errors = []
        for name, agent in self.agents.items():
            try:
                agent.shutdown()
            except Exception as e:
                errors.append((name, e))

        if errors:
            msgs = "; ".join(f"{n}: {repr(e)}" for n, e in errors)
            raise RuntimeError(f"Shutdown failed for agent(s): {msgs}")

    def run_network(self, timeout: Optional[float] = 30.0) -> None:
        """
        Compile (if needed), startup, run, and shutdown the network.

        This is the main entry point for executing a network.
        Students typically call this after creating a network.

        Args:
            timeout: Maximum seconds to wait for completion (default 30s, None = no timeout)

        Ensures shutdown is called even if errors occur.

        Raises:
            TimeoutError: If network doesn't complete within timeout
            RuntimeError: If agents fail during execution
        """
        # Compile if not already compiled
        if not self.compiled:
            self.compile()

        try:
            self.startup()
            self.run(timeout=timeout)
        finally:
            try:
                self.shutdown()
            except Exception:
                pass  # Don't mask run errors with shutdown errors

    # ========== Debug Output Formatting ==========

    def _format_connection(self, conn: Tuple[str, str, str, str]) -> str:
        """
        Format connection as user-facing string.

        Args:
            conn: 4-tuple (from_block, from_port, to_block, to_port)

        Returns:
            Formatted string: "from_block.from_port → to_block.to_port"
        """
        from_block, from_port, to_block, to_port = conn
        return f"{from_block}.{from_port} → {to_block}.{to_port}"

    def _format_connections(self, connections: List[Tuple[str, str, str, str]]) -> str:
        """
        Format list of connections for display.

        Returns multiline string with one connection per line.
        """
        if not connections:
            return "  (none)"

        lines = []
        for conn in connections:
            lines.append(f"  {self._format_connection(conn)}")
        return "\n".join(lines)

    def show_network(self, verbose: bool = False) -> None:
        """
        Print network structure in user-friendly format.

        Shows both pre-compilation (blocks) and post-compilation (agents) state.

        Args:
            verbose: If True, show additional details like auto-inserted agents
        """
        print(f"Network: {self.name or '(unnamed)'}")
        print("=" * 70)

        # Show blocks (pre-compilation view)
        print(f"\nBlocks ({len(self.blocks)}):")
        for name, block in self.blocks.items():
            block_type = type(block).__name__
            print(f"  {name}: {block_type}")
            if block.inports:
                print(f"    Inports:  {block.inports}")
            if block.outports:
                print(f"    Outports: {block.outports}")

        print(f"\nConnections ({len(self.connections)}):")
        if self.connections:
            for conn in self.connections:
                print(f"  {self._format_connection(conn)}")
        else:
            print("  (none)")

        # Show external ports if any
        if self.inports:
            print(f"\nExternal Inports: {self.inports}")
        if self.outports:
            print(f"\nExternal Outports: {self.outports}")

        # Show compiled state if compiled
        if self.compiled:
            print(f"\n{'=' * 70}")
            print("COMPILED STATE:")
            print("=" * 70)

            print(f"\nAgents ({len(self.agents)}):")
            for name, agent in self.agents.items():
                agent_type = type(agent).__name__
                print(f"  {name}: {agent_type}")

            print(f"\nAgent Connections ({len(self.graph_connections)}):")
            if self.graph_connections:
                for conn in self.graph_connections:
                    print(f"  {self._format_connection(conn)}")
            else:
                print("  (none)")

            # Verbose mode - show auto-inserted agents
            if verbose:
                from dsl.blocks.fanout import Broadcast
                from dsl.blocks.fanin import MergeAsynch

                auto_inserted = {}
                for name, agent in self.blocks.items():
                    if isinstance(agent, (Broadcast, MergeAsynch)):
                        # Check if name follows auto-generated pattern
                        if name.startswith("broadcast_") or name.startswith("merge_"):
                            auto_inserted[name] = agent

                if auto_inserted:
                    print(f"\nAuto-Inserted Agents ({len(auto_inserted)}):")
                    for name, agent in auto_inserted.items():
                        agent_type = type(agent).__name__
                        print(f"  {name}: {agent_type}")

                        # Show what it's doing
                        if isinstance(agent, Broadcast):
                            # Find incoming connection
                            incoming = [
                                self._format_connection(c)
                                for c in self.connections
                                if c[2] == name
                            ]
                            # Find outgoing connections
                            outgoing = [
                                self._format_connection(c)
                                for c in self.connections
                                if c[0] == name
                            ]
                            if incoming:
                                print(f"    Fanout from: {incoming[0]}")
                            if outgoing:
                                print(
                                    f"    Broadcasting to {len(outgoing)} destinations")

                        elif isinstance(agent, MergeAsynch):
                            # Find incoming connections
                            incoming = [
                                self._format_connection(c)
                                for c in self.connections
                                if c[2] == name
                            ]
                            # Find outgoing connection
                            outgoing = [
                                self._format_connection(c)
                                for c in self.connections
                                if c[0] == name
                            ]
                            if incoming:
                                print(
                                    f"    Fanin from {len(incoming)} sources")
                            if outgoing:
                                print(f"    Merging to: {outgoing[0]}")
        else:
            print(f"\n(Network not yet compiled)")
