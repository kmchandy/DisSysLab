# dissyslab/fn_lib/ — built-in function library

This folder is the framework's library of pre-built Python
transformers. Where `dissyslab/roles/` ships LLM-driven roles
(prompts in `*.md`) and custom Python roles (`.py` files
exporting an `AgentRoleEntry`), this folder ships **plain
functions with first-class state**.

> **Where does this fit?** `fn_lib/` is Layer 3 of the framework
> (framework-maintainer territory). For when to add an entry here
> vs. write a local Python role in your office vs. just ask Claude
> for an English role, see [`docs/EXTENDING.md`](../../docs/EXTENDING.md).


When Pat writes:

```
Sasha is a deduplicator(by="url").
```

the compiler:

1. Looks up `deduplicator` in `FN_LIB`.
2. Partitions Pat's kwargs by signature: kwargs that
   `initial_state` declares go to the construction call; kwargs
   that the per-message `fn` declares go to `params=`.
3. Builds `Transform(fn=..., params=..., state=..., name="Sasha")`
   automatically.

Pat never writes the `Transform(...)` line; she just names the
entry and supplies its kwargs.

## How an entry is shaped

A function-library entry has three pieces:

- `fn(msg, state, **params) -> Optional[Any]` — runs once per
  message. Mutates `state` in place. Returns the output message,
  or `None` to drop.
- `initial_state(**params) -> dict` — runs once per agent at
  construction. Returns a fresh mutable state dict. Only declares
  the kwargs it actually consumes — the framework filters Pat's
  kwargs by `inspect.signature`, so unused kwargs do not need to
  appear here.
- A short description for diagnostics and discovery.

Wrap them in an `FnEntry` and register under a name in `FN_LIB`.
See `dedup.py` for the canonical example.

## What `by="url"` means

Reading `Sasha is a deduplicator(by="url").` aloud: *"Sasha
deduplicates by the **value of the 'url' field** in each
incoming message."* The kwarg name `by` is the convention for
"the field to key on." This same reading applies wherever you
see `params={"by": "url"}` in the generated `build/run.py` —
the framework is forwarding Pat's choice of key into `fn` so
it knows which value to look up on every message.

## Lookup precedence

When the compiler resolves an agent's role name, it searches in
this order:

1. `<office>/roles/` — Pat's local Python or `.md` role files.
2. `dissyslab/roles/` — framework-shipped roles.
3. `dissyslab/fn_lib/` — this registry.

So an office can override a built-in by dropping a same-named
file in its own `roles/`.

## How to add an entry

1. Create `<name>.py` in this folder. Define `<name>_initial_state`
   and `<name>` (the per-message function), then wrap them in an
   `FnEntry`.
2. Import the entry in `__init__.py` and register it under a name
   in `FN_LIB`.
3. Add tests in `tests/unit/fn_lib/test_<name>.py` covering both
   the direct function call and an end-to-end run through a
   `Transform`.
4. Run `pytest`. Make sure the gallery snapshot still compiles.

## Curation policy

This folder is for transformers general enough to be useful
across many offices: deduplicators, rate limiters, throttles,
field projectors, schema normalisers, and so on. Domain-specific
or one-off transformers belong in the office's local `roles/`
as a Python role file, not here.
