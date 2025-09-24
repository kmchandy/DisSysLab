# Auto-generated from pipeline.yaml (network name = "pipeline")
# Description: 
from __future__ import annotations

import importlib
from dsl.core import Network
from dsl.blocks.source import Source
from dsl.blocks.sink import Sink

def _resolve(id_str: str):
        mod_name, qual = id_str.split(":", 1)
        mod = importlib.import_module(mod_name)
        obj = mod
        for part in qual.split("."):
            obj = getattr(obj, part)
        return obj

results_snk: list = []  # auto-collected sink

def build() -> Network:
    blocks = {}
    _fn_snk = _resolve('ops:to_list')
    blocks['snk'] = Sink(fn=_fn_snk, params={'target': 'results_snk'})
    _fn_src = _resolve('ops:from_list')
    blocks['src'] = Source(fn=_fn_src, params={'items': ['hello', 'world']})

    connections = [
        ('src', 'out', 'snk', 'in'),
    ]

    return Network(blocks=blocks, connections=connections)

if __name__ == "__main__":
    net = build()
    net.compile_and_run()
    print(results_snk)  # output of sink 'snk'
