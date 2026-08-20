# Decision: first-line debugging aids for Pat (2026-07-12)

Recorded for later. Three aids, one per bug class. Aids (a) and (b) work on a
**normal run** (no debug-mode replay needed). Aid (c), added 2026-07-21, works
on a **`--trace` run** (opt-in, see below) and is designed but not yet built.
Concerns both DisSysLab (instrumentation) and OfficeSpeak (the Pat-facing
explanation).

## (a) Test each agent by itself — catches *agent-specification / body* bugs

Isolating a worker removes concurrency from the picture: check whether one worker
does its job on fixed inputs, with no timing and no full office running. These are
the bulk of real bugs (a worker computing or deciding wrongly), and they are
deterministic given inputs.

- Claude-driven: propose representative inputs (including edge cases Pat wouldn't
  think of — empty, extreme, malformed), run the body, show input → (memory) →
  output, Pat reacts.
- Oracle: checkable output for computational workers; behavioral / Pat-judged for
  LLM-judgment workers ("sensible across these cases", not exact match).
- Stateful workers must be tested as a **sequence** so the memory trajectory is
  visible (as in the weather weight-trajectory view).
- Validates a body against its **contract**, not the contract against intent
  (that's wiring — aid (b)). Doubles as a regression test when a body is refined.

## (b) Channel counts — catches *wiring / liveness* bugs

`sent` / `received` per port are already collected for termination detection. A
channel whose backlog grows without bound is the visible signature of a receiver
stuck waiting on it.

- The starvation risk is concentrated at **Coordinator** destinations, which read
  a *chosen* inport (merge_synch waiting for `in_1`; gate waiting for `done`;
  select waiting on the inport its state points to). A Transform or Sink always
  consumes, so it cannot starve a channel.
- **Localizes, does not explain** — the counts say *which* channel is stuck; the
  receiver's coordination state / tape says *why*. Chains with (a).
- Need the **trend**, not a snapshot — a Coordinator waits on one inport at a time
  by design, so a momentary imbalance is normal; the bug signal is an imbalance
  that never resolves (received stops advancing while sent climbs).
- Ties to machinery we have: termination detection fires when every channel is
  drained, so a should-terminate office that hangs has undrained channels at
  exactly the stuck edges; a checkpoint already captures per-inport in-flight
  messages.
- fair_merge never leaves a nonempty channel unread, so the aim is the
  deterministic Coordinators — which is where it's placed.
- Accounting nuance for later: `sent` is per *outport*; a broadcast outport feeds
  several channels, so faithful *per-channel* backlog needs per-channel counters,
  not just per-port. The raw material exists; the granularity needs a look.

## (c) Show the real run — catches nothing new by itself, but shows what actually happened

Aids (a) and (b) both work on **synthetic** cases: (a) hand-picked inputs fed
to one isolated worker, (b) aggregate counts. Neither shows Pat an actual
worker doing its actual job on the actual messages that flowed during a real
run. Aid (c) is that: a per-agent log of the real messages each worker sent
and received, timestamped with a Lamport logical clock so every agent's log
can be merged into one ordered, cross-agent playback and narrated action by
action in English — "here is the message the accountant received, here is
what it sent."

- Full design: `docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md`.
- Opt-in and off by default (`--trace` on `dsl run`), same "normal mode is
  cheap" principle as debug-mode replay — but **not the same feature as
  debug-mode replay** (`replay_debug_mode_decision.md`). Aid (c) never
  re-executes anything; it only narrates one run that already happened, so
  it doesn't need that feature's harder completeness condition over
  nondeterminism.
- Works uniformly for **both** computational and LLM workers, unlike aid
  (a) — it's descriptive (what happened), not evaluative (was it right),
  so the LLM-judgment restriction below doesn't apply to it.

## Scope: computational workers only; LLM workers are prompt-only

Aid (a) applies to **computational** workers (Python bodies) — their behaviour is a
fixed, deterministic function, so a test is trustworthy and a bug is checkable and
localizable. For **LLM / judgment workers we do not test, evaluate, explain, or
debug** — their judgment isn't a fixed function and can't be graded the way a Python
body can. Instead OfficeSpeak **shows Pat the prompt and asks "Is this what you
mean?"**, and may show a few example inputs and the model's outputs — for Pat to
read, not for the system to score. Correctness of an LLM worker is whether its
prompt captures Pat's intent, which is Pat's call. This keeps the debugging story
honest and bounds it to where checking is meaningful.

## Mapping

(a) is the **content** check (is each computational worker doing its job, on
cases it didn't actually see?); (b) is the **liveness / wiring** check (is
every message getting where it needs to go, or is someone waiting forever?);
(c) is the **real-execution narration** (what did each worker actually do, on
the messages that actually flowed, in the order they actually happened?).
None of the three requires debug-mode replay. Together they mirror the
paper's "two layers, one seam" plus a third, orthogonal axis: synthetic vs.
real data.

## Worked example built (2026-07-12)

`OfficeSpeak/offices/debug_demo/` — a determinate, pure-Python office (`temp_watch`)
with a planted body bug in a computational worker (`Alerter` compares the raw
reading instead of the rise above baseline → floods with alerts). `per_agent_tests.py`
isolates each worker and localizes the bug (Baseline fine, Alerter wrong);
`debugging_walkthrough.md` is the Pat-facing story. Verified: buggy = 10 alerts,
fixed = 1. This is aid (a) end to end.

## Status

- **(a)** built and verified (`debug_demo`, above).
- **(b)** **decided not to pursue (2026-07-23).** The reasoning: "nothing
  moving" on a channel is not, by itself, a reliable bug signal — a
  Coordinator blocked on one inbox by design (merge_synch waiting for a
  slot, gate waiting for `done`) looks identical, from sent/received
  counts alone, to a Coordinator that's genuinely stuck. Turning that into
  a trustworthy diagnostic needs more context (expected wait patterns,
  or a human judgment call) than the raw counts give for free, and isn't
  worth building until a real case makes the ambiguity concrete. We're
  living with the gap: today, "why is nothing moving" is answered
  after the fact via aid (c) (`dsl explain-trace` / `dsl show-checkpoint`),
  not by a live stuck-office diagnostic.
- **(c)** built and verified (2026-07-22): `dsl run --trace` records it,
  `dsl explain-trace` merges/sorts it, Claude narrates it. See
  `docs/algorithms/TRACE_AND_LOGICAL_CLOCK.md` for the design and
  implementation/verification notes.
