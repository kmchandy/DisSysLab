# os_agent — implementation notes

A walk through `dissyslab/os_agent.py`. Read
[os_agent_overview.md](os_agent_overview.md) first for what it is for.

## Construction

`OsAgent(agents, graph_connections, poll_interval, snapshot_interval,
snapshot_dir, office_name)`, built by `Network._create_os_agent()` during
phase 1 of `compile()` — *after* flattening, so it sees the flat graph
and never the office hierarchy. There is exactly one per compiled
network, however many nested offices went into it.

`client_queues` is filled in later, by `_wire_os_agent_queues()`, because
inbox queues do not exist until `_wire_queues()` has run. That ordering
is not incidental: getting it wrong is one of the three faults that made
the abandoned per-agent process mode unusable — `compile_for_processes`
re-linked the data plane and left os_agent holding orphaned queues.

State it keeps:

| Field | Meaning |
|---|---|
| `all_agents` | name → agent, the flat graph |
| `source_agents` / `non_source_agents` | split by whether the agent has inboxes |
| `edge_sent` / `edge_received` | per `(agent, port)` counts, from replies |
| `idle` | name → the bit from that agent's latest reply |
| `final` | names that reported "never active again" — sticky |
| `_round` / `_round_responded` | the poll round, and which round each agent last answered |
| `waiting_on` | for a coordinator, the inbox it will read next |
| `heard_from` | retained; superseded by `final` for the predicate |

## The loop

```
while True:
    _send_give_me_counts()      # bump the round, poll every inbox
    sleep(poll_interval)
    _drain_responses()
    maybe _initiate_snapshot()
    if _terminated(): _shutdown_all(); return
```

Poll, *then* wait, *then* collect — in that order, so the replies drained
answer the round just sent. That is what lets "reply round == current
round" mean "this agent is blocked in `recv` right now" rather than
"answered at some point".

### `_send_give_me_counts`

Increments `_round` and puts one `_GiveMeCounts(round_id=_round)` on
**every** inbox queue of every non-source agent. See the overview for
why every inbox rather than the first.

Two consequences to know about. A coordinator blocked on one inbox
accumulates one poll message per round on each of the others, bounded by
how long it stays blocked — the case where it grows fastest is a stuck
coordinator, which is the case you most want to survive long enough to
diagnose. And when it does read those copies later, it answers again with
an *older* `round_id`; `_round_responded[name] = rid` is a plain
assignment, so an agent's recorded round can briefly move backwards. That
delays detection by a round or two and can never cause a false
termination, since the test is `== self._round`.

### `_drain_responses`

Non-blocking drain of `in_q`, dispatching by type: `_Reply` to snapshot
collection, `_RecoverReady` to the recovery handshake, and a plain dict
to `_update_counts`.

### `_update_counts`

Records the reply. Counts are **assigned, not accumulated** — each reply
carries the agent's running totals — so duplicate replies are idempotent.

`idle` defaults to **`False`** when absent. That is the conservative
default from `Agent.is_idle`: an agent kind whose reply omits the field
is treated as active, so forgetting to report delays termination rather
than causing a premature one. `final` is sticky: once set it is never
cleared, so a later reply cannot un-finalise an agent that has ended.

### `_terminated`

```python
for name in self.all_agents:
    if name in self.final:                       continue
    if self._round_responded.get(name) != self._round: return False
    if not self.idle.get(name, False):           return False

for (fa, fp, ta, tp) in self.graph_connections:
    if edge_sent[fa, fp] == edge_received[ta, tp]:  continue
    waiting = self.waiting_on.get(ta)
    if waiting is not None and waiting != tp:       continue   # unreachable
    return False
return True
```

A **source that is still running** has sent no reply at all — it is
neither final nor current — so it fails the first loop. This is the case
the older `heard_from` check covered, and it still holds; a source is
never polled, because it is not sitting in `recv` where a poll could
reach it. Its single `_send_termination` message carries
`idle=True, final=True` and is its entire report.

`tests/unit/test_termination_activity.py` pins each of those branches
against the predicate directly, including the conservative default and
the staleness rule. Removing the `idle` check makes two of them fail —
worth knowing, since the rest of the suite passes with it removed.

### `_shutdown_all`

`_Shutdown` to every non-source agent, which raises `_ShutdownSignal`
inside `recv` and unwinds `run()`. Sources are not sent one: they have
already exited by the time termination is declared.

## Snapshots and recovery

`_initiate_snapshot(N)` sends a marker to each agent; `_collect_reply`
gathers the `_Reply` objects; `_write_snapshot` writes
`snapshots/checkpoints/<N:06d>/`. `initiate_recovery(N)` runs the resume
handshake, waiting for `_RecoverReady` from every agent before releasing
the barrier with `_StartRecover`.

Markers travel **in-band, on the data channels**, which is what makes the
recorded cut consistent. OS messages are never counted and never recorded
into channel state — a property that `_TimerFired` will rely on when
alarms land, and one that has a consequence: an obligation carried by an
OS message is invisible to a snapshot, so an agent that can report active
must be able to reconstruct the means of becoming idle from its recorded
state alone.

## Where this is going

`termination_detection_design.md` extends the predicate to a network of
offices running as separate processes. The design is that the *same*
predicate applies one level up, with offices as the children and
inter-office channels as the edges, and that an office reports upward the
same `(idle, counts)` message an agent reports here. Nothing in this file
should acquire a second algorithm.
