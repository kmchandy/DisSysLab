# DisSysLab v2 — Next Steps (Frozen Plan)

## Big Picture (agreed/frozen)
- **Single shapes**
  - **Source**: `fn(**params) -> Iterator`
  - **Transform**: `fn(msg, **params) -> Any`
  - **Sink**: `fn(msg, **params) -> None`
- **Student API**: `generate(fn, **params)`, `transform(fn, **params)`, `record(fn, **params)`, plus `Network`, routers, and `pipeline` (via `dsl.kit`).
- **Blocks (runtime)**: `dsl/blocks/source.py`, `transform.py`, `sink.py`, `fanin.py`, `fanout.py`, `graph_structures.py`.
- **Catalog functions (authoring)** live under `dsl/ops/` and are plain functions (no closures/factories).

---

## Recommended Implementation Order
1) **core.py sanity pass**
   - Keep as one file for now. Ensure `Agent` has abstract `run()` and consistent STOP semantics. Remove `SimpleAgent`.
2) **kit layer**
   - `dsl/kit/api.py`:
     - `generate(fn, **p)` → `Source(fn=lambda: fn(**p))`
     - `transform(fn, **p)` → `Transform(fn=lambda m: fn(m, **p))`
     - `record(fn, **p)` → `Sink(fn=lambda m: fn(m, **p))`
3) **ops refactor**
   - Rename modules (see naming below). Convert all source/sink functions to **plain** shapes (no closures/factories).
4) **tests**
   - Add a tiny runner helper to avoid repetition. Start with simple source→sink, then add source→transform→sink.
5) **Tap block**
   - Implement as a Transform that returns `msg` unchanged and calls a sink-style fn as a side effect (for debugging).
6) **YAML → Network**
   - Build a small normalizer + validator; keep separate from registry at first.

---

## Naming & Structure Adjustments
- **ops layout** (drop “common_*”):
  - `dsl/ops/sources/` — `list.py` (from_list), `files.py` (from_file_lines, from_jsonl), `csv.py`, `rss.py`, `timers.py`, `rng.py`
  - `dsl/ops/transforms/` — `text.py` (uppercase), `nlp.py` (add_sentiment), `struct.py` (pick_keys, add_timestamp), `math.py` (scale, add, etc.)
  - `dsl/ops/sinks/` — `collections.py` (to_list, to_set), `console.py` (to_console), `files.py` (to_file), `jsonl.py` (to_jsonl), `http.py` (to_webhook)
- **Package init**: each role’s `__init__.py` imports its modules so registrations run, e.g.:
  ```python
  # dsl/ops/sources/__init__.py
  from . import list, files, csv, rss, timers, rng  # noqa
  ```
- **Students** never import from `dsl.ops`; they only use `dsl.kit`.

---

## Tests (scope & style)

### tests/test_sources.py
- Pipeline: **source under test** → `to_list` sink.
- Use `generate(from_list, items=[...])` and `record(to_list, target=results)`.
- Cover: empty list, one/many items; file/jsonl read; random/timer with small counts.

### tests/test_sinks.py
- Pipeline: `from_list` → **sink under test**.
- Use `tmp_path` for file outputs; assert line-by-line for `to_file`/`to_jsonl`.

### tests/test_transforms.py
- Pipeline: `from_list` → **transform under test** → `to_list`.
- Cover: `uppercase`, `add_sentiment`, and simple struct transforms.
- Test error handling: if transform raises, stream emits STOP and terminates cleanly.

### Shared helpers
- `_run(blocks, connections)` or `_run_linear(*blocks)` to keep tests DRY.
- Assert STOP propagation (no STOP delivered to user sink; network terminates).

---

## Tap Block (debugging)
- Implement as a **Transform**:
  - Signature in runtime: `Tap(fn, **params)` where `fn(msg, **params) -> None`.
  - Behavior: call `fn(msg, **params)`; return `msg` unchanged; forward STOP.
  - Error policy: log and continue (optionally `strict=False` to avoid halting debug runs).

---

## YAML Topology (normalize early)
- **Connections**
  - **Pair form** (both ends single-port): `["src", "tr"]` ⇒ `{"from":"src","out":"out","to":"tr","in":"in"}`.
  - **Object form** (explicit): `{"from":"split","out":"left","to":"A","in":"in"}` or with indices `{"from":"split","out":1,"to":"B","in":0}`.
- **Blocks**
  - Canonical entry: `{ id, role, ref, shape? }`.
  - If `role in {source, transform, sink}` and no `shape`: assume
    - source: `in:0, out:1`, transform: `in:1, out:1`, sink: `in:1, out:0`.
  - Multi-port blocks (e.g., split/merge) **must** provide `shape`, e.g. `{ out: ["left","right"] }` or `{ out: 2 }`.
- **Validation (without registry)**
  - Name/arity checks from `shape` or defaults.
  - Accept port by **name** or **0-based index**; derive default names when indices used (`"in_{i}"`, `"out_{i}"`).

---

## Gotchas to Watch
- **Mutable defaults**: never use `{}` as a default arg.
- **Abstract base**: subclasses must define `run()` (don’t pass `run=` into `Agent.__init__`).
- **Sink shapes**: convert closure-style sinks to parameter sinks (`fn(msg, **params)`).
- **Iterator contract**: sources must return an **iterator**, not a list.
- **Error paths**: on exception in Source/Transform/Sink, print traceback and emit STOP once.

---

## Acceptance Checks (milestones)
- **ops/sources converted**: `test_sources.py` passes (list/files/jsonl at least).
- **ops/sinks converted**: `test_sinks.py` passes (console/list/file/jsonl).
- **ops/transforms baseline**: `uppercase`, `add_sentiment` pass in `test_transforms.py`.
- **Tap**: unit test confirms mirror behavior + side-effect recording.
- **kit/api**: integration test with `generate/transform/record` across all above.
- **YAML normalizer**: round-trip test YAML → Network → run on a trivial flow.

---

## Quick reference (frozen contracts)
- **generate(fn, **params)** → Source wrapping `lambda: fn(**params)`
- **transform(fn, **params)** → Transform wrapping `lambda msg: fn(msg, **params)`
- **record(fn, **params)** → Sink wrapping `lambda msg: fn(msg, **params)`
