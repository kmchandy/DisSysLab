# Process parallelism: scrap per-agent, do per-office

**Status: postponed. Roughly a week's work, not scheduled.**
Recorded 2026-08-09 so the diagnosis is not lost and the design does
not have to be re-derived.

## Where things stand

`dsl run --processes` (one OS process per agent) does not work, and
never has, on any platform or start method. Reported by an outside
tester on Windows; confirmed here on Linux.

Three independent faults:

1. **Spawn cannot work without a redesign.** Agents reach the child by
   being pickled. They hold a `queue.SimpleQueue` -- the reported
   `TypeError: cannot pickle '_queue.SimpleQueue' object` -- and behind
   that, agent bodies are arbitrary callables, routinely lambdas and
   closures (`Transform(fn=lambda x: x*2)`), which can never pickle.
   Affects Windows always, macOS by default, and Linux from 3.14
   (default start method became `forkserver`).

2. **Fork has a plumbing bug.** `compile()` calls `_wire_queues()` then
   `_wire_os_agent_queues()`, which captures those thread queues into
   `os_agent.client_queues`. `compile_for_processes()` then calls
   `_wire_mp_queues()`, which correctly re-links the data plane but
   never re-runs `_wire_os_agent_queues()`. So os_agent keeps sending
   `_GiveMeCounts` and `_Shutdown` into orphaned `SimpleQueue`s. The
   control plane (os_agent's inbox, per-source OS inboxes) is also
   still `SimpleQueue`, which `fork` copies per child, so control
   messages cannot cross at all.

3. **Termination does not complete.** With 1 and 2 patched
   experimentally, messages flowed correctly across processes (a
   three-agent office's sink received every message) but agents never
   exited. The count-based protocol does not close across process
   boundaries; `multiprocessing.Queue`'s `empty()` and buffering
   semantics are approximate where `SimpleQueue`'s are exact, and the
   polling depends on that.

No test exercises process mode, which is why this survived. The
`cli.py` comment pointing at `examples/module_08` as the canonical
demo refers to a path that is not in the repo (it lives under the
gitignored `dev/future_gallery/`).

## The decision

Per-agent processes is the wrong granularity. **The only unit of
process parallelism will be a whole office.**

Everything that broke above broke because the interior of an office
assumes shared memory. Splitting at the office boundary leaves all of
that intact: each office runs in its own process exactly as it does
today, with its own threads, its own os_agent, its own queues. Each
process is launched from a spec (the office directory) and compiles
its own office, so nothing is pickled but the channel handles -- which
also makes `spawn` work, and the platform problem disappears rather
than being worked around.

## What the work actually is

A network of offices **may contain cycles**, so end-of-stream
sentinels are not sufficient and real distributed termination
detection is required at the higher level.

The structure is recursive, and this is the point: the existing
termination-detection and global-snapshot algorithms are correct as
they stand and do not change. They are applied a second time, one
level up.

- An **OS process** at the network-of-processes level, playing the
  same role for offices that the OS agent plays for agents within an
  office.
- **Inter-process OS messages** carrying counts of messages sent and
  received on each inter-office channel, so the network-level OS
  process can apply the same "every channel quiescent and every
  source exhausted" test os_agent already applies to edges.
- Global snapshots compose the same way: a marker on each inter-office
  channel, recording in-flight messages as channel state, per
  Chandy-Lamport -- which is what the intra-office checkpoint already
  implements.

This also closes the compositionality gap listed as unbuilt future
work in the paper: offices wired together by feeding one's output
messages into another's input, with the composition itself an office.
Process parallelism and composition become one mechanism rather than
two efforts.

## Open items to settle when this is picked up

- Messages crossing a process boundary must be picklable. This is a
  contract on inter-office channels and should be stated and checked.
- `multiprocessing.Queue` is unbounded by default; inter-office
  channels need a `maxsize` or a fast producer silently grows memory.
- A dead peer process must fail the whole network loudly. A producer
  writing into a queue nobody drains would otherwise report success --
  the same silent-success class fixed for empty sources.
- Whatever lands needs a test that actually runs an office network in
  process mode. The absence of one is why this shipped broken.

## Until then

`--processes` is still advertised in the README ("How it runs", and in
the "Current limitations" section) and in the paper's limitations
section, all of which state that it works. That claim needs pulling or
the flag needs to fail immediately with a clear message. **Not yet
decided.**
