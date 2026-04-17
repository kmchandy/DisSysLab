# components/__init__.py

"""
Components: Reusable building blocks for distributed networks.

This library provides sources, transformers, and sinks that can be
composed into distributed systems using the DSL.

Organized by type:
- sources/: Data stream origins (RSS, mocks, lists)
- transformers/: Processing nodes (AI agents, filters)
- sinks/: Output destinations (console, email, files)

Each component comes in two versions:
- Real: Production-ready (Module 9)
- Mock: Test/teaching version (Module 2)
"""

# Make subpackages easily accessible
from . import sources
from . import transformers
from . import sinks

__all__ = ['sources', 'transformers', 'sinks']
