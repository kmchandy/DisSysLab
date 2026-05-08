# Building offices programmatically with `make_office`

This doc captures a new way to build a DisSysLab office. Most of
the time you'll continue writing offices by hand — opening an
editor, typing `office.md`, dropping prompt files in `roles/`. That
remains the primary path and is documented in
[`BUILD_APPS.md`](BUILD_APPS.md).

But there's now a second path: construct the office in Python and
call `make_office` to write it to disk. The two paths produce
identical artifacts; everything downstream — `dsl build`, `dsl run`,
the parser, the compiler, the runtime — treats hand-written and
programmatically-generated offices the same.

This is small in code (one new function) but conceptually
significant. It opens the framework to tools that want to author
offices without templating markdown.

---

## The picture

```
                           ┌──────────────────┐
        Pat writes by      │                  │
        hand in editor ────►   office folder  │
                           │   (office.md +   │
        Pat or a tool      │    roles/)       │
        calls make_office ─►                  │
                           │                  │
                           └────────┬─────────┘
                                    │
                                    ▼
                           dsl run / dsl build
                           (treats both paths
                            the same)
                                    │
                                    ▼
                           Network running 24/7
```

Two paths converge on a folder. After that, the existing pipeline
runs unchanged.

---

## Path 1 — write by hand (the primary path)

This is what you do today after `pip install dissyslab`. Open an
editor; create a folder; type `office.md`; drop role files in
`roles/`. See [`BUILD_APPS.md`](BUILD_APPS.md) for the full
walkthrough.

```
my_office/
├── office.md          # the wiring, in plain English
└── roles/
    └── analyst.md     # one prompt per role
```

This path is right for: a person sitting at a keyboard who knows
what office they want and doesn't need help writing it. It is
the path that aligns most directly with DisSysLab's mission of
"describe what you need in plain English."

---

## Path 2 — call `make_office` programmatically

`make_office` is a Python function that takes an office description
in dict form and writes the folder for you. It's the inverse of
`parse_office_dir`: where the parser reads markdown into an
`OfficeSpec`, `make_office` writes an `OfficeSpec` back out as
markdown.

```python
from pathlib import Path
from dissyslab.office_v2 import (
    OfficeSpec, RoleRef, SourceSpec, SinkSpec,
    ConnectionStmt, Endpoint,
    make_office,
)

spec = OfficeSpec(
    name="my_first_office",
    sources=(SourceSpec(name="hacker_news",
                        args=(("max_articles", 10),)),),
    sinks=(SinkSpec(name="console_printer"),),
    agents=(RoleRef(agent_name="Alex", role_name="analyst"),),
    connections=(
        ConnectionStmt(
            source=Endpoint("hacker_news", "destination"),
            destinations=(Endpoint("Alex", "in_"),),
        ),
        ConnectionStmt(
            source=Endpoint("Alex", "briefing"),
            destinations=(Endpoint("console_printer", "in_"),),
        ),
    ),
)

target = Path("./my_first_office")
make_office(target, spec, roles_lib={})
```

After that runs, `./my_first_office/` exists with `office.md`
inside, structurally identical to a hand-written gallery office:

```
# Office: my_first_office

Sources: hacker_news(max_articles=10)
Sinks: console_printer

Agents:
Alex is an analyst.

Connections:
hacker_news's destination is Alex.
Alex's briefing is console_printer.
```

You can then `dsl run ./my_first_office/` exactly as if you'd typed
the file.

### What's in the dicts

`make_office` accepts three library dicts as arguments:

| Argument | Type | What it holds |
| --- | --- | --- |
| `roles_lib` | `dict[str, RoleEntry]` | Definitions of named roles (LLM prompts and Python transformers). |
| `fn_lib` | `dict[str, Callable]` | Pre-built Python transformers usable as roles. (Reserved in v1.) |
| `office_lib` | `dict[str, ...]` | Pre-built sub-offices Pat can compose. (Reserved in v1.) |

`v1` uses the dicts only for forward-compatibility — the function
writes `office.md` and lets the existing role-file machinery resolve
roles at compile time. Future versions will use the libraries to
populate `target_dir/roles/` automatically.

---

## When to use which path

**Use Path 1 (by hand) when:**

- You're Pat, sitting at a keyboard, designing one office for one
  problem you understand. This is the case the framework is
  optimised for.
- You want to read the role prompts as you write them, tweak as
  you go, and see the result instantly.
- You want the simplest possible thing.

**Use Path 2 (`make_office`) when:**

- You're writing a tool that *generates* offices. Examples:
  - A wizard that asks Pat questions and composes an office from
    her answers.
  - A batch generator that creates one office per row of a
    spreadsheet ("monitor each of these 50 product pages").
  - A future LLM-driven helper that turns a free-form description
    into a working office.
- You have an office description that already lives as data
  somewhere (a JSON file, a database row, a config) and want to
  materialise it as a runnable folder.
- You want round-trip verification: compose the spec, write the
  office, parse it back, confirm it equals the original.

For the carpenter case — Pat building one office for her own
use — Path 1 stays the right answer. Path 2 is for *tools that
serve Pat*, not for Pat directly.

---

## What `make_office` does, and doesn't, do (v1 scope)

It does:

- Create `target_dir` (raising `FileExistsError` if it already
  exists — no accidental overwrites).
- Write `office.md` from the `OfficeSpec`, formatted to round-trip
  with `parse_office_dir`.
- Return the path to the folder it created.

It deliberately does *not*:

- **Run an LLM** to fill anything in. The function is pure
  serialisation. If you want LLM-driven assembly, build it as a
  layer above `make_office`.
- **Verify the result with the user.** No "is this what you had in
  mind?" prompt. Pat (or the calling tool) inspects `office.md`
  herself.
- **Populate `target_dir/roles/`.** That's reserved for a future
  version once the framework's built-in role library lands. For
  now, ensure every role used in the spec resolves either via
  files Pat places in `roles/` herself or via a future built-in
  library.

---

## Round-trip guarantee

For any well-formed `OfficeSpec`:

```python
target = make_office(some_path, spec, roles_lib={})
assert parse_office_dir(target) == spec      # structurally
```

(In practice we compare `name`, `inputs`, `outputs`, `sources`,
`sinks`, `agents`, and `connections` separately because the
`OfficeSpec` dataclass is frozen and each field is independently
checkable; whitespace in the file may differ from a hand-written
version, but the *parsed* result is the same.)

This guarantee is the foundation. Tools that compose offices in
Python can rely on it: whatever they construct, the framework
reads back the same way.

---

## A note on architecture

DisSysLab now has three separable concerns that an office passes
through:

1. **Construction.** Either a person typing or a tool calling
   `make_office`. Output: a folder on disk.
2. **Parsing.** `parse_office_dir` reads the folder into an
   `OfficeSpec`.
3. **Compilation.** `compile_office` turns the spec plus the
   relevant libraries into a runtime `Network` and (optionally,
   via codegen) a readable `build/run.py`.

The dicts (`roles_lib`, `fn_lib`, `office_lib`) flow through stage
3 today. Stage 1 was previously a black box — only-hand-written.
With `make_office`, stage 1 has a typed Python interface too.

The framework's primitive becomes the dict. Markdown is one
ingestion path; programmatic construction is another. Every later
extension (a wizard, an LLM-driven assembler, a batch tool) can
slot in at stage 1 without touching the rest of the pipeline.

---

## See also

- [`BUILD_APPS.md`](BUILD_APPS.md) — designing and writing offices
  by hand. Path 1.
- [`LANGUAGE_MODELS.md`](LANGUAGE_MODELS.md) — choosing and mixing
  language model backends.
- [`COST.md`](COST.md) — what it actually costs to run a DisSysLab
  office. *(forthcoming)*
- The reference implementation: `dissyslab/office_v2/make_office.py`.
- Tests demonstrating the round-trip guarantee:
  `tests/unit/office_v2/test_make_office.py`.
