"""
Module: core.py
This module contains the Block, Network, Agent and SimpleAgent classes which
form the framework for building distributed applications.
We refer to an instance of Block, Network, Agent, and SimpleAgent as block,
network, agent and simple_agent respectively.


Block
-----
A block is specified by a name, an optional description, a list of input ports,
and a list of output ports. Ports are strings. So, all parameters are strings.

The block name and description are put in a block repository which can be searched
to find blocks that fit a specification.  Block descriptions and repository structure
are in JSON.

RunnableBlock
-------------
A RunnableBlock is identical to a Block except that a RunnableBlock has a
run function. A RunnableBlock B is executed by calling B.run().


Network
-------
A network is an instance of Block. A network consists of a set of blocks
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
Agent is a RunnableBlock with two additional functions: send and recv.
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
from multiprocessing import SimpleQueue
from threading import Thread
from typing import Optional, List, Callable, Dict, Tuple, Union, Any
import inspect
import time
from collections import deque
import logging

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


def find_from_block_port_in_list(L, frm_b, frm_p):
    # return connection in L where from_block, from_port = frm_b, frm_p
    for v in L:
        if v[0] == frm_b and v[1] == frm_p:
            return v
    return None


def find_to_block_port_in_list(L, to_b, to_p):
    # return connection in L where to_block, to_port = to_b, to_p
    for v in L:
        if v[2] == to_b and v[3] == to_p:
            return v
    return None


def find_in_parameter_map(L: List, child_block_name: str):
    # triple is (
    # parameter of this node,
    # name of a child,
    # name of child's parameter )
    for triple in L:
        if triple[1] == child_block_name:
            return triple
    return None


def is_queue(q):
    # Return True if q is a queue with 'put' and 'get' functions.
    return callable(getattr(q, "put", None)) and callable(getattr(q, "get", None))


# =================================================
#                    Block                        |
# =================================================

class Block:
    """
Name: Block

Summary:
Base class for all components in the message-passing framework.
A Block has named input and output ports.

Parameters:
- name: Optional name for the block.
- description: Optional description.
- inports: List of input port names.
- outports: List of output port names.

Behavior:
- Blocks are connected to form networks.

Use Cases:
- Abstract superclass for all functional blocks in the system.

Example:
(Not used directly — see subclasses like Agent or SimpleAgent)

Tags: block, base class, ports
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
    ):
        # name and description for this block are optional.
        # A block is renamed when the block is put in a network.
        self.name = name or ""
        self.description = description or ""
        self.inports = inports or []
        self.outports = outports or []
        self.validate_block_structure()

    def validate_block_structure(self):
        if self.name and not isinstance(self.name, str):
            raise TypeError(f"Block name '{self.name}' must be a string.")

        if '.' in self.name:
            raise ValueError(
                f"Block name '{self.name}' may not contain dots ('.') due to internal pathing logic.")

        if not isinstance(self.description, str):
            raise TypeError(
                f"description '{self.description}' of block {self.name} must be a string.")

        if not isinstance(self.inports, list):
            raise TypeError(
                f"inports '{self.inports}' of block {self.name} must be a string.")

        if not isinstance(self.outports, list):
            raise TypeError(
                f"outports '{self.outports}' of block {self.name} must be a string.")

        if len(set(self.inports)) != len(self.inports):
            raise ValueError(f"Duplicate inport names in block '{self.name}'.")

        if len(set(self.outports)) != len(self.outports):
            raise ValueError(
                f"Duplicate outport names in block '{self.name}'.")

        for inport in self.inports:
            if inport and not isinstance(inport, str):
                raise TypeError(
                    f"Inport '{inport}' in block '{self.name}' must be a string.")

        for outport in self.outports:
            if outport and not isinstance(outport, str):
                raise TypeError(
                    f"Outport '{outport}' in block '{self.name}' must be a string.")

    def stop(self):
        """
        Stop the block. This is a placeholder method that can be overridden by subclasses.
        """
        for outport in self.outports:
            self.send(msg="__STOP__", outport=outport)
        logging.debug(f"Stopping block {self.name}.")
        # Placeholder for any cleanup or stopping logic.
        pass


# =================================================
#           Runnable Block                        |
# =================================================

class RunnableBlock(Block):
    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
        run_fn: Optional[Callable] = None,
    ):
        super().__init__(
            name=name,
            description=description,
            inports=inports,
            outports=outports,
        )
        if not callable(run_fn):
            raise NotImplementedError(
                f"Class {self.__class__.__name__} must define a callable `run_fn`."
            )
        self.run_fn = run_fn

# =================================================
#                    Agent                        |
# =================================================


class Agent(RunnableBlock):
    """
Name: Agent

Summary:
A RunnableBlock with send and recv functions. The
run function of an agent may call send and recv.

Parameters:
- name: Optional name.
- description: Optional description.
- inports: List of input ports (default: ["in"]).
- outports: List of output ports.
- run: Function to call with `self` as input.

Behavior:
- An agent may have an arbitrary number of inports and an arbitrary number
  of outports.
- An agent is executed by calling the agent's run function which may
    call send and recv functions to send messages on the agent's outports
    and receive messages on the agent's inports, respectively.

Use Cases:
- Custom logic in a block.

Tags: agent, message-passing
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
        run: Optional[Callable] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        inports = inports or []
        outports = outports or []
        # Call RunnableBlock constructor
        super().__init__(name, description, inports, outports, run)

        # Allows parameters to be a list or a dict in which values are None.
        if parameters is None:
            parameters = {}
        elif isinstance(parameters, list):
            parameters = {k: None for k in parameters}
        self.parameters = parameters

        # Each inport 'p' is associated with its own queue in_q['p']
        in_q = {inport: SimpleQueue() for inport in inports}
        # Each outport 'r' is associated with its own queue out_q['r']
        # If outport 'p' of agent X is connected to inport 'r' of agent Y
        # then X.out_a['p'] is set to Y.in_q['r'] so messages sent on
        # outport 'p' of X are put in the queue Y.in_q['r'] and received
        # by Y from its inport 'r'.
        out_q = {outport: SimpleQueue() for outport in outports}

        # Set instance-specific attributes
        self.inports = inports
        self.outports = outports
        self.in_q = in_q
        self.out_q = out_q
        # If a run function is provided use it, otherwise wrap it as a bound method
        if run is not None:
            if inspect.ismethod(run):
                self.run = run
            else:
                self.run = lambda: run(self, **self.parameters)
        else:
            raise NotImplementedError(
                f"Agent '{name}' must define a run(agent, **kwargs) method."
            )
        if self.parameters:
            if not isinstance(self.parameters, dict):
                raise TypeError(f'parameters of agent {name} must be a dict.')
        for parameter in self.parameters:
            if not isinstance(parameter, str):
                raise TypeError(
                    f'parameter {parameter} of agent {name} must be a string.')

        # self.inport_most_recent_msg is the inport from which a message was
        # received most recently. Used only in recv_from_any_port. It is
        # used to ensure fairness -- a message sent to any inport is received eventually.
        self.inport_most_recent_msg = None

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

class SimpleAgent(Agent):
    """
Name: SimpleAgent

Summary:
Simplified agent class where user defines init_fn and handle_msg functions
instead of a run function. Executes init_fn and then receives and handles
messages from its only inport.

Parameters:
- name: Optional name.
- description: Optional description.
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
        description: Optional[str] = None,
        # Simple agent has at most one inport
        inport: Optional[str] = None,
        outports: Optional[List[str]] = None,
        init_fn: Optional[Callable] = None,
        handle_msg: Optional[Callable[[Any, Any], None]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        if handle_msg and not inport:
            raise ValueError(
                f"SimpleAgent '{name}' handles incoming messages but has no inport")
        # Allows parameters to be a list or a dict in which values are None.
        if parameters is None:
            parameters = {}
        elif isinstance(parameters, list):
            parameters = {k: None for k in parameters}
        self.parameters = parameters

        # Set instance-specific attributes
        self.name = name or ""
        self.description = description or ""
        self.inport = inport
        self.inports = [inport] if inport else []
        self.outports = outports if outports else []
        self.handle_msg = handle_msg
        self.init_fn = init_fn

        # Define run method as a closure inside __init__

        def run_method(self_, **kwargs):
            if self_.init_fn:
                self_.init_fn(self_, **self_.parameters)

            if not self_.handle_msg:
                self_.stop()
                return

            while True:
                msg = self_.recv(self_.inport)
                if msg == "__STOP__":
                    self_.stop()
                    break
                else:
                    self_.handle_msg(self_, msg, **self_.parameters)

        # Call Agent constructor
        super().__init__(
            name=self.name,
            description=self.description,
            inports=self.inports,
            outports=self.outports,
            run=run_method,
            parameters=self.parameters,
        )


# =================================================
#                  Network                        |
# =================================================
class Network(Block):
    """
Name: Network

Summary:
A container for a group of interconnected blocks. Specifies
connections between ports

Parameters:
- name: Optional[str]          -- inherited from class Block
- description: Optional[str]   -- inherited from class Block
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
        name: str = None,
        description: str = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
        blocks: Dict[str, Block] = None,
        connections: List[Connection] = None,
        parameters: Optional[Dict[str, Any]] = None,
        parameter_map: Optional[List[ParameterMapTriple]] = None,
    ) -> None:
        # Initialize as a Block
        super().__init__(
            name=name,
            description=description,
            inports=inports,
            outports=outports,
        )

        # Store the network's internal blocks and connection graph.
        self.blocks = blocks or {}
        # Assign names specified in the dict 'blocks' to the component
        # blocks of the network.
        for block_name, block in self.blocks.items():
            if not isinstance(block, Block):
                raise TypeError(
                    f"Block {block_name} must be an instance of Block or its subclass."
                )
            block.name = block_name
        # Store internal parameters
        self.connections = connections or []
        # Allows parameters to be a list or a dict in which values are None.
        if parameters is None:
            parameters = {}
        elif isinstance(parameters, list):
            parameters = {k: None for k in parameters}
        self.parameters = parameters
        self.parameter_map = parameter_map
        self.compiled_blocks = {}
        self.compiled_connections = []
        self.compiled_parameters = {}

    # ---------------------------------------------------------
    def detect_cycles(self):
        from collections import defaultdict

        graph = defaultdict(list)
        for frm, _, to, _ in self.graph_connections:
            graph[frm].append(to)

        visited = set()
        stack = set()
        has_cycle = False

        def dfs(node):
            nonlocal has_cycle
            if node in stack:
                has_cycle = True
                return
            if node in visited:
                return
            visited.add(node)
            stack.add(node)
            for neighbor in graph[node]:
                dfs(neighbor)
            stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node)

        if has_cycle:
            logging.warning(f"⚠️ Cycle detected in network '{self.name}'. "
                            "Ensure termination detection algorithm is in place.")

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

        # Helper for clear errors
        def assert_single_connection(port, matches):
            if len(matches) != 1:
                raise ValueError(
                    f"{port} must be connected exactly once, but found {len(matches)} connections in block {self.name}."
                )

        # Step 1. Make sure that there is no block called 'external'
        if "external" in self.blocks:
            raise ValueError(
                " *external* is a reserved keyword but is used as a block name in {self.name}."
            )

        # Step 2. Check connections
        for connect in self.connections:
            # Step 2.1 Check connections from external network inports.
            # Checking (from "external", in_port, to_block, to_port)
            if connect[0] == "external":
                if connect[1] not in self.inports:
                    raise ValueError(
                        f" The network '{self.name}' has no inport called {connect[1]}."
                    )
                # A connection from "external" must go to an internal component.
                if connect[2] not in self.blocks:
                    raise ValueError(
                        f""" The network {self.name} inport {connect[1]} is connected to block {connect[2]} 
                        which is not one of the declared blocks of the network."""
                    )
                # A connection from external must go to an inport of the internal component
                if connect[3] not in self.blocks[connect[2]].inports:
                    raise ValueError(
                        f""" The network {self.name} inport {connect[1]} is connected to port {connect[3]}
                        of block {connect[2]}. But {connect[3]} is not an input port of block {connect[2]}."""
                    )
            # Finished step 2.1 checking (from "external", in_port, to_block, to_port)

            # Step 2.2. Check connection (from_block, from_port, "external", external from port)
            if connect[2] == "external":
                if connect[3] not in self.outports:
                    raise ValueError(
                        f""" The network '{self.name}' has no outport called '{connect[3]}'."""
                    )
                if connect[0] not in self.blocks:
                    raise ValueError(
                        f""" The network '{self.name}' outport '{connect[3]}' is connected to 
                    block '{connect[0]}' which is not one of the declared blocks of the network."""
                    )
                if connect[1] not in self.blocks[connect[0]].outports:
                    raise ValueError(
                        f""" The network '{self.name}' outport '{connect[3]}' is connected to port '{connect[1]}' 
                    of block '{connect[0]}'. But '{connect[1]}' is not an output port of block '{connect[0]}'."""
                    )
            # Finished step 2.2 checking connection (from_block, from_port, "external", external from port)

            # Step 2.3 Check (from_block, from_port, to_block, to_port) where blocks are internal.
            if (connect[0] != "external") and (connect[2] != "external"):
                # connect[0] and connect[2] must be names of components (i.e. internal blocks)
                if connect[0] not in self.blocks:
                    raise ValueError(
                        f""" The connection '{connect}' of network '{self.name}' is incorrect.
                    '{connect[0]}' is not a block of the network."""
                    )
                if connect[2] not in self.blocks:
                    raise ValueError(
                        f""" The connection '{connect}' of network '{self.name}' is incorrect.
                    '{connect[2]}' is not a block of the network."""
                    )
                # connect[1] and connect[3] must be ports of these components
                if connect[1] not in self.blocks[connect[0]].outports:
                    raise ValueError(
                        f""" The connection '{connect}' of network '{self.name}' is incorrect. '{connect[1]}' is not an output
                        port of block '{self.blocks[connect[0]].name}'."""
                    )
                if connect[3] not in self.blocks[connect[2]].inports:
                    raise ValueError(
                        f""" The connection '{connect}' of network '{self.name}' is incorrect.
                    '{connect[3]}' is not an input port of block '{self.blocks[connect[2]].name}'
                    The inports of '{self.blocks[connect[2]].name}' are '{self.blocks[connect[2]].inports}'."""
                    )
            # Finished step 2.3
            # checking (from_block, from_port, to_block, to_port) where blocks are internal.
        # Finished step 2: Checking connections.

        # Step 3. Each network-level inport must be connected to one inport or one component block.
        for inport in self.inports:
            matches = [
                e for e in self.connections if e[0] == "external" and e[1] == inport
            ]
            assert_single_connection(
                port=f"Network {self.name} inport '{inport}'", matches=matches
            )

        # Step 4. Each network-level outport must be fed by a channel from one outport or one
        #    component block.
        for outport in self.outports:
            matches = [
                e for e in self.connections if e[2] == "external" and e[3] == outport
            ]
            assert_single_connection(
                port=f"Network {self.name}  outport '{outport}'", matches=matches
            )

        # Step 5. Validate each block’s inports and outports
        for block_name, block in self.blocks.items():
            # 5.1 Check connections from outports of blocks
            for outport in block.outports or []:
                # to_external is the list of connections from this block, outport to
                # "external"
                to_external = [
                    e
                    for e in self.connections
                    if e[0] == block_name and e[1] == outport and e[2] == "external"
                ]
                # to_internal is the list of connections from this block, outport to
                # ports of components.
                to_internal = [
                    e
                    for e in self.connections
                    if e[0] == block_name and e[1] == outport and e[2] != "external"
                ]
                # Verify that there is exactly one connection from this outport of this component.
                if len(to_external) == 1 and len(to_internal) == 0:
                    continue  # valid single external connection
                elif len(to_internal) == 1 and len(to_external) == 0:
                    continue  # valid single internal connection
                else:
                    raise ValueError(
                        f"""Outport '{outport}' of block '{block_name}' of network {self.name}
                        must be connected exactly once. It is connected to {len(to_external)}
                        outports of the network and to {len(to_internal)} inports of blocks
                        in the network. Check your connections {self.connections}
                        """
                    )
            # Finished step 5.1 checking outports of component blocks.

            for inport in block.inports or []:
                # Step 5.2 Check connections to inports of component blocks
                from_external = [
                    e
                    for e in self.connections
                    if e[0] == "external" and e[3] == inport and e[2] == block_name
                ]
                from_internal = [
                    e
                    for e in self.connections
                    if e[3] == inport and e[2] == block_name and e[0] != "external"
                ]
                # Warning of unconnected port.
                if len(from_external) + len(from_internal) == 0:
                    logging.debug(
                        f"WARNING: Inport '{inport}' of block '{block_name}' in network '{self.name}' is not connected."
                    )
                # Verify that there is exactly one connection to this inport of this component block.
                if len(from_external) == 1 and len(from_internal) == 0:
                    continue  # valid single external connection
                elif len(from_internal) == 1 and len(from_external) == 0:
                    continue  # valid single internal connection
                else:
                    raise ValueError(
                        f"Inport '{inport}' of block '{block_name}' in network '{self.name}' "
                        f"must be connected exactly once. It is connected to "
                        f"{len(from_external)} external source(s) and "
                        f"{len(from_internal)} internal source(s). "
                        f"Check your connections: {self.connections}."
                    )
            # Finished step 5.2 Check connections to inports of component blocks
        # Finished step 5.

    # -----------------------------------------------------------------------------
    def compile(self, parameters=None):
        """
        Compile the network into runnable blocks and executable connections.
        This block (self) is treated as the root of a block tree.

        Steps:
        1. Return dict `runnable_blocks`: full-path-name → runnable block
        2. Assign all runnable block parameter values
        3. Return list `graph_connections`: (from_block, from_port, to_block, to_port)
        """
        def find_from_block_port(L, frm_b, frm_p):
            return next((v for v in L if v[0] == frm_b and v[1] == frm_p), None)

        def find_to_block_port(L, to_b, to_p):
            return next((v for v in L if v[2] == to_b and v[3] == to_p), None)

        class PathNode:
            def __init__(self, block: Union[RunnableBlock, Network], full_path_name: str):
                self.block = block
                self.full_path_name = full_path_name

        assert isinstance(self, Network), "root must be a Network"

        self.runnable_blocks = {}
        self.graph_connections = []
        self.unresolved_connections = []
        self.parameters = parameters or {}
        if not self.name or self.name.strip() == '':
            self.name = "root_block"
        self.root_path_node = PathNode(self, self.name)
        logging.debug(
            f"[compile] root_path_node for {self.name}")
        self.frontier = deque([self.root_path_node])
        self.check()
        # ----------------------------
        # STEP 1: Get runnable blocks
        # ----------------------------
        while self.frontier:
            path_node = self.frontier.popleft()

            if isinstance(path_node.block, RunnableBlock):
                self.runnable_blocks[path_node.full_path_name] = path_node.block
                continue

            mappings = path_node.block.parameter_map or []
            logging.debug(
                f"[compile] parameter mappings for {path_node.full_path_name}: {mappings}")

            for child_name, child_block in path_node.block.blocks.items():
                full_path = f"{path_node.full_path_name}.{child_name}" if path_node.full_path_name else child_name
                logging.debug(
                    f"[compile] full_path {full_path}: block_name {child_name}")

                if child_block.parameters is None:
                    child_block.parameters = {}

                for map_in, map_block, map_param in mappings:
                    if map_block == child_name:
                        if map_param not in child_block.parameters:
                            raise ValueError(
                                f"Missing param '{map_param}' in '{child_name}'")
                        if map_in not in path_node.block.parameters:
                            raise ValueError(
                                f"Missing param '{map_in}' in '{path_node.block.name}'")
                        child_block.parameters[map_param] = path_node.block.parameters[map_in]

                self.frontier.append(PathNode(child_block, full_path))

        # -------------------------------
        # STEP 2: Resolve connections
        # -------------------------------
        self.frontier = deque([self.root_path_node])

        while self.frontier:
            path_node = self.frontier.popleft()

            if isinstance(path_node.block, RunnableBlock):
                continue

            for child_block in path_node.block.blocks.values():
                child_full_path = f"{path_node.full_path_name}.{child_block.name}" if path_node.full_path_name else child_block.name
                self.frontier.append(PathNode(child_block, child_full_path))

            for from_blk, from_p, to_blk, to_p in path_node.block.connections:
                from_path = f"{path_node.full_path_name}.{from_blk}" if from_blk != "external" else path_node.full_path_name
                to_path = f"{path_node.full_path_name}.{to_blk}" if to_blk != "external" else path_node.full_path_name
                self.unresolved_connections.append(
                    (from_path, from_p, to_path, to_p))

        # Merge connections until fixpoint
        changed = True
        while changed:
            changed = False
            for conn in self.unresolved_connections[:]:
                from_b, from_p, to_b, to_p = conn

                match = find_from_block_port(
                    self.unresolved_connections, to_b, to_p)
                if match:
                    new_conn = (from_b, from_p, match[2], match[3])
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True

                match = find_to_block_port(
                    self.unresolved_connections, from_b, from_p)
                if match:
                    new_conn = (match[0], match[1], to_b, to_p)
                    self.unresolved_connections.remove(conn)
                    self.unresolved_connections.remove(match)
                    self.unresolved_connections.append(new_conn)
                    changed = True

        # Finalize graph_connections
        for conn in self.unresolved_connections[:]:
            from_b, _, to_b, _ = conn
            if from_b in self.runnable_blocks and to_b in self.runnable_blocks:
                self.unresolved_connections.remove(conn)
                self.graph_connections.append(conn)

        logging.debug(
            f"[compile] runnable_blocks: {list(self.runnable_blocks.keys())}")
        logging.debug(
            f"[compile] final graph connections: {self.graph_connections}")
        logging.debug(
            f"[compile] remaining unresolved: {self.unresolved_connections}")

        # -------------------------------
        # STEP 3: Wire queues
        # -------------------------------
        for conn in self.graph_connections:
            from_b, from_p, to_b, to_p = conn
            sender = self.runnable_blocks[from_b]
            receiver = self.runnable_blocks[to_b]

            if not isinstance(sender, Agent) or not isinstance(receiver, Agent):
                raise TypeError(
                    f"Connection {conn} must be between Agent instances.")

            q = SimpleQueue()
            sender.out_q[from_p] = q
            receiver.in_q[to_p] = q

        # -------------------------------
        # STEP 3: CHECKS
        # -------------------------------
        # Check one-to-one constraint on outport -> inport
        outport_usage = {}
        inport_usage = {}

        for from_block, from_port, to_block, to_port in self.graph_connections:
            out_key = (from_block, from_port)
            in_key = (to_block, to_port)

            if out_key in outport_usage:
                raise ValueError(
                    f"Outport '{from_port}' of block '{from_block}' is connected to multiple destinations. "
                    f"Current connections: {outport_usage[out_key]} and ({to_block}, {to_port})"
                )
            if in_key in inport_usage:
                raise ValueError(
                    f"Inport '{to_port}' of block '{to_block}' is connected to multiple sources. "
                    f"Current connections: {inport_usage[in_key]} and ({from_block}, {from_port})"
                )

            outport_usage[out_key] = (to_block, to_port)
            inport_usage[in_key] = (from_block, from_port)

        # Check no unresolved connections
        assert (self.unresolved_connections == [])

        # Check that all parameters of all runnable blocks have values
        for name, block in self.runnable_blocks.items():
            for parameter in block.parameters:
                if block.parameters[parameter] is None:
                    raise ValueError(
                        f"No value for parameter {parameter} in block {name}")

    def run(self):
        """
        Run all runnable blocks concurrently using threads.
        Waits for all threads to complete before returning.
        """
        threads = []
        try:
            for name, block in self.runnable_blocks.items():
                t = Thread(target=block.run, name=f"{name}_thread")
                threads.append(t)

            for t in threads:
                t.start()
            for t in threads:
                t.join()
        except Exception as e:
            raise RuntimeError(f"Failed to run blocks: {e}") from e

    def compile_and_run(self):
        self.compile()
        self.run()
