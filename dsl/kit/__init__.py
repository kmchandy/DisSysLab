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
import dsl.block_lib.sources.source_lib.common_sources        # noqa: F401
import dsl.block_lib.transforms.transform_lib.common_transforms  # noqa: F401
import dsl.block_lib.sinks.sink_lib.common_sinks              # noqa: F401

# 2) Adopt registrations into the catalog
catalog.adopt_from_registry_core()

# 3) Convenience view: name -> callable
FN = catalog.view_funcs()

# 4) Student API verbs
from .api import generate, transform, record  # noqa: E402

# 5) Re-export routers and core conveniences
from dsl.block_lib.routers.fanout import Broadcast, SplitBinary  # noqa: E402
from dsl.block_lib.routers.fanin import MergeSynch, MergeAsynch  # noqa: E402
from dsl.block_lib.graph_structures import pipeline              # noqa: E402
from dsl.core import Network                                     # noqa: E402

# 6) Public surface
__all__ = [
    "generate", "transform", "record",
    "FN",
    "Network", "pipeline",
    "MergeSynch", "MergeAsynch", "Broadcast", "SplitBinary",
]
