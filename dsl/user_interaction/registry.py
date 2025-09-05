# =============================
# File: dsl/block_lib/registry.py
# =============================
"""Central registry for beginner-facing names, aliases, and port defaults.


This lets multiple tools (wizard, draft runner, CLI) share one source of truth.


- CLASS_ALIASES: historical/colloquial names → canonical class names
- CANONICAL_CLASSES: the set of classes DisSysLab actually exposes
- DEFAULT_PORTS: default in/out port names used to fill missing ports
"""
from __future__ import annotations


# Historical / colloquial → canonical
CLASS_ALIASES = {
    # Transformers
    "FunctionToBlock": "TransformerFunction",
    "WrapFunction": "TransformerFunction",
    # GPT prompt-based (adjust to your canonical)
    "PromptToBlock": "GPTTransformer",
    # Recorders
    "StreamToList": "RecordToList",
    "StreamToFile": "RecordToFile",
}


# Canonical classes available in the block library (non-exhaustive; extend as needed)
CANONICAL_CLASSES = {
    "StreamGenerator",
    "TransformerFunction",
    "RecordToList",
    "RecordToFile",
    # Fan-out / Fan-in
    "Broadcast",  # fan-out
    "MergeSynch",  # fan-in (sync)
    "MergeAsynch",  # fan-in (async)
    # GPT-based transformers (optional)
    "GPTTransformer",
}


# Default ports per class. Used when the user omits port names in connections.
DEFAULT_PORTS = {
    # Single producer
    "StreamGenerator": {"in": [], "out": ["out"]},
    # 1→1 transforms
    "TransformerFunction": {"in": ["in"], "out": ["out"]},
    # Recorders (sink)
    "RecordToList": {"in": ["in"], "out": []},
    "RecordToFile": {"in": ["in"], "out": []},
    # Fan-out (one input, many outputs)
    "Broadcast": {"in": ["in"], "out": ["out0", "out1"]},
    # Fan-in (many inputs, one output)
    "MergeSynch": {"in": ["in0", "in1"], "out": ["out"]},
    "MergeAsynch": {"in": ["in0", "in1"], "out": ["out"]},
    # GPT-based (treat as 1→1)
    "GPTTransformer": {"in": ["in"], "out": ["out"]},
}


def canonicalize_class(name: str) -> str:
    """
    Map an incoming class name to a canonical class name using aliases.
    """

    return CLASS_ALIASES.get(name, name)
