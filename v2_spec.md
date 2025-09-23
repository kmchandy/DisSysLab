# DisSysLab v2 — Frozen Specification (`spec_v2.md`)

_Last updated: 2025-09-23_

---

## 0) Purpose

DisSysLab v2 is a minimal, teachable framework for building distributed applications.

- **Students**: author **one YAML file per network** and run it with **one command**.
- **Programmers**: implement lean Python blocks (Source / Transform / Sink + Merge / Broadcast).
- **No catalog**: bindings refer directly to Python via `module:qualname`.

---

## 1) UX Contract (single command)

- **One file** per network, e.g. `pipeline.yaml`.
- **Run**:

## dsl run pipeline.yaml


- The runner: **validates** → prints **autofix suggestions** (and applies safe, in-memory fixes) → if valid, **builds** the `Network` and **executes** it.
- If a sink is `ops:to_list` without `target`, the runner **auto-collects** to a fresh list and **prints** the result.

### Optional flags (still one verb)

- `dsl run pipeline.yaml --emit-python out.py`  
  Validate + run + **emit canonical Python** that builds the same network.
- `dsl run pipeline.yaml --no-run --emit-python out.py`  
  Validate + **emit-only** (no execution).

_No JSON emission in v2._

---

## 2) YAML: one canonical shape per network

```yaml
graph: [[src, snk]]          # list of [u, v] edges; nodes are inferred

bindings:
  src: { id: ops:from_list, params: { items: ["hello", "world"] } }
  snk: { id: ops:to_list }   # runner auto-collects & prints
```

2.1 Graph rules (pure directed graph)

Edges: list of pairs [u, v]. Whitespace trimmed, duplicates deduped.

Nodes: inferred as all endpoints of edges (no ports in YAML).

Names: strings; no dots (.); reserved name external disallowed. Cycles allowed.

Roles (inferred per node):

Source: in-degree = 0, out-degree ≥ 1

Sink: out-degree = 0, in-degree ≥ 1

Transform: in-degree ≥ 1 and out-degree ≥ 1

Auto-insertion at build time:

MergeAsynch where in-degree > 1 (weakly fair; STOP after all inputs STOP)

Broadcast where out-degree > 1 (fan-out to all)

2.2 Bindings (catalog-free)

Each node has:

```
node:
  id: "<module>:<qualname>"   # resolved via importlib; dot-walk allowed after ':'
  params: {...}               # optional; filtered to the function signature
  msg_param: "<name>"         # optional; only if the message must go into a named parameter
```

Source call: fn(**params) → must return an iterator/iterable.

Transform/Sink call (default): fn(msg, **params).

If the function expects the message in a named parameter, set msg_param.
Example (re.sub(string=...)):

tr: { id: re:sub, msg_param: "string", params: { pattern: "A", repl: "X" } }


Parameter handling: unknown keys are ignored with a warning (via filter_kwargs).

2.3 Examples

Simplest (Source → Sink)

```
graph: [[src, snk]]
bindings:
  src: { id: ops:from_list, params: { items: ["hello", "world"] } }
  snk: { id: ops:to_list }
```

### Uppercase pipeline

```
graph: [[src, tr], [tr, snk]]
bindings:
  src: { id: ops:from_list, params: { items: ["a", "b"] } }
  tr:  { id: builtins:str.upper }
  snk: { id: ops:to_list }
```

### Regex replace

```
graph: [[src, tr], [tr, snk]]
bindings:
  src: { id: ops:from_list, params: { items: ["A", "BA", "CAB"] } }
  tr:  { id: re:sub, msg_param: "string", params: { pattern: "A", repl: "X" } }
  snk: { id: ops:to_list }
```

3) Runner behavior (dsl run pipeline.yaml)

Load & normalize graph

Trim + dedupe edges; verify names; infer nodes; compute roles.

Plan MergeAsynch insertions (multi-in) and Broadcast insertions (multi-out).

Resolve bindings

Import module with importlib, dot-walk qualname, verify callability.

Apply msg_param (if provided).

filter_kwargs to function signature; warn about stray params.

Build Network

Construct Source / Transform / Sink for user nodes.

Insert MergeAsynch and Broadcast blocks where required.

Enforce one-to-one queue connections (multi-in/out mediated only by explicit blocks).

Execute

compile_and_run() (thread per agent).

If any sink is ops:to_list with no target, the runner auto-creates a list and prints results.

Autofix policy

Safe normalizations are applied in-memory (dedupe edges, trim whitespace, drop stray params).

Non-fixable issues: show clear errors and a suggested corrected YAML preview; do not run.

4) Python runtime — frozen contracts
4.1 Core

Agent (abstract)

inports, outports: lists of strings.

in_q, out_q: dicts of queues (wired by Network).

Lifecycle: startup(), run() (abstract), shutdown(), stop() (sends STOP on all outports).

Messaging: send(msg, outport), recv(inport).

Network

Contains named blocks (Agents / Networks) + connections (from_block, from_port, to_block, to_port).

Validates: unique port names; each outport connected exactly once; each inport connected exactly once (base layer).
Multi-in/out is achieved via MergeAsynch / Broadcast.

Compiles nested networks to agent-level graph, wires queues, spawns one thread per agent.

4.2 Blocks (single-shape API)

Source(fn, params?)

Accepts: callable, iterator, or iterable. Normalization:

If callable: used as a factory; called with **params.

If iterator: consumed once (warn on reuse); treated as a factory returning the same iterator.

If iterable: wrapped as iter(iterable).

Emits each non-None item to "out", then STOP.

Forbids user-yielded STOP (warn + terminate stream).

Transform(fn, params?)

Contract: fn(msg, **params) -> Any.

None = drop (do not emit).

Forwards STOP when input closes.

Sink(fn, params?)

Contract: fn(msg, **params) -> Any.

Ignores None messages; consumes STOP; emits nothing.

4.3 Fan-in / Fan-out

MergeAsynch

Weakly fair merge of multiple inputs.

Emits a single STOP after all inputs STOP.

Broadcast

For each input message, sends to all outputs.

On input STOP, forwards STOP to all outputs.

4.4 Sentinels & Queues

STOP: "__STOP__" — end-of-stream sentinel (internal only; never authored by students).

None = drop across Source / Transform / Sink.

Queues: unbounded (queue.SimpleQueue). Docs warn about backpressure / throttling.

5) Student-facing ops shim (curated IDs)

To keep bindings tidy, ship a tiny ops package that re-exports common functions:

ops:from_list (source)

ops:to_list (sink)

Internally these point at your real implementations (e.g., dsl.ops.sources.lists:from_list). Students only see ops:*.

6) Non-goals / deferred (post-v2)

Backpressure / bounded queues.

Advanced routers (hash/range/conditional split), windowing, timers beyond simple sources.

Multi-file registries/manifests; decorators; hot-reload.

Wizard UI (CLI only in v2).

JSON emission (may add later if needed internally).

7) Appendix

Reserved names: node name must not be "external"; must not contain ".".

Deterministic naming for inserted blocks:

Merge: merge_<node>_<idx>

Broadcast: bcast_<node>_<idx>

Error messaging: every fatal error includes a “Suggested corrected YAML” preview.

8) Quick Start (copy/paste)

pipeline.yaml

```
graph: [[src, snk]]
bindings:
  src: { id: ops:from_list, params: { items: ["hello", "world"] } }
  snk: { id: ops:to_list }
```

## Run
```
dsl run pipeline.yaml
```

### Emit Python too
```
dsl run pipeline.yaml --emit-python out.py
```