# Office-per-process: planned implementation

**Status: design only. Nothing built.** Companion to
`process_parallelism_decision.md`, which records why per-agent
processes were scrapped. Roughly a week's work, currently postponed.

## 1. Unit and scope

One office, one OS process. That is the only granularity. An office's
interior is unchanged: threads, its own os_agent, its own
`SimpleQueue`s, shared memory. Everything that broke in per-agent mode
broke where an office's interior assumes shared memory, and an office
boundary does not.

A **network of offices** is a directed graph whose nodes are offices
and whose edges are channels. It **may contain cycles**, so
end-of-stream sentinels are not sufficient and real distributed
termination detection is required.

## 2. The composition spec

No new file format. Kahn's formulation -- and the paper's -- is that a
process is either a sequential program or itself a network of
processes. So a composition is an `office.md` whose agents happen to be
offices:

```
Sources: csv_stock_history(directory="sp100_data")
Sinks:   console_printer

Agents:
SIGNALS is an office(path="./signal_office", processes=1).
BACKTEST is an office(path="./backtest_office", processes=1).

Connections:
csv_stock_history's destination is SIGNALS.
SIGNALS's out is BACKTEST.
BACKTEST's out is console_printer.
```

`office(...)` is a new component kind. The parser and the graph model
need no changes: an office-agent has inboxes and outboxes like any
other agent, and the compiler already validates wiring against
contracts. What changes is what the compiler *builds* for that node --
a child process rather than a thread.

This is also the compositionality feature listed as unbuilt in the
paper. Composition and process parallelism are one mechanism.

## 3. Launch model

The parent process is the **network runner**. For each office-agent it
starts a child with two things: the office directory, and the channel
endpoints it owns. The child compiles its own office from `office.md`
and runs it exactly as `dsl run` does today.

Nothing live is pickled -- no agents, no lambdas, no closures. Only
the office path and channel handles cross. This is what makes `spawn`
viable, so Windows, macOS and Linux 3.14+ work rather than being
worked around. It is the "rebuild in the child from a spec" design
per-agent mode would have had to invent; an office already has a spec
and a compile step.

Inside the child, an inter-office channel materialises as ordinary
components: a `channel_sink` on the sending side, a `channel_source`
on the receiving side. The office model does not learn about
processes.

## 4. Channels

A `Channel` protocol, with the transport chosen by `DSL_CHANNEL`,
mirroring how `DSL_BACKEND` selects an LLM provider:

```python
class Channel(Protocol):
    def send(self, msg: Any) -> None: ...
    def recv(self, timeout: float | None) -> Any: ...
    def counts(self) -> tuple[int, int]:   # (sent, received)
    def close(self) -> None: ...
```

Two implementations:

- **`LocalChannel` (default)** -- `multiprocessing.Queue`. Zero
  install, same machine. This must stay the default: the framework's
  promise is `pip install` and nothing else, for first-year
  undergraduates.
- **`AMQPChannel` (opt-in)** -- one AMQP queue per directed channel.
  Buys durability, flow control, and machines, at the cost of a
  broker.

Both must be **FIFO per channel**, because Chandy-Lamport requires it.
`multiprocessing.Queue` is FIFO. An AMQP queue is FIFO with a *single*
consumer, which the model already guarantees: a channel feeds exactly
one inbox.

## 5. The network OS process

The piece that does not exist yet. It plays the same role for a
network of offices that os_agent plays for a network of agents.

Each office's os_agent gains an **uplink**: a control channel to the
network OS process. Over it the office reports, and receives:

- up: local quiescence, plus per-inter-office-channel sent/received
  counts
- down: `_GiveMeCounts`, `_Shutdown`, and snapshot markers

Each office already tracks counts for its internal edges. Inter-office
counts come from the `channel_sink` / `channel_source` pair, which sit
at the boundary and are the natural place to instrument.

## 6. Termination detection

Unchanged within an office. At the network level the network OS
process applies the identical test one level up: termination when, in
the same round, every office is locally quiescent, every inter-office
channel has `sent == received`, and every true source is exhausted.

The subtlety that makes the count comparison necessary -- rather than
just asking each office "are you done?" -- is that a locally quiescent
office can be woken again by a message still in flight toward it.
Sent-but-not-yet-received is exactly what the comparison catches. This
is the same reason os_agent compares edge counts instead of polling
agents for an opinion, applied recursively.

Because the algorithm is the existing one, cycles across offices are
handled for free.

## 7. Global snapshots

Also recursive, and also the existing algorithm.

The network OS process initiates by sending a marker to each office's
os_agent. Each office takes its own internal snapshot with the current
checkpoint code, unchanged. On its inter-office channels it follows
the standard marker rule: on the first marker, record local state;
thereafter record messages arriving on each other channel as that
channel's state until that channel's marker arrives.

Markers travel **in-band on the data channel**, not on the uplink, or
the ordering premise of the algorithm is lost.

The result is a consistent cut across the whole network of offices,
with in-flight inter-office messages captured as channel state.

## 8. AMQP: what it buys, what it costs

Buys, and these map directly onto open items in the decision note:

- **Backpressure** -- `basic.qos` prefetch plus `x-max-length`. Today's
  unbounded `multiprocessing.Queue` lets a fast producer grow memory
  silently.
- **Dead-peer detection** -- connection loss and consumer-cancel
  notifications. A producer writing into a queue nobody drains
  currently reports success.
- **Durability** -- durable queues with persistent messages survive a
  broker restart, which composes well with checkpoint/resume.
- **Machines** -- the same mechanism gives the multi-machine
  distribution listed as v2.x roadmap. This is the strongest argument
  for AMQP: not two processes, but two hosts.

Costs, and one of them is serious:

- **At-least-once delivery, not exactly-once.** After a crash, AMQP
  may redeliver an unacked message. The checkpoint/resume claim is
  that resuming "neither drops nor duplicates work". Redelivery
  breaks the duplicate half unless messages carry an id and receivers
  dedupe, or acks are tied to snapshot boundaries (ack a message only
  once a checkpoint containing its effect is durable). **This must be
  settled before AMQP is offered for a checkpointed office**, because
  it contradicts a stated guarantee.
- **A broker to install.** RabbitMQ, or Docker. For the target
  audience this is a large step, which is why it cannot be the
  default.
- **Serialisation.** Bodies are bytes. JSON by default -- safe,
  inspectable, cross-language. Pickle only opt-in and never over a
  network: unpickling a broker message is arbitrary code execution.
- **Latency.** A broker hop is far more expensive than
  `multiprocessing.Queue`. Fine for coarse messages, poor for the
  10,000 fine-grained points `recovery_demo` pushes. Channel choice is
  a per-network decision, not a global default.

## 9. What must not regress

`pip install dissyslab` then `dsl run periodic_brief`, with no broker,
no service and no configuration. Everything above is opt-in.

## 10. Testing

The absence of a single test is why per-agent process mode shipped
broken. Non-negotiable for this work:

- a two-office network, acyclic, run in process mode end to end
- a **cyclic** two-office network terminating correctly
- a global snapshot across two offices, asserting an in-flight
  inter-office message is captured as channel state
- all of the above on Linux, macOS and Windows in CI, which means
  under `spawn` -- the case per-agent mode could never satisfy

## 11. Sequencing

1. `Channel` protocol and `LocalChannel`; `channel_sink` /
   `channel_source` components.
2. `office(...)` component kind; network runner; child launch from
   spec. Acyclic pipeline runs end to end.
3. Network OS process, uplink, inter-office counts. Cyclic networks
   terminate.
4. Snapshot markers across offices; consistent cut.
5. CI on three platforms.
6. `AMQPChannel`, opt-in, with the duplicate-delivery question
   answered first.

Steps 1-5 are the week. Step 6 is separate and should not gate it.

## 12. Open questions

- Does an office-agent's contract get declared in the parent
  `office.md`, or read from the child's own `office.md` at compile
  time? Reading it is better -- one source of truth -- but means the
  parent compile step touches the child directory.
- Does the network runner itself have a snapshot, or is the network
  snapshot just the set of office snapshots plus channel states?
- How does `dsl run` present failure in a child office? A traceback
  from another process is exactly the kind of output a beginner
  cannot act on.
