# Coordinator — design note and where we left off (2026-07-11)

A checkpoint of the discussion so we can pick up tomorrow. The base class
is written and smoke-tested; the subclasses are the next job.

## The decision

Generalise `Transform` (one inbox, one outbox) to a base class for
agents with **several inboxes and outboxes** whose behaviour is
controlled by their own state. The base class is named **`Coordinator`**.
The scratch file `temp.py` used during the discussion has been deleted.
`transform.py` is unchanged (by request).

New file: `dissyslab/blocks/coordinator.py`, exported from
`dissyslab/blocks/__init__.py` as `Coordinator`.

## What a Coordinator does, each step

1. `inport = self._get_inport(state)` — choose which inbox to read.
   Depends on `state` alone.
2. `msg = self.recv(inport)` — blocking read.
3. `sends = self._step(msg, state, inport)` — the step function. Returns
   a **list of `(outport, message)` pairs**, or `None`/`[]` to send
   nothing.
4. `self.send(message, outport)` for each pair.

Two things vary per primitive and are the override points:

- **`_get_inport(state)`** — the inbox-selection policy (the
  coordination).
- **`_step(msg, state, inport)`** — the computation, i.e. what to send
  and where.

Both can be supplied inline as `get_inport=` / `fn=` callables (for
one-off agents), or overridden as methods in a subclass (the trusted
primitives will do this).

## Why the signatures are what they are

- **`fn` returns a list of `(outport, message)` pairs, not a single
  value.** An empty list lets an agent *consume without emitting* (a
  join swallowing the first of a pair); the explicit outport lets an
  agent *choose its outbox* (a router). This is the generalisation of
  Transform's "always send the result to `out_`".
- **`fn` receives `inport`.** It is load-bearing, not cosmetic:
  `merge_synch` needs it to know which slot to fill; `gate` needs it to
  tell a data message from a "done" message. Signature:
  `fn(msg, state=state, inport=inport, **params)` (stateful) or
  `fn(msg, inport=inport, **params)` (stateless).
- **`get_inport` depends on `state` alone.** An agent that blocks on an
  inbox it chose from its state is a determinate (Kahn) process. This is
  the reason the *deterministic* primitives are Coordinators and
  `fair_merge` is not.

## Why this base = exactly the deterministic primitives

`fair_merge` (MergeAsynch) reads "whichever inbox is ready first" — it
cannot be a `get_inport(state)` and is the sole nondeterministic
primitive, so it stays its own multi-threaded agent (unchanged). Every
*deterministic* coordination primitive is a Coordinator. The class
hierarchy now draws the determinate/nondeterminate line itself. (Good
line for the paper's determinism section too.)

## Checkpointing

`Coordinator.save_state` / `load_state` persist the `state` dict, so
coordination state (a join's half-filled slots, a gate's busy flag)
survives a checkpoint and a replay. `transform.py` does not do this for
its own state; if we want stateful Transforms to checkpoint, that's a
separate follow-up — noted, not done.

## Product decision that stands (from the prior turn)

The OfficeSpeak assistant is told about the **named subclasses**
(`merge_synch`, `gate`, `select`, `router`, `fair_merge`) and selects
among them. It is **not** given `Coordinator` to instantiate — that
would mean the LLM writes `get_inport`/`step` bodies, i.e. generates
coordination, which is exactly what the trusted-substrate design
forbids. Coordinator is a framework-internal base: less duplication, one
place to verify the deterministic primitives. Adding a new primitive =
a human writes and verifies a new Coordinator subclass, then tells the
assistant about it.

## Status

- [x] `Coordinator` written, exported, smoke-tested.
- [x] `temp.py` deleted.
- [x] **`MergeSynch`** (`merge_synch.py`) — join over `in_0..in_{n-1}`;
      `_get_inport` returns the next unfilled inport in order; `_step`
      files each into a slot and emits the combined message when full.
      Optional `combine(messages)`; default output is the ordered list.
      Verified end-to-end on the real runtime (two sources → join →
      sink, 3 paired emits, termination detection fired).
- [x] **`Gate`** (`gate.py`) — inports `["in_", "done"]`, state
      `{"busy": bool}`; `_get_inport` reads `done` while busy, else
      admits from `in_`. Verified direct-drive (in_ → done → in_).
- [x] **`Select`** (`select.py`) — reads the inport `state["next"]`
      points to; the step fn sets `state["next"]`. Verified direct-drive
      on the ask-and-wait pattern (in_ → request; reply → out_).
- [x] **router / Split — decided NOT needed.** Routing to one of several
      places is plain computation, so a `Transform` covers it; not a
      coordination primitive. (Prompts still mention `router` — a
      follow-up is to drop it there for consistency.)

All three exported from `dissyslab/blocks/__init__.py`. `fair_merge`
(MergeAsynch) left as is — the sole nondeterministic primitive.

## Next

- Consider re-expressing the weather office's ad-hoc `SyncJoin` as
  `MergeSynch` to confirm the base carries a real office end-to-end.
- Full-network tests for `Gate` (needs a done-loop) and `Select` (needs
  a keeper) — logic already covered by direct-drive; the `MergeSynch`
  end-to-end run confirms the Coordinator loop integrates with the
  runtime (recv/send/TD).
- Update the prompts to drop `router` from the named primitives.
