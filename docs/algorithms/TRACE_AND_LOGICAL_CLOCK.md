# Logical clocks, activity-log recording, and trace playback — DRAFT

Design note, not yet coded. Written to be reviewed before implementation
starts. Mirrors the structure of `CHECKPOINT_RESUME.md` since this feature
shares its neighborhood (per-agent, per-message instrumentation) but is a
**separate, independent** capability — see "Relationship to existing
designs" below before assuming any overlap.

## Why this document exists

Mani wants two Pat-facing explainer features, in addition to the checkpoint
explainer already scoped in `PAPER_NOTES.md` (OfficeSpeak repo):

1. **A per-agent activity log** — each agent records, in order, the
   messages it received and the messages it sent. Explained in English:
   "here is the message the accountant received, here is what it sent."
2. **A way to "run" a recorded trace** — merge every agent's log into one
   ordered sequence and step through it, action by action, in English.

Both are instances of the project's general capability: translate a formal
distributed-systems object into English a non-programmer can read, without
ever showing them the formalism. The checkpoint explainer does this for a
snapshot; this does it for a run's message history.

## Relationship to existing designs (read this before building anything)

Two existing internal docs use similar words for a **different** feature.
Do not conflate them.

- **`docs/internals/replay_debug_mode_decision.md`** — "debug mode" is an
  **exact-reproduction** tool for engineers (Al-facing): it logs *every*
  source of nondeterminism (fair_merge's forward order, LLM responses, any
  RNG/clock/external call) so a run can be **replayed bit-for-bit** from a
  checkpoint, for chasing a bug that may not recur. That is a much harder
  problem (it has an explicit "completeness condition" and a known open gap
  — bodies that grab nondeterminism the substrate can't see) and is not
  what this document is about.
- **This document** — a **read-only narration** tool for a non-programmer
  (Pat-facing): record what actually happened in one real run, and explain
  it in English afterward. It does not attempt to reproduce or re-run the
  office. It makes no completeness claim about nondeterminism, because it
  never re-executes anything — it only narrates a log of what already
  happened once.

Consequence: this feature does **not** need to solve fair_merge ordering,
LLM-response logging, or the RNG/clock/external-call problem that debug-mode
replay has to solve. It only needs a faithful record of one real execution,
which is strictly easier.

## User-facing workflow (Mani, 2026-07-21)

The steps a person actually goes through, end to end:

1. **Turn on debug execution from a checkpoint.** The checkpoint could be
   the initial state — i.e. this is the existing `--resume <N>` mechanism
   (or no `--resume` at all, for a fresh run from the initial state),
   combined with the new `--trace` flag from Part 2. Starting a trace run
   from a resume point is already consistent with this document's earlier
   decision that a trace covers one uninterrupted stretch: resuming and
   then tracing just begins a new stretch (a new logical-time segment) at
   the resume point, exactly as already decided.
2. **Stop execution from the command line.** Manual only — Ctrl-C, or
   natural completion. (Already decided in Part 2; restated here as the
   step in the workflow it belongs to.)
3. **Get Claude to explain the trace.** Important clarification: the English
   narration is **not** a hard-coded template-printing script. DisSysLab's
   job stops at producing a faithful, complete, machine-readable record (the
   `trace/*.jsonl` files from Part 2). Turning that record into English for
   Pat is OfficeSpeak's job, done by Claude reading the raw trace and
   narrating it — the same division of labor as everywhere else in this
   project (DisSysLab is the mechanism; OfficeSpeak/Claude is the English
   translation layer), and the same pattern already used for office
   structure, "Things I assumed," and the `debug_demo` walkthrough. See
   Part 3, revised accordingly.
4. **Fix bugs.** Ordinary edit-and-rebuild, informed by what the explanation
   surfaced.
5. **Start a fresh run** — debug/traced or not, as needed — and repeat.

## Part 1 — Logical clock, grounded in physical time (revised 2026-07-21)

**This section replaces the pure-Lamport-counter version below it.** Mani's
revised rule: use the physical clock (`time()`) as the timestamp, corrected
so that every message's receive-timestamp is later than its send-timestamp
— i.e., real wall-clock time as the base, with a Lamport-style correction
layered on top to guarantee causal ordering regardless of clock skew or
timing jitter between agents.

This is (a version of) a **Hybrid Logical Clock** (Kulkarni et al., *Logical
Physical Clocks and Consistent Snapshots in Globally Distributed Databases*,
2014) — physical time for human-meaningful values, Lamport's correction for
distributed-systems correctness. It extends the paper's theoretical
throughline one step further: Lamport 1978 (happened-before) →
global snapshots (1985) → hybrid logical clocks (2014, physical +
logical) all under one roof.

### The rule — one rule, applied identically to every agent

On receiving **one** message timestamped `t`, when the receiving agent's own
clock currently reads `x`:

```
x := max(t, x + 1)
```

Every outgoing message is tagged with the agent's current clock value `x`
at the moment it is sent.

**This is the entire algorithm. There are no special cases:**

- **Sources need no special rule.** A source has no inbox, so it never
  applies the receive-side correction — it simply tags each successive
  message with its own advancing clock, and since physical time only moves
  forward, each successive message from a source already has an increasing
  timestamp.
- **Coordinators with multiple inports (e.g. `merge_synch`) need no special
  rule either.** A `Coordinator` reads one inport at a time via one blocking
  `recv()` per step (see `coordinator_design.md`) — it never receives two
  messages in a single combined event. So `merge_synch` waiting on
  `in_0` then `in_1` just applies the ordinary single-message rule twice, in
  sequence: the first `recv()` (say, timestamp `t_a`) updates the clock to
  `max(t_a, x+1)`; the second `recv()` (timestamp `t_b`) updates *that*
  result to `max(t_b, x'+1)`. The causal dependency on both inputs falls out
  automatically from applying the same rule twice — no separate "max over
  several incoming timestamps" formula is needed. (An earlier draft of this
  document proposed exactly such a special case; it's unnecessary and has
  been removed.)
- **Sends need no special rule.** An outgoing message is simply tagged with
  whatever the agent's clock currently reads — the clock was already updated
  by the most recent receive (or, for a source, by its own last send).

One rule, applied the same way everywhere, covers the whole system.

### Why this specific formula (`max(t, x+1)`, not `max(t+1, x)`)

An earlier draft of this document used `max(t+1, x)` — incrementing the
*incoming* timestamp before comparing. That formula does **not** guarantee
the clock strictly increases: if the agent's own clock is already `≥ t+1`,
a receive leaves it completely unchanged, and two different actions at the
same agent can end up with the identical timestamp (breaking "playback,
action by action" — no way to tell which of that agent's two actions came
first).

Mani's formula, `max(t, x+1)`, increments the *agent's own* clock instead,
and this is always at least `x+1` — strictly greater than `x`, unconditionally,
on every single receive. It also has a nicer property for a *physical*
clock specifically: it only advances as far as necessary (either to `t`, if
the incoming message is from further ahead in time, or to `x+1`, the
minimum needed to stay strictly increasing) — so the clock tracks true wall
time closely rather than drifting arbitrarily ahead the way an
always-add-1 rule would over a long-running office.

**A nice side effect worth noting:** this same correction also protects
against a physical clock that occasionally reads backwards (e.g. an NTP
time adjustment) — even if the raw reading dips, `max(t, x+1)` guarantees
each agent's own sequence of timestamps never decreases. Worth deciding,
but not blocking: whether the underlying physical reading should be
`time.time_ns()` (real epoch time, human-meaningful, occasionally
non-monotonic on its own) or `time.monotonic_ns()` (guaranteed monotonic,
but not anchored to a real time-of-day Pat could read). Given the goal is
showing Pat something that looks like real time, `time.time_ns()` plus this
correction is probably the right choice — flagging for confirmation, not
deciding unilaterally.

### Truncation is a display concern only, not an arithmetic one

Physical timestamps (nanoseconds or milliseconds since epoch) are long
numbers — too long to show Pat directly. Keep full precision for every
stored clock value and every `max(...)` comparison; truncate only at the
final step, when rendering a timestamp for a human to read (e.g. show
`14:32:07.114` instead of the raw epoch integer). If the *stored* value
itself were truncated to something coarse (say, whole seconds) rather than
just its on-screen rendering, the collision risk the correction rule is
built to avoid comes right back — two messages a few milliseconds apart
could round to the identical displayed second, and then it's genuinely
ambiguous which happened first. Precision internally, brevity only on the
page.

### [Superseded] Coordinators with multiple inbound messages

*(Kept for the record, since a decision log should show what changed —
resolved above: no special case is needed. A `Coordinator` never actually
receives multiple messages in one combined event; it reads one inport at a
time, so the single-message rule already composes correctly across
sequential reads.)*

### Total order needs a tie-break

Lamport timestamps give a partial order consistent with causality
(happened-before ⇒ smaller timestamp) — not a full total order. Two
actions at *different* agents can legitimately land on the same timestamp
if neither caused the other. To render one linear playback, sort by
`(timestamp, agent_name)` (agent_name as an arbitrary but fixed
tie-break — any fixed rule works, e.g. lexicographic on the agent's
flattened name).

**Say this precisely in the paper:** the playback shown to Pat is *a*
valid causally-consistent linearization of what happened, not *the* one
true real-time order — real-time order isn't a well-defined concept for an
asynchronous system without synchronized clocks. Being honest with a
non-programmer about exactly what ordering guarantee she's looking at is a
correct and worthwhile thing to say explicitly, not just an implementation
footnote.

**Found during implementation (2026-07-22): plain `(timestamp,
agent_name)` isn't quite enough — a send and its own matching receive
can tie.** The clock rule `x := max(t, x+1)` guarantees each *agent's
own* sequence strictly increases, but makes no such promise between a
sent message's timestamp and the timestamp its receiver assigns to
receiving it: whenever the receiver's clock was already behind the
sender's (the common case for a physical-time-grounded clock, since
most agents are idle most of the time relative to nanosecond
resolution), `max(t, x+1)` reduces to exactly `t` — the receive gets
the *identical* timestamp as the send. Verified against a real
`--trace` run of `recovery_demo`: roughly a third of all timestamps
were exactly this kind of send/receive tie. Plain `agent_name` as the
tie-break has no reason to sort a "sent" action before the "received"
action for the very same message — it depends entirely on which
agent's name happens to sort first alphabetically, which is exactly
backwards about a third of the time. `dsl explain-trace` now breaks
ties by `(timestamp, sent-before-received, agent_name)` — sent sorts
before received when timestamps tie, which is correct for the common
case (a message's own send/receive pair) and remains an arbitrary but
harmless fixed choice for the rarer case of two truly unrelated
actions that happen to tie. This is a display-ordering fix only —
it does not change the clock algorithm in Part 1, which is unmodified.

## Part 2 — Recording the per-agent activity log

### What gets captured, per action

For every send: `(agent_name, direction="sent", outport, timestamp,
message_summary)`.
For every receive: `(agent_name, direction="received", inport, timestamp,
message_summary)`.

`message_summary` is whatever a short, safe, human-readable rendering of
the message is (str() of a small dict, or a truncation policy for large
payloads — needs a decision, see Open Questions).

### Where the timestamp has to live in transit

The receiving agent's clock update needs to see the *sender's* timestamp
at the moment the message was sent — so the timestamp must travel with the
message on the wire, not be reconstructed after the fact.

Recommend a small internal wrapper, in the same spirit as `_OsMessage`
subclasses (`_Checkpoint`, `_GiveMeCounts`) but on the **data plane**, not
the control plane:

```python
class _Timestamped:
    __slots__ = ("payload", "clock")
    def __init__(self, payload, clock):
        self.payload = payload
        self.clock = clock
```

`send()` wraps the client's message in `_Timestamped(msg, self._clock)`
before `q.put(...)` — invisible to the client, which still calls
`self.send(msg, outport)` exactly as today. `recv()` unwraps it
**immediately after `q.get()`** (or after the recovery-buffer pop), updates
`self._clock` from the unwrapped `.clock` value, appends the activity-log
entry, and returns only `.payload` to the client — exactly mirroring how
`_Checkpoint`/`_GiveMeCounts` are intercepted before the "client data
message" branch today (`core.py` `recv()`, the `else:` branch around line
495).

**This must happen before existing channel-state recording sees the
message.** `recv()` already copies in-flight messages into
`self._recording["channels"][inport]` during a checkpoint (for
global-snapshot channel-state). If unwrapping happens first, that recording
path is unaffected — it keeps storing plain payloads exactly as it does
today, no change needed there. Get this ordering right and the two features
don't interact at all.

### Interaction with checkpoint/resume — recommend scoping it out for v1

If an office resumes from a snapshot, messages replayed from the recovery
buffer are plain payloads (per the above, channel-state recording already
strips the wrapper). Those replayed messages would arrive with no logical
timestamp, since the wrapper was only used in-flight, once. Two options:
(a) re-timestamp on replay as if newly arriving (simplest — the trace
before a resume and the trace after are two separate logical-time
segments, joined at the resume point), or (b) persist the timestamp into
the snapshot's channel state too, so logical time is continuous across a
resume (more correct, more work, touches the checkpoint format that's only
six days stable).

**Decided (2026-07-21): (a).** Logical-time continuity is scoped to a
single uninterrupted run. The checkpoint/recovery format is not touched.
This keeps the activity log fully decoupled from the snapshot machinery
that was just stabilized, at the cost of trace continuity across a
crash-and-resume — an acceptable v1 limitation, and one line to state
honestly in the paper if it comes up.

### On-disk format

Mirror `snapshot.py`'s layout style: one append-only log file per agent,
under the office's run directory, e.g.:

```
<run_dir>/trace/<agent_name>.jsonl
```

One JSON line per action: `{"t": <int>, "dir": "sent"|"received", "port":
<str>, "msg": <summary>}`. JSONL (not pickle) so the log is human-readable
and diffable, and so the playback tool (Part 3) doesn't need to import
DisSysLab internals to read it.

**`message_summary` truncation policy (decided):** render the message as
`str()`/`repr()` and cut it off at a fixed character cutoff (300 chars is a
reasonable default), appending `"... (truncated, N more chars)"` when cut.
Simple, no per-worker configuration needed for v1.

**LLM prompts (decided): not logged.** A worker's prompt is part of its own
definition and is already visible in that worker's file under `roles/` —
duplicating it into the trace log would bloat every entry from an LLM
worker for no benefit. The log and the playback narrate the worker's
*input and output messages only* — what it received and what it sent —
never the prompt that produced the output. This applies uniformly to
computational and LLM workers, exactly as intended.

### Opt-in, off by default, manually started and stopped

Logging every send/receive has a real cost (a disk write per message).
Follow the existing pattern of `--snapshot-interval` being opt-in: add a
`--trace` flag to `dsl run` (alongside `--processes`, `--snapshot-interval`,
`--resume` in `cli.py`'s `p_run` parser). Normal runs pay zero overhead,
exactly the "normal mode: nothing extra logged, cheap" principle already
established for debug-mode replay, applied here for the same reason.

**Stopping (decided): manual only, from the terminal** — the same way any
`dsl run` is stopped today (Ctrl-C, or natural termination-detection
completion for an office that finishes on its own; see `recovery_demo`'s
own instructions, which already use "press Ctrl-C" as the way to end a
run). No automatic stop condition (e.g. "stop after an agent has taken more
than N actions") is being built — that adds real complexity (per-agent
counters, a policy for what counts as "an action," a decision on what
happens to the office when tracing stops but the office doesn't) for
unclear benefit over just letting the person doing the tracing decide when
they have enough and hit Ctrl-C.

### Retention (decided): none needed

Unlike periodic checkpoints — which accumulate every `--snapshot-interval`
seconds for the life of a long-running office and need a keep-N policy —
trace files are one append-only log per agent for the span of a single
`--trace` run. There's no equivalent accumulation problem, so no retention
policy is needed; the person doing the tracing can delete old trace
directories by hand if they want to.

## Part 3 — Running (playing back) a recorded trace

### Design: DisSysLab produces the record; Claude produces the English

Not a re-execution of the office — the office already ran, and finished, or
you wouldn't have a complete trace to play back. "Running a recorded trace"
splits into two genuinely separate jobs, on two sides of the DisSysLab /
OfficeSpeak boundary:

- **DisSysLab's job** (mechanical, deterministic, no LLM involved): read the
  `trace/*.jsonl` files written during a `--trace` run, merge every agent's
  entries, and order them by `(t, agent_name)` (Part 1's tie-break) into one
  linear sequence. This can be a small standalone tool with no dependency on
  the live runtime, the OS agent, or the checkpoint machinery — it only
  reads JSONL and produces one ordered, still-structured sequence of
  actions. Proposed CLI surface, consistent with existing subcommands: `dsl
  explain-trace <office_dir>/trace/` — though note per the point below, this
  command's own job is to hand the ordered structured trace to Claude, not
  to print English itself.
- **OfficeSpeak's job** (Claude reads the ordered structured trace and
  narrates it): turning "agent Alex received `(0.31, 0.88)` on inport `in_`
  at t=41" into the kind of sentence Pat can read is exactly the same
  translation move already used for office structure, "Things I assumed,"
  and the `debug_demo` walkthrough — done by Claude, not by a fixed template
  string. This means the explanation can adapt (more or less detail, answer
  a follow-up question about one specific step, connect an action back to
  the worker's plain-English job description) the way every other
  OfficeSpeak explanation already does, rather than being frozen into
  whatever a template author anticipated.

### English rendering, worked example (recovery_demo)

Using the same office as the checkpoint explainer's worked example
(`dissyslab/gallery/apps/recovery_demo` — five-agent Monte Carlo π
estimator), a few consecutive narrated steps might read (illustrative — the
actual wording is Claude's, generated fresh from the structured trace, not
a fixed string):

> "[t=41] Alex received a point from the source: (0.31, 0.88)."
> "[t=42] Alex decided the point is inside the circle, and sent that count
> (413) onward to Pi."
> "[t=43] Pi received Alex's count of 413 inside points, combined it with
> Bob's most recent count, and updated its running estimate of π to
> 3.14179."

Exactly the same translation move as the checkpoint explainer and the
office-structure explainer: formal object in, plain English out — except
here the "formal object" is an ordered log rather than a single structure or
a single snapshot.

### Why this is safe to build

Purely additive and read-only: no change to any agent's decision logic, no
new control messages, no interaction with termination detection, and (per
Part 2) explicitly decoupled from checkpoint/recovery. The riskiest part of
this whole feature is the `send()`/`recv()` wrapper in Part 2; the playback
tool itself is just a file reader with a merge-sort and a template.

## Status of open questions

All four questions originally raised here were resolved by Mani on
2026-07-21 and are now folded into Parts 1–3 above: logical time does not
survive a checkpoint/resume (v1); messages are truncated at a fixed
character cutoff; LLM prompts are not logged or narrated (they're already
visible in `roles/`); tracing starts and stops manually via the terminal,
with no automatic stop condition.

One question remains open, not yet decided:

1. **Where "explain a trace" sits relative to the two debugging aids
   already scoped** (`debugging_aids_decision.md`: (a) isolated worker
   testing on synthetic inputs, built; (b) channel-count liveness check,
   scoped, not built). This is closest to a "(c)": narrate a real run's
   actual messages, works for both computational and LLM workers (aid (a)
   is computational-only). Worth naming and cross-referencing once built,
   so the three aids read as one coherent family in both the code and the
   paper.

## Decision log

- 2026-07-21 — Mani confirmed the v1 scoping recommendation: logical time
  does not need to survive a checkpoint/resume.
- 2026-07-21 — Mani: truncate large messages with a fixed cutoff.
- 2026-07-21 — Mani: LLM prompts don't need to be logged; they're already
  visible in `roles/`.
- 2026-07-21 — Mani: tracing must be turned on by the user and stopped from
  the terminal; an automatic stop condition (e.g. after N actions by an
  agent) was considered and rejected as unneeded complexity.
- 2026-07-21 — Mani: no reason for trace-file retention policy.
- 2026-07-21 (later same day) — Mani replaced the pure Lamport-counter clock
  with a physical-time-grounded hybrid clock: `x := max(t, x+1)` on every
  single-message receive, one uniform rule for every agent (sources,
  transforms, sinks, and multi-inport coordinators alike — no special
  cases). Removed the earlier "coordinators with multiple inbound messages"
  generalization as unnecessary. Clarified the workflow (turn on tracing
  from a checkpoint or the initial state; stop manually; Claude explains
  the trace; fix bugs; start fresh) and that the English narration in Part 3
  is produced by Claude reading the structured trace, not a fixed template
  — DisSysLab produces the record, OfficeSpeak/Claude produces the English,
  same division of labor as the rest of the project.
- 2026-07-22 — Implemented: `_Timestamped` wrapper and clock/trace hooks in
  `core.py`, `trace_dir` propagation in `network.py`, `--trace` flag and
  `DSL_TRACE` env var in `cli.py`/`codegen.py`, and `dsl explain-trace` to
  merge and sort the per-agent JSONL files. Verified against a real
  `--trace` run of `recovery_demo` (copied out of the repo to avoid
  touching its tracked snapshot fixtures): every agent's own clock is
  strictly monotonically increasing, as designed; a normal (non-`--trace`)
  run is behaviorally unchanged. Found and fixed one real issue during this
  verification — see "Total order needs a tie-break" above for the
  send/receive tie-break refinement. Also found and fixed a latent
  cross-platform bug before it could ship: agent names contain `::`, which
  is invalid in Windows filenames, so trace files now go through
  `snapshot.py`'s existing `safe_filename` sanitizer (`::` → `__`), the
  same convention already used for checkpoint files, instead of using
  `self.name` raw. Full pytest suite could not be run in this sandbox (no
  network access to install pytest or the runtime's third-party
  dependencies) — real end-to-end verification was done instead by
  building and running a live office with stub modules standing in for
  the unavailable dependencies (anthropic, requests, feedparser), none of
  which `recovery_demo`'s actual code path touches.
- 2026-07-22 (later same day) — Mani ran the real pytest suite on his own
  machine (`.venv`, not this sandbox): all tests pass. Regression-tested,
  closing the one open item from the entry above.
- 2026-07-22 (later still) — Built the checkpoint-explainer counterpart:
  `dsl show-checkpoint <office_dir> <N|latest>`, mirroring `dsl
  explain-trace`'s division of labor for a snapshot instead of a run. See
  `docs/algorithms/CHECKPOINT_RESUME.md`'s new "Showing a checkpoint's
  contents (v1.7)" section for the design and verification notes. Also
  wrote OfficeSpeak's `DEBUG_TRACE_AND_CHECKPOINT_WALKTHROUGH.md` — a
  Pat-facing, extreme-step-by-step teaching document covering both this
  trace feature and the new checkpoint explainer, using `recovery_demo`.
  Every command and every JSON/JSONL excerpt in that document was run for
  real and copy-pasted from actual output, not hand-typed — including
  catching and fixing one drafting mistake (a wrong π arithmetic check,
  and an example that had spliced two different checkpoints' data
  together) before publishing it.
