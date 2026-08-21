# os_agent — what it does and why

`dissyslab/os_agent.py`. One per office, running in its own thread,
created during compilation once the flat agent graph exists. It is the
office's operating system: it decides when the office has finished, it
shuts it down, and it initiates snapshots and recovery.

Agents never talk to each other about any of this. They answer questions.

## The question it is trying to answer

**Can any agent in this office execute again?** If not, the office is
finished and should stop; if it does not stop, `dsl run` hangs and the
user has no way to tell a long computation from a dead one.

The answer is not local to any agent. An agent blocked in `recv` knows
only that *it* has nothing; it cannot know whether a message is on its
way. So the question needs a party that can see every agent and every
channel at once, and that is os_agent.

## How it asks

It polls. Every `poll_interval` it sends a `_GiveMeCounts` to every
inbox queue of every agent that has inboxes, waits, and drains the
replies. A reply carries:

- the agent's **sent and received counts**, per port;
- an **`idle` bit** — does it owe a future send;
- a **`final` flag** — will it never be active again;
- the **round it is answering**;
- for a coordinator, **`waiting_on`** — the inbox it will read next.

Two things about that are worth understanding, because everything else
follows from them.

**A poll goes to every inbox, not just the first.** A coordinator blocks
on whichever inbox its state selects. A poll placed only on `inbox[0]`
would never be seen while it waits on another, and os_agent would never
learn it is stuck. The extra copies are read later and answered again;
`_update_counts` is idempotent, so a late duplicate is harmless.

**Answering is itself evidence.** OS messages are intercepted inside
`recv`, so an agent can only reply from a point in its code where it is
blocked waiting for input — which for a *reactive* agent is a point
where it owes nothing. That is why the reply is tagged with the round: a
reply for the current round means "this agent is idle right now", and an
agent that is mid-computation simply does not answer.

## The predicate

Termination is declared when both hold:

1. **Every agent is idle and said so recently** — each has either
   reported `final`, or answered *this* round with `idle`.
2. **Every reachable channel is empty** — `sent == received` on each
   edge, with one refinement below.

The two halves of (1) do different jobs and neither is redundant. The
round tag proves the answer is *current*; the bit says whether the agent
owes a send. For a reactive agent the bit is constant and the tag carries
the weight. For a **non-reactive** agent — a source, an alarm, anything
with its own thread of control — the agent can answer while it still owes
something, so the tag proves nothing and the bit carries the weight.

Reading a bit rather than classifying agents by kind is deliberate. It
means a new kind of agent reports its own activity and os_agent needs no
branch for it. The contract for such a kind is **conservative by
default**: report active unless you can prove otherwise, because a false
`idle` ends the office early and silently discards work, while a false
`active` only delays the verdict.

## The coordinator refinement

Condition (2) says *reachable*, not simply *empty*. A coordinator reads
one inbox at a time, chosen by its state. A message buffered on one of
its other inboxes is not work remaining — the coordinator is blocked
elsewhere and can never consume it. Treating that channel as non-empty
made offices with uneven coordinator inputs hang forever; `waiting_on`
names the inbox the coordinator *will* read, and messages anywhere else
are disregarded.

This is correct and it has a consequence worth knowing: an office with a
stranded message is declared **terminated**, because nothing more can
happen — which is true, and is also indistinguishable from success. The
message is not lost to the *snapshot*, which records it either as channel
state or, if it was consumed into a join's half-filled slots, as process
state. Termination detection answers "should I stop"; the snapshot
answers "what was everyone holding". Bending the first to answer the
second is what produces patches.

## What else it does

**Shutdown.** On termination it sends `_Shutdown` to every non-source
agent, which unwinds `run()` via `_ShutdownSignal`.

**Snapshots.** Every `snapshot_interval` it initiates a global snapshot,
collecting each agent's state and the recorded channel states into
`snapshots/checkpoints/<N>/`.

**Recovery.** It drives the resume handshake — `_PrepareRecover`,
then `_StartRecover` once every agent is ready.

## Further reading

- [os_agent_implementation.md](os_agent_implementation.md) — a walk
  through the code.
- [termination_detection_design.md](../design/termination_detection_design.md) —
  the design, including alarms and the extension to networks of offices
  running as separate processes.
- [coordinator_design.md](../design/coordinator_design.md) — why a coordinator
  reads one inbox at a time.
