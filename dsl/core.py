# dsl/core.py
from __future__ import annotations
from queue import SimpleQueue
from threading import Thread
from typing import Optional, List, Dict, Tuple, Union, Any
from collections import deque
from abc import ABC, abstractmethod

STOP = "__STOP__"  # end-of-stream sentinel
# (from_block, from_port, to_block, to_port)
Connection = Tuple[str, str, str, str]


class Agent(ABC):
    """
    Minimal agent: blocking recv/send; STOP handling is per concrete block.
    NOTE: `name` is assigned by Network during compile; do not rely on it earlier.
    """

    def __init__(
        self,
        *,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
    ):
        # Avoid mutable-default traps
        self.inports: List[str] = list(inports) if inports is not None else []
        self.outports: List[str] = list(
            outports) if outports is not None else []
        self.in_q: Dict[str, Any] = {p: None for p in self.inports}
        self.out_q: Dict[str, Any] = {r: None for r in self.outports}
        self.name: Optional[str] = None  # set by Network

    # Lifecycle
    def startup(self) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    def shutdown(self) -> None:
        pass

    def stop(self) -> None:
        """Default: emit STOP on all outports (concrete blocks may override)."""
        for outport in self.outports:
            self.send(STOP, outport)

    # I/O
    def send(self, msg: Any, outport: str) -> None:
        if outport not in self.outports or outport not in self.out_q:
            raise ValueError(
                f"{outport} of agent {self.name} is not an output port.")
        q = self.out_q[outport]
        if q is None:
            raise ValueError(
                f"Outport {outport} of agent {self.name} is not connected.")
        q.put(msg)

    def recv(self, inport: str) -> Any:
        if inport not in self.inports or inport not in self.in_q:
            raise ValueError(
                f"[{self.name}] Input port {inport} not in inports.")
        q = self.in_q[inport]
        if q is None:
            raise ValueError(
                f"[{self.name}] Input port {inport} is not connected.")
        return q.get()

    # Infra close (logical; SimpleQueue has no real close)
    def close(self, inport: str) -> None:
        """
        Logical close hook for an input port. For SimpleQueue this is a no-op.
        Blocks may override to record closed state; Network may use it in the future.
        """
        return


class Network:
    """
    Container of interconnected Agents/Networks with 1→1 edges.
    External ports may be used; all referenced ports/blocks must exist.
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
        blocks: Optional[Dict[str, Union[Agent, "Network"]]] = None,
        connections: Optional[List[Connection]] = None,
    ) -> None:
        self.name = name
        self.inports = list(inports) if inports is not None else []
        self.outports = list(outports) if outports is not None else []
        self.blocks: Dict[str, Union[Agent, Network]] = blocks or {}
        self.connections: List[Connection] = connections or []

        # Assign runtime names to blocks
        for block_name, block_object in self.blocks.items():
            block_object.name = block_name

        self.check()

        self.compiled_blocks: Dict[str, Agent] = {}
        self.compiled_connections: List[Connection] = []

    def check(self) -> None:
        """
        Validate:
        - Blocks are Agent/Network; IDs are unique/strings; no '.'; 'external' reserved.
        - Every connection references existing blocks/ports (or 'external').
        - Each declared port exists.
        - Each outport is connected exactly once.
        - Each inport is connected exactly once.
        - External in/out ports, if used, are each connected exactly once.
        """
        # Block structure
        for block_name, block_object in self.blocks.items():
            if not isinstance(block_name, str):
                raise TypeError(f"Block name must be a string: {block_name!r}")
            if "." in block_name:
                raise ValueError(
                    f"Block name '{block_name}' may not contain '.'")
            if block_name == "external":
                raise ValueError(
                    "'external' is reserved and cannot be a block name.")
            if not isinstance(block_object, (Agent, Network)):
                raise TypeError(
                    f"Block {block_name} must be an Agent or Network.")
            if not isinstance(block_object.inports, list):
                raise TypeError(f"inports of {block_name} must be a list.")
            if not isinstance(block_object.outports, list):
                raise TypeError(f"outports of {block_name} must be a list.")
            if len(set(block_object.inports)) != len(block_object.inports):
                raise ValueError(
                    f"Duplicate inport names in block '{block_name}'.")
            if len(set(block_object.outports)) != len(block_object.outports):
                raise ValueError(
                    f"Duplicate outport names in block '{block_name}'.")

        # Connection endpoint validation
        def _block_exists(b: str) -> bool:
            return b == "external" or b in self.blocks

        for (fb, fp, tb, tp) in self.connections:
            if not _block_exists(fb):
                raise ValueError(
                    f"Connection references unknown from_block '{fb}'.")
            if not _block_exists(tb):
                raise ValueError(
                    f"Connection references unknown to_block '{tb}'.")
            if fb != "external":
                if fp not in self.blocks[fb].outports:
                    raise ValueError(
                        f"Unknown from_port '{fp}' on block '{fb}'.")
            if tb != "external":
                if tp not in self.blocks[tb].inports:
                    raise ValueError(
                        f"Unknown to_port '{tp}' on block '{tb}'.")

        # Each inport connected exactly once;
        # each outport connected exactly once
        for block_name, block_object in self.blocks.items():
            # Inports: exactly one incoming connection
            for inport in block_object.inports:
                matches = [c for c in self.connections if c[2]
                           == block_name and c[3] == inport]
                if not matches:
                    raise TypeError(
                        f"Inport '{inport}' in block '{block_name}' is not connected.")
                if len(matches) > 1:
                    raise ValueError(
                        f"Inport '{inport}' in block '{block_name}' is connected more than once.")
            # Outports: exactly one outgoing connection each
            for outport in block_object.outports:
                matches = [c for c in self.connections if c[0]
                           == block_name and c[1] == outport]
                if not matches:
                    raise TypeError(
                        f"Outport '{outport}' in block '{block_name}' is not connected.")
                if len(matches) > 1:
                    raise ValueError(
                        f"Outport '{outport}' in block '{block_name}' is connected more than once.")

        # External ports (if declared on this network): exactly once
        for p in self.inports:
            matches = [c for c in self.connections if c[0]
                       == "external" and c[1] == p]
            if len(matches) == 0:
                raise ValueError(
                    f"External inport '{p}' is not connected. It must be connected exactly once.")
            if len(matches) > 1:
                raise ValueError(
                    f"External inport '{p}' connections {matches}. Must be connected exactly once.")
        for p in self.outports:
            matches = [c for c in self.connections if c[2]
                       == "external" and c[3] == p]
            if len(matches) == 0:
                raise ValueError(
                    f"External outport '{p}' is not connected. It must be connected exactly once.")
            if len(matches) > 1:
                raise ValueError(
                    f"External outport '{p}' connections {matches}. It must be connected exactly once.")

    def compile(self) -> None:
        """
        Flatten nested networks, resolve external links to direct agent→agent edges,
        wire queues, and prepare one thread per agent.
        """
        class PathNode:
            def __init__(self, block: Union[Agent, Network], full_path_name: str):
                self.block = block
                self.full_path_name = full_path_name

        assert isinstance(self, Network)

        self.agents: Dict[str, Agent] = {}
        self.graph_connections: List[Connection] = []
        # Reserved: track queues if we later model close-state checks.
        self.queues: List[SimpleQueue] = []
        self.threads: List[Thread] = []
        self.unresolved_connections: List[Connection] = []
        root = PathNode(self, "root")
        pending = deque([root])

        # Flatten to agents and lift connections to full paths
        while pending:
            node = pending.popleft()
            blk, path = node.block, node.full_path_name
            if isinstance(blk, Agent):
                self.agents[path] = blk
                continue
            # blk is a Network
            for child in blk.blocks.values():  # type: ignore[attr-defined]
                pending.append(
                    PathNode(child, f"{path}.{child.name}" if path else child.name))
            # type: ignore[attr-defined]
            for (fb, fp, tb, tp) in blk.connections:
                fpath = path if fb == "external" else f"{path}.{fb}"
                tpath = path if tb == "external" else f"{path}.{tb}"
                self.unresolved_connections.append((fpath, fp, tpath, tp))

        # Collapse externals to direct agent→agent edges (fixpoint)
        changed = True
        while changed:
            changed = False
            for conn in self.unresolved_connections[:]:
                fb, fp, tb, tp = conn
                # external-out collapse: (X,p)->(Y,r) where (Y,r)->(Z,s)
                match = next(
                    (v for v in self.unresolved_connections if v[0] == tb and v[1] == tp), None)
                if match:
                    new_conn = (fb, fp, match[2], match[3])
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True
                    continue
                # external-in collapse: (W,q)->(X,p) where (Y,r)->(W,q)
                match = next(
                    (v for v in self.unresolved_connections if v[2] == fb and v[3] == fp), None)
                if match:
                    new_conn = (match[0], match[1], tb, tp)
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True

        # Keep only agent↔agent connections
        for (fb, fp, tb, tp) in self.unresolved_connections[:]:
            if fb in self.agents and tb in self.agents:
                self.unresolved_connections.remove((fb, fp, tb, tp))
                self.graph_connections.append((fb, fp, tb, tp))

        if self.unresolved_connections:
            print(
                f"WARNING: external unconnected ports: {self.unresolved_connections}")

        # Wire queues (one queue per inport)
        for agent in self.agents.values():
            for p in agent.inports:
                agent.in_q[p] = SimpleQueue()
                self.queues.append(agent.in_q[p])

        # Connect outports to the receiver's inport queues (1→1 edges already validated)
        for (fb, fp, tb, tp) in self.graph_connections:
            recv = self.agents[tb]
            send = self.agents[fb]
            send.out_q[fp] = recv.in_q[tp]

        # Prepare threads
        for full_name, block in self.agents.items():
            t = Thread(target=block.run,
                       name=f"{full_name}_thread", daemon=False)
            self.threads.append(t)

    def startup(self) -> None:
        errors = []
        for name, block in self.agents.items():
            try:
                block.startup()
            except Exception as e:
                errors.append((name, e))
        if errors:
            msgs = "; ".join(f"{n}: {repr(e)}" for n, e in errors)
            raise RuntimeError(f"Startup failed for block(s): {msgs}")

    def shutdown(self) -> None:
        errors = []
        for name, block in self.agents.items():
            try:
                block.shutdown()
            except Exception as e:
                errors.append((name, e))
        if errors:
            msgs = "; ".join(f"{n}: {repr(e)}" for n, e in errors)
            raise RuntimeError(f"Shutdown failed for block(s): {msgs}")

    def run(self) -> None:
        """Start all agent threads and join them; worker exceptions are not intercepted."""
        for t in self.threads:
            t.start()
        for t in self.threads:
            t.join()

    def compile_and_run(self) -> None:
        self.compile()
        try:
            self.startup()
            self.run()
        finally:
            try:
                self.shutdown()
            except Exception:
                pass
