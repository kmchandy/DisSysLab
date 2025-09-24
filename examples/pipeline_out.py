# Auto-generated from simple_source_sink.yaml (network name = "simple_source_sink")
# Description: 
from __future__ import annotations

import importlib
from dsl.core import Network
from dsl.blocks.source import Source
from dsl.blocks.sink import Sink

def _resolve(id_str: str):
        mod_name, qual = id_str.split(":", 1)
        ALIAS = {"ops": "dsl.ops"}  # safety for any legacy 'ops:*' that slipped through
        mod_name = ALIAS.get(mod_name, mod_name)

        # Try deepest module path first: e.g., dsl.ops.sinks.lists:to_list
        parts = qual.split(".")
        module_path = mod_name + ("" if len(parts) == 1 else "." + ".".join(parts[:-1]))
        try:
            mod = importlib.import_module(module_path)
            return getattr(mod, parts[-1])
        except Exception:
            # Fallback: getattr-chain off base module (works if __init__ re-exports)
            mod = importlib.import_module(mod_name)
            obj = mod
            for part in parts:
                obj = getattr(obj, part)
            return obj

results_snk: list = []  # auto-collected sink

def build() -> Network:
    blocks = {}
    _fn_snk = _resolve('dsl.ops.sinks.lists:to_list')
    _params_snk = {}
    _params_snk['target'] = results_snk
    blocks['snk'] = Sink(fn=_fn_snk, params=_params_snk)
    _fn_src = _resolve('dsl.ops.sources.lists:from_list')
    blocks['src'] = Source(fn=_fn_src, params={'items': ['hello', 'world']})

    connections = [
        ('src', 'out', 'snk', 'in'),
    ]

    return Network(blocks=blocks, connections=connections)

if __name__ == "__main__":
    net = build()
    net.compile_and_run()
    print(results_snk)  # output of sink 'snk'
