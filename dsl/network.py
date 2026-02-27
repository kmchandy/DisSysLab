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
import multiprocessing

from dsl.core import Agent, ExceptionThread, ExceptionProcess


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
    - Compiles into executable graph with threads or processes and queues
    - Manages agent lifecycle (startup → run → shutdown)

    **Execution modes:**
        g.run_network()      # each agent runs in its own thread  (default)
        g.process_network()  # each agent runs in its own process (true parallelism)

    Both modes use identical network descriptions. The difference is invisible
    to agent code — agents communicate through queues in both cases.
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

        # ── Thread compilation state (populated by compile()) ──────────────
        self.compiled: bool = False
        self.agents: Dict[str, Agent] = {}
        self.graph_connections: List[Tuple[str, str, str, str]] = []
        self.queues: List[SimpleQueue] = []
        self.threads: List[ExceptionThread] = []
        self.unresolved_connections: List[Tuple[str, str, str, str]] = []

        # ── Process compilation state (populated by compile_for_processes())
        self.compiled_for_processes: bool = False
        self.mp_queues: List[multiprocessing.Queue] = []
        self.processes: List[ExceptionProcess] = []
        # agents and graph_connections are shared — _prepare() populates them
        # once; both compile paths reuse them.

    # ========== Validation ==========

    def check(self) -> None:
        """
        Validate basic network structure before compilation.
        """
        # ========== Validate Block Names ==========
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

        # ========== Validate Block Types ==========
        for block_name, block_object in self.blocks.items():
            if not isinstance(block_object, (Agent, Network)):
                raise TypeError(
                    f"Block '{block_name}' must be Agent or Network, "
                    f"got {type(block_object).__name__}"
                )

        # ========== Validate Port Structure ==========
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

        # ========== Validate Connection Endpoints ==========
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

        # ========== Validate External Port Connectivity ==========
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

    # ========== Shared Graph Preparation (steps 0-2) ==========

    def _prepare(self) -> None:
        """
        Run the three graph-manipulation steps shared by both compile paths.

        Steps:
            0. Insert fanout/fanin agents (Broadcast/MergeAsynch)
            1. Flatten nested networks to leaf agents
            2. Resolve external port chains to direct agent↔agent edges

        After _prepare():
            self.agents            — flat dict of all leaf agents
            self.graph_connections — direct agent↔agent edges
            self.unresolved_connections — empty (all resolved)

        Both compile() and compile_for_processes() call _prepare() first.
        _prepare() is idempotent: calling it twice is safe because compile()
        and compile_for_processes() each guard with their own compiled flag.
        """
        self._insert_fanout_fanin()
        self._flatten_networks()
        self._resolve_external_connections()

    # ========== Compilation Pipeline — Thread Version ==========

    def compile(self) -> None:
        """
        Compile network for thread-based execution.

        Pipeline:
            _prepare()         — steps 0-2: shared graph work
            _wire_queues()     — SimpleQueue between agents
            _create_threads()  — one ExceptionThread per agent
            _validate_compiled()

        After compile(), call run_network() to execute.
        """
        if self.compiled:
            return

        self._prepare()
        self._wire_queues()
        self._create_threads()
        self._validate_compiled()
        self.compiled = True

    def compile_for_processes(self) -> None:
        """
        Compile network for process-based execution.

        Pipeline:
            _prepare()           — steps 0-2: shared graph work (same as compile)
            _wire_mp_queues()    — multiprocessing.Queue between agents
            _create_processes()  — one ExceptionProcess per agent
            _validate_compiled()

        After compile_for_processes(), call process_network() to execute.

        Note on true parallelism:
            Each agent runs in its own OS process with its own Python interpreter,
            bypassing the GIL. For compute-intensive agents (heavy numpy, image
            processing, simulations) this gives genuine CPU parallelism.

            Cost: messages are pickled/unpickled as they cross process boundaries.
            For large numpy arrays this serialization overhead can outweigh the
            parallelism benefit. For I/O-bound agents (API calls, file reads),
            thread-based execution is usually sufficient.
        """
        if self.compiled_for_processes:
            return

        self._prepare()
        self._wire_mp_queues()
        self._create_processes()
        self._validate_compiled_for_processes()
        self.compiled_for_processes = True

    # ========== Graph Steps (shared) ==========

    def _insert_fanout_fanin(self) -> None:
        """Insert Broadcast and MergeAsynch agents for fanout/fanin connections."""
        from dsl.blocks.fanout import Broadcast
        from dsl.blocks.fanin import MergeAsynch

        out_degree: Dict[Tuple[str, str], int] = {}
        in_degree: Dict[Tuple[str, str], int] = {}

        for (fb, fp, tb, tp) in self.connections:
            out_degree[(fb, fp)] = out_degree.get((fb, fp), 0) + 1
            in_degree[(tb, tp)] = in_degree.get((tb, tp), 0) + 1

        fanout_cases = [(b, p)
                        for (b, p), deg in out_degree.items() if deg > 1]

        broadcast_count = 0
        for (block, port) in fanout_cases:
            outgoing = [
                c for c in self.connections
                if c[0] == block and c[1] == port
            ]
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
                    (broadcast_name, f"out_{i}", dest_block, dest_port)
                )

        in_degree = {}
        for (fb, fp, tb, tp) in self.connections:
            in_degree[(tb, tp)] = in_degree.get((tb, tp), 0) + 1

        fanin_cases = [(b, p) for (b, p), deg in in_degree.items() if deg > 1]

        merge_count = 0
        for (block, port) in fanin_cases:
            incoming = [
                c for c in self.connections
                if c[2] == block and c[3] == port
            ]
            num_inputs = len(incoming)
            merge_name = f"merge_{merge_count}"
            merge = MergeAsynch(num_inputs=num_inputs, name=merge_name)
            self.blocks[merge_name] = merge
            merge_count += 1

            for c in incoming:
                self.connections.remove(c)
            for i, (src_block, src_port, _, _) in enumerate(incoming):
                self.connections.append(
                    (src_block, src_port, merge_name, f"in_{i}")
                )
            self.connections.append((merge_name, "out_", block, port))

    def _flatten_networks(self) -> None:
        """Flatten nested networks to leaf agents."""
        class PathNode:
            def __init__(self, block, path):
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
        """Resolve external port chains to direct agent↔agent connections."""
        changed = True
        while changed:
            changed = False

            for conn in self.unresolved_connections[:]:
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

    # ========== Wiring — Thread Version ==========

    def _wire_queues(self) -> None:
        """
        Wire SimpleQueue objects between agents (thread execution).

        Creates one SimpleQueue per agent inport.
        Connects sender outports to receiver inport queues.
        """
        for agent in self.agents.values():
            for port in agent.inports:
                agent.in_q[port] = SimpleQueue()
                self.queues.append(agent.in_q[port])

        for (fb, fp, tb, tp) in self.graph_connections:
            sender = self.agents[fb]
            receiver = self.agents[tb]
            sender.out_q[fp] = receiver.in_q[tp]

    # ========== Wiring — Process Version ==========

    def _wire_mp_queues(self) -> None:
        """
        Wire multiprocessing.Queue objects between agents (process execution).

        Identical to _wire_queues() but uses multiprocessing.Queue instead of
        SimpleQueue. multiprocessing.Queue is process-safe: it serializes
        (pickles) messages as they cross process boundaries.

        Messages must be picklable. Standard Python types (dicts, lists,
        strings, numbers, numpy arrays) are all picklable.
        """
        for agent in self.agents.values():
            for port in agent.inports:
                agent.in_q[port] = multiprocessing.Queue()
                self.mp_queues.append(agent.in_q[port])

        for (fb, fp, tb, tp) in self.graph_connections:
            sender = self.agents[fb]
            receiver = self.agents[tb]
            sender.out_q[fp] = receiver.in_q[tp]

    # ========== Thread Creation ==========

    def _create_threads(self) -> None:
        """Create one ExceptionThread per agent."""
        for full_name, agent in self.agents.items():
            t = ExceptionThread(
                target=agent.run,
                name=f"{full_name}_thread",
                daemon=False
            )
            self.threads.append(t)

    # ========== Process Creation ==========

    def _create_processes(self) -> None:
        """
        Create one ExceptionProcess per agent.

        Each process runs agent.run() in a separate OS process with its
        own Python interpreter — no shared GIL, true CPU parallelism.
        """
        for full_name, agent in self.agents.items():
            p = ExceptionProcess(
                target=agent.run,
                name=f"{full_name}_process",
                daemon=False
            )
            self.processes.append(p)

    # ========== Validation ==========

    def _validate_compiled(self) -> None:
        """Validate thread-compiled network structure."""
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
                    f"Compilation failed: Connection references unknown agent '{fb}'"
                )
            if tb not in self.agents:
                raise ValueError(
                    f"Compilation failed: Connection references unknown agent '{tb}'"
                )

    def _validate_compiled_for_processes(self) -> None:
        """
        Validate process-compiled network structure.

        Same port-wiring checks as _validate_compiled() — agents must have
        all ports connected to multiprocessing.Queue objects.
        """
        for agent_name, agent in self.agents.items():
            for inport in agent.inports:
                if agent.in_q[inport] is None:
                    raise ValueError(
                        f"Process compilation failed: Agent '{agent_name}' "
                        f"inport '{inport}' is not connected to any queue."
                    )
            for outport in agent.outports:
                if agent.out_q[outport] is None:
                    raise ValueError(
                        f"Process compilation failed: Agent '{agent_name}' "
                        f"outport '{outport}' is not connected to any queue."
                    )

    # ========== Execution Methods — Thread Version ==========

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
        """Start all agent threads and wait for completion."""
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

    def run_network(self, timeout: Optional[float] = 30.0) -> None:
        """
        Compile (if needed), startup, run, and shutdown the network.

        Each agent runs in its own thread. Threads share memory and
        communicate through SimpleQueue objects. This is the default
        execution mode and works well for I/O-bound workloads (API calls,
        file reads, network requests) and numpy-heavy workloads (the GIL
        releases during C-extension calls).

        For CPU-bound Python code that does not release the GIL, use
        process_network() instead.

        Args:
            timeout: Maximum seconds to wait for completion (default 30s,
                     None = no timeout)
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

    # ========== Execution Methods — Process Version ==========

    def run_processes(self, timeout: Optional[float] = 30.0) -> None:
        """
        Start all agent processes and wait for completion.

        Mirrors run() but for ExceptionProcess instances.
        Exceptions in child processes are shipped back via a Queue
        and re-raised here in the parent.
        """
        import time

        start_time = time.time()
        for p in self.processes:
            p.start()

        failed_processes = []
        hung_processes = []

        for p in self.processes:
            if timeout is not None:
                elapsed = time.time() - start_time
                remaining = max(0.1, timeout - elapsed)
                p.join(timeout=remaining)
                if p.is_alive():
                    hung_processes.append(p)
                    p.terminate()
            else:
                p.join()

            if p.exception:
                failed_processes.append(p)

        if hung_processes:
            print("\n" + "="*70)
            print("NETWORK TIMEOUT - PROCESSES STILL RUNNING:")
            print("="*70)
            print(f"\n⏱️  Network did not complete within {timeout} seconds")
            print(f"\n🔍 These agents are still running (may be hung):")
            for p in hung_processes:
                agent_name = p.name.replace("_process", "")
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
                f"Processes still running: {[p.name for p in hung_processes]}"
            )

        if failed_processes:
            print("\n" + "="*70)
            print("AGENT FAILURES DETECTED:")
            print("="*70)
            for p in failed_processes:
                print(f"\nProcess: {p.name}")
                print(p.traceback_str)
            print("="*70)
            raise RuntimeError(
                f"{len(failed_processes)} agent(s) failed. See traceback above."
            )

    def process_network(self, timeout: Optional[float] = 30.0) -> None:
        """
        Compile (if needed), startup, run, and shutdown the network using processes.

        Each agent runs in its own OS process with its own Python interpreter.
        This bypasses the GIL and gives true CPU parallelism for compute-intensive
        agents.

        The network description is identical to run_network() — change one word
        in app.py to switch execution modes:

            g.run_network()      # threads (default)
            g.process_network()  # processes (true parallelism)

        When to use process_network():
            - Agents do heavy CPU-bound Python computation
            - You want to use all available CPU cores
            - Workload justifies the serialization cost of inter-process messaging

        When run_network() is sufficient:
            - Agents call numpy, scipy, PIL (GIL releases for C extensions)
            - Agents do I/O (file reads, API calls, network requests)
            - Messages are large numpy arrays (pickling cost may dominate)

        Args:
            timeout: Maximum seconds to wait for completion (default 30s,
                     None = no timeout)
        """
        if not self.compiled_for_processes:
            self.compile_for_processes()
        try:
            self.startup()
            self.run_processes(timeout=timeout)
        finally:
            try:
                self.shutdown()
            except Exception:
                pass

    # ========== Debug Output Formatting ==========

    def _format_connection(self, conn: Tuple[str, str, str, str]) -> str:
        from_block, from_port, to_block, to_port = conn
        return f"{from_block}.{from_port} → {to_block}.{to_port}"

    def _format_connections(self, connections: List[Tuple[str, str, str, str]]) -> str:
        if not connections:
            return "  (none)"
        lines = []
        for conn in connections:
            lines.append(f"  {self._format_connection(conn)}")
        return "\n".join(lines)

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
            print("COMPILED STATE (threads):")
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

        if self.compiled_for_processes:
            print(f"\n{'=' * 70}")
            print("COMPILED STATE (processes):")
            print("=" * 70)
            print(f"  {len(self.processes)} processes ready")

        if not self.compiled and not self.compiled_for_processes:
            print(f"\n(Network not yet compiled)")
