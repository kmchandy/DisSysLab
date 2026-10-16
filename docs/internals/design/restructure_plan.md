# Restructuring the implementation toward the spec

Status: **proposal, 16 October 2026.** For review before any code moves.
Companion to `officespeak_revised.md` (the spec). Agreed approach: restructure
toward the spec, small steps, Mani commits each; type hints checked with mypy.

## 1. Where the code is today

About 25,000 lines in `dissyslab/` outside the gallery. The suite is green
(1,162 passed; the one failure is a superseded checkpoint note naming a
command that does not exist yet). A full map was made by reading the code;
the facts that shape the plan:

| Area | Today | Problem |
|---|---|---|
| Office → runnable | `codegen.py` writes `build/run.py` (used by `dsl run`, `dsl build`); `compiler.py` builds a `Network` in process (used only by tests) | The same tree-walk twice, already drifted (local `sources/` only in the compiler, `X's AI is Y` only in codegen). The gallery sweep tests the path users never take. |
| Older generator | `assemble.py`, `from_officespeak.py`, `officespeak_spec.py`, `make_office.py` | Not reachable from the CLI; no tests except `make_office` |
| `dsl check` vs `dsl run` | separate; `dsl run` never runs the checks | |
| Runtime | `core.py` (Agent, 1,294 lines), `network.py` (1,279), `os_agent.py`, `snapshot.py`, `blocks/` (12 kinds) | Sound core; blocks the spec retires (`select`, `split`, `alarm`, `merge_synch`, `role` routing by status strings) |
| Process mode | `Network.process_network` | Never starts the termination detector; ends on a 30 s timeout. No test. |
| Roles | `library.py` (1,905 lines): `nl_role` appends a contract, merges replies, routes by `send_to`; `AgentRoleEntry`; `PARAMETERIZED_LIBRARY`; `fn_lib/`; `roles/` | The spec replaces all of this |
| Prompt | `office_run_context.py` appends wardrobe and weather text to **every** English role's prompt | Contradicts "the framework appends nothing" |
| Front matter | four separate parsers | |
| Built-in roles dir | located in six places | |
| Registries | `office/utils.py`: sources and sinks, with ~15 aliases; six sinks import from `dissyslab.gallery` | Framework reaches into the gallery |
| CLI | `cli.py`, 2,579 lines, one file | |
| Dead code | `components/transformers/` (11 files), `office/agent_spec.py`, `office/draft_template.py`, `utils/get_credentials.py`, an empty test file | Nothing imports them |
| Tests | 68 files, 1,162 tests | `test_compiler.py` writes `brief.html` and `radar.html` into the current directory |

## 2. Target layout

One path from `office.md` to a running network, organised by the spec's
layers (Principle 1: roles / office / operating system).

```
dissyslab/
    __init__.py            public API: Agent, Network, load_office, run_office
    runtime/               the operating system (spec §0, layer 3)
        agent.py           Agent: ports, send/recv, counts, failure reporting
        network.py         Network: validate, wire, start, run, report
        plumbing.py        hidden fan-out / fan-in (Broadcast, MergeAsynch)
        termination.py     the termination detector (today os_agent.py)
        snapshot.py        checkpoints and resume
        trace.py           logical clocks and trace files
        summary.py         run summary, incl. "who is still waiting" (§4.5.6)
    office/                the language (spec §3)
        syntax.py          parser for the line form (§3.1)
        model.py           OfficeSpec dataclasses (one AgentSpec, one EXTERNAL)
        frontmatter.py     the one front-matter reader (§4.4)
        resolve.py         how a kind is found (§3.2), helper modules, needs:
        build.py           the one builder: OfficeSpec -> Network (§8)
        checks/            dsl check: one module per family of W codes,
                           catalogue.py (codes, §9)
        draw.py            text and Mermaid diagrams
    agents/                how roles become running agents (spec §4–6)
        english.py         prompt = file text + message JSON; reply check §4.5
        python_role.py     load the one class, construct, call, checkpoint
        reply.py           §4.5 reply checking, shared by both
        router.py          router(on=…)
        synchronizer.py    keyed; collect= form
        gate.py
        record.py
    components/            sources and sinks (spec §7)
        registry.py        built-ins declare themselves; no aliases
        sources/  sinks/   (each declares out:/in: in its docstring)
    backends/              model providers (unchanged in shape)
    roles/                 built-in role files (data)
    cli/                   one module per command family
        main.py  run.py  check.py  draw.py  init.py  show.py  chat.py  …
    market/                market_data, market_fetch (used by mac_speed_suite)
```

What disappears: `codegen.py` and generated `build/run.py`; `compiler.py`
(merged into `office/build.py`); `assemble.py`, `from_officespeak.py`,
`officespeak_spec.py`, `draft_template.py`, `agent_spec.py`; `library.py`
(split into `agents/`); `fn_lib/`; `blocks/` (what survives moves into
`runtime/` or `agents/`); `office_run_context.py`; `components/transformers/`;
`builder.py` (if the `network([(a, b)])` API is not kept, see decisions);
the sink aliases.

## 3. Decisions (Mani, 16 October)

- **Keep it simple; nothing hidden from the student; no magic.** This governs
  every step below.
- (1) One build path, in process: **agreed**. `dsl build` and `run.py` retire.
- (2) Process mode: **removed**.
- (3) Building networks from Python (`Network(...)`, `builder.network`):
  **dropped or postponed**. `Network` stays as an internal runtime class only.
- (4) Gallery-specific sinks move to their offices' `sinks/`: **agreed**.
- (5) mypy strict on new packages, lenient elsewhere: **agreed**.
- **The operating-system algorithms wait:** termination detection,
  snapshots, tracing, and the "who is still waiting" report are left as they
  are for now. Phase 1 below shrinks to moving and documenting the runtime
  without changing those algorithms.

### Change of direction (Mani, 17 October)

**The course goal changed:** students run distributed systems of several
LLM agents, learn to impose guardrails, and learn ways LLM agents
collaborate. The runtime's job is therefore to be reliable and to stop
cleanly with a clear summary, not to be small or teachable.

- **The runtime is frozen.** Phase 1 ended by moving the runtime into
  `dissyslab/runtime/` (agent, os_hooks, messages, network, termination,
  snapshot, plumbing); the old module names remain as aliases. No further
  restructuring of it. Snapshots and tracing stay (opt-in, unseen by
  students).
- **Not done, recorded for later:** replacing the termination detector by
  a single-process stop rule ("option B": every thread finished or
  waiting on empty channels, checked under one lock). Smaller and
  provable, but new code in the most failure-sensitive place and tied to
  one process. A fallback if the detector misbehaves in the labs.
- **Next:** end-to-end tests of the lab paths (each kept example through
  the real `dsl run` path with a scripted fake model: stops by itself on a
  finite input, a failing role, a guardrail firing, a stalled loop); then
  implement the spec (Phases 2-4); the stall report on top of the existing
  detector; then the labs.

**Exceptions to the freeze, each approved by Mani:**

1. The run summary notes fields a role's replies carried without
   declaring them (`network.print_run_summary`).
2. **The stall report** (spec 4.5, item 6; built 17 October). An agent
   that holds work -- a gate's admitted item, a synchronizer's
   incomplete group -- reports it (`holding`, beside `waiting_on`). The
   detector walks back from the inboxes the holder needs: the one
   connection into each inbox, then the agent and outbox feeding it; if
   the connection is empty and that agent idle, every inbox *it* reads,
   until each branch ends in a cycle or at a finished source (Mani's
   design). Success means a closed set of idle agents with every
   connection into it empty and coming from inside it or from a
   finished source -- the termination condition applied to part of the
   office -- so the holder never gets what it needs. While the office is
   still running (a source that never finishes) a stall is declared only
   when two consecutive rounds agree; at termination one walk suffices.
   Each stall is printed once, when found, and makes `dsl run` exit
   non-zero. `runtime/termination.py` (`_stall_walk`, `_find_stalls`).

The options as first proposed:

1. **One build path.** I recommend the in-process builder only: `dsl run`
   parses, checks (errors stop the run), builds and runs. `dsl build` and the
   generated `run.py` retire. The run.py was meant to be readable, but under
   the spec the office file *is* the readable description, and two paths have
   already drifted. (If a script form is wanted, `python -m dissyslab run
   <folder>` does the same.)
2. **Process mode** (`--processes`): fix it (start the termination detector
   in the parent, give it multiprocessing queues) or remove it for this
   release. I recommend **remove**, and restore it with a test when the course
   needs it. It does not work today.
3. **`builder.network([(a, b), …])`** and hand-written `Network(blocks=…)`:
   keep as the Python API for building networks without an office file (used
   by `dsl doctor` and docs), or drop. I recommend **keep `Network`**, drop
   `builder` unless the course uses it.
4. **Gallery-specific sinks** (periodic_brief, debate_display, report_html,
   …) move out of the framework registry into their offices' own `sinks/`
   folders, which the spec now allows (§3.2).
5. **mypy strictness.** Start with `disallow_untyped_defs` on the new
   packages (`runtime/`, `office/`, `agents/`) and lenient elsewhere; tighten
   as modules are rewritten. I cannot run mypy in my sandbox (no network to
   install it); you would run `mypy dissyslab` on your Mac at each step, or I
   add it to CI.

## 4. Order of work (each step one commit, suite green)

**Phase 0: clear the ground** (no behaviour change)
1. Delete dead code (list in §1), and the unreachable generator
   (`assemble`, `from_officespeak`, `officespeak_spec`), fixing the error
   strings that mention it.
2. Fix test pollution: the gallery sweep runs from a temporary directory.
3. Add mypy configuration to `pyproject.toml` and a `py.typed`-consistent
   baseline.

**Phase 1: the runtime** (`runtime/`): move `core.py`, `network.py`,
`os_agent.py`, `snapshot.py`, tracing, fan-out/fan-in into `runtime/` with
types and docstrings; keep old import paths as thin re-exports until Phase 5;
remove process mode (if decided); add the stalled-office report (§4.5.6).

**Phase 2: the language** (`office/`): new parser for the line form, one
model, one front-matter reader, resolution with local `sources/`/`sinks/`
and `_helper` modules. Written beside the old parser, tested on the nine
paper ports.

**Phase 3: agents** (`agents/`): English roles (no appended text), Python
roles (one class, signature-only inspection, `needs:`), reply checking,
router, keyed synchronizer with `collect=`, gate, record.

**Phase 4: checks**: W1–W14, G1–G2 rewritten on the new model; W16–W32.

**Phase 5: one build path and the CLI**: `office/build.py`; `dsl run` checks
then builds; CLI split into `cli/`; old modules and re-exports removed;
registries cleaned (declarations, `path=` everywhere, aliases gone).

**Phase 6: examples and docs**: the eight kept examples rewritten; the rest
of the gallery archived; skills (`office-builder`,
`backtest-strategy-builder`) and the reference rewritten; microcourse
finalised. Split into steps (Mani, 17 October):

- **6a, done 17 October.** The version 1 gallery left `main` (it is on the
  `v1` branch and the `v1.10.2` tag; links in the docs point there). The
  nine 2.0 offices are `dissyslab/gallery/`, flat. `dsl list`, `dsl init`
  and `dsl check <name>` use it; `dsl run <name>` on a gallery office
  says to copy it first (a run writes beside `office.md`). Tests that
  swept the old gallery with the old tools were removed; the
  mac_speed_suite strategy tests now test the 2.0 office's code
  (`tests/mac_speed_suite_roles.py`).
- **6b.** Remove the old build path (parser, compiler, codegen, library,
  check_wiring, the old `dsl check`/`draw`/`show`/`roles`) and its tests;
  `office_roles/` becomes `roles/` (the v1 roles go). Ported from the old
  `dsl check` into the new one before it goes, because they are
  guardrails: W11 (an untrusted source reaching an acting sink) and the
  role-effects scan (a role that launches a program). `dsl draw` for the
  new syntax.
- **6c.** Docs: README, GETTING_STARTED, SOURCES_AND_SINKS and the rest
  still teach version 1 offices and the sentence form. Skills
  (`office-builder`, `backtest-strategy-builder` -- its bundled
  `check_no_lookahead.py` still names the v1 roles path, pinned identical
  to the office's `_contract_checks.py`), the reference, the microcourse.

**Phase 7: release**: reliability evaluation (§11), rehearsed install.

## 5. How each step is verified

- The full suite, run on a copy of the repository in my sandbox (so test
  side effects never touch your folder), without the optional extras.
- New code: unit tests written with it; the nine paper ports become parser
  and check tests in Phase 2–4.
- mypy on your Mac for each step that adds types.
