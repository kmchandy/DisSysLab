# dsl/ops/__init__.py
from . import sources, sinks  # expose subpackages as attributes

# Curated re-exports so short or base-qualified IDs work:
from .sources.lists import from_list
from .sinks.lists import to_list

__all__ = ["sources", "sinks", "from_list", "to_list"]
