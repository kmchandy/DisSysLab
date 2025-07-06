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
from dsl.core import Network


# =================
# EXAMPLE        |
# =================
# Example of a network with blocks sender, transformer, receiver
# imported from blocks_and_agents.
#

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
net.run()
assert receiver.saved == [0, 2, 4]
