# Termination detection: one algorithm, every level

**Status: design, agreed in discussion 2026-08-18/19. Nothing built.**
Extends `docs/internals/design/process_per_office_design.md` §6. Read that first
for the office-per-process context; this document replaces its sketch of
termination detection with a worked design, and adds alarms.

---

## 1. What this changes, and why

Today's detector (`dissyslab/os_agent.py`) works, and its soundness rests
on an argument that is easy to lose when the code is edited:

> A message can only appear via a send. Every send is caused by a receive.
> The recursion must bottom out at something that sends *without* having
> received. Today the only such thing is a source, so "every source is
> exhausted" closes the base case.

Three things break that argument, and all three are coming:

1. **Alarms.** An agent that asks to be woken later introduces a second
   way to send without receiving. The base case is no longer just sources.
2. **Offices in processes.** The detector must work one level up, over a
   graph whose nodes are offices, and it must be the *same* algorithm or
   there are two things to get right instead of one.
3. **Agent kinds not yet invented.** An HTTP request in flight, a
   subprocess that will report back, a task on a thread pool — each is
   another way to owe a future send.

The fix is to stop enumerating the exceptions and to name the property
they share.

---

## 2. Terminology

The standard terms, used throughout:

- **active** — the agent has an *outstanding obligation*: it will send at
  some future point without needing to receive anything first.
- **idle** — not active.

And a distinction about *how* idleness can be known:

- A **reactive** agent sends only in response to a message. It can only
  answer a query from inside `recv`, where by construction it owes
  nothing — so **answering is itself the proof of idleness**.
- A **non-reactive** agent — a source, an alarm — has its own thread of
  control and can answer a query while active. **Answering proves
  nothing**; such an agent must report its state.

That asymmetry is the whole of the design.

---

## 3. The reply

Every agent answers a query with the same message, whatever its kind:

```python
{
    "agent":      "Sasha",
    "round_id":   7,
    "idle":       True,           # ← the new field
    "final":      False,          # ← optional; True = never active again
    "sent":       {outbox: n, ...},
    "received":   {inbox: n, ...},
    "waiting_on": "in_1",         # coordinators only, as today
}
```

`idle` is one bit. That is the entire cost of making the scheme open to
agent kinds nobody has written yet: os_agent stops classifying agents and
simply reads what each one says about itself. The judgement lives in the
only place that can make it.

For a reactive agent `idle` is constant `True` — redundant, and worth
paying for the uniformity.

### 3.1 `idle` must be computed at reply time, never cached

It is read from whatever counters the agent maintains, at the moment of
replying. Caching it reintroduces a window between the obligation being
discharged internally and the flag being updated.

### 3.2 The contract for any new agent kind: **conservative by default**

> Report `active` unless you can prove you owe nothing.

A false `idle` terminates the office early and silently discards work. A
false `active` only delays the verdict. The asymmetry is what makes
"add more kinds later" safe rather than merely possible: an author who
has never read the detector gets it right if the default errs active.

### 3.3 Its resume-side counterpart

> An agent that can report `active` must be able to reconstruct the means
> of becoming idle from its snapshotted state alone.

A snapshot records messages and process state. It does **not** record
machinery — a thread, an open socket, a subprocess handle. Every
non-reactive agent carries its obligation partly in such machinery, so
restoring `active` without restoring the means of discharging it leaves
an obligation nobody will ever meet, and the office never terminates.

For the alarm this means recording that a timer is outstanding and
re-arming the worker on resume. For any future kind it means the same
thing in that kind's own terms, and it is a question worth asking the
moment a new non-reactive agent is proposed.

### 3.4 Define idleness over messages processed, not over the world

The alarm is idle iff it *has not yet received* the finished message from
its worker — not "iff the worker has finished." The two differ for the
few microseconds while that message is in flight, and the message-based
definition is better for two reasons: it errs in the conservative
direction of §3.2, and it makes the agent's state a function of its own
message history, which is exactly the property that makes the state
snapshottable at all.

The same discipline should apply to any agent kind that owes a future
send: define its idleness by what it has processed, never by the state of
something it cannot observe atomically.

---

## 4. The predicate

At **any** level, over that level's children and the channels between
them:

```
Quiescent  ⟺  ∀ child c:  idle(c) ∧ ( final(c) ∨ replied(c, this_round) )
           ∧  ∀ reachable channel between children:  sent == received
```

Two conditions, and they do different jobs. Losing either is a bug:

- **`replied(c, this_round)`** proves the reply is *current*. A reactive
  agent that is mid-computation does not reply at all; without the round
  tag its previous reply — which said `idle`, because it was sent from
  inside `recv` — would be believed while the agent is busy.
- **`idle(c)`** says whether the agent owes a future send. The round tag
  cannot establish this for a non-reactive agent, which can reply while
  active.

**`final`** covers the agent that stops replying because it is gone: an
exhausted source ends its thread. Once an agent reports `final`, the
detector records it as permanently idle and stops expecting fresh
replies. This makes explicit what `heard_from` does implicitly today.

- a source is final when exhausted;
- an alarm is never final while the office runs — it replies every round;
- a reactive agent is final only at shutdown.

**"reachable"** keeps today's coordinator refinement: a non-empty channel
into an inbox a coordinator will not read (`waiting_on` names the one it
*will*) is unreachable and does not block quiescence. See §8.

---

## 5. Levels, and where each count is reported

An office with external connections is compiled with boundary agents: a
`channel_sink` for each outgoing inter-office channel, a `channel_source`
for each incoming one. They are ordinary agents inside the office.

**Each channel is accounted for at exactly one level, and only one.** The
office detector never sees an external count; the network detector never
sees an internal one:

| Count | Held by | Reported to |
|---|---|---|
| internal edge, sender's outbox | the sending agent | office detector |
| internal edge, receiver's inbox | the receiving agent | office detector |
| `channel_sink`'s **internal inbox** | `channel_sink` | office detector |
| `channel_sink`'s **external sends** | `channel_sink` | network detector |
| `channel_source`'s **internal outbox** | `channel_source` | office detector |
| `channel_source`'s **external receives** | `channel_source` | network detector |

The boundary agent filters its own report, so the office detector needs
no knowledge of which of its agents are boundaries — consistent with §3's
principle that the agent knows and nobody else has to.

### 5.1 What this buys

From inside, `channel_sink` looks exactly like a sink and `channel_source`
exactly like a source. The office's internal graph is closed, and the
office detector is *unmodified*.

And it dissolves a problem the earlier sketch had to special-case.
`channel_source` reports `idle` whenever it holds nothing — it is not a
source in the "may spontaneously produce" sense, because everything it
emits is caused by an external message, and that message is accounted for
by the network detector's external counts. So an office never wrongly
concludes anything about its upstream: it reports *quiescent*, and only
the level above can conclude *terminated*.

### 5.2 Only the root acts

Every detector computes the same predicate. What differs is what it does
with a true result:

- a **non-root** detector reports `idle` upward and waits;
- the **root** detector — the office detector of a standalone office, or
  the network detector of a network — initiates shutdown.

A standalone office is therefore the same code with no parent, which is
why today's behaviour is preserved exactly.

### 5.3 Transport is not a level

Whether an office's process is on this machine or another changes the
latency of a round, not the algorithm. Pipes versus sockets never enters
into it.

### 5.4 An office is logical; a process is an execution construct

Decided 2026-08-19, and it supersedes `process_per_office_design.md` §2,
which wrote `office(path="./signal_office", processes=1)` in the
composition. That baked deployment into the logical structure, which
costs reuse: an office with an opinion about how it is run cannot be a
process in one deployment and a nested component in another.

- **An office is a logical construct**, and offices nest arbitrarily.
  Composition is a source-level convenience.
- **Flattening turns the hierarchy into a flat network of agents** — and
  adds agents nobody wrote, the Broadcast and Merge nodes inserted for
  fan-out and fan-in. The `office.md` boundary leaves no runtime trace
  except in the prefixed agent names (`recovery_demo::Alex`).
- **A separate declaration, at run time, names the cut**: which offices
  become processes. Nothing in any `office.md` mentions processes.

**The cut is a single antichain, so there are exactly two levels** —
agents within a process, and processes within the network. Never three,
never arbitrary depth. §4 states the predicate recursively because that
is what shows the two levels to be one algorithm rather than two; the
implementation only ever instantiates two, and should not be built for a
depth that cannot occur.

`channel_sink` / `channel_source` are inserted **at the cut and nowhere
else**. Office boundaries above or below it dissolve in flattening.

### 5.5 For now: the cut is the top level

**Decided, in the interest of finishing simple code.** The one-to-one
mapping between offices and processes exists only at the top level. If
`A` contains `A1` and `A2`, and all three of `A1`, `A2`, `B` are to be
processes, the grouping `A` is forgotten at that level.

**The known cost**, recorded so it is not rediscovered: `A` is not just a
namespace — it has internal wiring. Promoting `A1` and `A2` means
re-expressing `A`'s connections in the top-level composition, so the same
wiring is described in two files with nothing checking that they agree.
That is the divergence pattern this repository has spent a week on, and
it is the reason to generalise the cut eventually.

**Three conventions make the generalisation cheap, and all three cost
nothing now.** They should be followed from the first commit:

1. **The cut is data, computed in one place.** `flatten(node, process_cut)`
   takes a *set of office paths*, never a rule. Today's caller is a
   one-liner returning the top-level office children; tomorrow's reads a
   deployment file. The recursion asks only "is this node in the set?"
   The failure to avoid is `if depth == 1` appearing inside the
   recursion, because generalising then means finding everywhere it
   leaked.
2. **Name boundaries by their flattened path from the start** — `root::A1`
   today, so that `A::A1` slots in later without renaming the deployment
   file, the channel identifiers, or the error messages.
3. **State the leftover rule generally:** *the root process runs
   everything not inside a chosen office.* Today that is only the
   top-level composition's own sources and sinks; tomorrow it also picks
   up `A`'s. Written as "the root process runs the top-level sources and
   sinks" it would not generalise.

Write the **antichain check** now — reject the set if any chosen name is
a prefix of another, i.e. no process inside a process. It cannot fire
today, since siblings do not nest. Writing it now means the general case
arrives with its validation already in place and tested, rather than
needing a new path through `dsl check` at the moment it is least fresh.

---

## 6. Alarms

### 6.1 Model

An alarm is an **ordinary agent in the graph**. An agent `X` that wants
one has a private `X_alarm`: the only edge into it is from `X`, the only
edge out of it is to `X`. No new component kind, no new wiring rules, no
change to the graph model.

**One outstanding request.** There is no use case for more, and allowing
more brings cancellation, reordering and per-request identity with it. A
second request while a timer is armed is an **error**, reported as
`{"type": "alarm_error", ...}` on the outbox — which the run summary
already counts and surfaces with the source's own reason.

### 6.2 Counters

The alarm keeps two, and reports `idle` derived from them:

- `accepted` — incremented only when a timer is actually armed;
- `discharged` — incremented by the send of the wake-up itself.

```
idle  ⟺  accepted == discharged
```

Equivalently, and this is the framing to keep in mind: **the alarm is idle
iff it has not yet received the finished message from its worker.**
`discharged` advances when that message is processed, so the two
statements are the same — but the second makes plain that idleness
depends only on messages the alarm has handled, never on the worker's
internal state. See §3.4.

**Not** the raw port totals. The rejected-request error message travels
on the same outbox, so `sent` would advance without discharging
anything, and the alarm would read idle with a timer still pending. The
counters must count arming and firing, not traffic.

Because `discharged` is advanced *by the send*, there is no instant at
which the alarm reads idle while owing a message.

### 6.3 Lifecycle, with the query landing at every point

| Point | accepted | discharged | X→A | A→X | verdict |
|---|---|---|---|---|---|
| request in flight | 0 | 0 | 1 ≠ 0 | — | not quiescent ✓ |
| request consumed, timer armed | 1 | 0 | = | = | **active** ✓ |
| worker waiting | 1 | 0 | = | = | **active** ✓ |
| worker signals expiry | 1 | 0 | = | = | **active** ✓ |
| main loop sends wake-up | 1 | 1 | = | 1 ≠ 0 | not quiescent ✓ |
| X consumes it | 1 | 1 | = | = | idle → quiescent ✓ |

The obligation is covered at every instant, either by the counter
inequality or by an unbalanced channel, and the handover between the two
is a single event — the send — which advances both.

### 6.4 The worker thread signals; it never sends

On accepting a request the alarm spawns a thread that waits. The alarm's
main loop stays in `recv`, so it answers polls, snapshot markers and
shutdown promptly — an alarm set for an hour still answers a snapshot
query ten minutes in.

**The worker must not call `send`.** Two reasons, and the second is the
serious one:

- the counters would be read-modify-written from one thread while read
  from another;
- Chandy–Lamport requires a process to record its state atomically with
  respect to its own send and receive events. A worker sending while the
  main thread composes a snapshot reply can produce a recorded state
  saying "I have not sent" for a message the receiver has already taken
  as pre-cut — an inconsistent cut, and on recovery the message is lost
  or duplicated.

So: **all message events happen on the agent's own thread.** The worker's
sole job is to signal expiry.

### 6.5 Why not a timed receive instead of a thread

A `recv` with a timeout does hear OS messages during the wait — measured:
a thread waiting with `timeout=10.0` and sent a poll 0.2 s in received it
after 0.200 s. So responsiveness is not the discriminator.

The discriminator is that a timed receive inherits a correctness
obligation: **the deadline is absolute, the timeout is relative.** `recv`
loops after handling an OS message, and if it re-waits the full interval
each time, every poll resets the alarm. Measured, with polls every 0.3 s
and a 1 s alarm:

```
naive (re-waits the full timeout): alarm set for 1.000 s fired at NEVER
absolute deadline, waits remainder: alarm set for 1.000 s fired at 1.000 s
```

Silent when wrong — the alarm simply never goes off and the office never
terminates. "Signal, don't send" is a rule that can be stated once and
checked by inspection; deadline arithmetic must be got right every time
the loop is touched. Hence the thread.

### 6.6 Shutdown

The worker waits on a `threading.Event` with a timeout, not `time.sleep`.
Shutdown sets the event; the worker returns without sending. No thread
outlives the office, and Ctrl-C does not wait out an hour-long timer.

---

## 7. How the worker signals, and what resume must restore

### 7.1 The signal: an OS message, through a hook in `recv`

The main loop is blocked on its inbox, so a `threading.Event` cannot wake
it. The worker must put something on that queue with a direct `q.put` —
not `send()`, which is for outboxes — and that something must not be
counted as a received message or `received` inflates.

So `_TimerFired` subclasses `_OsMessage`. Counting in `recv()` happens
only in the final client-data branch, and `send()` is symmetric
(`if not isinstance(msg, _OsMessage)`), so the property is inherited
rather than added.

`recv()` must then hand it to the subclass. There is already a precedent
for subclass extension in that dispatch — `Coordinator` extends the poll
reply via `_termination_info()` — so the symmetric hook is one branch:

```python
            elif self._handle_os_extension(msg, inbox):
                pass                      # a subclass recognised it
```

with a base implementation returning `False`, and:

```python
    def _handle_os_extension(self, msg, inbox):
        if isinstance(msg, _TimerFired):
            self.send(self._wake_up_message(), "out_")
            self.discharged += 1
            return True
        return False
```

Four lines in `core.py` and a three-line default. Because the branch runs
inside `recv`, the send happens on the agent's own thread, satisfying
§6.4 with no further arrangement.

**Rejected: `Alarm` runs its own drain loop**, reading its queue directly
and dispatching OS messages itself. This looked attractive because it
keeps `core.py` untouched, but `recv()` is not a thin wrapper. It handles
the recovery-buffer fast path, `_Timestamped` unwrapping for the logical
clock, `_GiveMeCounts`, `_Shutdown`, `_Checkpoint`, `_PrepareRecover`,
`_StartRecover`, and then for a client message the `RECOVER_WAITING`
discard, channel-state recording under `_snapshot_lock`, the count, and
the clock update. Three of those are snapshot- and recovery-critical. A
second implementation would diverge the first time any of them changed,
and the symptom would be a corrupted cut rather than a wrong number.

### 7.2 Snapshot is fine; resume is the requirement

There is no race here, and an earlier draft of this section claimed there
was. `_TimerFired` and a snapshot query arrive on the **same** queue, and
the alarm's own processing of them defines the order. Two cases, both
correct:

1. The query is ahead of `_TimerFired`. The alarm reports `active`, which
   by §3.4's definition it is — it has not yet received the finished
   message. The recorded state is right.
2. `_TimerFired` is ahead of the query. The alarm sends the wake-up,
   `discharged` advances, and it then reports `idle`. The recorded state
   is right.

This argument depends on the alarm having exactly **one** inbox. With
two, a marker could arrive on one while `_TimerFired` sat on the other,
and ordering them would need the full channel-state machinery. The
single-inbox design is doing real work.

**What does need care is resume.** In case 1 the recorded state is
`{active, accepted = 1, discharged = 0}` — correct — but the thing that
will discharge that obligation is a worker *thread*, and a snapshot
records state, not threads. Restore that state alone and the alarm is
active with nothing alive to make it idle: it stays active forever and
the office never terminates.

So, per §3.3: the alarm's snapshotted state records the outstanding
timer, and resume re-arms the worker.

**The one decision genuinely left open** is whether a re-armed timer
waits the full `T` or the remainder. Logical time does not survive
checkpoint/resume in the current design, so **full `T`** appears to be
the honest answer — the remainder is not a quantity the system can claim
to know. It should be a decision rather than an accident.

---

## 8. What this does *not* fix, deliberately

An office whose coordinator holds a half-filled join, or has a message
stranded on an inbox it will never read, is **quiescent**: nothing more
can happen, so the verdict "terminated" is correct. It is also
deadlocked, and the held data is discarded.

Termination detection is the wrong instrument for that distinction and
should not be bent to provide it. The **snapshot** is the right one, and
already has what is needed:

- a message still in a queue at the cut → recorded as **channel state**;
- a message consumed and held inside an agent — a join's half-filled
  `slots` → recorded as **process state** (`coordinator.py:150`).

The snapshot also records the coordinator's state, from which
`get_inport(state)` is computable, so it can determine reachability for
itself rather than being told via `waiting_on`.

The division of labour to aim for:

- **the poll answers "should I stop?"** — cheap, frequent, needs only
  cardinalities;
- **the snapshot answers "what happened, and why am I stuck?"** —
  expensive, occasional, needs contents.

One consequence worth acting on: a **snapshot at termination** is the
cheapest and most consistent cut that will ever be available — everything
is idle, every queue quiescent — and it guarantees that a stranded
message is captured, which a periodic snapshot taken earlier does not.

---

## 9. Implementation notes

- **`dsl check` and boundary agents.** From inside, `channel_sink` has no
  outgoing internal edge and `channel_source` no incoming one, so W4
  (dead end) and W3 (unreachable) would fire on them. They must be
  recognised as legitimate terminus and origin — the graph model already
  has `EXTERNAL` for exactly this, and `_terminated` already consults
  `graph.inputs` / `graph.outputs`.
- **Reporting a wait.** An office idle but holding an alarm obligation
  should say so — "waiting on `Wake` (1 obligation outstanding)" — rather
  than looking hung. The number is now available.
- **A perpetual ticker prevents termination**, correctly but invisibly. A
  sibling of W7 — informational, not an error — is worth adding: *this
  office contains a periodic source, so it will not stop on its own.*

---

## 10. Tests, before any of it is believed

1. An alarm fires; the office terminates.
2. An alarm is pending; the office does **not** terminate.
3. Shutdown during a pending wait: no thread outlives the office, and
   `dsl run` exits promptly rather than waiting out the timer.
4. A second request while busy: `alarm_error` emitted, neither counter
   advances, idleness still correctly reported.
5. Snapshot taken while an alarm is pending, then resume: the office
   still terminates.
6. A reactive agent mid-computation: the round tag must prevent a stale
   `idle` reply from being believed.
7. Two offices, acyclic, terminating across a channel.
8. Two offices, **cyclic**, terminating — the case end-of-stream
   sentinels cannot handle and the reason the network detector exists.
