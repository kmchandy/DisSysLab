"""
Module: core.py
This module contains the Network, Agent and SimpleAgent classes which
form the framework for building distributed applications.


Network
-------
 A network consists of a set of blocks
blocks. We refer to blocks within a network as components of the network.

A network may have input ports and output ports, and components of the
network may also have input and output ports. A Connection is a
4-tuple (from_block, from_port, to_block, to_port) which represents
a directed communication channel from the from_port of the block from_block
to the to_port of the block to_block. A Connection may be represented in
the documentation as:
       (from_block, from_port) -> (to_block, to_port)

An input port of the network is connected to an input port of a component of the
network. An output port of the network is sent messages by an output port of a
component. Connections between ports are specified by a labeled directed graph in
which a vertex is a Block and an edge is a Connection.

Each block in a network has a unique name and each port of a block has a unique name.
When we refer to block 'X' and port 'p' we mean the block with name 'X' and the port
with name 'p' respectively.

Connections: connecting ports
-----------------------------------------
When specifying connections in a network, we refer to the network itself as "external".
Input and output ports are called inports and outports, respectively.

Connections are specified in the following way:

1. Connect inport 'p' of the network to inport 'w' of component called 'X'.
        [inport 'p'of network ]   --->   [inport 'w' of component called 'X']
        ('external', 'p', 'w', 'X')

2. Connect outport 'w' of component 'X' to outport 'p' of the network.
    [outport 'w' of component called 'X']   --->    [outport 'p'of network ]
        ('X', 'w', 'external', 'p')

3. Connect outport 'p' of component 'X' to inport 'r' of component 'Y'.
    [outport 'p' of component called 'X']   --->    [inport 'r' of component called 'Y' ]
        ('X', 'p', 'Y', 'r')

4. An outport of a component is connected exactly once. Likewise, an input port
of a component is connected exactly once.


Agent
-----
Agent functions: send and recv.
    (1) for an agent X and outport 'p' of X, and a message msg
              X.send(msg, 'p')
     sends msg through outport 'p'.
    (2) for an agent X and inport 'p' of X,
              msg = X.recv('p')
     If there is a message at inport 'p' then the message is removed from
     the port and assigned to variable msg of X. If there is no message at
     'p' then X waits until a message arrives at 'p' and then assigns the
     message to msg.


SimpleAgent
-----------
SimpleAgent is an Agent. A SimpleAgent has a single inport and is specified
by two functions init_fn and handle_msg. The run function of SimpleAgent is
overridden by a function that first executes init_fn and then executes
a loop which waits for messages on its single inport and then calls
handle_msg to process the message. The loop terminates when a '__STOP__' message
is received.

Tags: core, block, agent, network, message-passing, framework
"""

from __future__ import annotations
# Use multiprocessing for executing on different processes
# from multiprocessing import SimpleQueue
from queue import SimpleQueue
from threading import Thread
from typing import Optional, List, Callable, Dict, Tuple, Union, Any
import inspect
import time
from collections import deque
import logging
from abc import ABC, abstractmethod

STOP = "__STOP__"   # end-of-stream sentinel.


# Configure logging
logging.basicConfig(
    filename='debug.log',           # Log file name
    filemode='w',                   # Overwrite each time; use 'a' to append
    level=logging.DEBUG,            # Only log DEBUG and above
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define a Connection as (from_block, from_port, to_block, to_port)
# where from_block and to_block are block names, and from_port and to_port
# are port names.
# (from_block, from_port) -> (to_block, to_port)
Connection = Tuple[str, str, str, str]

# block_parameter_name, child_block_name, child_block_parameter_name
ParameterMapTriple = Tuple[str, str, str]

# =================================================
#         Helper Functions                        |
# =================================================


def filtered_kwargs(fn, pool: dict) -> dict:
    """
    Pass only what the callable accepts; supports **kwargs too.
    """
    sig = inspect.signature(fn)
    params = sig.parameters.values()
    if any(p.kind == p.VAR_KEYWORD for p in params):  # has **kwargs
        return dict(pool)
    names = {p.name for p in params if p.kind in (
        p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}
    return {k: v for k, v in pool.items() if k in names}


# =================================================
#                    Agent                        |
# =================================================

class Agent(ABC):
    """
Parameters:
- name: 
- inports: List of input ports (default: ["in"]).
- outports: List of output ports.
- run: Function to call with `self` as input.

Behavior:
- An agent may have an arbitrary number of inports and an arbitrary number
  of outports.
- An agent is executed by calling the agent's run function which may
    call send and recv functions to send messages on the agent's outports
    and receive messages on the agent's inports, respectively.
Notes:
    Queues
    ------
    in_q and out_q are dicts that map port names to queues.
    The wiring part -- see Step 3 -- of compile() assigns queues.
    If outport 'p' of agent X is connected to inport 'r' of agent Y
    then X.out_a['p'] is assigned a queue, and Y.in_q['r'] is set 
    equal to X.out_a['p']. So messages sent on outport 'p' of X are 
    put in the queue Y.in_q['r'] and received by Y from its inport 'r'.

    self.inport_most_recent_msg is the inport from which a message was
    received most recently. Used only in recv_from_any_port. It is
    used to ensure fairness -- a message sent to any inport is received eventually.

Use Cases:
- Custom logic in a block.

Tags: agent, message-passing
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
    ):
        self.inports = inports
        self.outports = outports
        # Queues are assigned later by the Network during wiring.
        # in_q[p] and out_q[r] are the queues associated with ports p, r.
        self.in_q: Dict[str, Any] = {p: None for p in self.inports}
        self.out_q: Dict[str, Any] = {r: None for r in self.outports}
        self.inport_most_recent_msg = None

# =================================================
#        startup, run, shutdown, stop

    def startup(self) -> None:
        """Initialization. Called once before run()."""
        pass

    @abstractmethod
    def run(self) -> None:
        """ Subclasses must override.
        Main loop. Called only after startup. ."""
        raise NotImplementedError

    def shutdown(self) -> None:
        """Cleanup. Called after all worker threads/processes have joined."""
        pass

    def stop(self):
        """
        Stop the Agent. This is a placeholder method that can be overridden by subclasses.
        """
        for outport in self.outports:
            self.send(msg=STOP, outport=outport)
        logging.debug(f"Stopping block {self.name}.")


# =================================================
#        send, recv


    def send(self, msg, outport: str):
        """Send msg on outport. Put msg on the queue associated with outport."""
        if outport not in self.outports or outport not in self.out_q:
            raise ValueError(
                f"{outport} of agent {self.name} is not an output port.")
        if self.out_q[outport] is None:
            raise ValueError(
                f"The outport, {outport}, of agent {self.name} is not connected to an input port."
            )
        self.out_q[outport].put(msg)

    def recv(self, inport: str) -> Any:
        """Receive a message from an input port.
        Get message from the queue associated with inport."""
        if inport not in self.inports or inport not in self.in_q:
            raise ValueError(
                f"[{self.name}] Input port: {inport} of agent {self.name}  not in inports."
            )
        if self.in_q[inport] is None:
            raise ValueError(
                f"[{self.name}] Input port '{inport}' of agent {self.name}  is not connected."
            )
        return self.in_q[inport].get()

    def recv_if_waiting_msg(self, inport: str) -> Any:
        """
        Returns the message if there is a message at inport.
        Returns None if there is no message at inport
        """
        if inport not in self.in_q:
            raise ValueError(f"[{self.name}] Input port '{inport}' not found.")
        q = self.in_q[inport]
        if q.empty():
            return None
        else:
            return q.get()

    def recv_from_any_port(self, list_of_inports: List[str]) -> Tuple[Any, str]:
        """
        Scans the given list of inports and returns the first available (msg, port).
        If no message is waiting on any port, returns (None, "No msg in inports").
        """
        # rotate_list ensures fairness in asynchronous merge of messages
        # from multiple inports. rotate_list ensures that the inport at the head of
        # a list doesn't get preferential treatment.
        if not self.inport_most_recent_msg:
            self.inport_most_recent_msg = list_of_inports[0]
        rotated_list = list_of_inports
        if self.inport_most_recent_msg not in rotated_list:
            raise ValueError(f"{self.inport_most_recent_msg} not in list.")
        i = rotated_list.index(self.inport_most_recent_msg)
        rotated_list = rotated_list[i+1:] + rotated_list[:i+1]
        for inport in list_of_inports:
            msg_or_none = self.recv_if_waiting_msg(inport)
            if msg_or_none is not None:
                self.inport_recently_received = inport
                return (msg_or_none, inport)
            else:
                return (None, "No msg in inports")

    def wait_for_any_port(self, list_of_inports: List[str] = None, sleep_time=0.01) -> Tuple[Any, str]:
        if list_of_inports is None:
            list_of_inports = self.inports
        while True:
            msg, port = self.recv_from_any_port(list_of_inports)
            if msg:
                return msg, port
            else:
                time.sleep(sleep_time)

# =================================================
#                  SimpleAgent                    |
# =================================================


class SimpleAgent(Agent, ABC):
    """
Name: SimpleAgent

Summary:
Simplified agent class where user defines init_fn and handle_msg functions
instead of a run function. Executes init_fn and then receives and handles
messages from its only inport.

Parameters:
- name: Optional name.
- outports: List of output ports.
- init_fn: Optional initialization function.
- handle_msg: Optional function to apply to each incoming message.

Behavior:
- May have 0 or 1 inports and an arbitrary number of outports.
- Executes `init_fn(self)` once at the start.
- If it has an inport then it repeatedly receives messages from its only inport.
- Applies `handle_msg(self, msg)`.
- Sends results using self.send().
- Automatically stops on receiving "__STOP__".
- run(self_) is defined dynamically in __init__. We use 'self_' inside the closure
  to avoid confusion with the outer class-level 'self'.
- We adopt the convention that the single input port is called 'in'. Name can be overridden,

Use Cases:
- A block with no inports or outports. This is a Python object that is runnable.
- A block with 1 inport and no outports. Used in recording messages that arrive at the inport.
- A block with no inports and 1 or more outports. Used to generate messages.
- A block with 1 inport and 1 or more outports. Used to transform messages.


Tags: agent, single inport, handle one message at a time
    """

    def __init__(
        self,
        name: Optional[str] = None,
        # Simple agent has at most one inport
        inport: Optional[str] = None,
        outports: Optional[List[str]] = None,
    ):
        # Call Agent constructor
        super().__init__(
            name=name or "SimpleAgent",
            inports=[inport] if inport else [],
            outports=outports,
        )
        self.inport = inport

    @abstractmethod
    def handle_msg(self) -> None:
        """
        A subclass must implement handle_msg()
        """
        raise NotImplementedError

    def run(self):
        while True:
            msg = self.recv(self.inport)
            if msg == STOP:
                self.stop()
                return
            else:
                self.handle_msg(msg)


# =================================================
#                  Network                        |
# =================================================
class Network():
    """
Name: Network

Summary:
A container for a group of interconnected blocks. Specifies
connections between ports

Parameters:
- name: Optional[str]          -- inherited from class Block
- inports: list of str         -- inherited from class Block
- outports: list of str        -- inherited from class Block
- blocks is a dict:  block_name   --->  block
    where block is a component of the network, and block is an instance of Block.
- connections is a list of 4-tuples where the elements are strings.
    A connect is one of the following:
        (a) [from_block, from_port, to_block, to_port]
        Connect from_port of from_block to to_port of to_block.
        (b) ['external', from_port, to_block, to_port]
        Connect from_port of the network to to_port of to_block.
        (c) [from_block, from_port, 'external', to_port]
        Connect from_port of from_block to to_port of the network.

Behavior:
- Connects ports of components and connects its own (externally visible)
 ports to ports of its components.

Use Cases:
- Encapsulation and information-hiding
- Creating reusable distributed applications.

Example:
>>> net = Network(
>>>     blocks={"source": Generator(), "sink": Logger()},
>>>     connections=[("source", "out", "sink", "in")]
>>> )

Tags: network, orchestration, encapsulation, information-hiding,
plug-and-play, composition
    """

    def __init__(
        self,
        *,
        name: str = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
        blocks: dict[str, Agent | Network] | None = None,
        connections: List[Connection] = None,
    ) -> None:
        self.inports = inports
        self.outports = outports
        self.blocks = blocks or {}
        self.connections = connections or []

        for block_name, block_object in self.blocks.items():
            block_object.name = block_name

        self.check()

        self.compiled_blocks = {}
        self.compiled_connections = []

    # ------------------------------------------------------------------------
    def check(self):
        """
        Validates that:
        - block and port names are valid.
        - An externally visible inport of the network is connected to exactly one 
            inport of a component block.
        - An externally visible outport of the network is connected to exactly one 
            outport of a component block.
        - Each outport of a component block is connected exactly once.
            An outport of a component block is connected to exactly one inport of a 
            component block or to one externally visible outport of the network.
        - Each inport of a component block can be connected an arbitrary number of times.
            An inport of a component block can be fed from multiple externally visible 
            inports of the network and from multiple outports of component blocks.

        """

        # Step 1. Validate block structure
        for block_name, block_object in self.blocks.items():
            if not (isinstance(block_object, Agent) or isinstance(block_object, Network)):
                raise TypeError(
                    f"Block {block_name} must be Agent or a Network."
                )

            if not isinstance(block_name, str):
                raise TypeError(f"Block name '{block_name}' must be a string.")

            if '.' in block_name:
                raise ValueError(
                    f"Block name '{block_name}' may not contain dots ('.') due to internal pathing logic.")

            if "external" == block_name:
                raise ValueError(
                    " *external* is a reserved keyword but is used as a block name in {block_name}."
                )

            if not isinstance(block_object.inports, list):
                raise TypeError(
                    f"inports of block {block_name} must be a list.")

            if not isinstance(block_object.outports, list):
                raise TypeError(
                    f"outports  of block {block_name} must be a list.")

            if len(set(block_object.inports)) != len(block_object.inports):
                raise ValueError(
                    f"Duplicate inport names in block '{block_name}'.")

            if len(set(block_object.outports)) != len(block_object.outports):
                raise ValueError(
                    f"Duplicate outport names in block '{block_name}'.")

            for inport in block_object.inports:
                if not isinstance(inport, str):
                    raise TypeError(
                        f"Inport '{inport}' in block '{block_name}' must be a string.")
                matches = [con for con in self.connections if
                           con[2] == block_name and con[3] == inport]
                if not matches:
                    raise TypeError(
                        f"Inport '{inport}' in block '{block_name}' is not connected.")

            for outport in block_object.outports:
                if not isinstance(outport, str):
                    raise TypeError(
                        f"Outport '{outport}' in block '{block_name}' must be a string.")
                matches = [con for con in self.connections if
                           con[0] == block_name and con[1] == outport]
                if not matches:
                    raise TypeError(
                        f"Outport '{outport}' in block '{block_name}' is not connected.")
                if len(matches) > 1:
                    raise ValueError(
                        f"Outport '{outport}' in block '{block_name}' is connected more than once."
                    )

    # -----------------------------------------------------------------------------

    def compile(self, parameters=None):
        """
        Compile the network into runnable blocks and executable connections.
        This block (self) is treated as the root of a block tree.

        Steps:
        1. Return dict `agents`: full-path-name → runnable block
        2. Assign all runnable block parameter values
        3. Return list `graph_connections`: (from_block, from_port, to_block, to_port)
        """

        class PathNode:
            def __init__(self, block: Union[Agent, Network], full_path_name: str):
                self.block = block
                self.full_path_name = full_path_name

        assert isinstance(self, Network), "root must be a Network"

        self.agents = {}
        self.graph_connections = []
        self.queues = []
        self.threads = []
        self.unresolved_connections = []
        self.parameters = parameters or {}
        self.root_path_node = PathNode(self, "root")
        # list of networks or agents: Used in wiring
        self.unresolved_agents = deque([self.root_path_node])
        self.check()

        # ---------------------------------------------------------
        # STEP 1: Get agents and connections from unresolved_agents
        # ----------------------------------------------------------
        while self.unresolved_agents:
            path_node = self.unresolved_agents.popleft()
            # this_block is a network or an agent
            this_block = path_node.block
            this_full_name = path_node.full_path_name

            if isinstance(this_block, Agent):
                # Add the agent, with its full path name from root to self.agents.
                self.agents[this_full_name] = this_block
                continue

            if not isinstance(this_block, Network):
                raise TypeError(
                    f"Block {this_block.name} must be an Agent or a Network.")

            # this_block is a Network
            for child_block in this_block.blocks.values():
                child_full_path = f"{this_full_name}.{child_block.name}" if this_full_name else child_block.name
                self.unresolved_agents.append(
                    PathNode(child_block, child_full_path))

            for from_blk, from_p, to_blk, to_p in path_node.block.connections:
                from_path = f"{this_full_name}.{from_blk}" if from_blk != "external" else this_full_name
                to_path = f"{this_full_name}.{to_blk}" if to_blk != "external" else this_full_name
                self.unresolved_connections.append(
                    (from_path, from_p, to_path, to_p))

        # Merge connections until fixpoint
        changed = True
        while changed:
            changed = False
            for conn in self.unresolved_connections[:]:
                from_b, from_p, to_b, to_p = conn
                # check for match connection for any diff_block, diff_port
                # (to_b, to_p, to_diff_block, to_diff_port)
                match = next((v for v in self.unresolved_connections if
                              v[0] == to_b and v[1] == to_p), None)
                if match:
                    # replace (from_b.from_p) -> (to_b, to_p) -> (to_diff_block, to_diff_port)
                    # by (from_b.from_p) -> (to_diff_block, to_diff_port)
                    # remove (from_b, from_p, to_b, to_p)
                    # remove (to_b, to_p, to_diff_block, to_diff_port)
                    # add (from_b, from_p, to_diff_block, to_diff_port)
                    new_conn = (from_b, from_p, match[2], match[3])
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True

                match = next((v for v in self.unresolved_connections if
                              v[2] == from_b and v[3] == from_p), None)
                if match:
                    # replace (from_diff_b.from_diff_p) -> (from_b, from_p) -> (to_b, to_p)
                    # by (from_diff_b.from_diff_p) -> (to_b, to_p)
                    new_conn = (match[0], match[1], to_b, to_p)
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True

        # graph_connections are connections between agents
        for conn in self.unresolved_connections[:]:
            from_b, _, to_b, _ = conn
            if from_b in self.agents and to_b in self.agents.keys():
                self.unresolved_connections.remove(conn)
                self.graph_connections.append(conn)

        # If there are unresolved connections then there is a
        # connection from or to an external port of a network that is
        # not connected.
        if self.unresolved_connections:
            print(
                f"WARNING: external unconnected ports. {self.unresolved_connections} ")

        # ----------------------------------------
        # STEP 3: Wire queues and make threads
        # ---------------------------------------
        self.queues = []

        # Each inport of each agent has a queue.
        for agent_name, agent_object in self.agents.items():
            if not agent_object.inports:
                continue
            for inport in agent_object.inports:
                agent_object.in_q[inport] = SimpleQueue()

        # Each outport of each agent has a queue which is
        # the same as the queue of the inport to which it
        # is connected.
        for conn in self.graph_connections:
            from_b, from_p, receiver_block_name, receiver_port = conn
            receiver_block_object = self.agents[receiver_block_name]
            # Find all connections to (receiver_block, receiver_port)
            conns = [v for v in self.graph_connections if
                     v[2] == receiver_block_name and v[3] == receiver_port]
            for conn in conns:
                sender_block_name, sender_port = conn[0], conn[1]
                sender_block_object = self.agents[sender_block_name]
                sender_block_object.out_q[sender_port] = receiver_block_object.in_q[receiver_port]

        for name, block in self.agents.items():
            t = Thread(target=block.run, name=f"{name}_thread", daemon=False)
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

    def run(self):
        """
        Run all runnable blocks concurrently using threads.
        Waits for all threads to complete before returning.
        """
        try:
            for t in self.threads:
                t.start()
            for t in self.threads:
                t.join()
        except Exception as e:
            raise RuntimeError(f"Failed to run blocks: {e}") from e

    def compile_and_run(self) -> None:
        self.compile()
        try:
            self.startup()
            self.run()
        finally:
            pass
            # Attempt shutdown, even if startup/run raised
            try:
                self.shutdown()
            except Exception as e:
                # Optionally log; avoid masking original exception if any
                if not hasattr(e, "__suppress_context__"):
                    pass
