# dsl/__init__.py
from __future__ import annotations

from .graph import network, Graph   # re-export at top level

__all__ = ["network", "Graph"]  # add "Graph" here too if you export it
