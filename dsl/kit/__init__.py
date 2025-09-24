# dsl/kit/__init__.py
"""
DisSysLab Student Kit (v2)
--------------------------
Single import surface for:
- function registry view (FN)
- three verbs: generate(), transform(), record()
- core Network and common routers
"""

from __future__ import annotations


# 1) Import function modules so their @register decorators run (populate pending)
import dsl.ops.sources.lists
import dsl.ops.transforms.common_transforms
import dsl.ops.sinks.lists
from dsl.blocks.fanout import Broadcast
from dsl.blocks.fanin import MergeAsynch
from dsl.blocks.graph_structures import pipeline
from dsl.core import Network
from .kit import generate, transform, record, pipeline
from dsl.ops.sources.lists import from_list
from dsl.ops.sinks.lists import to_list

# Public surface
__all__ = [
    "generate", "transform", "record",
    "FN",
    "Network", "pipeline",
    "MergeAsynch", "Broadcast",
    "from_list", "to_list",
]
