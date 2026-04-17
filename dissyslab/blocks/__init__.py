# dsl/blocks/__init__.py
"""
Standard agent blocks for building distributed systems.

Available blocks:
- Source: Generate messages (no inputs)
- Transform: Process messages (one input, one output)
- Sink: Consume messages (one input, no outputs)
- Broadcast: Fanout - copy message to multiple outputs
- MergeAsynch: Fanin - merge multiple inputs into one stream
- Split: Content-based routing to multiple outputs
"""

from dissyslab.blocks.source import Source
from dissyslab.blocks.transform import Transform
from dissyslab.blocks.sink import Sink
from dissyslab.blocks.fanout import Broadcast
from dissyslab.blocks.fanin import MergeAsynch
from dissyslab.blocks.merge_synch import MergeSynch
from dissyslab.blocks.split import Split
from dissyslab.blocks.role import Role

__all__ = [
    "Source",
    "Transform",
    "Sink",
    "Broadcast",
    "MergeAsynch",
    "MergeSynch",
    "Split",
    "Role",
]
