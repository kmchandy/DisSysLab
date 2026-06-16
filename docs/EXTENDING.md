# Extending DisSysLab

This guide answers the question *"where do my changes go?"* —
local to my office, or up into the framework library? It is
organised around three audiences. Most readers fit one of them.


## Who this doc is for

- **The high school user.** You can install DisSysLab and you
  know how to talk to Claude. You don't write Python. **You
  rarely need this doc** — `docs/GETTING_STARTED.md` is the
  right starting place. Come back when you hit a case where
  Claude's English-driven role is too slow or too unpredictable
  for what you want.

- **The first-year undergraduate.** You know basic Python. Most
  of the agents in your office are described in English; for the
  occasional agent that needs to be deterministic or fast, you
  ask Claude to write a small `.py` role and you read it.
  **Most of this doc is for you** — it explains where that `.py`
  role goes and how it relates to the framework's libraries.

- **The framework developer.** You know DisSysLab's internals.
  You promote local roles to the framework library when a pattern
  recurs across offices. **The last section is for you** — it
  defines the promotion criteria and the placement rule (`fn_lib/`
  vs `office/library.py`).

If you do not fit one of these and you are confused, start with
`docs/GETTING_STARTED.md` instead.


## The layered framework surface

DisSysLab has three layers, ordered from *"what most users
touch"* to *"framework internals."*

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — office.md + English roles                        │
│  Pure English. Each agent has a markdown prompt; Claude     │
│  executes the prompt at runtime.                            │
│  Audience: high school student, first-year, developer       │
│  Default for ~80% of agents.                                │
└─────────────────────────────────────────────────────────────┘
                              ↓ when an English role is too
                              ↓ costly, too slow, or not
                              ↓ deterministic enough
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — local Python role in this office's roles/        │
│  A `.py` file in <office>/roles/, often written by asking   │
│  Claude. Pure Python; runs locally; no LLM call at runtime. │
│  Audience: first-year, developer                            │
│  Use case: deduplicate by URL; sliding-window RMS; etc.     │
└─────────────────────────────────────────────────────────────┘
                              ↓ when the same local Python
                              ↓ role recurs in 3+ shipped
                              ↓ gallery offices
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — framework library                                │
│  Promoted to dissyslab/fn_lib/ (Transform shape) OR         │
│  dissyslab/office/library.py (arbitrary Agent shape).       │
│  Audience: framework developer only                         │
│  Use case: deduplicator, synchronizer, gate, evaluator      │
└─────────────────────────────────────────────────────────────┘
```

The high school user normally lives entirely in Layer 1. A
first-year student crosses into Layer 2 occasionally. Only the
framework developer touches Layer 3.


## When to write what — three honest factors

For any single agent, three factors decide whether to use
English (Claude) or Python (a local `.py` role or a library
entry):

| Factor | Use Claude when… | Use Python when… |
|---|---|---|
| **Task type** | Needs judgment or language understanding (sentiment, summarisation, *"is this relevant?"*) | Deterministic and well-specified (deduplicate by URL, RMS over a window, regex match) |
| **Cost** | Office runs once a day | Office runs every 5 seconds, or on a stream of thousands of messages |
| **Determinism** | *"Mostly right"* is fine | Answer must be exact and reproducible across runs |

In practice, this gives a simple rule:

- **Default to English.** Describe what you want, Claude writes
  the role file.
- **Drop to Python only when one of the three factors above
  forces it.**

When you drop to Python, you almost always write a *local* role
in your office's `<office>/roles/` folder. That is Layer 2. You
do not need to think about the framework library at all.


## `fn_lib/` vs `library.py` — shape determines location

If you are at Layer 3 (a framework developer adding a new
built-in role), the placement is mechanical once you know the
rule.

### `dissyslab/fn_lib/` — for Transform-shaped operations

A `Transform` is the framework's primitive for *"one message in,
one message out, with mutable state."* The compiler builds it
as `Transform(fn=..., params=..., state=...)`.

A `fn_lib/` entry is three things:

- `fn(msg, state, **params) -> Optional[Any]` — runs once per
  message; mutates `state` in place; returns the output message
  or `None` to drop.
- `initial_state(**params) -> dict` — runs once at construction
  to seed mutable state.
- A name.

**Example.** `deduplicator` is in `fn_lib/` because its shape is
*"one message in, decide-and-pass-or-drop with `{"seen": set()}`
as state."* That is pure Transform shape; the compiler wraps it
automatically.

Other things that would belong in `fn_lib/`: sliding-window
RMS, running average, rate limiter, throttle, hash bucketer.

### `dissyslab/office/library.py` — for full `Agent` subclasses with custom shape

When the operation cannot fit *"one message in, one message
out, function-per-message"*, you need a real `Agent` subclass
with its own `run()` loop and custom port topology.
`office/library.py` holds **role-helper factories** that return
`AgentRoleEntry` objects; each factory defines its own `Agent`
subclass internally.

**Example.** `synchronizer` is in `library.py` because:

- It has **N inports** (configurable at office-define time —
  `synchronizer_role(["entities", "severity", "topic", "location"])`),
  one outport. Transform has 1 in / 1 out.
- Its `run()` is a *wait-for-all-then-merge* loop. Transform's
  `run()` is *"for each msg: yield fn(msg, state)"*.

That shape does not fit `fn_lib/`'s function-of-one-message
contract. So it lives in `library.py` as a role helper that
builds its own `Agent`.

Other things that would belong in `library.py`: gate
(multi-state waiting), evaluator (publish/revise routing),
debate panelist (multi-round state machine).

### The decision tree

```
For a new built-in role, ask:
  does it fit Transform shape?
  (one inport, one outport, function-per-message,
   state in a dict)

  YES → fn_lib/
        FnEntry(fn, initial_state, name).
        Compiler wraps as Transform automatically.

  NO  → office/library.py
        Write a <name>_role(...) factory that returns
        AgentRoleEntry. Define the Agent subclass inline.
        You control ports and the run() loop.
```


## Promotion criteria — when to move a role into the framework library

If you are a framework developer (the third audience), do not
add to `fn_lib/` or `library.py` on first sight of a useful
pattern. Two criteria:

1. **Recurrence.** The pattern appears in **3 or more shipped
   gallery offices**. One or two is not enough.
2. **Genericity.** The role makes no app-specific assumptions —
   no hard-coded URLs, no shape-specific message keys, no
   wired-in business rules.

When both criteria are met, copy the role from its host office's
`roles/` folder into the framework library at the location shape
dictates (`fn_lib/` or `office/library.py`). Update the host
office to remove the local copy. Add a brief docstring naming
the gallery offices that used it.

If recurrence is high but genericity is low, the right answer is
usually to refactor the role so the app-specific parts become
parameters, then promote the now-generic core.


## See also

- `docs/BUILD_APPS.md` — `office.md` grammar and the design
  path for a new office.
- `docs/GETTING_STARTED.md` — the first-10-minutes guide for
  the high school user.
- `dissyslab/fn_lib/README.md` — `FnEntry` API in detail.
- `dissyslab/office/library.py` — the source of named role
  helpers (`nl_role`, `synchronizer_role`, `specialist_role`).
- `dissyslab/blocks/` — primitive `Agent` classes the compiler
  uses internally (`Source`, `Sink`, `Transform`, `Broadcast`,
  `MergeAsynch`, `Split`, `Role`).
