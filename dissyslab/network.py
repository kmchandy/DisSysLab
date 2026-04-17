# dissyslab/network.py
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
import multiprocessing
from dissyslab.core import Agent, ExceptionThread, ExceptionProcess


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
    4. Create os_agent: Termination detector with full network knowledge
    5. Wire: Create queues and connect agent ports
    6. Thread: Create one thread per agent plus os_agent thread
    7. Validate: Verify compilation succeeded

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
        # Store configuration
        self.name = name
        self.inports: List[str] = list(inports) if inports is not None else []
        self.outports: List[str] = list(
            outports) if outports is not None else []
        self.blocks: Dict[str, Union[Agent, Network]] = blocks or {}
        self.connections: List[Tuple[str, str, str, str]] = connections or []

        # Assign names to blocks (for debugging/errors)
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
        self._os_agent = None

        # Process compilation state (populated by compile_for_processes())
        self.compiled_for_processes: bool = False
        self.mp_queues: List[multiprocessing.Queue] = []
        self.processes: List[ExceptionProcess] = []

    # ========== Validation ==========

    def check(self) -> None:
        """
        Validate basic network structure before compilation.
        """
        if not self.blocks:
            raise ValueError(
                f"Network '{self.name or '(unnamed)'}' must have at least one block. "
                f"Empty networks are not allowed."
            )

        for block_name in self.blocks:
            if not isinstance(block_name, str):
                raise TypeError(
                    f"Block name must be string, got {type(block_name).__name__}: {block_name!r}"
                )
            if "::" in block_name:
                raise ValueError(
                    f"Block name '{block_name}' cannot contain '::' "
                    f"(reserved for nested network paths)"
                )
            if block_name == "external":
                raise ValueError(
                    "'external' is reserved and cannot be used as block name"
                )

        for block_name, block_object in self.blocks.items():
            if not isinstance(block_object, (Agent, Network)):
                raise TypeError(
                    f"Block '{block_name}' must be Agent or Network, "
                    f"got {type(block_object).__name__}"
                )

        for block_name, block_object in self.blocks.items():
            if not isinstance(block_object.inports, list):
                raise TypeError(
                    f"Inports of block '{block_name}' must be list, "
                    f"got {type(block_object.inports).__name__}"
                )
            if not isinstance(block_object.outports, list):
                raise TypeError(
                    f"Outports of block '{block_name}' must be list, "
                    f"got {type(block_object.outports).__name__}"
                )
            if len(set(block_object.inports)) != len(block_object.inports):
                raise ValueError(
                    f"Block '{block_name}' has duplicate inport names: "
                    f"{block_object.inports}"
                )
            if len(set(block_object.outports)) != len(block_object.outports):
                raise ValueError(
                    f"Block '{block_name}' has duplicate outport names: "
                    f"{block_object.outports}"
                )

        for conn in self.connections:
            from_block, from_port, to_block, to_port = conn
            if from_block != "external" and from_block not in self.blocks:
                raise ValueError(
                    f"Connection references unknown from_block '{from_block}': "
                    f"{self._format_connection(conn)}\n"
                    f"Valid blocks: {list(self.blocks.keys()) + ['external']}"
                )
            if to_block != "external" and to_block not in self.blocks:
                raise ValueError(
                    f"Connection references unknown to_block '{to_block}': "
                    f"{self._format_connection(conn)}\n"
                    f"Valid blocks: {list(self.blocks.keys()) + ['external']}"
                )
            if from_block != "external":
                if from_port not in self.blocks[from_block].outports:
                    raise ValueError(
                        f"Unknown from_port in connection: {self._format_connection(conn)}\n"
                        f"Block '{from_block}' has no outport '{from_port}'.\n"
                        f"Valid outports: {self.blocks[from_block].outports}"
                    )
            if to_block != "external":
                if to_port not in self.blocks[to_block].inports:
                    raise ValueError(
                        f"Unknown to_port in connection: {self._format_connection(conn)}\n"
                        f"Block '{to_block}' has no inport '{to_port}'.\n"
                        f"Valid inports: {self.blocks[to_block].inports}"
                    )

        for p in self.inports:
            matches = [c for c in self.connections if c[0]
                       == "external" and c[1] == p]
            if len(matches) == 0:
                raise ValueError(
                    f"External inport '{p}' is not connected. "
                    f"All declared external ports must be connected."
                )

        for p in self.outports:
            matches = [c for c in self.connections if c[2]
                       == "external" and c[3] == p]
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
        4. Create os_agent (needs full graph from steps 1-3)
        5. Wire queues between agents
        6. Create execution threads (client agents + os_agent)
        7. Validate compiled structure
        """
        if self.compiled:
            return

        # Step 1: Maintain 1-to-1 invariant
        self._insert_fanout_fanin()

        # Step 2: Flatten to leaf agents
        self._flatten_networks()

        # Step 3: Resolve external port chains
        self._resolve_external_connections()

        # Step 4: Create os_agent (needs full graph from steps 1-3)
        self._create_os_agent()

        # Step 5: Wire communication channels
        self._wire_queues()

        # Step 6: Wire os_agent client queues (needs wired queues from step 5)
        self._wire_os_agent_queues()

        # Step 7: Create execution threads
        self._create_threads()

        # Step 7: Validate compilation succeeded
        self._validate_compiled()

        self.compiled = True

    def _insert_fanout_fanin(self) -> None:
        """Insert Broadcast and Merge agents for multiple connections."""
        from dissyslab.blocks.fanout import Broadcast
        from dissyslab.blocks.fanin import MergeAsynch

        out_degree: Dict[Tuple[str, str], int] = {}
        in_degree: Dict[Tuple[str, str], int] = {}

        for (fb, fp, tb, tp) in self.connections:
            out_degree[(fb, fp)] = out_degree.get((fb, fp), 0) + 1
            in_degree[(tb, tp)] = in_degree.get((tb, tp), 0) + 1

        fanout_cases = [(b, p)
                        for (b, p), deg in out_degree.items() if deg > 1]

        broadcast_count = 0
        for (block, port) in fanout_cases:
            outgoing = [c for c in self.connections if c[0]
                        == block and c[1] == port]
            num_outputs = len(outgoing)
            broadcast_name = f"broadcast_{broadcast_count}"
            broadcast = Broadcast(num_outputs=num_outputs, name=broadcast_name)
            self.blocks[broadcast_name] = broadcast
            broadcast_count += 1
            for c in outgoing:
                self.connections.remove(c)
            self.connections.append((block, port, broadcast_name, "in_"))
            for i, (_, _, dest_block, dest_port) in enumerate(outgoing):
                self.connections.append(
                    (broadcast_name, f"out_{i}", dest_block, dest_port))

        in_degree = {}
        for (fb, fp, tb, tp) in self.connections:
            in_degree[(tb, tp)] = in_degree.get((tb, tp), 0) + 1

        fanin_cases = [(b, p) for (b, p), deg in in_degree.items() if deg > 1]

        merge_count = 0
        for (block, port) in fanin_cases:
            incoming = [c for c in self.connections if c[2]
                        == block and c[3] == port]
            num_inputs = len(incoming)
            merge_name = f"merge_{merge_count}"
            merge = MergeAsynch(num_inputs=num_inputs, name=merge_name)
            self.blocks[merge_name] = merge
            merge_count += 1
            for c in incoming:
                self.connections.remove(c)
            for i, (src_block, src_port, _, _) in enumerate(incoming):
                self.connections.append(
                    (src_block, src_port, merge_name, f"in_{i}"))
            self.connections.append((merge_name, "out_", block, port))

    def _flatten_networks(self) -> None:
        """Flatten nested networks to leaf agents."""
        class PathNode:
            def __init__(self, block: Union[Agent, Network], path: str):
                self.block = block
                self.path = path

        root_name = self.name if self.name else "root"
        root = PathNode(self, root_name)
        pending = deque([root])

        while pending:
            node = pending.popleft()
            blk, path = node.block, node.path

            if isinstance(blk, Agent):
                self.agents[path] = blk
                continue

            assert isinstance(blk, Network)
            for child_name, child_block in blk.blocks.items():
                child_path = f"{path}::{child_name}" if path else child_name
                pending.append(PathNode(child_block, child_path))

            for (fb, fp, tb, tp) in blk.connections:
                fpath = path if fb == "external" else f"{path}::{fb}"
                tpath = path if tb == "external" else f"{path}::{tb}"
                self.unresolved_connections.append((fpath, fp, tpath, tp))

    def _resolve_external_connections(self) -> None:
        """Resolve external port chains to direct agent→agent connections."""
        changed = True
        while changed:
            changed = False
            for conn in self.unresolved_connections[:]:
                if conn not in self.unresolved_connections:
                    continue
                fb, fp, tb, tp = conn

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

        for (fb, fp, tb, tp) in self.unresolved_connections[:]:
            if fb in self.agents and tb in self.agents:
                self.unresolved_connections.remove((fb, fp, tb, tp))
                self.graph_connections.append((fb, fp, tb, tp))

        if self.unresolved_connections:
            raise ValueError(
                f"Network has unresolved external connections:\n"
                f"{self._format_connections(self.unresolved_connections)}\n"
                f"All external ports must be fully connected to agents."
            )

    def _create_os_agent(self) -> None:
        """
        Create os_agent with full knowledge of the flattened network.

        Called after _resolve_external_connections() so that both
        self.agents and self.graph_connections are fully populated.

        First assigns each agent's name to its full flattened path
        so that status messages from agents match os_agent's keys.
        """
        from dissyslab.os_agent import OsAgent

        # Assign full path names — must match self.agents keys
        # so that status messages from agents can be matched correctly
        for full_name, agent in self.agents.items():
            agent.name = full_name

        self._os_agent = OsAgent(
            agents=self.agents,
            graph_connections=self.graph_connections,
        )

        # Inject os_agent's input queue into every client agent
        for agent in self.agents.values():
            agent.os_q = self._os_agent.in_q

    def _wire_queues(self) -> None:
        """Wire communication queues between agents."""
        for agent in self.agents.values():
            for port in agent.inports:
                agent.in_q[port] = SimpleQueue()
                self.queues.append(agent.in_q[port])

        for (fb, fp, tb, tp) in self.graph_connections:
            sender = self.agents[fb]
            receiver = self.agents[tb]
            sender.out_q[fp] = receiver.in_q[tp]

    def _wire_os_agent_queues(self) -> None:
        """
        Populate os_agent's client_queues with wired inport queues.

        Called after _wire_queues() so that agent.in_q is populated.
        Stores ALL inport queues per agent so that _Shutdown reaches
        every worker thread (important for MergeAsynch which has one
        worker thread per inport).

        client_queues[name] = [q0, q1, ...] — one queue per inport.
        _GiveMeCounts goes to the first queue only.
        _Shutdown goes to all queues.
        """
        for name, agent in self.agents.items():
            if agent.inports:
                self._os_agent.client_queues[name] = [
                    agent.in_q[port] for port in agent.inports
                ]

    def _create_threads(self) -> None:
        """
        Create execution thread for each agent and for os_agent.

        Client agents run via agent.start() — which calls agent.run()
        and handles _ShutdownSignal cleanly.
        os_agent runs its own run() loop independently.
        """
        # One thread per client agent — target is start(), not run()
        for full_name, agent in self.agents.items():
            t = ExceptionThread(
                target=agent.start,
                name=f"{full_name}_thread",
                daemon=False
            )
            self.threads.append(t)

        # os_agent gets its own thread
        t = ExceptionThread(
            target=self._os_agent.run,
            name="os_agent_thread",
            daemon=False
        )
        self.threads.append(t)

    def _validate_compiled(self) -> None:
        """Validate compiled network structure."""
        for agent_name, agent in self.agents.items():
            for inport in agent.inports:
                if agent.in_q[inport] is None:
                    raise ValueError(
                        f"Compilation failed: Agent '{agent_name}' inport '{inport}' "
                        f"is not connected to any queue."
                    )
            for outport in agent.outports:
                if agent.out_q[outport] is None:
                    raise ValueError(
                        f"Compilation failed: Agent '{agent_name}' outport '{outport}' "
                        f"is not connected to any queue."
                    )

        if self.unresolved_connections:
            raise ValueError(
                f"Compilation failed: Unresolved external connections remain:\n"
                f"{self._format_connections(self.unresolved_connections)}"
            )

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
        """Call startup() on all agents before running."""
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

        Includes os_agent thread. Termination is declared by os_agent
        when all edges balance — no timeout needed for normal operation.
        timeout is a safety net for hung networks.
        """
        import time

        start_time = time.time()
        for t in self.threads:
            t.start()

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

        if hung_threads:
            print("\n" + "="*70)
            print("NETWORK TIMEOUT - AGENTS STILL RUNNING:")
            print("="*70)
            print(f"\n  Network did not complete within {timeout} seconds")
            print(f"\n  Agents still running:")
            for t in hung_threads:
                agent_name = t.name.replace("_thread", "")
                print(f"   - {agent_name}")
            print("="*70)
            raise TimeoutError(
                f"Network timed out after {timeout}s. "
                f"Agents still running: {[t.name for t in hung_threads]}"
            )

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
        """Call shutdown() on all agents after running."""
        errors = []
        for name, agent in self.agents.items():
            try:
                agent.shutdown()
            except Exception as e:
                errors.append((name, e))

        if errors:
            msgs = "; ".join(f"{n}: {repr(e)}" for n, e in errors)
            raise RuntimeError(f"Shutdown failed for agent(s): {msgs}")

    def run_network(self, timeout: Optional[float] = 300.0) -> None:
        """
        Compile (if needed), startup, run, and shutdown the network.

        Main entry point for executing a network.
        Termination is detected automatically by os_agent.
        timeout is a safety net — under normal operation os_agent
        declares termination before timeout is reached.
        """
        if not self.compiled:
            self.compile()

        try:
            self.startup()
            self.run(timeout=timeout)
        finally:
            try:
                self.shutdown()
            except Exception:
                pass

    # ========== Process-based Execution ==========

    def _wire_mp_queues(self) -> None:
        """Wire multiprocessing.Queue objects between agents."""
        for agent in self.agents.values():
            for port in agent.inports:
                q = multiprocessing.Queue()
                agent.in_q[port] = q
                self.mp_queues.append(q)

        for (fb, fp, tb, tp) in self.graph_connections:
            sender = self.agents[fb]
            receiver = self.agents[tb]
            sender.out_q[fp] = receiver.in_q[tp]

    def _create_processes(self) -> None:
        """Create one ExceptionProcess per agent."""
        for full_name, agent in self.agents.items():
            p = ExceptionProcess(
                target=agent.run,
                name=f"{full_name}_process",
                daemon=False
            )
            self.processes.append(p)

    def compile_for_processes(self) -> None:
        """Compile network for process-based execution."""
        if self.compiled_for_processes:
            return
        if not self.compiled:
            self.compile()
        self._wire_mp_queues()
        self._create_processes()
        self.compiled_for_processes = True

    def process_network(self, timeout: Optional[float] = 30.0) -> None:
        """Compile (if needed) and run the network using OS processes."""
        if not self.compiled_for_processes:
            self.compile_for_processes()

        try:
            self.startup()
            self._run_processes(timeout=timeout)
        finally:
            try:
                self.shutdown()
            except Exception:
                pass

    def _run_processes(self, timeout: Optional[float] = 30.0) -> None:
        """Start all agent processes and wait for completion."""
        import time
        start_time = time.time()

        for p in self.processes:
            p.start()

        failed = []
        hung = []

        for p in self.processes:
            if timeout is not None:
                elapsed = time.time() - start_time
                remaining = max(0.1, timeout - elapsed)
                p.join(timeout=remaining)
                if p.is_alive():
                    hung.append(p)
                    p.terminate()
            else:
                p.join()

            if p.exception:
                failed.append(p)

        if hung:
            raise TimeoutError(
                f"Network timed out after {timeout}s. "
                f"Agents still running: {[p.name for p in hung]}"
            )

        if failed:
            print("\n" + "="*70)
            print("AGENT FAILURES DETECTED (processes):")
            print("="*70)
            for p in failed:
                print(f"\nProcess: {p.name}")
                print(p.traceback_str)
            print("="*70)
            raise RuntimeError(
                f"{len(failed)} agent(s) failed. See traceback above."
            )

    # ========== Debug Output Formatting ==========

    def _format_connection(self, conn: Tuple[str, str, str, str]) -> str:
        from_block, from_port, to_block, to_port = conn
        return f"{from_block}.{from_port} → {to_block}.{to_port}"

    def _format_connections(self, connections: List[Tuple[str, str, str, str]]) -> str:
        if not connections:
            return "  (none)"
        return "\n".join(f"  {self._format_connection(conn)}" for conn in connections)

    def show_network(self, verbose: bool = False) -> None:
        """Print network structure in user-friendly format."""
        print(f"Network: {self.name or '(unnamed)'}")
        print("=" * 70)

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

        if self.inports:
            print(f"\nExternal Inports: {self.inports}")
        if self.outports:
            print(f"\nExternal Outports: {self.outports}")

        if self.compiled:
            print(f"\n{'=' * 70}")
            print("COMPILED STATE:")
            print("=" * 70)

            print(f"\nAgents ({len(self.agents)}):")
            for name, agent in self.agents.items():
                print(f"  {name}: {type(agent).__name__}")

            print(f"\nAgent Connections ({len(self.graph_connections)}):")
            if self.graph_connections:
                for conn in self.graph_connections:
                    print(f"  {self._format_connection(conn)}")
            else:
                print("  (none)")

            if verbose:
                from dissyslab.blocks.fanout import Broadcast
                from dissyslab.blocks.fanin import MergeAsynch
                auto_inserted = {
                    name: agent for name, agent in self.blocks.items()
                    if isinstance(agent, (Broadcast, MergeAsynch))
                    and (name.startswith("broadcast_") or name.startswith("merge_"))
                }
                if auto_inserted:
                    print(f"\nAuto-Inserted Agents ({len(auto_inserted)}):")
                    for name, agent in auto_inserted.items():
                        print(f"  {name}: {type(agent).__name__}")
        else:
            print(f"\n(Network not yet compiled)")
