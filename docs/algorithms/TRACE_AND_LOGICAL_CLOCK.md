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

## Part 1 — Logical clock (Lamport timestamp)

Mani's rule, as stated: sources timestamp messages starting at 0,
increasing with each message a source emits. Each agent keeps its own
timestamp. On receiving a message with timestamp `t`, an agent sets its own
timestamp to the larger of `t+1` and its current timestamp. An agent
timestamps its outgoing messages with its own current timestamp.

This is Lamport's logical clock algorithm (Lamport, *Time, Clocks, and the
Ordering of Events in a Distributed System*, CACM, 1978) — the same Lamport
as in Chandy-Lamport snapshots, already in the paper via the checkpoint
explainer. One 1978→1985 theoretical throughline under both features.

### Corrected update rule

As stated, the rule is `new_clock = max(t+1, current_clock)`. This only
moves the clock when an incoming timestamp forces it higher — if the
agent's clock is already ≥ `t+1`, a receive leaves it unchanged. Two
different actions by the same agent can then land on the identical
timestamp, which breaks a clean "playback, action by action" (no way to
tell, from the timestamp alone, which of that agent's own two actions came
first).

**Fix — increment on every event, not only when forced:**

```
On receive of a message timestamped t:
    clock := max(clock, t) + 1        # always increments

On any other action that produces an outgoing message
(no incoming message drove it directly — sources; a coordinator
emitting without having just consumed, if that ever occurs):
    clock := clock + 1                # bump first, then tag the outgoing message
```

This guarantees every action at a given agent gets a strictly higher
timestamp than its last action, so one agent's own actions are always
totally ordered by timestamp alone.

### Coordinators with multiple inbound messages

`merge_synch` (and any `Coordinator` subclass whose `_step` combines
messages from more than one inport — see `synchronizer_role`'s dict-merge)
can produce one combined receive-event from several incoming messages.
Generalize: `clock := max(clock, t_1, t_2, ..., t_k) + 1`, taking the max
over all contributing incoming timestamps, not just one.

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
Chandy-Lamport channel-state). If unwrapping happens first, that recording
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

### Design: a decoupled, read-only narration tool

Not a re-execution of the office — the office already ran, and finished, or
you wouldn't have a complete trace to play back. "Running a recorded trace"
means: read the `trace/*.jsonl` files written during a `--trace` run,
merge all agents' entries, order them by `(t, agent_name)` (Part 1's
tie-break), and walk through them one at a time, each rendered in English.

This can be a standalone script/CLI command with no dependency on the live
runtime, the OS agent, or the checkpoint machinery — it only reads JSONL
files and prints/steps through English sentences. Proposed CLI surface,
consistent with existing subcommands: `dsl explain-trace <office_dir>/trace/`.

### English rendering, worked example (recovery_demo)

Using the same office as the checkpoint explainer's worked example
(`dissyslab/gallery/apps/recovery_demo` — five-agent Monte Carlo π
estimator), a few consecutive playback steps might read:

> "[t=41] Alex received a point from the source: (0.31, 0.88)."
> "[t=42] Alex decided the point is inside the circle, and sent that count
> (413) onward to Pi."
> "[t=43] Pi received Alex's count of 413 inside points, combined it with
> Bob's most recent count, and updated its running estimate of π to
> 3.14179."

Exactly the same translation move as the checkpoint explainer and the
office-structure explainer: formal object in, plain English out.

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
