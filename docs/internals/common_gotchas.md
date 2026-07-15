# Common gotchas

A reference of foot-guns that have caught real users (including the
author) while writing custom roles, sinks, sources, and small
research extensions on top of DisSysLab. Each entry names the
trap, shows the wrong pattern, shows the right pattern, and
explains why.

This document is for power users and contributors. Pat — who only
writes English in `office.md` and never touches Python — does not
need it. Anyone writing `.py` files inside an office's `roles/`,
or building a research extension that imports `dissyslab`, will
hit at least one of these.

---

## 1. Non-source agents must keep recv()-ing until _Shutdown

Non-source agents in DSL (anything with at least one inport — `Role`,
`Synchronizer`, custom Python agents) follow a single, universal
convention: **loop forever on `recv()` and let the framework end
the agent**, not your own logic.

**Wrong:**

```python
def run(self) -> None:
    while True:
        msg = self.recv("in_")
        if self._cursor >= len(self._bank):
            return                 # ← kills this agent's thread
        ...
```

**Right:**

```python
def run(self) -> None:
    while True:
        msg = self.recv("in_")
        if self._cursor >= len(self._bank):
            continue               # ← stay alive; do nothing this iteration
        ...
```

**Why:** the framework's `os_agent` polls non-source agents
periodically (via `_GiveMeCounts`) to track per-edge sent/received
counts; it shuts the network down only when every edge balances
and every agent has been heard from. An agent that returns
voluntarily from `run()` kills its thread before the next poll;
`os_agent` then has stale counts that never balance, and the
network deadlocks instead of terminating.

`recv()` itself transparently handles framework messages
(`_GiveMeCounts`, `_Shutdown`, `_Checkpoint`, etc.). When
`_Shutdown` arrives, `recv()` raises `_ShutdownSignal` which the
agent's `_run_wrapper` catches; that is the *only* clean way for
a non-source agent's thread to end.

This convention matches `Role` (in `dissyslab/blocks/role.py`)
and `Synchronizer` (the factory in `dissyslab/office/library.py`).
Read either for the canonical pattern.

**Source agents** (no inports) follow a different convention:
their `fn` returns `None` when exhausted; the wrapping `Source`
class sends one termination message to `os_agent` and then
returns. Do not extend this convention to non-source agents.

---

## 2. Multi-outport agents use indexed runtime port names

When a custom Python role declares **more than one** semantic
outport in its `AgentRoleEntry`, the compiler translates each
semantic name to a positional runtime name (`out_0`, `out_1`, ...)
in the same order. The Agent class itself must use the indexed
names; the AgentRoleEntry stays semantic so that `office.md` can
refer to them.

**Wrong:**

```python
class _Moderator(Agent):
    def __init__(self, name=None):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=["to_cold", "to_hot", "finish"],   # ← will fail
        )

    def run(self) -> None:
        ...
        self.send(msg, "to_cold")                       # ← will fail

role = AgentRoleEntry(
    name="moderator",
    in_ports=("in_",),
    out_ports=("to_cold", "to_hot", "finish"),
    factory=_Moderator,
)
```

At runtime you'll see:

```
ValueError: Unknown from_port in connection: Mod.out_0 → ClaudeCold.in_
Block 'Mod' has no outport 'out_0'.
Valid outports: ['to_cold', 'to_hot', 'finish']
```

**Right:**

```python
# AgentRoleEntry declares semantic names that office.md sees;
# the framework translates each to an indexed runtime port:
#
#   out_ports[0] "to_cold"  → runtime port "out_0"
#   out_ports[1] "to_hot"   → runtime port "out_1"
#   out_ports[2] "finish"   → runtime port "out_2"
OUT_TO_COLD = "out_0"
OUT_TO_HOT  = "out_1"
OUT_FINISH  = "out_2"


class _Moderator(Agent):
    def __init__(self, name=None):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=[OUT_TO_COLD, OUT_TO_HOT, OUT_FINISH],
        )

    def run(self) -> None:
        ...
        self.send(msg, OUT_TO_COLD)


role = AgentRoleEntry(
    name="moderator",
    in_ports=("in_",),
    out_ports=("to_cold", "to_hot", "finish"),    # ← stays semantic
    factory=_Moderator,
)
```

**Why:** `office.md` connections like `Mod's to_cold is ClaudeCold`
need a human-readable port name. The runtime uses indexed names so
multi-output `Role` agents (English `.md` roles) and custom Python
agents share one convention. The compiler does the translation
based on the *order* of `out_ports`.

**Single-outport agents** follow a different rule: one declared
port becomes `out_` (with trailing underscore) at runtime. See
`dissyslab/blocks/source.py` and `dissyslab/blocks/role.py`'s
`if len(statuses) == 1` branch. The bug pattern above only shows
up with two or more outports.

---

## 3. The `qwen_*` aliases route to Ollama, not OpenRouter

In `dissyslab/backends/__init__.py`, the AI aliases are:

```python
"claude_creative":  "anthropic_creative",
"claude_precise":   "anthropic_precise",
"qwen_creative":    "ollama_creative",      # ← surprises OpenRouter users
"qwen_precise":     "ollama_precise",
"gpt_creative":     "openai_creative",
"gpt_precise":      "openai_precise",
```

Writing `ClaudeCold's AI is qwen_precise.` in `office.md` routes
to a local Ollama server on `127.0.0.1:11434`. If Ollama is not
running, the request hangs for up to 600 seconds before timing out
with an opaque `HTTPConnectionPool` error.

**To use Qwen via cloud (OpenRouter):**

```
X's AI is openrouter_precise.
X's AI is openrouter_creative.
```

These hit OpenRouter's API with the model named in `OPENROUTER_MODEL`
(default Qwen 2.5 7B Instruct). Set the env var to override:

```bash
export OPENROUTER_MODEL='qwen/qwen-2.5-72b-instruct'
```

The `qwen_*` shorthand was a convenience for users running Qwen
locally; cloud users should reach for `openrouter_*` directly.
This will likely be made less surprising in a future DSL release.

---

## 4. Files in `roles/` starting with `_` are skipped by the role loader

`load_roles_dir` in `dissyslab/office/library.py` iterates over
`*.py` and `*.md` files in an office's `roles/` directory, **with
the exception that files whose name starts with `_` are skipped**.
This matches the Python convention for private modules (e.g.,
`__init__.py`).

Use this for **role-adjacent utility modules** that a role needs
to import but that are not themselves agent roles.

**Wrong (DSL's role loader will reject):**

```
roles/
├── moderator.py
└── math_equiv.py              # ← loader tries to find role = ...
```

```
ValueError: roles/math_equiv.py: module has no top-level 'role' attribute
```

**Right (the underscore-prefix convention):**

```
roles/
├── moderator.py               # imports from _math_equiv
└── _math_equiv.py             # ← skipped by loader; importable by siblings
```

But see the next gotcha — for substantial shared code, a real
Python package is better than the underscore trick.

---

## 5. Substantial shared code belongs in a package, not in `roles/`

The underscore-prefix trick (gotcha 4) is fine for a single small
utility used by exactly one office's roles. For **anything beyond
a single file**, or anything that **multiple offices need**, put
the code in a real Python package outside `roles/`.

**Wrong (utility under `roles/` with awkward path manipulation):**

```python
# roles/moderator.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _math_equiv import is_equivalent
```

This works but ties your role module to the directory structure
and breaks if the role is imported from a different working
directory.

**Right (a `src/` layout package; `pip install -e .`):**

```
my_research_repo/
├── pyproject.toml             # declares the package
├── src/
│   └── my_pkg/                # actual Python package
│       ├── __init__.py
│       └── math_equiv.py
└── experiments/.../office/
    └── roles/
        └── moderator.py       # from my_pkg.math_equiv import is_equivalent
```

`pyproject.toml`:

```toml
[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

Then `pip install -e .` from the repo root makes the package
importable from any working directory, no path tricks needed.

This is the right structure for research repos that depend on
DisSysLab (e.g., your team's experiments and the offices they
ship for class). See `DisSysLab-Debate` for a worked example.

---

## 6. `math_verify` parses `\boxed{X}` and raw `X` differently

If your office uses Hugging Face's `math_verify` to grade LLM
outputs against ground truth (e.g., MATH-500 answers in LaTeX),
**wrap both sides in `\boxed{...}` before parsing**. Without
the wrapper, `math_verify`'s default parser extracts only the
first numeric token, which is wrong for tuples, fractions,
symbolic expressions.

**Wrong (asymmetric):**

```python
from math_verify import parse, verify

key  = parse(r"\left( 3, \frac{\pi}{2} \right)")      # → 3   (loses the tuple)
pred = parse(r"\boxed{\left( 3, \frac{\pi}{2} \right)}")
                                                       # → (3, pi/2)  (full tuple)
verify(pred, key)                                      # → False
```

**Right (wrap both):**

```python
def _wrap(s):
    s = s.strip()
    if s.startswith(r"\boxed{") and s.endswith("}"):
        return s
    return r"\boxed{" + s + "}"

key  = parse(_wrap(r"\left( 3, \frac{\pi}{2} \right)"))   # → (3, pi/2)
pred = parse(_wrap(r"\boxed{\left( 3, \frac{\pi}{2} \right)}"))
                                                          # → (3, pi/2)
verify(pred, key)                                         # → True
```

Also include a **string-equality fast path** before calling
`math_verify`: if the two strings are byte-identical after
stripping, they are trivially equivalent. Without this, an LLM
producing `\boxed{X}` to match a ground truth `\boxed{X}` may
still fail when `math_verify` cannot parse `X` and both
parses return `None`.

---

## 7. Long generations at high temperature can silently hang

Calling an LLM at high temperature (T ≥ 0.7) on a problem that
invites long enumeration (e.g., a Bayesian probability puzzle that
benefits from case-by-case analysis) sometimes results in the
model generating very long output that exceeds the contract
parser's expectations. Symptoms:

- `dsl run` produces no output for several minutes.
- The Python process is alive but at 0% CPU (`ps aux` shows `S+`).
- No record is written to the recorder sink.
- API budget is consumed even though no successful completion is
  recorded.

**Mitigations:**

1. **Bound the response in the prompt:** add
   `"Keep your reasoning under 200 words."` or similar.
2. **Constrain the output format:** ask for a fraction in
   lowest terms with no decimal, or for a single numeric
   answer, instead of free-form text plus a final answer.
3. **Add a per-call timeout** in your LLM-call wrapper. The
   `anthropic` and `openai` libraries accept `timeout=` on
   their request methods.

Investigating one of these hangs requires logging the request
and response inside `nl_role.call_llm` (in
`dissyslab/office/library.py`). That instrumentation is a
straightforward 5-line addition for the rare cases it's needed.

---

## 8. Cached `.pyc` files mask source edits during local development

When developing locally, editing `.py` files does not always
immediately take effect because Python caches compiled
bytecode in `__pycache__/`. This is *usually* invalidated
correctly by file-mtime checks, but **edits made under an
editable install (`pip install -e .`) sometimes don't trigger
re-compilation**, especially across multiple `python3` invocations
that happen quickly.

**Symptom:** you edit a source file, re-run, and the old
behavior persists.

**Fix:** clear all `__pycache__/` directories under the repo:

```bash
find ~/Documents/MyProject -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

Then re-run.

This is most likely to bite you when:
- Iterating fast on a role file inside `roles/`.
- Iterating on an editable-installed package's source.
- Running tests immediately after a code change.

Add the `find` command to your shell history; it's the first
thing to try whenever your edit appears to have no effect.

---

## 9. The `dsl run` startup phase is silent

If `dsl run office` produces no output for more than ~30 seconds,
do not assume it has crashed. Three legitimate reasons for
extended startup silence:

- **sympy import via math_verify** takes 1-3 seconds.
- **The first LLM call** can take 10-60 seconds, especially at
  high temperature on a complex problem.
- **Rate-limit retry loops** in the LLM SDK silently wait up to
  60 seconds between retries on `429` responses.

To distinguish "slow" from "hung," check the process:

```bash
ps aux | grep "dsl run" | grep -v grep
```

- `S+` state and 0% CPU → blocked on I/O. Almost certainly waiting
  for the LLM API. Wait longer or check the API status page.
- `R` state or >5% CPU → still doing work. Wait.

For visibility into startup, set `PYTHONUNBUFFERED=1`:

```bash
PYTHONUNBUFFERED=1 dsl run office
```

This forces stdout/stderr to flush after each `print`. Some
startup banners that are otherwise buffered then appear in
real time.

---

## 10. `office.md` rejects prose between the title and the first section

The `office.md` parser expects the file to begin with a `# Office:
<name>` line and then jump straight to recognised sections
(`Sources:`, `Sinks:`, `Agents:`, `Connections:`). Any free-form
prose between the title and the first section is treated as a
parse error, not as documentation.

**Wrong:**

```markdown
# Office: phase1_pilot

Two-panellist office for measuring transition kernels on
multiple-choice problems. The Qwen and Llama panellists each
answer the question; the moderator records the per-round
transitions until the panel agrees or rounds run out.

Sources: starter

Sinks: jsonl_recorder(path="answers.jsonl")
...
```

At build time:

```
dsl build: .../office.md:3: parse error: unexpected text outside any section
    Two-panellist office for measuring transition kernels on
```

**Right:** put the documentation in a sibling `README.md` in the
same office directory, and keep `office.md` minimal — just the
title and the recognised sections:

```markdown
# Office: phase1_pilot

Sources: starter

Sinks: jsonl_recorder(path="answers.jsonl")
...
```

Then in `README.md`, write whatever prose, diagrams, and tables
are useful for a reader of the office. The README lives next to
`office.md`, so the documentation stays co-located with the
code it documents without confusing the parser.

**Why:** the parser is a simple line-oriented walker that
expects every non-blank line after the title to belong to a
recognised section. There is currently no syntax for comments
or for a free-form description block. (Future DSL releases will
likely accept either a `<!-- … -->` HTML comment, an YAML
front-matter block, or a leading-prose-as-description rule —
tracked as a separate backlog item.)

---

## Adding a new gotcha

When you (or a student) hit a non-obvious failure mode that
takes more than 10 minutes to diagnose, add a section here.
Each entry should follow the same shape:

1. One-line name.
2. **Wrong:** code or pattern that produces the bug, with the
   error message you'd see.
3. **Right:** the working pattern.
4. **Why:** a short explanation of the underlying mechanism.

Future-you will thank present-you.
