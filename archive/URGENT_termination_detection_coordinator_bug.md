# Termination detection is wrong for coordinators (selective receive)

**Status: RESOLVED (2026-07-15).** See "Resolution" at the bottom. Correctness bug.
Affected any office with a coordinator whose inputs are uneven or that does ask-and-wait —
i.e. much of what phase 2 will run — and underpins the paper's "termination detection works
even with loops/coordinators" claim.

## The bug

Current termination detection declares the office done iff **every channel is empty**
(per-edge `sent == received`) and all agents are quiescent.

But a **coordinator reads exactly one inbox at a time**, chosen by its state (see the
Coordinator model). A message buffered in one of the coordinator's *other* inboxes is
**not live work** — the coordinator is blocked elsewhere and will never touch it. The
current condition treats that nonempty channel as "work remaining," so it **refuses to
terminate and the office hangs forever**, even though no message can make progress.

Examples:
- **merge_synch** joined some pairs, is now blocked on `in_0` whose source has ended;
  `in_1` has one leftover, unpairable message. No further output is possible, but the
  `in_1` channel is nonempty → current TD never fires → hang.
- **gate** blocked on `control` (waiting for a downstream "done") while `data` has
  buffered items. Nonempty `data` channel → hang.
- **select** (ask-and-wait) blocked on the reply inbox while its info inbox has buffered
  messages it will not read until it advances.

## Corrected predicate (rephrase termination)

The office is **quiescent** (→ terminate) iff:

1. every channel directed into a **non-coordinator** agent is empty (an ordinary
   transform/sink/record/Worker reads its single inbox unconditionally, so a nonempty
   inbox there *is* live work); **and**
2. every **coordinator** is blocked waiting on some inbox X, and **all channels feeding
   X are empty** (nothing can unblock it; its other inboxes may be nonempty but are
   unreachable and do not count as progress); **and**
3. all sources are exhausted (no new external input).

If all hold, **no message anywhere can be received by any agent** → truly quiescent →
terminate. This subsumes both natural termination and stuck-coordinator deadlock into
one quiescence condition (in both, no progress is possible, so the runtime should stop
rather than hang).

## Implementation implication

The os_agent's per-edge count-matching (`sent == received`) is **not sufficient** —
it cannot tell that a nonempty channel feeds an inbox the coordinator isn't reading.
The TD protocol must additionally know, **for each coordinator, which inbox it is
currently blocked on** (its state-chosen inbox), and combine that with channel emptiness
to evaluate (1)/(2). So:

- each coordinator must expose its current "waiting-on inbox" to the TD protocol (via
  the recv machinery, or a reported field), captured consistently with the channel-state
  snapshot;
- then quiescence = (1) ∧ (2) ∧ (3) above.

Care needed: capturing "which inbox each coordinator is blocked on" together with the
channel states must be consistent (a coordinator must not be counted as blocked-on-X
while an X message is in flight) — fold this into the existing snapshot/marker machinery.

## Impact / severity

- **Correctness:** coordinator-heavy offices hang instead of terminating (false negative).
- **Blocks phase 2** (offices with merge_synch/select/gate + records).
- **Paper:** the termination claim must be stated with this refined predicate.

## Resolution (2026-07-15)

Implemented exactly the refined predicate above, using the checkpoint insight: a
coordinator's waiting-on inbox is `_get_inport(state)`, a **pure function of its state**,
so the coordinator can just report it. No separate global snapshot is needed for the TD
check itself — the count-poll already in place carries the extra field.

Changes:

- **`core.py`** — `_GiveMeCounts` now carries a `round_id`; every agent echoes it in its
  reply. A reply for the *current* round proves the agent is blocked in `recv` right now,
  i.e. **passive**. New base-class hook `Agent._termination_info()` (returns `{}` by
  default) lets a subclass add fields to that reply.
- **`blocks/coordinator.py`** — overrides `_termination_info()` to return
  `{"waiting_on": self._get_inport(self._state)}` (best-effort; omitted if the policy
  can't name an inport, which falls back to the strict rule).
- **`os_agent.py`** —
  1. `_send_give_me_counts` stamps each poll with a monotonic round and delivers it to
     **every** inport queue of each agent (not just inport[0]), so a coordinator blocked
     on any inbox still sees the poll and replies.
  2. `_update_counts` records each agent's answered round and its `waiting_on`.
  3. `_terminated` now returns True iff **(1)** every agent heard from (sources exhausted),
     **(2)** every non-source agent answered the current round (all passive — guards
     against a false "done" while e.g. an LLM worker is mid-call with balanced counts),
     and **(3)** every *reachable* channel is empty: for an ordinary agent every inbound
     channel; for a coordinator only the channel into its `waiting_on` inport (messages
     buffered on its other inports are unreachable and don't count).
  4. `run()` reordered to send → sleep → drain, so drained replies answer the round just
     sent.

Tests: `tests/integration/test_coordinator_termination.py` — a `merge_synch` with an
unpaired leftover and a `gate` starved on its `done` inport, both of which hung under the
old predicate, now terminate with the correct output. Full suite: 446 passed, 42 skipped,
no regressions; the three phase-2 offices (room_monitor, triage_swap, tutor) still run and
terminate.
