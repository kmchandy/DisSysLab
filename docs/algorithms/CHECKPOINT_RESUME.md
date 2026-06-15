# Checkpoint-and-Resume — Snapshot Algorithm for Sense & Respond: DRAFT


## Why this document exists

DisSysLab is a framework for **sense-and-respond systems** —
a network of agents that ingest streams of inputs, operate
on them, and produce streams of outputs. A network of agents
is represented in DisSysLab as an office of agents, and the
network structure is represented by an org chart.
A long-running office must recover from crashes. 
This document describes how DisSysLab uses the Chandy-Lamport
algorithm to take a distributed snapshot. 
(Chandy and Lamport, *Distributed Snapshots:
Determining Global States of Distributed Systems*, ACM TOCS,
1985).
The document also describes an algorithm for restarting an 
office from its most recent checkpoint.


## Adapting the Chandy-Lamport algorithm for sense & respond systems.

We use three adaptations to the protocol:

1. **The OS manager initiates a snapshot by putting the marker
   only into source input queues**. There is a path in the
   network to each agent from some source. So, markers are
   propagated from sources to all agents.


2. **A four-way recovery handshake** — `PrepareRecover` →
   `RecoverReady` → `StartRecover` — synchronizes every agent
   before any of them resumes client work.  
   
   ***State Transitions***
   NORMAL          ── _Checkpoint(N)         ──►  RECORDING
RECORDING       ── all inports closed     ──►  NORMAL          (and send _Reply(N))
NORMAL          ── _PrepareRecover(N)     ──►  RECOVER_WAITING (and load + send _RecoverReady)
RECORDING       ── _PrepareRecover(N)     ──►  RECOVER_WAITING (abandon in-flight snapshot; load + reply)
RECOVER_WAITING ── _StartRecover(N)       ──►  NORMAL
   
   Each agent in the
   network has a queue by which the agent sends messages to 
   the OS manager. The OS manager sends messages to all agents
   by sending messages to sources, and then these messages get
   propagated to all agents in the same way that markers are
   propagated.

   The OS manager instructs all agents to prepare to recover.
   When an agent receives the message it halts its execution and
   sends a 
   
   
   The handshake closes
   two race conditions that arise when restarting from a
   snapshot: agents seeing the recovery trigger at different
   times, and agents resuming `recv()` before all queues have
   been refilled with channel-state messages.

3. **A source/sink boundary protocol** gives end-to-end
   correctness across the office's boundary with the world.
   Each source records `ptr(N)` (the count of inputs read) at
   snapshot and `ptr_to_now` (the count at recovery), then
   replays the gap from its on-disk log. Each sink records the
   same pointers and skips the `ptr_to_now - ptr(N)` duplicate
   emissions during the catchup phase. The world sees no gap on
   the input side and no duplicate on the output side.

Implementation lives in `dissyslab/core.py`,
`dissyslab/os_agent.py`, `dissyslab/network.py`, and
`dissyslab/snapshot.py`. The `recovery_demo` gallery office
demonstrates the protocol end-to-end and is the recommended
starting point for readers who want to see the algorithm
running on a small office before reading the specification
below.

---

## Notation

- **N** — snapshot number, a monotonically increasing integer.
- **Edge** — a 4-tuple `(Y, α, X, β)` where `Y` is the sending
  agent, `α` is `Y`'s outport, `X` is the receiving agent, `β`
  is `X`'s inport. The framework's flattened graph is a set of
  edges; each edge corresponds to one FIFO queue.
- **checkpoint(N)** — the marker payload, an `_OsMessage`
  subclass. May travel on the OS agent's control channels
  (OS→agent broadcast) or on a data edge (agent→agent
  propagation).
- **reply(N)** — an `_OsMessage` subclass carrying an agent's
  recorded state and channel states back to the OS agent. Travels
  on the existing back-channel that today carries `_GiveMeCounts`
  replies.
- **prepare_recover(N)** — an `_OsMessage` subclass sent by the
  OS manager to every source's input queue at the start of a
  recovery from snapshot N. Sources propagate it on their
  outports; downstream agents receive it on data inports. On
  receipt each agent loads its checkpoint-N state, fills the
  per-inport recovery buffer, and enters RECOVER_WAITING.
  Sources and sinks additionally use this message as the moment
  at which to record `ptr_to_now` before entering playback (for
  sources) or skip (for sinks).
- **recover_ready(N, agent)** — agent → OS reply: "I have
  stopped, loaded my state, filled my recovery buffer, and am
  waiting for start_recover." Travels on the existing
  back-channel.
- **start_recover(N)** — OS broadcast (only after every agent's
  recover_ready has been received) sent to each source's input
  queue. Sources propagate it on their outports. Each agent on
  receipt exits RECOVER_WAITING and resumes normal execution.
- **L, L'** — conceptual endless lists representing the items a
  source reads from the world and the items a sink writes to the
  world, respectively. The algorithm uses these as the boundary
  abstraction; their on-disk realisation varies by source type.

## Assumptions

- Data queues are FIFO. (Python `queue.Queue` satisfies this.)
- All control and data queues remain operational for the lifetime
  of the office. Queue failures are out of scope for v1.6; if a
  queue stops working a reply will not arrive and the OS agent
  will wait indefinitely. The user may then `Ctrl-C` to abort.
  Failure detection and snapshot timeouts are future work.
- Execution is single-process for v1.6 (`dsl run`). The
  multi-process mode (`dsl run --processes`) is supported by the
  framework today, but extending the snapshot protocol across
  process boundaries is future work.

## OS Agent Algorithm

### Local variables

- `N`: the next snapshot number. Initially `N = 0`.
- For each agent `X`: the most recently recorded state of `X`.
  Initially empty.
- For each inport `β` of each agent `X`: the most recently
  recorded queue state of the inbound edge into `β`. Initially
  empty.

### Algorithm

```
while True:
    Delay for T seconds.
    For each source S in the (flattened) network:
        put checkpoint(N) in S's input queue.
    Wait until reply(N) has been received from every agent.
    For each reply: record the agent's saved state and the
        agent's recorded channel states into the global state.
    Persist the global state for snapshot N to disk.
    N := N + 1.
```

The OS manager only puts checkpoint(N) into source input queues.
The marker propagates downstream because every agent that
receives checkpoint(N) for the first time forwards checkpoint(N)
on every one of its outports. Sources have no inports of their
own, so they receive checkpoint(N) only via their input queue
(which exists purely so the OS manager has a queue to put into;
it is the same kind of object as every non-source agent's first
inport queue).

The same loop body is used for periodic, manual, and
error-driven snapshots: a periodic snapshot fires when the delay
expires, a manual snapshot fires when an external trigger sets
the delay to zero, an error-driven snapshot fires when an agent
exception is observed before the OS agent sends `_Shutdown`.

## Agent Algorithm

### Two layers within each agent

For the purposes of the snapshot algorithm, an agent `X` has two
conceptually separate layers:

- **The client layer** is the application code the agent author
  wrote: `rms_meter`, `topic_tagger`, the per-app and library
  roles. It receives data messages on its data inports, processes
  them, and emits data messages on its outports. It does not know
  about checkpoint(N), reply(N), or the snapshot algorithm at
  all. It runs continuously throughout the lifetime of the office
  and is never paused or signalled by the snapshot.

- **The OS layer** is framework infrastructure that wraps the
  client. It intercepts checkpoint(N) messages arriving on data
  inports (the client never sees them); it injects checkpoint(N)
  into outport queues directly (independent of client sends); it
  calls `X.save_state()` at the right moment; and it sends
  reply(N) on the back-channel to the OS agent. The OS layer is
  the only part of `X` that participates in the snapshot
  algorithm.

The OS layer does not block, pause, or interfere with the client
layer. While the OS layer is collecting the snapshot, the client
continues to process data messages exactly as it does at any
other time. A data message arriving on an inport `β` during the
OS layer's recording window for `β` is processed by the client
*and* copied (by the OS layer, as a side effect) into the
channel-state recording for `β`; the client is unaware that the
copy happened. The only client-visible touch from the OS layer
during a snapshot is the call to `X.save_state()`, which is a
method call rather than a message, and which the client author
wrote to be cheap and fast.

The steps below describe OS-layer behaviour. The client layer
continues unchanged.

### When the OS layer of X receives checkpoint(N)

A source `X` receives checkpoint(N) on its input queue, put there
directly by the OS manager. A non-source agent `X` receives
checkpoint(N) on one of its data inports, where it was placed by
an upstream agent that had previously received checkpoint(N) and
forwarded it on every outport. The OS layer of `X` intercepts the
message in either case; it never reaches the client.

Multi-worker agents (`MergeAsynch`) may forward checkpoint(N) on
the same outport more than once — one forward per worker thread
that processes a checkpoint(N) on its inport. The downstream
receiver is idempotent on duplicate checkpoint(N) arrivals on an
inport: the first checkpoint(N) triggers the subsequent-marker
branch (closing that inport's recording), and any later
checkpoint(N) on the same inport is discarded as duplicate. This
relaxes "forwarding is exactly-once per outport" to "forwarding
is at-least-once per outport," which simplifies the multi-worker
handler without changing correctness.

1. **Idempotency.** If `X` is already recording for snapshot
   `N` (because a checkpoint(N) on a different channel arrived
   first), `X` does not restart the recording. The duplicate
   marker, if it arrived on a data edge `β`, is consumed inside
   the in-progress `inports_checkpointing` as the per-edge close
   for `β`; if it arrived on the OS control channel, it is
   redundant and is discarded. Either way, `X` continues its
   in-progress checkpoint behaviour. `X` returns from the
   checkpoint behaviour only when step 5 completes (reply(N)
   sent to OS).
2. **Save own state.** `X` calls its `save_state()` method and
   stores the returned object in a local variable.
3. **Forward on outports.** For each of `X`'s outports `α'`,
   `X` sends checkpoint(N) on `α'`. This send happens before
   `X` sends any further data messages on that outport, so the
   marker is FIFO-ordered ahead of post-snapshot traffic on each
   outgoing edge.
4. **Checkpoint incoming queues.** `X` calls the
   `inports_checkpointing` subroutine (described below) to record
   the state of every inbound edge.
5. **Reply to OS.** When `inports_checkpointing` returns, `X`
   sends reply(N) to the OS agent on the existing back-channel,
   carrying both the saved state and the recorded channel states
   for every inbound edge.

Throughout steps 1–5 the client layer of `X` is processing data
messages normally; it does not pause, resume, or change behaviour
in any way. The OS layer does steps 1–5 in parallel with the
client. A data message arriving on an inport `β` after the OS
layer has finalised the channel-state recording for `β` plays no
part in snapshot N; it is a post-snapshot message and the client
processes it as it would at any other time.

### Special cases

- **Sources** (agents with no inports). `inports_checkpointing`
  is trivially empty and returns immediately. Sources still
  forward checkpoint(N) on their outports.
- **Sinks** (agents with no outports). Step 3 is trivially empty.
  Sinks still record channel state for their inbound edges in
  step 4.
- **Agents with both inports and outports.** All four steps apply
  in the order given.

## inports_checkpointing subroutine

Let `incoming(X)` be the set of edges `(Y, α, X, β)` of the
flattened graph. For each `β` in the inports of `X`, the
subroutine records the queue state of the inbound edge to `β`.

```
For each edge e = (Y, α, X, β) in incoming(X):
    if checkpoint(N) on edge e was X's first checkpoint(N):
        the recorded queue state for e is the empty list.
    else:
        the recorded queue state for e is the list of data
        messages X received on edge e from the moment X first
        recorded its own state until the moment checkpoint(N)
        arrived on edge e.
Return once a recorded queue state exists for every edge in
incoming(X).
```

The "first checkpoint(N)" referred to here may have arrived from
the OS agent on the control channel rather than from a data
edge. In that case no inbound edge is the empty-queue special
case; recording begins on every inbound edge from the moment the
OS broadcast was received, and each edge's recording closes when
its own checkpoint(N) arrives via marker propagation from the
upstream agent.

## State Contract

The phrase "save state" in the algorithm refers to a call to
`X.save_state()`, which returns a Python object that is opaque to
the framework. The framework treats the returned object as
write-once-read-once durable data: it is serialised into the
snapshot, and on resume it is passed back to `X.load_state()` to
restore the agent's state.

- Stateless agents inherit the default `save_state()` returning
  `{}` and a no-op `load_state()`.
- Stateful agents override both methods.
- The agent author decides what to save. Re-derivable artifacts
  (loaded ML model weights, decoded audio buffers, file handles)
  should *not* be saved; they are reloaded on first use after
  resume. Position cursors, accumulators, debounce timers,
  per-event counters, RSS seen-URL sets, and similar are saved.

## Resume Procedure

`dsl run <office_dir> --resume <snapshot_id>` (or
`--resume latest`) performs the following steps:

1. Read the snapshot manifest. Validate that the office name
   matches the office that took the snapshot.
2. Build the office network exactly as `dsl run` does today
   (codegen + Network compilation).
3. Start the agent threads.
4. The OS manager puts prepare_recover(N) in each source's input
   queue. Each source forwards prepare_recover(N) on every
   outport, so the message propagates downstream by the same
   induction as checkpoint(N).
5. On receiving prepare_recover(N), each agent loads its
   checkpoint-N state via `load_state` from disk, fills a
   per-inport recovery buffer from the snapshot's channel-state
   files for its incoming edges, sends recover_ready(N, agent)
   on the back-channel, and enters RECOVER_WAITING. In addition:
   each source records `ptr_to_now` (the last log entry written
   before the crash); each sink records `ptr_to_now` (the count
   of items written to the world before the crash).
6. The OS manager waits until recover_ready(N) has been received
   from every agent.
7. The OS manager puts start_recover(N) in each source's input
   queue. Each source forwards start_recover(N) on every
   outport. Each agent on receipt exits RECOVER_WAITING and
   resumes normal execution: client-layer `recv` returns
   buffered channel-state messages first, then falls through to
   the inport queue.
8. Each source enters its playback phase, reading entries
   `L[ptr(N)+1 .. ptr_to_now]` from its on-disk log and emitting
   them into the office. Each sink enters its skip phase,
   discarding the first `ptr_to_now - ptr(N)` messages it
   receives. When playback and skip are both exhausted, the
   office is at steady state.

The error-driven path (snapshot triggered by an agent exception,
followed by recover from the just-taken snapshot in the same
process) reuses the same four-way handshake inside the running
process: prepare_recover(N) → recover_ready(N) → start_recover(N).

## Correctness

For a single snapshot N, the recorded global state is a
*consistent cut* of the office's execution: for every data
message `m`, if the receive of `m` is in the cut, then the send
of `m` is also in the cut. The proof is the standard one for
Chandy-Lamport; the OS-broadcast initiation does not affect the
property because:

- Each agent records its state on its first checkpoint(N),
  regardless of whether that first marker arrived from the OS
  agent or from an upstream agent.
- Each agent forwards checkpoint(N) on every outport before
  sending any post-snapshot data on that outport. By FIFO order,
  the marker arrives at the downstream agent ahead of every
  post-snapshot message.
- Channel state for an edge is recorded as exactly the data
  messages that crossed that edge between "first marker received"
  and "marker arrived on this edge" — which is precisely the
  set of messages that were in transit on that edge at the moment
  of the cut.

### End-to-end correctness at the boundary

With the source and sink protocols of the previous section in
place, the snapshot is correct not only internally but also
across the office's boundary with the world. Across a snapshot
and a recovery, the world experiences:

- **No missing inputs to the office.** Items the source had
  read between checkpoint N and recover are replayed from the
  source's on-disk log; the office consumes exactly the
  sequence of items the world produced.
- **No duplicate outputs from the office.** Items the sink had
  written between checkpoint N and recover are not re-emitted;
  the world receives exactly the sequence of items the office
  was meant to produce.

The world's view of the office is therefore the same as if the
crash and recovery had never happened, modulo a possible pause
in real-time delivery during the playback-and-skip phase
(bounded by the catchup constraint).

## Sources and Sinks at the Office Boundary

The Chandy-Lamport algorithm above captures the office's internal
state — the agents and the channels between them. Sources and
sinks stand at the boundary of the office, with one end inside
and one end in the world. To preserve correctness across the
boundary, each source and each sink follows a small additional
protocol on top of the Agent Algorithm. The protocols are duals
of one another. With them in place, the snapshot is end-to-end
correct: the world sees no duplicates and no gaps in the
sequence of items it produces for the office or receives from
the office.

### Sources

Each source `S` is modelled as reading items from a conceptual
endless list `L`. `S` maintains an integer pointer that counts
how many items from `L` it has read into the office so far.

- **At checkpoint(N).** `S` records `ptr(N)` — the value of the
  pointer at the moment of the snapshot — as part of its saved
  state in reply(N).
- **Between snapshot N and a recover.** `S` continues normal
  operation; the pointer advances.
- **At recover(N).** When `S` receives the OS manager's
  recover(N) message, it records `ptr_to_now` — the value of
  the pointer at that moment.
- **Playback.** During playback, `S` re-reads items
  `L[ptr(N)+1 .. ptr_to_now]` from its on-disk log and re-emits
  them into the office. These are the items `S` had emitted
  between snapshot N and the recover — the items the snapshot
  restoration discarded.
- **Resumption.** Once playback is exhausted, `S` resumes normal
  operation, reading from `L[ptr_to_now + 1]` onward.

For `S` to re-read past items, the items must be available to it
at playback time. This is handled uniformly:

> **Every source records every emitted message to an append-only
> on-disk log.** On playback the source reads from the log
> between `ptr(N)+1` and `ptr_to_now`.

For a file source the file itself serves as the log (the cursor
recovers everything). For other source types — pull-with-history,
pull-current, live-push — the source maintains its own
append-only log alongside its capture loop. The protocol is
uniform across all source types; only the implementation of
"re-read past items" differs.

**Retention.** After checkpoint(N) the source can discard log
entries received before checkpoint(N-1). Steady-state disk
consumption is approximately `2 × (checkpoint interval) ×
(arrival rate)`.

**Completion detection.** The source learns that checkpoint(N)
is complete by observing the arrival of checkpoint(N+1). The OS
manager initiates N+1 only after N has globally completed, so
the arrival of N+1's checkpoint message is implicit proof. No
additional protocol message is required.

### Sinks

Each sink `K` is modelled as writing items to a conceptual
endless list `L'` — the stream of items the sink has emitted to
the world. `K` maintains an integer counter of how many items it
has written.

- **At checkpoint(N).** `K` records `ptr(N)` — the value of the
  counter at the moment of the snapshot — as part of its saved
  state in reply(N).
- **Between snapshot N and a recover.** `K` continues writing
  normally; the counter advances.
- **At recover(N).** When `K` receives the OS manager's
  recover(N) message, it records `ptr_to_now` — the value of
  the counter at that moment.
- **Skip phase.** During recovery the office's internal state
  has been restored to checkpoint N, the source is replaying
  inputs in `L[ptr(N)+1 .. ptr_to_now]`, and the office's
  processing of those replayed inputs produces output messages
  that flow toward `K`. `K` **does not emit** the first
  `ptr_to_now - ptr(N)` messages it receives during the skip
  phase — they correspond to items `L'[ptr(N)+1 .. ptr_to_now]`
  which the world has already received.
- **Resumption.** Once the skip phase is exhausted, `K` resumes
  normal writing, advancing the counter from `ptr_to_now + 1`
  onward.

**Retention.** Sinks need only the integer counters `ptr(N)` and
`ptr(N-1)` (one for the most recent completed snapshot, one for
the previous as a safety margin). Disk cost is essentially zero.

### The symmetry

The two protocols are duals on the same conceptual primitive: a
boundary stream with two pointers, `ptr(N)` taken at snapshot
and `ptr_to_now` taken at recover, with a gap range
`[ptr(N)+1 .. ptr_to_now]`.

- **Source:** *re-emits* the gap into the office during playback.
- **Sink:** *skips* the gap out of the office during the skip phase.

The world sees a continuous stream with no duplicates and no
missing items in either direction.

### Determinism is not required

The sink protocol works by *count*, not by content comparison.
DSL's processing is non-deterministic in the general case — an
LLM call may produce a different response on replay, a
random-sampling agent uses a different seed, a time-of-day
branch resolves differently. The messages the sink receives
during the skip phase will not be byte-identical to the items
`L'[ptr(N)+1 .. ptr_to_now]` the world originally received. The
sink discards them by count anyway. The world sees only the
original pre-checkpoint items followed by the post-recover
items; replay divergence inside the office is invisible to the
world.

The same property is true on the source side. The items the
source replays from its log are the items it originally
captured; they re-enter the office as if no recovery had
happened. Downstream processing in the office on replay may
diverge from the original execution (because of LLM
non-determinism or similar) but the divergence is bounded inside
the office and ends at the sinks, where it is discarded.

### The catchup constraint

The source's playback feeds the office faster than real time.
For the office to return to real time after recovery, the
steady-state processing rate of the slowest downstream agent
must exceed the steady-state arrival rate from the source. If
not, the office accumulates lag indefinitely.

This is a property of the office, not of the algorithm. The
framework cannot detect the condition statically. The framework
should log buffer depth during catchup so the office author can
observe whether the office is converging back to real time.

## Out of scope for v1.6

The following are deliberately deferred and will be addressed in
later releases:

- **Queue failures.** The algorithm assumes all queues remain
  operational. A failed queue prevents reply(N) from being
  delivered. Adding a snapshot timeout, failure detection, or
  recovery from a partial snapshot is future work.
- **Multi-process snapshots.** `dsl run --processes` runs each
  agent in its own OS process. Extending the marker protocol and
  the reply path across process boundaries requires additional
  IPC plumbing. Future work.
- **Multi-machine snapshots.** Out of scope.
- **Schema evolution.** Resuming a snapshot taken by an earlier
  version of the office's code is not supported in v1.6. The
  manifest records enough about the office structure that the
  resume procedure can detect a mismatch and refuse to resume
  with a clear error; graceful schema migration is future work.
- **Encrypted snapshots.** Snapshot files are written with
  `pickle` and are unencrypted in v1.6. Users with sensitive
  state in their agents should consider their own filesystem
  protections. Encrypted-at-rest snapshots are future work.
