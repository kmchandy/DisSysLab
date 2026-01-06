# Module 5 — Build a Distributed System with DisSysLab + AI

If you arrived here from the **top-level DisSysLab README**, this is the next step: you’ll go from “I understand a graph of agents” to “I can build and customize a working distributed app.”

You’ll learn two workflows:

- **Workflow A (recommended):** assemble a system from the **catalog**, then customize it by composing small transforms.
- **Workflow B (advanced):** use **AI** to create a new agent (source/transform/sink), test it, register it, and plug it into your network.

---

## Start here (funnel from the main README)

Before Module 5, make sure you can do these two things:

- [ ] You can import DisSysLab in Python (or run the quickstart script from the main README).
- [ ] You have run *one* small end-to-end pipeline successfully (source → transform → sink).

If either is not true, go back to the top-level README and run its **Quickstart** first.  
Module 5 assumes you already know how to run a basic pipeline.

---

## What you’ll build in this module

A tiny streaming app:
```
random_walk_source → anomaly_detector → (console summary)
                            ↘ → jsonl_recorder
```


- The **source** produces a stream of dict messages
- The **transform** adds fields (ema/std/anomaly, etc.)
- The **sinks** display and record output so you can inspect results

---

## Core idea

A DisSysLab system is a **directed graph of callables**.

Two callable “shapes” matter:

1) **Sources**: `fn(**params) -> Iterator[dict]`  
   They *yield* messages (dicts).

2) **Transforms / Sinks**: `fn(msg: dict, **params) -> dict | None`  
   - transforms return a message (dict or value promoted into dict by a wrapper, depending on your runtime)
   - sinks return `None` (or return value is ignored)

Messages are plain dicts. Keep them small, stable, and well-named.

---

# Workflow A (recommended) — Build from the catalog

This workflow is the fastest way to build useful systems without writing new code.

## A1 — Pick a source (catalog)

Example op id:
- `sources.random_walk_1d`

What it emits (typical shape):
- `t_step: int`
- `x: float`
- (optional) `source: str`, `time: float`

## A2 — Add an anomaly transform

Example op id:
- `transforms.anomaly_exponential_ema_std`

Typical output additions:
- `ema: float`
- `std: float`
- `z: float` or `score: float`
- `anomaly: bool` (or numeric score)
- (optional) prediction bands/intervals

## A3 — Customize without editing core code (composition)

Many transforms output extra fields. Prefer **composition** over editing.

Useful utility transforms (examples):
- `transforms.select_fields(keep=[...])`
- `transforms.drop_fields(drop=[...])`
- `transforms.rename_fields(map={...})`

Example goal: keep only the essentials:

- `t_step`, `x`, `ema`, `std`, `anomaly`

## A4 — Add sinks

Examples:
- `sinks.console_summary`
- `sinks.jsonl_recorder(path="anomaly_stream.jsonl")`

Console sink helps you iterate quickly. JSONL gives you a durable artifact.

## A5 — Run and inspect results

Iterate in this loop:

1. run
2. inspect console + jsonl
3. tweak params (source drift/noise, anomaly threshold/window)
4. rerun

---

## Workflow A: a complete “first run” (template)

Below is a **template** you can adapt to your repo’s current API.
The important part is the *structure*: source → transform → sinks.

```python
# module_5_demo.py (template)

from dsl.catalog.load import load_catalog
from dsl.catalog.factories import make_op  # op_id + params -> callable
# If your project uses GraphSpec + runner, import those instead.

def run():
    catalog = load_catalog()

    src = make_op("sources.random_walk_1d", {
        "n_steps": 200,
        "seed": 0,
        "sigma": 1.0,
        "dx": 0.0,
    })

    anomaly = make_op("transforms.anomaly_exponential_ema_std", {
        "alpha": 0.05,
        "k": 3.0,
        # ... any other params ...
    })

    select = make_op("transforms.select_fields", {
        "keep": ["t_step", "x", "ema", "std", "anomaly"],
    })

    console = make_op("sinks.console_summary", {
        "every": 10,
        "fields": ["t_step", "x", "anomaly"],
    })

    rec = make_op("sinks.jsonl_recorder", {
        "path": "anomaly_stream.jsonl",
    })

    # PSEUDOCODE: connect into a network/graph using your runner
    #
    # g = Graph(...)
    # run_graph(g)
    #
    # or:
    # net = Network()
    # net.connect(src, anomaly).connect(select).fanout(console, rec)
    # net.run()

if __name__ == "__main__":
    run()
```

## Workflow B (advanced) — Create a new agent with AI

Use this when the catalog does not contain the agent you need.

### B1 — Write the contract first (don’t code yet)

Decide:

- **Role:** source / transform / sink  
- **Inputs required:** which fields must exist in `msg`?  
- **Outputs produced:** which fields do you add/modify?  
- **Parameters:** names + defaults  
- **Determinism:** do you accept `seed`?

Example contract: a **2D random walk source** emits:

- `t_step: int`
- `x: float`
- `y: float`

### B2 — Ask AI for a starter implementation (prompt)

Prompt template:

> Write a Python callable (or class) named `random_walk_2d` that yields `n_steps` dict messages.  
> Each message has keys `t_step` (int), `x` (float), `y` (float).  
> The walk starts at (`base_x`, `base_y`), adds drift (`dx`, `dy`), Gaussian noise (`sigma`), optional jumps,  
> accepts `seed`, and has `sleep_time_per_step` (0 means no sleep).  
> Include a small `if __name__ == "__main__"` test that prints the first 10 messages.

Tips:

- Ask for **type hints**.
- Ask for **no external dependencies** unless necessary.
- Require **reproducibility with seed**.

### B3 — Test it alone (always)

Before plugging into a network, verify:

- It runs without the framework.
- It emits the expected keys/types.
- Values are finite (`not NaN`, `not inf`).
- It is reproducible with a fixed seed.

### B4 — Register it as a “user op” (so upgrades won’t overwrite it)

Put new ops in a user-owned location, e.g.:

- `dsl/user_ops/`
- or your module folder (anything outside the core library)

Then add:

1) **Catalog metadata entry (JSON):** describes params/defaults/examples  
2) **Factory binding (Python):** maps `op_id` → implementation

The end goal: the wizard and the runner can construct your op only from:

- `op_id`
- `params`

### B5 — Use it like any other catalog op

Now it behaves exactly like catalog-built nodes in Workflow A.

---

## Best practices (Module 5 rules of thumb)

- Prefer **composition** (`select_fields` / `drop_fields` / `rename_fields`) over editing core ops.
- Keep messages as **small dicts** with stable field names.
- Add a tiny test for each new op **before** wiring it into a network.
- Always save your **graph spec** (or the script that builds it) so runs are reproducible.
- Start with **console sinks**, then add recorders (jsonl/csv) when stable.

---

## Troubleshooting

### “KeyError: field not found”

A transform expects a field that isn’t present. Fix by:

- choosing a different upstream transform, or
- inserting `rename_fields`, or
- changing the transform’s `input_field` parameter (if it has one)

### “My output dict is huge”

Insert `select_fields` immediately after the transform that bloats the message.

### “I changed a parameter but nothing changed”

Confirm:

- you saved the file you’re running
- you’re running the correct script
- you’re not reusing an old cached artifact (if any)

---

## What’s next

After you complete Module 5, you should be able to:

- build a multi-node system from the catalog
- customize outputs purely by composing transforms
- add sinks to observe and record results
- (advanced) add a new op and register it cleanly

Next module typically focuses on one of:

- richer sinks (csv/xlsx dashboards, live viewers)
- connectors (rss/http/fs)
- “recipes” (end-to-end apps you can reuse)
