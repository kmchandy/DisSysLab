# Decision: first-line debugging aids for Pat (2026-07-12)

Recorded for later. Not designed or coded yet. Two aids, one per bug class; both
work on a **normal run** (no debug-mode replay needed), so they are the right
things to build before the first pilot. Concerns both DisSysLab (instrumentation)
and OfficeSpeak (the Pat-facing explanation).

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

(a) is the **content** check (is each computational worker doing its job?); (b) is
the **liveness / wiring** check (is every message getting where it needs to go, or
is someone waiting forever?). Together they mirror the paper's "two layers, one
seam."

## Worked example built (2026-07-12)

`OfficeSpeak/offices/debug_demo/` — a determinate, pure-Python office (`temp_watch`)
with a planted body bug in a computational worker (`Alerter` compares the raw
reading instead of the rise above baseline → floods with alerts). `per_agent_tests.py`
isolates each worker and localizes the bug (Baseline fine, Alerter wrong);
`debugging_walkthrough.md` is the Pat-facing story. Verified: buggy = 10 alerts,
fixed = 1. This is aid (a) end to end; aid (b) (channel counts) is still to build.
