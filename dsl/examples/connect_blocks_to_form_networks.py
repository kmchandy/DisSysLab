'''
This page introduces Network.
These examples show how to build networks (instances of
Network) by connecting outports of component blocks of
the network to inports of component blocks.

The Network class inherits from the Block class, and so
a network is an instance of Block. The parameters of
Network (in addition to those in Block) are as follows.

blocks
------
    blocks is a dict with keys that are strings and values
    that are instances of Block.
    Example:
    blocks={
                  'source': sender,
                  'transform': transformer,
                  'sink': receiver,
              }
    specifies a network with 3 blocks called 'source'
    'transform' and 'sink' which are the sender, transformer,
    and receiver objects.

connections
-----------
    connections is a list of tuples where each tuple has
    4 elements: from_block, from_port, to_block, to_port
    where from_block and to_block are the names of blocks,
    and from_port is the name of an outport of the block
    called from_block, and to_port is the name of an
    inport of the block called to_block.
    Example:
    connections=[
                  ('source', 'out', 'transform', 'in'),
                  ('transform', 'out', 'sink', 'in')
              ]
    specifies two connections:
    (1) the outport called 'out' of the block
    called 'source' is connected to the inport called 'in'
    of the block called 'transform', and
    (2) the outport called 'out' of the block
    called 'transform' is connected to the inport called 'in'
    of the block called 'sink'

'''

from blocks_and_agents import sender, receiver, transformer, sum_prod
from blocks_and_agents import send_msg_sequence, sum_and_prod, print_msg
from dsl.core import Agent, Network


# =================
# EXAMPLE        |
# =================
# Example of a network with blocks sender, transformer, receiver
# imported from blocks_and_agents. See the description above.

net = Network(name="net",
              blocks={
                  'source': sender,
                  'transform': transformer,
                  'sink': receiver,
              },
              connections=[
                  ('source', 'out', 'transform', 'in'),
                  ('transform', 'out', 'sink', 'in')
              ]
              )
print(f'RUNNING EXAMPLE:  {net.name} \n')
net.run()


# ================
# EXAMPLE        |
# ================
# Example of a network with the following blocks and connections.
# Blocks (called):
# 'source_0' 'source_1', 'sum_prod_block', 'print_sum' and 'print_prod'
# Connections:
# 1. Outport 'out' of block'source_0' is connected
# to inport 'in_0' of block 'sum_prod_block'.
# 2. Outport 'out' of block 'source_1' is connected
# to inport 'in_1' of block 'sum_prod_block'.
# 3. Outport 'sum' of block 'sum_prod_block' is connected
# to inport 'in' of block 'print_sum'.
# 4. Outport 'prod' of block 'sum_prod_block' is connected
# to inport 'in' of block 'print_prod'.

sum_and_prod_network = Network(name="sum_and_prod_net",
                               blocks={
                                   'source_0': Agent(
                                       outports=['out'], run_fn=send_msg_sequence
                                   ),
                                   'source_1': Agent(
                                       outports=['out'], run_fn=send_msg_sequence
                                   ),
                                   'sum_prod_block': Agent(
                                       inports=['in_0', 'in_1'],
                                       outports=['sum', 'prod'],
                                       run_fn=sum_and_prod
                                   ),
                                   'print_sum': Agent(
                                       name='sum_printer', inports=['in'], run_fn=print_msg
                                   ),
                                   'print_prod': Agent(
                                       name='prod_printer', inports=['in'], run_fn=print_msg
                                   ),
                               },
                               connections=[
                                   ('source_0', 'out', 'sum_prod_block', 'in_0'),
                                   ('source_1', 'out', 'sum_prod_block', 'in_1'),
                                   ('sum_prod_block', 'sum', 'print_sum', 'in'),
                                   ('sum_prod_block', 'prod', 'print_prod', 'in'),
                               ]
                               )
print(f'RUNNING EXAMPLE:  {sum_and_prod_network.name} \n')
sum_and_prod_network.run()
