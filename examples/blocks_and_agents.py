'''
This file is a brief introduction to Block and Agent,
the classes that form the core of this distributed
computing framework.

Block
-----

A Block is an object that sends and receives messages.
A block sends messages on its output ports and receives
messages on its input ports. A block is specified by
the following parameters.

Block Instance Parameters
-------------------------
name: Optional, string
  name of the block instance
  
description: Optional, string
  Describes the role of the block in the 
  network in which the block is a component.

inports: Optional, list of string
  Example: inports = ['temperature', 'pressure'] means
  that the block can receive messages along the port called
  'temperature' and on the port called 'pressure'.

outports: Optional, list of string
  Example: outports = ['valve_control', 'alarm'] means
  that the block can send messages along the port called
  'valve_control' and on the port called 'alarm'.

run_fn: Optional, a function
  The function that executes the block.

Agent
-----
An agent is a block with primitives send and recv.
Examples
send
----
    send(msg='turn_off', outport='valve_control')
    causes the message 'turn_off' to be sent from the port
    called 'valve_control'
recv
----
    p = recv(inport='pressure')
    causes the agent to wait for a message to arrive on the
    port called 'pressure' and the assign the arriving message
    to variable p.

You may want to the include print statements (which are comments
in the code) when you run the agents: see
connect_blocks_to_form_networks.py

'''

from dsl.core import Agent
import time

# =================
# EXAMPLE        |
# =================
# Example of an agent, sender, that sends the sequence
# of messages 1, 2, 3 and then the message "__STOP__"
# on its output port called 'out'
# This agent has no input ports. The name and
# description are not given in this example.


def send_msg_sequence(self):
    for i in range(3):
        # print(f'sending msg {i}')
        self.send(msg=i, outport='out')
        # sleep for 0.1 seconds
        time.sleep(0.1)
    self.send(msg='__STOP__', outport='out')
    # print(f'sending __STOP__')


# Create the agent
sender = Agent(outports=['out'], run_fn=send_msg_sequence)

# =================
# EXAMPLE        |
# =================
# Example of an agent, receiver, that receives messages
# on its input port called 'in' and prints the messages.
# The agent halts if it receives a message '__STOP__'.
# This agent has no output ports.


def print_msg(self):
    while True:
        msg = self.recv(inport='in')
        if msg == "__STOP__":
            break
        print(f'Agent {self.name} received message {msg} \n')


receiver = Agent(name='receiver', inports=['in'], run_fn=print_msg)

# =================
# EXAMPLE        |
# =================
# Example of an agent, transformer, with an input port 'in'
# and an output port 'out'. The agent receives a message
# msg on its input port and sends 2* on its
# output port where h is a given function. The agent
# stops executing when it receives a message '__STOP__'


def double(self):
    while True:
        msg = self.recv(inport='in')
        # print(f'received {msg} in transformer')
        if msg == "__STOP__":
            self.send(msg='__STOP__', outport='out')
            break
        self.send(msg=2*msg, outport='out')


transformer = Agent(inports=['in'], outports=['out'], run_fn=double)

# =================
# EXAMPLE        |
# =================
# Example of an agent, sum_prod with two input ports
# 'in_0', and 'in_1' and two output ports 'sum' and 'prod'.
# The agent gets a message on 'in_0' and then on 'in_1', and
# sends the sum of the message on outport 'sum' and the
# product of the messages on outport 'prod'
# The agent halts if it receives a message '__STOP__' and
# sends the message on each of its output ports.


def sum_and_prod(self):
    while True:
        msg_0 = self.recv(inport='in_0')
        # print(f'received {msg_0} from msg_0')
        if msg_0 == "__STOP__":
            for outport in self.outports:
                self.send(msg='__STOP__', outport=outport)
            break
        else:
            msg_1 = self.recv(inport='in_1')
            # print(f'received {msg_1} from msg_1')
            if msg_1 == "__STOP__":
                for outport in self.outports:
                    self.send(msg='__STOP__', outport=outport)
                break
            else:
                # print(f'sending {msg_0 + msg_1} on outport sum')
                self.send(msg=msg_0 + msg_1, outport='sum')
                # print(f'sending {msg_0 * msg_1} on outport prod')
                self.send(msg=msg_0 * msg_1, outport='prod')


sum_prod = Agent(
    inports=['in_0', 'in_1'],
    outports=['sum', 'prod'],
    run_fn=sum_and_prod)
