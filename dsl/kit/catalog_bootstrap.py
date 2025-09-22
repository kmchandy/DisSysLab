# dsl/kit/__init__.py
"""
DisSysLab Student Kit (v2)
--------------------------
Single import surface for:
- function registry (REGISTRY) and a simple function view (FN)
- student verbs: generate(), transform(), record()
- core Network and common router blocks
Registry is bootstrapped externally (no decorators required in ops libs).
"""

from __future__ import annotations
from typing import Callable, Dict

# Core
from dsl.core import Network  # runtime network container

# Common routers (keep only what exists in v2)
from dsl.blocks.fanin import MergeAsynch  # noqa: F401
from dsl.blocks.fanout import Broadcast   # noqa: F401

# Student API verbs
from .api import generate, transform, record  # noqa: F401

# Registry bootstrap (pure-function catalog)
from dsl.kit.utils import REGISTRY, build_registry  # noqa: F401

# Convenience: function-only view {id -> callable}
FN: Dict[str, Callable[..., object]] = {
    rid: fn for rid, (_reg, fn) in REGISTRY.items()}

__all__ = [
    "generate", "transform", "record",
    "FN",
    "REGISTRY", "build_registry",
    "Network",
    "MergeAsynch", "Broadcast",
]
