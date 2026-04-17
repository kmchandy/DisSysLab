# dissyslab/__init__.py
"""
DisSysLab - Distributed Systems Teaching Framework

Public API exports.
"""

from dissyslab.core import Agent, ExceptionThread
from dissyslab.network import Network
from dissyslab.builder import network, PortReference

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

__version__ = '1.0.0'
