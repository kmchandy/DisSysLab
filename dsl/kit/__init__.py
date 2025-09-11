# dsl/kit/__init__.py
"""
DisSysLab Student Kit
---------------------
A single import surface that re-exports the most common 
Sources (From* ...), Sinks (To* ...), Transforms (Map, Filter, etc),
Merge and Split.
"""

# Sources
from dsl.block_lib.sources.source_lib.common_classes import (
    FromList,
    FromListWithKey,
    FromListWithKeyWithTime,
    FromFile,
    FromFileWithKey,
    FromFileWithKeyWithTime,
    FromCSV,
    FromNumpyRows,
    FromRSS,
)

# Sinks
from dsl.block_lib.sinks.sink_lib.common_classes import (
    ToList,
    ToSet,
    ToFile,
    ToJSONL,
    ToConsole,
    Print,
)
# Transforms
from dsl.block_lib.transforms.transform_lib.common_classes import (
    Uppercase,
    AddSentiment,
)
# Graph Structures: pipeline
from dsl.block_lib.graph_structures import pipeline
# Core
from dsl.core import Network

__all__ = [
    # Sinks
    "ToList",
    "ToSet",
    "ToFile",
    "ToJSONL",
    "ToConsole",
    "Print",
    # Sources
    "FromList",
    "FromListWithKey",
    "FromListWithKeyWithTime",
    "FromFile",
    "FromFileWithKey",
    "FromFileWithKeyWithTime",
    "FromCSV",
    "FromNumpyRows",
    "FromRSS",
    # Transforms
    "Uppercase",
    "AddSentiment",
    # core
    "Network",
    # Graph Structures: pipeline
    "pipeline",
]
