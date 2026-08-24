# Where the project is — 2026-08-23

One page. What is true now, what is open, and in what order.
Everything dated and finished lives in [archive/](../../archive/);
this file is the only status document that is kept current, and it is
deliberately the only one. A separate plan would be a second thing to
keep true.

If you are picking the project up cold, read this, then
[reference/architecture.md](reference/architecture.md), then the
overview half of whichever module you are about to change.

---

## The measure of success

> A first-year builds an app they care about, then studies the
> algorithms underneath it.

**The course runs 4 January – 10 March 2027 — 19 weeks away.**
Everything below is prioritised against that sentence: a change that
makes a first-year's first hour work beats a change that makes the
framework more general.

Three tracks, on different clocks.

| Track | Clock | Why |
|---|---|---|
| **Backtesting** (Vikram, Sebu) | now, no deadline | Live testers. Decays if left, and it is the only outside evidence the thesis works. |
| **Conversational offices** | 4 January | This *is* the pedagogy. |
| **Processes, deadlock detection** | after January | See "Two that may not be features". |

---

## 1. Course-blocking. Do first.

**Fix the timed-out office that cannot be shut down.**
`run_network(timeout=T)` raises `TimeoutError`, but nothing tells the
agents to stop — `os_agent` sends `_Shutdown` only when it declares
termination, and the timeout path does not. Agent threads are
`daemon=False`, so they park in `recv` and the process cannot exit.
A student meets this in the first hour and concludes Ctrl-C is broken.
Small fix, changes `Network.run` for every caller. See the note at the
foot of `tests/unit/test_alarm.py`.

**Release 1.7.2 — and ship the skill with it.** The repository is
ahead of the wheel by W5 (nearest-spelling suggestion for an unknown
source or sink — a typo currently reads to a student as a missing
feature), the yfinance change, error counting in the run summary, and
`dsl draw`. **The skill and the wheel are now coupled**: `office-builder`
teaches `inboxes=`, which needs the alias in `office_spec.py`. A student
on PyPI 1.7.2 with the current skill gets a mismatch.

**`dsl draw` is unreachable until the skill knows about it.** A user
who says *"draw the network"* gets it only if the assistant knows the
subcommand exists. Teaching the skill before the release ships would
point students on PyPI 1.7.2 at a command they do not have — the same
coupling as `inboxes=`, and the second instance of it. Both clear
together.

**Thirty students installing at once has never been tested.** One
unresolved install failure costs a class hour, thirty times. Windows
is the sharp end: CI runs it, and the checkpoint/resume tests fail
there. Do this early — what it finds needs a release to fix.

**Verify the cost guard on a *generated* office.** "Every shipped
office stops after a few cycles by default" is asserted. Is it true of
an office Cowork writes? A student who leaves one polling a hosted
model over a weekend finds out. A claim with a bill attached.

**Course materials.** The algorithm sequence and what is taught when.

## 2. The pedagogy. Weeks 5–10.

**Conversational office construction — the draft office is built.**
`Jay is unassigned.` parses as undecided, an office holding one is a
draft, `dsl check` reports remaining work and exits 0, and `dsl run`
refuses by naming the agents whose job is not decided. Two new
findings: G1 *"has no job yet"* and G2 *"nothing leaves this office"*.
What is left is the assistant's half — the turn protocol, and the
skill. See building_by_conversation.md §3–§4 (built) and §5, §7 (not).

**Found while building it: the grammar is not as strict as we say it
is.** The README argues that the narrow grammar is what lets
`dsl check` catch what a language model got wrong. But an agent line
that matches nothing falls through to a legacy `name is <path>` form,
so `Jay is deduplicator.` — the exact line the strictness is supposed
to reject — silently becomes a sub-office in `./deduplicator`, and
`dsl check` says nothing about it. It surfaces at compile time as a
missing office. Tightening the fallback is its own change with an
unknown blast radius on offices that use the legacy form; recorded in
`tests/unit/test_draft_office.py` where the assertion had to be
weakened to match.

**Conversational office construction, the rest.** Storyboard first,
then design, then build. The storyboard is
[storyboard_first_office.md](design/storyboard_first_office.md) — one
first-year, fourteen panels, ending in the question that opens the
algorithms half of the course. Its §12 costs every panel and is the
current work list. Design so far in
[building_by_conversation.md](design/building_by_conversation.md): the
`unassigned` placeholder, automatic draft mode, the gap list, the turn
protocol. Not implemented, deliberately.

**Four things the storyboard found that no design covers.** A way to
list library roles with one line each on what they *emit* — there is
no registry, no `dsl roles`, and no summary line, so an assistant
paraphrases the prompt files afresh every time and no two students are
told the same thing. A protocol for teaching turns (*"what is a
source?"* asked mid-build) as distinct from building turns. What to
call a role invented for one agent, since `Dan is a dan.` is what the
grammar produces today. And an answer to *"undo that"*, which will be
said in the first ten minutes and which putting `office.md` under
version control would give for free.

**A behavioural eval for the skill.** `test_docs_match_code.py` checks
that the documentation agrees with the code. **Nothing checks that the
skill, given "watch two feeds and email me a summary", produces an
office that runs.** The skill is the primary interface and the least
tested thing here. The `skill-creator` skill supports evals; this is
what they are for.

**A fixture or replay mode.** Stooq took out three stock sources with
no warning. If a student's source dies in week six their project dies.
Running an office from recorded data is insurance, and it is also what
makes offices testable offline.

**`sensor-office-builder` has no `references/`**, where
`office-builder` has four (E3).

**Assessment.** Thirty offices, someone reads them. `dsl check` gives
structure; nothing summarises an office for a marker.

## 3. Backtesting, in parallel

Vikram's own words for how he wants to work: **English and Excel.**
Not diagrams, not Kakushadze notation, though he reads the latter.

- **Phase 1 — the trace. Done, 23 Aug.**
  `mac_speed_suite/explain_strategy.py` writes a workbook: one row per
  day, every intermediate, the same quantity again as a live Excel
  formula, a match column, and a sentence saying which rule fired.
  Donchian and MAC; Turtle and RS still to do. It cannot silently
  disagree with the role it explains — the intermediates are checked
  against the real signal, and a mismatch writes nothing.
- **Phase 2 — corrections.** He edits the sheet or says what is wrong;
  Claude keeps prose and formulas consistent. One document, two ways
  to change it.
- **Phase 3 — Excel to Python.** Only if Phase 1 shows the sheet is
  the right instrument.

Design in [signal_notation.md](design/signal_notation.md). Open: whether
Excel is the specification or only the review surface.

**Two requests from Vikram, 23 Aug.**

*Control what is shown* — "show top 10 for a set of strategies". The
trace already takes `--strategy`, `--variant`, `--ticker`, `--bars`,
`--rows`. A ranked summary is a different thing: that is
`report.html`'s job made askable, and belongs in its own change.

*Turtle-style risk management* — ATR, position size by inverse
volatility, weights, a stop. **Half of this is expressible today and
half is not, and the difference matters.** `_backtester_core` computes
`gross = prior_signal * today_return`, so the signal is a position
*fraction*: per-instrument inverse-volatility sizing can be written as
a signal in [-1, 1] and it will backtest correctly. But signals are
computed per ticker with no shared state, so anything portfolio-level
— total risk across positions, unit caps across correlated markets,
sizing against current account equity — **cannot be expressed at all**.

An assistant asked for "Turtle risk management" will produce plausible
per-instrument code and call it Turtle. The gap is invisible in the
output. The skill needs to state the signal contract and say when a
request needs portfolio state the office does not have.

## 4. Debt, after January

**Processes, steps 3–5** — `Channel`/`PipeChannel`, boundary agents,
the cut and flatten, the network detector. Design in
[process_per_office_design.md](design/process_per_office_design.md) and
[termination_detection_design.md](design/termination_detection_design.md)
§5.4–§5.5.

**The identifier rename.** `inport`→`inbox` stopped at the
user-facing surface. 540 Python identifiers, the public
`Agent(inports=…)` keyword and the `open_inports` snapshot key still
need a deprecation path — renaming that key stops existing
checkpoints resuming.

**Source aliasing** — `bbc_world as Vikram`. Needed before *"make
Vikram a source"* can be written. Parser, spec, `check_wiring`,
codegen.

**Renames that are pure debt.** `office/utils.py` →
`office/registry.py` (16 import sites); `start_gallery/` → `chat/`;
the `OfficeSpeakSpec` / `from_officespeak.py` internals, the last
place the retired word survives.

**Smaller:** D1's tier-2 hang (undiagnosed, days); W2 and role shapes
(E2); the tier-3 instrument (D2/D4); the `\b` vocabulary bug that will
bite on possessives (E7); moving the three `skill_for_testers/`
bundles once the 25 August gate passes (E4); a `docs/apps/` page per
ready-made application, backtesting first, drug discovery later.

## Two that may not be features

**Deadlock detection.** The README already teaches its absence: a
structurally correct office can still deadlock, *"because whether a
message is ever readable can depend on execution history rather than
on the graph — that boundary is itself one of the ideas the course
teaches."* Building the detector removes the teaching moment.

**Processes.** An office in one process is a simpler system to reason
about while students are learning termination detection.
Multi-process is the interesting sequel, not the prerequisite.

If both hold, the two named leftovers move behind January and the
course does not suffer.

## Recently closed

- **Stooq is gone.** yfinance only, an optional `[market]` extra, each
  user fetching their own. Nothing here ships market data.
- **Termination detection has an explicit idleness bit.** The old
  predicate worked only because every agent was reactive; alarms are
  the first that can answer a poll while owing a send.
- **The vocabulary pass.** "OfficeSpeak" named nothing a reader could
  point at. Four nameable parts now.
- **Two renames.** *org chart* → network/graph; *inport/outport* →
  inbox/outbox on every user-facing surface, with `inboxes=`
  normalised in `RoleRef.__post_init__` so old offices still compile.
- **157 code-in-link labels unwrapped** — unreadable in some viewers.
- **The documentation is testable.** `test_docs_match_code.py` now
  also checks every relative link and `<img src>`, retired vocabulary,
  and link-label style.
- **`dsl draw`, and the §F it closed.** README said *"the diagram is
  generated from the office's `office.md`"* for months; nothing could
  generate a diagram, and the block had been drawn by hand and copied
  into three documents. Now it is generated, and §9 of
  `test_docs_match_code.py` asserts that any documented diagram equals
  what the generator produces from the office printed beside it.
  Deliberately **on request** rather than after every edit: a diagram
  redrawn on each change has to be stable under change, or adding an
  agent moves the ones the reader had already understood, and laying
  out a graph under that constraint is a real problem. Asked for once,
  it has no such obligation — which is the whole reason the module is
  150 lines. It draws an office that does not compile, too, since that
  is when a picture is worth most.

## The standing rule

When a document and the code disagree, the fix is not only to correct
the document. It is to ask what would have caught it, and add that.
Every section of `test_docs_match_code.py` came from a divergence that
shipped.
