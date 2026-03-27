# dsl/__init__.py
"""
DisSysLab - Distributed Systems Teaching Framework

Public API exports.
"""

from dsl.core import Agent, ExceptionThread
from dsl.network import Network
from dsl.builder import network, PortReference

__all__ = [
    # Core
    'Agent',
    'ExceptionThread',

    # Network
    'Network',
    'network',

    # Builder
    'PortReference',
]

__version__ = '0.1.0'
