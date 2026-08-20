# Decision: two run modes — normal vs debug replay (2026-07-12)

A design decision, recorded for later. Not designed or coded yet.

## The decision

Logging every nondeterministic choice is too expensive to do always. So an office
runs in one of two modes:

- **Normal mode** — nothing extra is logged. Cheap. **Not replayable.**
- **Debug mode** — started **from a checkpoint**; every nondeterministic choice is
  logged. The recorded stretch can be **replayed exactly**, as many times as
  wanted, from that checkpoint.

Pat runs normally in production and switches to debug mode from a checkpoint when
she wants a replayable trace.

## What "replay exactly" requires (completeness condition)

Debug mode must capture *every* source of nondeterminism, or replay silently
diverges. The full list for an office:

- **fair_merge forward order** — which inport each forwarded message came from, in
  sequence (the only nondeterministic coordination primitive).
- **each LLM response** (worker bodies that call a model).
- **any RNG seed, clock read, or external call** a worker body makes.

Replay = start from the checkpoint's consistent state cut, re-feed the logged
source inputs, and inject the logged choices at the points they are consumed.

## The key limitation: record-on-demand captures the *future*, not the *past*

A bug that already happened in a normal-mode run **cannot** be replayed after the
fact — its choices were never written down. Workflow: see the problem in normal
mode → restart in debug mode from the checkpoint just before it → *if it recurs*,
replay that trace exactly.

- **Deterministic bugs** (same inputs → same wrong answer: a logic error, an
  analyst reasoning badly, the accountant ignoring holdings) recur every time —
  airtight.
- **Genuinely nondeterministic bugs** (a race via a particular fair_merge
  interleaving, an LLM that misbehaves on one sampling) may not recur in the debug
  run, and logging can perturb the timing that caused them (probe effect). This is
  the intrinsic limit of record-on-demand, not a flaw in the design — but it is
  the sentence Pat must hear.

## Why this is tractable here (bounded nondeterminism)

Because coordination is trusted library code, the substrate **knows exactly where
nondeterminism can enter**: fair_merge, plus whatever bodies pull in (LLM, RNG,
clock, external I/O). The log points are enumerable — the first two funnel through
the substrate (fair_merge is library code; LLM calls go through the backend). The
open risk is **bodies that grab nondeterminism the substrate can't see** (a body
calling `time.time()` or `random` directly); exact replay requires those to route
through substrate-provided, logged channels. Closing that set is the real design
work later.

## Corollary

- A **determinate** office (no fair_merge, deterministic bodies) needs no debug
  mode: resume-from-checkpoint already replays exactly, because there is nothing
  nondeterministic to log.
- **Paper fix:** state deterministic replay as a **debug-mode capability available
  on demand from a checkpoint**, not as an always-on property. That is both true
  and a cleaner story than the current `draft_v2` §2 / contribution #3 wording,
  which overclaims (it says the runtime always records fair-merge order and
  "replays the exact same execution" — it does not; see
  `DisSysLab/docs/algorithms/CHECKPOINT_RESUME.md`, "Determinism is not required").

## Decision (2026-07-23): not pursuing this

Mani's call, and the reasoning behind it is worth keeping. What a user actually
wants while debugging isn't "replay the same run again" — it's closer to
step-control: "next, make agent X receive a message," chosen on demand, not
predetermined by a log. Giving a user that kind of control means the substrate
would have to run its own scheduler — deciding, one step at a time, which
agent's next action fires — rather than handing agents to Python's thread
scheduler and letting the OS interleave them. That's a materially different
runtime architecture, not an incremental addition to what exists, and the
assessment is that it's too much implementation cost for the value here.
**Exact bit-for-bit replay-from-a-log is off the roadmap.** What stays (and is
already built): read-only narration of a run that already happened
(`dsl explain-trace`) and of a saved checkpoint (`dsl show-checkpoint`) —
neither needs a custom scheduler, because neither re-executes anything.
