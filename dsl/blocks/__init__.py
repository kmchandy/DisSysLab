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

from dsl.blocks.source import Source
from dsl.blocks.transform import Transform
from dsl.blocks.sink import Sink
from dsl.blocks.fanout import Broadcast
from dsl.blocks.fanin import MergeAsynch
from dsl.blocks.split import Split

__all__ = [
    "Source",
    "Transform",
    "Sink",
    "Broadcast",
    "MergeAsynch",
    "Split",
]
