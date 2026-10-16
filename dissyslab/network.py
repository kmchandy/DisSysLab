"""Alias: moved to :mod:`dissyslab.runtime.network`.

Kept because every generated ``build/run.py`` imports
``dissyslab.network.Network``.
"""

from dissyslab.runtime.network import Network, OfficeRunError

__all__ = ["Network", "OfficeRunError"]
