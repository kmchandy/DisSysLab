# 📂 ToDo Version 2

- **Check core.py**. If necessary split into core/agent.py, core/network.py, core/utils.py. Remove SimpleAgent. Keep core very simple and robust.
- **dsl/blocks/source.py** (which contains **Source**) is unchanged.
- change **dsl/ops/sources/common_sources** to **list.py** which contains **from_list**, and **files.py** which contains **from_file_lines**, **from_jsonl** and change functions to return simple functions and not wrapped functions.
- **dsl/blocks/sink.py** (which contains **Sink**) is unchanged.
- change **dsl/ops/sinks/common_sinks** in the same way the change of **ops/sources/**
- **tests/test_sources** run tests with pipelines where each pipeline has 2 blocks, source and sink where the sink is **to_list** and the source is tested.
- **tests/test_sinks** run tests with pipelines where each pipeline has 2 blocks, source and sink where the source is **from_list** and the sink is tested.
- **dsl/blocks/transform.py** (which contains **Transform**) is unchanged.
- change **dsl/ops/sinks/common_transforms** in the same way the change of **ops/sources/**
- **tests/test_transforms** run tests with pipelines where each pipeline has 3 blocks -- source, transform, and sink -- where the source is **from_list**, the sink is **to_list** and the transform is tested.
- **Make a tap** a block with a single inport, a single outport, that sends inputs to outputs without change, and copies messages to a file or list just like sinks. Used for debugging.
  ## User interaction
  - Create function that takes a YAML specification of a network and creates a Python network
```
blocks:
- id: b0, in = ['rss', 'x'], out = ['left', 'right']
- id: b1, in = 2, out = ['sentiment']

- network: from bo, out: 'left', to 'b1' , in: 0

  - { id: split, role: transform, ref: split_ref, shape: { out: ["left","right"] } }
- { id: split, role: transform, ref: split_ref, shape: { out: 2 } }
```
**Connections**
Pair (defaults; only if both ends are single-port):
["src", "tr"] ⇒ ["src","out","tr","in"]

Object (explicit, accepts name or 0-based index):
{ from: "split", out: "left", to: "A", in: "in" }
{ from: "split", out: 1, to: "B", in: 0 }