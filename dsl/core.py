"""
Module: core.py
This module contains the Block, Network, Agent and SimpleAgent classes which
form the framework for building distributed applications.
We refer to an instance of Block, Network, Agent, and SimpleAgent as block,
network, agent and simple_agent respectively.

Block and Stream
----------------
A block is specified by a list of input ports, a list of output ports, and
a function run.

A stream -- a sequence of messages -- enters a block on each of its input
ports, and a stream leaves a block on each of its output ports. The lists
of input and output ports can be empty. We refer to input ports and output
ports as inports and outports, respectively.

A block starts execution when its run function is called.

A block may have a name and a description. The block name and description can be
put into a block repository which can be searched to find blocks that fit a
specification.  We use JSON for block descriptions and repository structure.
We can use AI to help build systems by having a block search the repository to
find other blocks with which it can collaborate to build applications.


Network
-------
A network is an instance of Block. A network consists of a set of interconnected
blocks. We refer to blocks within a network as components of the network.

Ports of the network are connected to ports of components. Output ports of compnents
are connected to input ports of components. Connections between ports are specified
by a directed graph in which a block is a component.

Each block in a network has a unique name and each port of a block has a unique name.
When we refer to block 'X' and port 'p' we mean the block with name 'X' and the port
with name 'p' respectively.

connections: Connecting ports
-----------------------------------------
Ports are connected in the following way:

1. Connect inport 'p' of the network to inport 'w' of component 'X'.
        [inport 'p'of network ]   --->   [inport 'w' of component 'X']

A stream to inport 'p' of the network is the stream to inport 'w' of component 'X'.
A message sent to inport 'p' of the network is received through inport 'w' of
component 'X'.

2. Connect outport 'w' of component 'X' to outport 'p' of the network.
    [output port 'w' of component 'X']   --->    [output port 'p'of network ]

A stream from outport 'p' of the network is the stream from outport 'w' of component 'X'.
A message sent through outport 'w' of component 'X' is sent through outport 'p' of the network.

3. Connect an inport of a component to arbitrarily many inports of the network
and to arbitrarily many outports of components.
                                              ___________________________________
    [inport 'p'of network ]             --->  |                                 |
    [inport 'q' of network ]            --->  | input port 'r' of component 'Z' |
    [outport 'w' of component 'X']      --->  |                                 |
    [outport 'v' of component 'Y']      --->  |_________________________________|

Multiple streams merge to form the input stream into an inport of a component.
Messages sent to inports 'p' and 'q' of the network and messages sent by component 'X'
through its outport 'w', and messages sent by component 'Y' through its outport 'v' are
received by inport 'r' of component 'Z'.

4. An outport of a component is connected exactly once. Connect outport 'w' of a
component 'X' to:
    a single outport of the network:
    [outport 'w' of component 'X']      --->     [outport 'v' of network]
    or to a single inport of a component.
    [outport 'w' of component 'X']   --->    [inport 'v' of component 'Y']
    Messages sent through outport 'w' of component 'X' are received by component 'Y'
    along inport 'v'.

A network executes its run function by executing run functions on all its component
blocks.



Agent
-----
Agent inherits from Block and has two additional functions.
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
SimpleAgent inherits from Agent. A simple_agent is specified by two functions
init_fn and handle_msg. A simple_agent has a single input queue. You do
not specify the run function of a simple agent. The run function consists of
executing init_fn followed by execution of a loop which waits for messages on
its single input port and then calls handle_msg to process the message. The
loop terminates when a '__STOP__' message is received.

Summary:
Defines the foundational classes for the DisSysLab message-passing framework.
These include Block, Agent, SimpleAgent, and Network. These abstractions form
the foundation of this framework for creating distributed applications.

Tags: core, block, agent, network, message-passing, framework
"""

from __future__ import annotations
from multiprocessing import SimpleQueue
from threading import Thread
from typing import Optional, List, Callable, Dict, Tuple, Any
import inspect


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
A Block has named input and output ports and a run function that
controls how it processes messages.

Parameters:
- name: Optional name for the block.
- description: Optional human-readable description.
- inports: List of input port names.
- outports: List of output port names.
- run_fn: Function to execute when the block is run.

Behavior:
- A block (Block instance) can be executed by calling run()
- A block receives messages on its input ports and sends
    messages on its output ports

Use Cases:
- Abstract superclass for all functional blocks in the system.

Example:
(Not used directly — see subclasses like Agent or SimpleAgent)

Tags: block, base class, ports
    """


class Block:
    def __init__(
        self,
        name: Optional[str],
        description: Optional[str],
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
        run_fn: Optional[Callable[[Agent], None]] = None,
    ):
        # Set name and description for this block
        self.name = name or self.__class__.__name__
        self.description = description or "No description provided."

        # Initialize input and output port lists
        self.inports = inports or []
        self.outports = outports or []

        # Set run_fn the function that executes this block
        # The run_fn is specified in Agent or Network subclasses
        # of block
        self.run_fn = run_fn

        # Check for duplicate port names
        if len(set(self.inports)) != len(self.inports):
            raise ValueError(f"Duplicate inport names in block '{self.name}'.")
        if len(set(self.outports)) != len(self.outports):
            raise ValueError(
                f"Duplicate outport names in block '{self.name}'.")

        # Check that port names are strings
        for inport in self.inports:
            if not isinstance(inport, str):
                raise TypeError(
                    f"Inport '{inport}' in block '{self.name}' must be a string."
                )
        for outport in self.outports:
            if not isinstance(outport, str):
                raise TypeError(
                    f"Outport '{outport}' in block '{self.name}' must be a string."
                )

        # self.in_q[inport] is a SimpleQueue
        self.in_q: Dict[str, SimpleQueue] = {
            inport: SimpleQueue() for inport in self.inports
        }
        # self.in_q[outport] is initially None. It will become a SimpleQueue
        # when this outport is connected to another port.
        self.out_q: Dict[str, Optional[SimpleQueue]] = {
            outport: None for outport in self.outports
        }
        # Ensure that the block has a  defined `run()` method.
        if not hasattr(self, "run") or not inspect.ismethod(getattr(self, "run")):
            raise NotImplementedError(
                f"Class {self.__class__.__name__}, see block {name} must define a `run()` method."
            )


# =================================================
#                    Agent                        |
# =================================================
class Agent(Block):
    """
Name: Agent

Summary:
An executable block with an input queue and a `send` method to emit messages
on output ports. Inherits from Block.

Parameters:
- name: Optional name.
- description: Optional description.
- inports: List of input ports (default: ["in"]).
- outports: List of output ports.
- run_fn: Function to call with `self` as input.

Behavior:
- Each Agent has a single input queue.
- When run, it calls `run(self)` and sends messages with `self.send(msg, port)`.

Use Cases:
- Custom logic in a block with access to input queue and send capability.

Tags: agent, message-passing, input queue, stream processing
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
        run_fn: Optional[Callable] = None,
    ):
        # Define inports and outports. Default to empty lists if none provided
        inports = inports or []
        outports = outports or []

        # Call Block constructor
        super().__init__(name, description, inports, outports, run_fn)

        # Each inport 'p' is associated with its own queue in_q['p']
        in_q = {inport: SimpleQueue() for inport in inports}
        # Each outport 'r' is associated with its own queue out_q['r']
        out_q = {outport: SimpleQueue() for outport in outports}

        # Set instance-specific attributes
        self.inports = inports
        self.outports = outports
        self.in_q = in_q
        self.out_q = out_q
        self._run_fn = run_fn
        # Ensure that the agent has a defined `run()` method.
        if not hasattr(self, "run") or not inspect.ismethod(getattr(self, "run")):
            raise NotImplementedError(
                f"Class {self.__class__.__name__}, see agent {name} must define a `run()` method."
            )

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

    def run(self):
        # run using the injected function, or raise error if missing
        # run is any callable function that may or may not send and recv messages.
        if self._run_fn is not None:
            return self._run_fn(self)
        raise NotImplementedError(
            f"Each Agent must override the run method or provide run_fn in the constructor."
        )


# =================================================
#                  SimpleAgent                    |
# =================================================
class SimpleAgent(Agent):
    """
Name: SimpleAgent

Summary:
Simplified agent class where user defines a handle_msg function instead of a run function.
Automatically receives and handles messages one at a time.

Parameters:
- name: Optional name.
- description: Optional description.
- inport: Name of input port (default: "in").
- outports: List of output ports.
- init_fn: Optional initialization function.
- handle_msg: Optional function to apply to each incoming message.

Behavior:
- Repeatedly takes messages from the input queue.
- Applies `handle_msg(self, msg)`.
- Sends results using self.send().
- Automatically stops on receiving "__STOP__".

Use Cases:
- Building simple blocks that process one message at a time.

Tags: agent, simplified, message handler, plug-and-play
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        inport: str = None,  # Simple agent has only one inport '
        outports: Optional[List[str]] = None,
        init_fn: Optional[Callable] = None,
        handle_msg: Optional[Callable[[Any, Any], None]] = None,
    ):
        # Validate: if handling messages, must have an input port
        if handle_msg and not inport:
            raise ValueError(
                f"If 'handle_msg' of SimpleAgent is provided then 'inport' must also be provided."
            )
        # Define inports and outports
        inports = [inport] if inport else []
        outports = outports or []

        # Call Agent constructor
        super().__init__(
            name=name,
            description=description,
            inports=inports,
            outports=outports,
        )
        # Set instance-specific attributes
        self.inport = inport
        self.handle_msg = handle_msg
        self.init_fn = init_fn

        def run(agent):
            # Run the initialization function if it exists
            if self.init_fn:
                self.init_fn(agent)
            # If no handle_msg function exists then send
            # '__STOP__' on output ports and halt.
            if not self.handle_msg:
                for outport in agent.outports:
                    agent.send(msg="__STOP__", outport=outport)
                return
            # If handle_msg function exists then continue to
            # receive messages on inport until '__STOP__' is received.
            while True:
                msg = agent.recv(self.inport)
                if msg == "__STOP__":
                    for outport in agent.outports:
                        agent.send(msg="__STOP__", outport=outport)
                    break
                else:
                    self.handle_msg(agent, msg)

        self.run = run


# =================================================
#                  Network                        |
# =================================================
class Network(Block):
    """
Name: Network

Summary:
A container for a group of interconnected blocks. Responsible for wiring up
queues between blocks and running the network.

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
- run function of Network overrides the run function in Block.
       The network run function executes run on the component blocks
       of the network.

Behavior:
- Automatically wires output ports to input queues.
- Runs each block by calling its run() function.

Use Cases:
- Orchestrating communication between multiple agents.
- Creating reusable distributed applications.

Example:
>>> net = Network(
>>>     blocks={"source": Generator(), "sink": Logger()},
>>>     connections=[("source", "out", "sink", "in")]
>>> )
>>> net.run()

Tags: network, orchestration, pipeline, distributed system
    """

    def __init__(
        self,
        name: str = None,
        description: str = None,
        inports: Optional[List[str]] = None,
        outports: Optional[List[str]] = None,
        blocks: Dict[str, Block] = None,
        connections: List[Tuple[str, str, str, str]] = None,
    ):
        # Initialize as a Block
        super().__init__(
            name=name, description=description, inports=inports, outports=outports
        )

        # Store the network's internal blocks and connection graph.
        # A network's blocks and connections can be passed in as parameters or
        # they can be edited and modified before executing check() and run().
        self.blocks = blocks or {}
        self.connections = connections or []

        # Create queues for the network-level, i.e. externally visible, inports.
        # For inport in self.inports,  self.in_q[inport] is a queue.
        # Messages sent to inport are put on the queue self.in_q[inport].
        # Initially, self.in_q is empty. (key, value) pairs are added to self.in_q
        # when network-level inports are connected to inports of component blocks.
        self.in_q = {}
        # Create queues for the network-level, i.e. externally visible, outports.
        # Similar to self.in_q
        self.out_q = {}
        # Connect blocks of the network. Connections are made recursively.
        # Connections within a block of the network are made before
        # connections across blocks of the network.
        self.connect()
        # Check that connections are well formed.
        self.check()

    def check(self):
        """
        Validates that:
        - All referenced block and port names are valid.
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

        # 1. Make sure that there is no block called 'external'
        if "external" in self.blocks:
            raise ValueError(
                " *external* is a reserved keyword but is used as a block name in {self.name}."
            )

        # 2. Check connections
        for connect in self.connections:
            # Check connections from network input ports
            if connect[0] == "external":
                if connect[1] not in self.inports:
                    raise ValueError(
                        f" The network '{self.name}' has no inport called {connect[1]}."
                    )
                if connect[2] not in self.blocks.keys():
                    raise ValueError(
                        f""" The network {self.name} inport {connect[1]} is connected to block {connect[2]} 
                        which is not one of the declared blocks of the network."""
                    )
                if connect[3] not in self.inports:
                    raise ValueError(
                        f""" The network {self.name} input port {connect[1]} is connected to port {connect[3]}
                        of block {connect[2]}. But {connect[3]} is not an input port of block {connect[2]}."""
                    )

            # Check connections to network output ports
            if connect[2] == "external":
                if connect[3] not in self.outports:
                    raise ValueError(
                        f""" The network {self.name} has no output port called {connect[3]}."""
                    )
                if connect[0] not in self.blocks.keys():
                    raise ValueError(
                        f""" The network {self.name} output port {connect[3]} is connected to 
                        block {connect[0]} which is not one of the declared blocks of the network."""
                    )
                if connect[1] not in self.outports:
                    raise ValueError(
                        f""" The network {self.name} output port {connect[3]} is connected to port {connect[1]} 
                        of block {connect[0]}. But {connect[1]} is not an output port of block {connect[0]}."""
                    )
            # Check internal connections
            if (connect[0] != "external") and (connect[2] != "external"):
                if connect[0] not in self.blocks.keys():
                    raise ValueError(
                        f""" The {connect} of network {self.name} is incorrect.
                        {connect[0]} is not a block of the network."""
                    )
                if connect[2] not in self.blocks.keys():
                    raise ValueError(
                        f""" The {connect} of network {self.name} is incorrect.
                        {connect[2]} is not a block of the network."""
                    )
                if connect[1] not in self.blocks[connect[0]].outports:
                    raise ValueError(
                        f""" The {connect} of network {self.name} is incorrect. {connect[1]} is not an output
                         port of block {self.blocks[connect[0]].name}."""
                    )
                if connect[3] not in self.blocks[connect[2]].inports:
                    raise ValueError(
                        f""" The {connect} of network {self.name} is incorrect.
                        {connect[3]} is not an input port of block {self.blocks[connect[2]].name}."""
                    )

        # 3. Validate network-level inports
        for inport in self.inports:
            matches = [
                e for e in self.connections if e[0] == "external" and e[1] == inport
            ]
            assert_single_connection(
                port=f"Network {self.name} inport '{inport}'", matches=matches
            )

        # 4. Validate network-level outports
        for outport in self.outports:
            matches = [
                e for e in self.connections if e[2] == "external" and e[3] == outport
            ]
            assert_single_connection(
                port=f"Network {self.name}  outport '{outport}'", matches=matches
            )

        # 5. Validate each block’s inports and outports
        for block_name, block in self.blocks.items():
            # Outports
            for outport in block.outports or []:
                to_external = [
                    e
                    for e in self.connections
                    if e[0] == block_name and e[1] == outport and e[2] == "external"
                ]
                to_internal = [
                    e
                    for e in self.connections
                    if e[0] == block_name and e[1] == outport and e[2] != "external"
                ]

                if len(to_external) == 1 and len(to_internal) == 0:
                    continue  # valid external connection
                elif len(to_internal) == 1 and len(to_external) == 0:
                    continue  # valid internal connection
                else:
                    raise ValueError(
                        f"""Outport '{outport}' of block '{block_name}' of network {self.name}
                        must be connected exactly once. It is connected to {len(to_external)}
                        outports of the network and to {len(to_internal)} inports of blocks
                        in the network. Check your connections {self.connections}
                        """
                    )

            # Inports
            for inport in block.inports or []:
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

                if len(from_external) + len(from_internal) == 0:
                    print(
                        f"""WARNING. Input port {inport} of block {block_name} of 
                          network {self.name} is not connected."""
                    )

    def connect_ports(self):
        # Connecting an outport 'p' of a component block 'x' to
        # an inport 'r' of a component block 'y' means that
        # the queue associated with outport 'p' of block 'x' becomes
        # the queue associated with inport 'r' of block 'y'.
        #
        # Ports of component blocks have been assigned to queues, and
        # now assign externally visible ports of the network to queues.
        #
        # Connecting an externally visible inport 'p' of the network
        # to an inport 'r' of component block 'y' means that the
        # queue associated with 'p' is assigned the queue associated with 'r'.
        # Connecting an outport 'p' of a component block 'x' to an
        # externally visible outport 'r' of the network means that the
        # queue associated with 'r' is assigned the queue associated with 'p'.
        for from_block, from_port, to_block, to_port in self.connections:
            try:
                if from_block == "external":
                    # Externally visible inport of the network is connected to
                    # an input port of a component block.
                    # In this case, from_port is an inport of the network.
                    # Messages sent to from_port of the network are sent to
                    # to_port of to_block.
                    # [input from_port of network ]   --->   [to_port of to_block]
                    if from_port not in self.in_q:
                        raise ValueError(
                            f"Input port '{from_port}' not in network '{self.name}'."
                        )
                    if to_port not in self.blocks[to_block].in_q:
                        raise ValueError(
                            f"Input port '{to_port}' not in block '{self.blocks[to_block].name}'."
                        )
                    if not is_queue(self.blocks[to_block].in_q[to_port]):
                        raise TypeError(
                            f"Input port {to_port} to {self.blocks[to_block].name} unconnected to queue.")
                    self.in_q[from_port] = self.blocks[to_block].in_q[to_port]
                elif to_block == "external":
                    # Connect outport of a component block to exterally visible network outport.
                    # In this case, to_port is an outport of the network.
                    # Messages sent from from_port of from_block are sent from
                    # to_port of the network.
                    # [from_port of from_block ]   --->   [output through to_port of network]
                    if to_port not in self.out_q:
                        raise ValueError(
                            f"Output port '{to_port}' not found in network '{self.name}'."
                        )
                    if from_port not in self.blocks[from_block].out_q:
                        raise ValueError(
                            f"out_port {from_port} not in block {self.blocks[from_block].name} "
                        )
                    if not is_queue(self.out_q[to_port]):
                        raise TypeError(f"Output port {to_port} of block {self.name} is not connected to a queue."
                                        )
                    self.out_q[to_port] = self.blocks[from_block].out_q[from_port]
                else:
                    # Connect from_port of from_block to to_port of to_block
                    # [from_port of from_block ]   --->   [to_port of to_block]
                    if from_port not in self.blocks[from_block].out_q:
                        raise ValueError(
                            f"out_port {from_port} not in block {self.blocks[from_block].name} "
                        )
                    if to_port not in self.blocks[to_block].in_q:
                        raise ValueError(
                            f"Input port '{to_port}' not in block '{self.blocks[to_block].name}'."
                        )
                    if not is_queue(self.blocks[to_block].in_q[to_port]):
                        raise TypeError(
                            f"{self.blocks[to_block].in_q[to_port]} of  of block {self.name} is not a queue. "
                        )
                    self.blocks[from_block].out_q[from_port] = self.blocks[to_block].in_q[to_port]
            except KeyError as e:
                raise ValueError(
                    f"Invalid block name in connection: {e}. Check connection {from_block}->{to_block}."
                )
            except Exception as e:
                raise ValueError(
                    f"Error connecting '{from_block}.{from_port}' to '{to_block}.{to_port}': {e}"
                )

    def connect(self):
        """
        Recursively connect ports of component blocks and the externally visible
        ports of the network. If a block is itself  a Network, it will call its 
        own connect() method first. Then: 
        (1) The network's externally visible inports are connected to inports of 
        its component blocks. 
        (2) The network's externally visible outports are connected to outports of 
        its component blocks.
        (3) Outports of the network's component blocks are connected to inports
        of the network's component blocks.

        """
        try:
            # Step 1: Recursively connect component blocks that are
            # themselves networks.
            for block in self.blocks.values():
                if isinstance(block, Network):
                    block.connect()

            # Step 2: Connect this network's components to each other
            # and to this networks externally visible ports.
            self.connect_ports()

        except Exception as e:
            raise RuntimeError(
                f"""Network '{self.name}' failed to connect.
    Check: misspelled or missing port or block name
    Error:
        {type(e).__name__}: {e}
    """
            ) from e

    def run(self):
        """
        Executes all component blocks concurrently using threads.
        Waits for all threads to complete before returning.
        """
        # Check that connections between ports are well formed.
        self.check()

        threads = []
        try:
            for block in self.blocks.values():
                thread = Thread(
                    target=block.run, name=f"{block.name}_thread")
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()
        except Exception as e:
            raise RuntimeError(
                f"Network '{self.name}' failed during execution: {e}"
            ) from e
