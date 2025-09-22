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

# Catalog (function-only registry)
from . import catalog

# 1) Import function modules so their @register decorators run (populate pending)
import dsl.ops.sources.lists
import dsl.ops.transforms.common_transforms
import dsl.ops.sinks.lists
from dsl.blocks.fanout import Broadcast, SplitBinary
from dsl.blocks.fanin import MergeSynch, MergeAsynch
from dsl.blocks.graph_structures import pipeline
from dsl.core import Network
from .catalog_bootstrap import REGISTRY, build_registry

# 2) Adopt registrations into the catalog
catalog.adopt_from_registry_core()

# 3) Convenience view: name -> callable
FN = catalog.view_funcs()

# 4) Student API verbs
from .api import generate, transform, record  # noqa: E402


# 5) Public surface
__all__ = [
    "generate", "transform", "record",
    "FN",
    "Network", "pipeline",
    "MergeSynch", "MergeAsynch", "Broadcast", "SplitBinary",
    "REGISTRY", "build_registry"
]
