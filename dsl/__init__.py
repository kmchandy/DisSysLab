# dsl/__init__.py
"""
DisSysLab: Distributed Systems Learning Framework

A framework for teaching distributed systems concepts through building
concurrent agent networks.

Main exports:
- Agent, Network, STOP, PortReference: Core classes
- network, Graph: Network building
- source_map, transform_map, sink_map: Decorators for wrapping functions
"""

from dsl.core import Agent, Network, STOP, PortReference
from dsl.graph import network, Graph
from dsl.decorators import source_map, transform_map, sink_map

__version__ = "1.0.0"

__all__ = [
    # Core classes
    "Agent",
    "Network",
    "STOP",
    "PortReference",
    # Network building
    "network",
    "Graph",
    # Decorators
    "source_map",
    "transform_map",
    "sink_map",
]
