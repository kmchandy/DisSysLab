# DisSysLab internals

Design and implementation notes for the framework itself. If you are
*using* DisSysLab to build offices, start with
[../../README.md](../../README.md) and [../BUILD_APPS.md](../BUILD_APPS.md);
the documents here are for developers who want to read the source.

**Start with [STATUS.md](STATUS.md)** — one page on where the project
is, what is open, and in what order. It is the only document in this
folder that is kept current.

The rest is in three folders, and the division is about how each kind
of document ages:

| Folder | What is in it | How it ages |
|---|---|---|
| [reference/](reference/) | How the code works now | Updated whenever the code changes. If it is wrong, that is a bug. |
| [design/](design/) | What is being built, and the argument for it | Living. Extended as the design is worked out. |
| [decisions/](decisions/) | A choice made once, with its reasons | Frozen. Never updated — a superseded decision gets a new document that says so. |

Anything dated and finished — plans, issue lists, acceptance runs,
resolved bug reports — moves to [../../archive/](../../archive/) and
is not maintained.

## reference/

Each major module has two paired documents — an *overview* of what the
module does and why, and an *implementation* note that walks through
the code:

| Module | Overview | Implementation |
|---|---|---|
| `dissyslab/core.py` | [core_overview.md](reference/core_overview.md) | [core_implementation.md](reference/core_implementation.md) |
| `dissyslab/network.py` | [network_overview.md](reference/network_overview.md) | [network_implementation.md](reference/network_implementation.md) |
| `dissyslab/builder.py` | [builder_overview.md](reference/builder_overview.md) | [builder_implementation.md](reference/builder_implementation.md) |
| `dissyslab/os_agent.py` | [os_agent_overview.md](reference/os_agent_overview.md) | [os_agent_implementation.md](reference/os_agent_implementation.md) |
| `dissyslab/blocks/` | (see overviews above) | [blocks_implementation.md](reference/blocks_implementation.md) |

This table is checked: `tests/integration/test_docs_match_code.py`
fails if a substantial module is missing from it, or if it links to a
document that does not exist.

Cross-cutting:

- [architecture.md](reference/architecture.md) — the framework's
  overall design.
- [making_a_component.md](reference/making_a_component.md) — how to
  add a source, transform, sink, or other block.
- [common_gotchas.md](reference/common_gotchas.md) — footguns when
  writing custom Python roles or research extensions. Grown as new
  ones are found.

## design/

- [termination_detection_design.md](design/termination_detection_design.md)
  — the activity model (active/idle, reactive/non-reactive), alarms,
  and the extension of the predicate to offices running as processes.
- [process_per_office_design.md](design/process_per_office_design.md)
  — the office as a logical construct, the process as an execution
  construct, and where the two are allowed to meet.
- [coordinator_design.md](design/coordinator_design.md) — selective
  receive, and why a message in an inbox the coordinator is not
  reading is not live work.
- [guard_rails.md](design/guard_rails.md) — an opt-in way for a user to
  put her own checks around a model call, and the micro-course on
  using models safely that it exists to carry. Composed inside one
  agent rather than wired as its own, so it cannot be bypassed by
  rewiring.
- [check_registry_design.md](design/check_registry_design.md) — where a
  domain's checks should live, and what silence means in a prompt.

## decisions/

- [process_parallelism_decision.md](decisions/process_parallelism_decision.md)
  — why per-agent processes were scrapped.
- [replay_debug_mode_decision.md](decisions/replay_debug_mode_decision.md)
  — why there is no "debug mode".
- [debugging_aids_decision.md](decisions/debugging_aids_decision.md)

---

For the layered framework surface and the *"fn_lib vs library.py"*
decision rule, see [../EXTENDING.md](../EXTENDING.md). That document
sits one level up because it is for both maintainers and advanced
users; the documents in this folder are for maintainers only.
