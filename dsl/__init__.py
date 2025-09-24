# dsl/__init__.py
from .graph import Graph
# Optional curated ops:
from dsl.ops.sources.lists import from_list
from dsl.ops.sinks.lists import to_list

__all__ = ["Graph", "from_list", "to_list"]
