# paxos — DRAFT, for review

An example of the Paxos algorithm with 3 proposers, 5 acceptors and 2 learners.

See figure 1 of `course/lecture_08.html`

## What is here

| file | what it is |
|---|---|
| `office.md` | the wiring: 3 proposers × 5 acceptors × 2 learners, and the acceptors' replies back |

## The shape of the network

**One outbox per message, not per destination.** A proposer sends the
same read, and later the same write, to every acceptor, so it has one
outbox, `out`, wired to all five:

```
P0's out are Q0, Q1, Q2, Q3 and Q4.
```

An acceptor's **reply** is the one message in this office that is not a
broadcast — it goes to the proposer that asked and to nobody else — so
an acceptor does need an outbox per proposer, `to_p0 … to_p2`. Its
messages to the learners are all broadcasts again, so those share one
outbox, `to_learners`, wired to both.

Each agent has a single inbox, `in_`, because `recv` blocks on the port
it is given and an agent must be able to take whichever message arrives
first.

So the sender has to be named *in* the message:

- a **read** or **write** carries `sender`, the proposer's name, and the
  acceptor uses it to choose the outbox it replies on
  (`self.reply_port[sender]`);
- a **reply** carries `sender`, the acceptor's name, and the proposer
  keys `self.replies` by it, so two replies from one acceptor count
  once and `len(self.replies) == M` means M *different* acceptors;
- a **learn** message carries `sender` too, and the learner keys
  `self.heard` by it for the same reason: M matching pairs must come
  from M different acceptors.

Two details of the framework that this office has to get right, both
found by running it rather than reading it:

- an outbox has two names, the one the office writes (`to_p1`) and the
  runtime's own (`out_1`, by position, in the order the role entry
  declares them — or just `out_` when the agent has one outbox). The
  role entry advertises the readable names and `self.send` uses the
  runtime's, as in `mac_speed_suite/roles/_walkforward.py` and
  `loudness_monitor/roles/rms_meter.py`;
- `self.name` is **not** the name the office wrote: at run time it is
  `paxos::Q2`. The id that travels in a message is the short name, from
  `roles/_names.py`. The first run of this office sent thirty reads and
  dropped every one of them as coming from an unknown proposer, in
  silence, with nothing in the error count.

## Transaction ids

A transaction id is a pair `(number, proposer name)`. The name makes
the ids of two proposers distinct even when their numbers collide, and
Python's tuple comparison is exactly the total order the proof uses.
`(0, "")` is the id-before-all-ids, used for an acceptor that has never
been assigned.

## What a reply's id is

An acceptor answers a read with the id of the request it is answering,
so a reply that reaches proposer p always carries an id that p itself
made. Two consequences, checked in `check4.py` and `check5.py`:

- **nothing in a reply is ever numbered above p's own `number`.** Not
  `t`, which is p's own id; and not `v_t` either. A reply is proof that
  the read was *not* dropped, so `q.t <= t`; and `q.v.t` was set when q
  accepted a write, when `q.t` equalled that write's id, and `q.t` never
  decreases — so `q.v.t <= q.t <= t`. A proposer therefore learns
  nothing about other proposers' numbers from a reply, and
  `self.number += 1` on a tick is the whole of the numbering. The two
  tests of the form `> self.number` that the draft used to carry never
  fired once in 39,828 replies, 2,355 of them stale;
- the single reply worth discarding is an answer to an **earlier
  transaction of p itself**, overtaken by the tick that started the
  current one. Counting it would put an acceptor's old value into the
  current read set. The check builds the run: a majority holds blue at
  `(1, "P1")`, five of P0's older replies arrive after P0's next tick,
  and with the guard removed every acceptor ends on green at
  `(2, "P0")` — agreement broken. So `if msg["t"] != self.t` stays, but
  as a guard against p's own past, not against other proposers.

## Open questions for review

1. **Rule 1 in a distributed setting.** A proposer raises `number` by
   one on every tick, and that is all it can do: as the section above
   shows, a reply tells it nothing about any other proposer's numbers,
   and a request with too small an id is dropped in silence, so the
   proposer does not even learn that it was dropped. Its next id is
   therefore larger than every id *it* has used, not larger than every
   id in the system, and a proposer that has ticked fewer times than
   another makes no progress until it has caught up by ticking.

   Now that each proposer has its own clock, that is measurable, and it
   is the office's main inefficiency. Thirty transactions, ten at each
   proposer: between **10 and 20 of them never reach a write**, and
   raising T from 20 ms to 200 ms does not improve it, because what
   stops them is not overlap. All three proposers arrive at the same
   number, the name breaks the tie, and the loser is dropped in
   silence. Per proposer, at T = 200 ms:

   ```
   P0 1/10   P1 10/10   P2 10/10
   P0 2/10   P1  0/10   P2 10/10
   P0 6/10   P1  9/10   P2  4/10
   ```

   Nothing unsafe happens — every run reached agreement and both
   learners learned the same value — but a starved proposer is the
   first thing a class will ask about. Is that the rule you want them
   to read? The alternative is for an acceptor to refuse out loud — a
   reply carrying `q.t` instead of silence — which is how real Paxos
   lets a proposer jump ahead, and which would need a new message kind.
2. **`== M` rather than `>= M`.** The write happens on the reply that
   completes the read set, exactly once. Later replies of the same
   transaction are collected but write nothing.
3. **Learners.** Now in `roles/learner.py`. A learner keeps the latest
   pair it has heard from each acceptor and learns as soon as M of them
   are the same pair; after that it ignores everything, which is the
   third requirement of the specification. Two questions: should a
   learner also tell the proposers what it learned, as the lecture's
   section on sequences needs, and should it announce once or on every
   message after it has learned?
4. **The tickers.** Each proposer has its own, waking it after a
   uniform random wait on `[T - delta, T + delta]` milliseconds, drawn
   again before every tick — `T = 5`, `delta = 2`, ten ticks each. A
   transaction takes about 2 ms here, so at T = 5 they overlap
   constantly, which is what exercises the proposer's guard; `T = 50`
   makes a calmer demonstration. `roles/ticker.py` carries the
   measurements. A seed fixes one ticker's sequence of waits but not
   the run: three runs with the same seeds agreed on red, blue and red.
   A ticker also has to stay in the office
   after its last tick, blocked on `recv`, because an agent whose
   `run()` returns leaves a dead thread and the shutdown protocol then
   waits for an answer that never comes. That is what the first run of
   this office did: it timed out after 25 seconds with every other
   agent still alive.

## Settled

**Overlapping transactions at one proposer.** A tick starts a new
transaction whether or not the previous one finished, and a proposer
does *not* ignore ticks while a transaction is in flight: a transaction
that never collects M replies would never complete, and the next tick
is the only retry it has. Overlap is therefore allowed, and
`if msg["t"] != self.t: continue` is the line that makes it safe.
Decided 1 October 2026.

## Running it

```
dsl run paxos
```

It has been run, under the real parser, compiler and network:

```
[1] L0 learned red, written in transaction (1, 'P2')
[2] L1 learned red, written in transaction (1, 'P2')
```

Thirty transactions, ten at each of P0, P1 and P2, both learners
agreeing on one value, no errors and no failures, and the network
reaches quiescence and shuts itself down. `dsl run` prints the two
lines above through `console_printer`. Which value, and which
transaction wrote it, is different every run — three runs agreed on red
at (1, 'P2'), blue at (6, 'P1'), and red again.

The properties that one run cannot show — that nothing goes wrong under
*any* pattern of lost messages — were exercised against a stub `Agent`,
which lets the test choose what to lose and in what order:

- replies reach only the proposer that asked, and each carries its
  acceptor's name;
- a transaction with two replies writes nothing;
- a value written by a majority is carried forward by proposers that
  propose something else;
- in 300 random runs with lost reads, replies and writes, nothing ever
  contradicted a majority once one was reached;
- with one `learn` message lost, L0 learns and L1 does not until a
  later transaction, which is figure 3 of the lecture;
- a learner that hears from one acceptor learns nothing;
- in 300 random runs with losses on every kind of message, no learner
  ever changed its value and no two learners disagreed;
- in 200 random runs, all 4207 replies carried an id made by the
  proposer they were sent to;
- across 800 runs — including ones where a single proposer ticks eight
  times as often as the others — no reply ever carried `t` or `v_t`
  numbered above the receiving proposer's `number`: 39,828 replies,
  2,355 of them stale;
- a reply overtaken by its own proposer's next tick breaks agreement if
  it is counted, and is dropped.
