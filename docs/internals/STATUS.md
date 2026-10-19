# Where the project is — 2026-10-17

One page. What is true now, what is open, and in what order. This is the
only status document kept current; the history is in git and in
[design/restructure_plan.md](design/restructure_plan.md).

If you are picking the project up cold, read this, then
[design/officespeak_revised.md](design/officespeak_revised.md) (the
language), then [reference/architecture.md](reference/architecture.md)
(how the pieces fit), then the module you are about to change.

## The measure of success

> A first-year builds an app they care about, then studies the
> algorithms underneath it.

**The course runs 4 January – 10 March 2027.** Its goal: students run
distributed systems of several language-model agents, learn to impose
guardrails, and learn ways agents can collaborate. Everything below is
ordered against that.

**People.** Mani Chandy (maintainer; merges). Jeffrey Zhou (TA; works on
branches and pull requests, see [CONTRIBUTING.md](../../CONTRIBUTING.md)).

## What is true now (2.0.0.dev0 on `main`)

- **The office language is 2.0**, as specified in
  `officespeak_revised.md`: `name: kind(args)` declarations and `a -> b`
  connections; annotator and author roles in English or Python; routers;
  the keyed synchronizer and the gate; nested offices; drafts. Version 1
  (the sentence form) is on the `v1` branch and the `v1.10.2` tag, and
  does not run on `main`.
- **One build path, in memory:** `office/syntax` → `resolve` → `build`.
  No generated `build/run.py`.
- **Guardrails** (all optional, Principle 6): **contracts on both ends of
  a role** (18 Oct): every message checked against the role's `in:`
  before the role is called, every reply against its `out:` (undeclared
  fields dropped and counted). A field may declare what it holds: values,
  `number`/`integer` with a range or bound, `text` with a maximum length
  (spec 4.4). **A refusal stops the whole office** (Mani, 18 Oct; spec 4.5
  step 5): no role runs again, finished work is kept, the refusal goes to
  `refused.jsonl`, the summary ends with `Stopped:`, no stall is reported.
  A Python role that raises still costs only that message. An office may
  instead wire an agent's **`refused` outbox** (`Sal.refused -> Sorry ->
  screen`, 18 Oct): the refusal goes there with a `refusal` field, is still
  recorded, and the office carries on; `dsl check` never treats it as a
  barrier. GETTING_STARTED 4.5 and Lab 1 step 7 show it.
  `needs:` checked before a run;
  `dsl check` notes for untrusted text reaching an acting sink, Python
  reaching past the sinks, and router outboxes that no declared value can
  reach.
- **The runtime is frozen** (`dissyslab/runtime/`), with two approved
  exceptions: the dropped-fields note, and the **stall report** (a walk
  back from held work proving it can never be released).
- **Ctrl-C** stops a running office with its summary (fixed 17 Oct; it
  used to hang).
- **The gallery** (`dissyslab/gallery/`): eleven offices, each with a
  README and an end-to-end test, from `inbox_sorter` to `mac_speed_suite`,
  including `car_dealer` (Lab 1).
- **Lab 1** (`course/lab1.html`, the one-dollar Tahoe): the `chat_page`
  source and `chat_reply` sink (a local chat page in the browser), the
  `car_dealer` office, `attacks.jsonl` and `grade.py`, and a reference
  guard in `tests/e2e/car_dealer_guarded/` (public: the repository is).
  The files the handout prints are built and run by the tests.
- **Lab 2** (`course/lab2.html`, the incident room, 18 Oct): the gallery's
  `incident_room` (an open whiteboard: a Python `Board`, three LLM
  analysts, a writer; `evidence.jsonl` carries an injected report),
  `grade.py` (quality, attack, spread on the board) and `trials.py` (N runs,
  rates; `--command` for any other system that writes `report.jsonl`).
  Students run A open board, B pipeline with contracts, C guarded board
  and D their own, 10+ runs each, and argue which to deploy. References
  for B and C in `tests/e2e/incident_room_pipeline/` and `_guarded/`;
  `tests/e2e/test_incident_room.py` and `test_lab2_handout.py`. An optional
  Claude Agent SDK track (`claude_room.py` on the page) is **untested**:
  written from the SDK docs; a staff member with the SDK should run it once.
  Like Lab 1, it needs a real-key rehearsal (does the attack spread on the
  default model at all?).
- **Course pages students open first, in 2.0:** `course/index.html`,
  `setup.html`, `microcourse.html`, `OfficeToolkit.html`, `lab1.html`; the
  old root `office_microcourse.html` redirects to the micro-course.
  **Day-1 pages rewritten around safety (18 Oct):** the micro-course (20
  screens, from `course/microcourse_plan.html`: LLM and Python agents,
  contracts, inboxes taught with coordinators; the previous one is in
  `_to_delete/`), the toolkit's "Contracts and guardrails", GETTING_STARTED
  part 4.5 (a message that breaks a contract stops the office), setup;
  Lab 1 step 7 explains contracts and refusals. The gallery's `clerk`,
  `manager` and `triage` now declare bounded `in:` contracts.
  **The project's safety case is required** (Mani, 18 Oct):
  `course/safety_case.html` (three parts, a template, the pass/fail
  reading, two checkpoints). **The worked example,
  `course/tahoe_case.html`, is handed out after Lab 1**: keep it out of git
  until then (GitHub Pages publishes `course/`); its tests skip while it is
  absent. Its real-model table is empty until the real-key rehearsal.
  `tests/integration/test_course_pages.py` checks links, every office,
  role and sink file the pages quote (illustrations against
  `tests/integration/microcourse_offices/`), every line of output on the
  micro-course, the toolkit's lists against the package, and the Tahoe
  case's quotes, `dsl check` output and the holes it claims in the guard.
- **Docs:** `docs/GETTING_STARTED.md` (the student guide; its outputs are
  re-checked by `tests/integration/test_getting_started.py`), the
  `dsl grammar` reference (shipped in the package, also what `dsl new`
  gives the model), recipes, and the three skills, all in 2.0.
- **CI:** Linux 3.10–3.14, macOS, Windows (advisory), mypy on the strict
  modules. The suite is about 740 tests and runs in under a minute.
  Windows failed 15 tests on b95fd2b; all are addressed (17 Oct) but
  not yet confirmed by a Windows run: CRLF checkout (`.gitattributes`
  now pins LF), `CSVPointsSource` leaving its file open at the end,
  unlocked appends in the scripted model's log, and `\` in paths.

## Open, in order

1. **Lab 1 needs a real-model rehearsal** (see 6 below). Confirm the
   Windows job is green after the 17 Oct fixes; if it is, consider
   making it required rather than advisory.
2. **Model reliability check** (spec §11), before release: every English
   role, old prompt form against new, on a small local model and a
   frontier model; tune the closing sentences; check every example in a
   role against its own `out:`. Needs a key and a small budget.
3. **Release 2.0.0** and **rehearse the install**: wheel into an empty
   virtualenv, then `docs/GETTING_STARTED.md` followed literally, parts 1
   to 8, on a clean machine, with a real key (part 6 has only been run
   against a scripted model).
4. **Thirty students installing at once** has never been tried. Windows
   is the sharp end. Do it before 4 January; what it finds needs a
   release.
5. **Course pages still in version 1:** `lecture_build.html` (`--trace`;
   linked only from `labs.html`; to retire, its three safety sections into
   the Lab 2 plan). Done 18 Oct: `DistributedSystemModel.html` (class 1, in
   2.0, tested) and **class 2 rebuilt as `Contracts.html`** (metadata,
   contracts, refusals and `refused`, barriers, a Python refund guard,
   `dsl check`, evidence, Lab 1 preview without its answer; every quoted file
   and output line tested, the guard office in
   `tests/integration/class2_offices/`). `OfficeRepresentation.html` and its
   notes are in `_to_delete/`; their logistics are on the index ("How this
   course works"). Also `labs.html`, the staff plan, which now says at the top what changed:
   Labs 2–4 need re-planning (no `select`/`match`, no `--trace`,
   `--resume`, `dsl build` in 2.0). `README.pypi.md` should be read
   through before the release, since it becomes the PyPI page.
6. **Lab 1, rehearsed with a real key:** whether the starter is
   vulnerable *enough* to the default model (if Sal resists every attack
   in `attacks.jsonl`, Step 5 teaches nothing), and how often the grader
   misjudges real replies. Ten minutes: `dsl init car_dealer lab1`, try
   Bakke's message in the browser, then Step 5.
7. **Cost guard on generated offices.** `dsl new` is told to prefer a
   file source and small `max_articles`; nothing enforces it. A student
   who leaves a generated office polling a hosted model over a weekend
   finds out.
8. **The next contracts** (after 18 Oct's `in:`/ranges), in order:
   (a) `in:` on sinks: **done for local sinks** (18 Oct, `agents/checked_sink.py`);
   built-in sinks have no front matter, so the acting ones (`gmail_sink`,
   `slack_sink`, `webhook_sink`) still need an `in:` of their own; (b) per-field taint
   in `dsl check`: text from an untrusted source stays tainted until a
   contract bounds it (values or a range), and a note names each tainted
   field that reaches an acting sink; (c) the field-flow checks W21–W31,
   comparing each producer's `out:` with the next role's `in:`. Not yet
   used in the course pages, the skills or Lab 1's reference guard; the
   course team decides where to teach them.
9. **Safety topics and lab ideas (to-do, 18 Oct).** Inside one model,
   for one lecture: prompt hardening and its failure rate, hallucination,
   nondeterminism (safety claims are rates: run an attack N times),
   sycophancy. Between models, the course itself: prompt injection
   (direct and indirect); least privilege; inter-agent trust (every
   model's output is untrusted input); error cascades; correlated errors
   (agreement is not correctness); exfiltration and privacy, including
   what the recorders log; human approval for irreversible actions;
   resource bounds; liveness; supply chain (third-party roles, MCP,
   model drift); auditability; red-teaming. Lab ideas: (a) the
   quarantined reader: the agent that reads the customer reaches the
   booking sink only through bounded fields (the dual-LLM pattern);
   (b) correlated errors: `debate` with one model family against three,
   scored on known answers; (c) the audit: from a run's logs, find the
   agent that introduced an error, then decide what should have been
   logged.

## Not built yet (spec, deferred)

- `dsl try <role> <input>` and `dsl show <role> --prompt` (spec §10).
- The whole-network checks (an unreachable agent, a sink nothing feeds:
  W1–W4, W7, W8) and the field-flow checks (W21–W31).
- `checkpoint`/`restore` for stateful Python roles, `--trace`,
  `--resume` and `--snapshot-interval`: the runtime has them; the 2.0
  build does not wire them, and `dsl run` refuses the flags.
- **Backtesting testers:** the 2.0 `mac_speed_suite` has no
  `explain_strategy.py` (the per-day Excel workbook Vikram uses). Testers
  on 1.x keep it; porting it is open.
- Renaming "office" to "network of agents" (spec §15): last, in one pass.
  If there is time, the same pass renames the role kind `author` to
  `composer` (not "agent", which already names the workers in an office),
  with `kind: author` accepted for one release; and the docs call
  sources, sinks, routers, coordinators and roles "components".

## Two that may not be features

**Deadlock detection beyond stalls.** A structurally correct office can
still deadlock, because whether a message is ever readable can depend on
execution history rather than on the graph. The stall report proves a
stall when it happens; detecting one before it happens is a different
question, and the boundary is itself something the course teaches.

**Processes.** An office in one process is simpler to reason about while
students learn termination detection. Multi-process is the sequel.

## The standing rule

When a document and the code disagree, the fix is not only to correct
the document. It is to ask what would have caught it, and add that. Every
section of `tests/integration/test_docs_match_code.py`, and
`test_getting_started.py`, came from a divergence that shipped or nearly
did.
