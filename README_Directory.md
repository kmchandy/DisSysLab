# 📂 DisSysLab Directory Structure

This file documents the planned layout of the DisSysLab repository.  
Each directory has its own `README.md` some with examples.

---

## Top Level
- **dsl/** – Core library of blocks, agents, and utilities.
- **chapters/** – Pedagogy-first tutorials with narrative + runnable code.
- **examples/** – Standalone example applications (buffet for exploration).
- **tests/** – Flat test suite, one file per concept/module.
- **README.md** – Main project guide (quickstart, philosophy).
- **README_Directory.md** – This document (repository map).

---

## dsl/
- **core.py** – The foundation: definitions of `Agent`, `Network`, `System`, and core message-passing logic.

### block_lib/
block library, grouped by role in a network.  

- **sources/** – Generators of messages.  
  - `source.py` – `StreamGenerator` class.  
  - `source_lib.py` – Python functions used by the ***StreamGenerator*** class to 
  generate items from (list, file, RSS, etc.).  
  - `README.md` – Explains sources and shows basic usage.  

- **transforms/** – Transformers of messages.  
  - `transform.py` – `Transformer` class.  
  - `transform_lib.py` – Python functions used by the ***Transformer*** class for common message transformations.
  - `README.md` – Explains transforms and examples.  

- **sinks/** – Recorders of messages.  
  - `sink.py` – `Sink` class 
  - `sink_lib.py` – Python functions used by the ***Sink*** class for writing to files, consoles, etc.
  - `README.md` – Explains sinks and usage.  

- **routers/** – Routing blocks (fan-in, fan-out).  
  - `fanin.py` – classes `MergeSynch`, `MergeAsynch`  for merging multiple message streams into a single stream.
  - `fanout.py` – classes `Broadcast`, `Split` for splitting a message stream into multiple output streams.
  - `README.md` – Explains routing.  

---

## chapters/
step-by-step tutorials.  
Each chapter has a `README.md` and one or more short Python examples.

- **ch01_blocks_connections/** – Basics: blocks + connections.  
- **ch02_messages_as_dicts/** – Messages with keys and values.  
- **ch03_fanin/** – Combining multiple streams.  
- **ch04_fanout/** – Splitting streams into branches.  

---

## examples/
A collection of standalone example applications for browsing and modifying 

Examples:  
- `rss_to_console.py` – Stream RSS feed headlines to console.  
- `stocks_portfolio_stream.py` – Combine two stock feeds and compute portfolio value.  
- `numpy_rows_sklearn.py` – Stream NumPy rows into a ML pipeline.  

---

## tests/
Flat layout for clarity. Each file tests one major category.

- `test_sources.py`  
- `test_source_lib.py`
- `test_transforms.py` 
- `test_transform_lib.py` 
- `test_sinks.py`
- `test_sink_lib.py`
- `test_routers_fanin.py`  
- `test_routers_fanout.py`  

Run all tests with:

```bash
pytest tests/
