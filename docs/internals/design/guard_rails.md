# Guard rails around a model call

**Status: designed, not built.** Nothing described here exists. It is
recorded now because the reasoning took a working session to reach and
would otherwise have to be reached again.

**It has two purposes, and the second is the larger one.** The
mechanism lets a user put her own checks around an agent that calls a
language model. The teaching says why she would want to, what such
checks can do, and — the part that is usually left out — what they
cannot. It is intended as the spine of a **micro-course on using
language models safely**, taught alongside the framework rather than
after it.

---

## Why this is a teaching problem before it is a software problem

A first-year will be handed, this year, a tool that produces confident
prose about anything. The useful lesson is not "models are dangerous"
and not "models are fine". It is that a model is a **subroutine whose
output is unvalidated**, and that everything one already knows about
unvalidated input applies to it.

That framing is available here in a way it is not in most settings,
because in an office the model call sits inside one Python function
with a message going in and a message coming out. The place a check
would go is visible, and she can put one there in five lines.

The three things worth her leaving with:

1. **What the model is for.** Content — judgement, summary,
   classification — where an exact rule does not exist or is not worth
   writing.
2. **What Python is for.** Form. Whether the answer has the shape it
   was supposed to have, and whether it names something that was not in
   the question.
3. **That the second does not make the first safe.** It narrows the
   opening. A guard that approves a message has approved sending it,
   and the bound on what an office can do is still its sinks.

Point 3 is the one that must not be dropped in the retelling. A guard
believed to be complete is worse than no guard, because it moves the
belief without moving the risk.

---

## The mechanism, minimally

Opt-in. Nothing is wired into every agent, and no default checks ship.
A guard exists only in an office where somebody wrote one.

```python
# roles/checked_filter.py -- exists only because guards were wanted
from dissyslab.office.library import guard

def before(msg):
    ...          # raise to reject

def after(msg, outbox):
    ...          # raise to reject

role = guard("relevance_filter", before=before, after=after)
```

```
Screen is a checked_filter.
Screen's keep is Rate.
Screen's discard is discard.
```

### It is one agent, not three

This is the point most easily misread. `Screen` is a single agent, a
single node, a single thread. `guard` composes three plain function
calls inside that agent's own function:

```
message arrives at Screen's inbox
        │
        ▼
   before(msg)                  ← plain call; raises to reject
        │
        ▼
   relevance_filter's fn(msg)   ← plain call; makes the HTTP request
        │
        ▼
   after(msg, outbox)           ← plain call; raises to reject
        │
        ▼
message leaves on Screen's `keep` or `discard`
```

Nothing is queued between the steps, no thread is handed off, and
`relevance_filter` never appears in `office.md`. The network is exactly
what it was — same nodes, same edges, same drawing.

This works because an LLM role is *already* a Python closure that makes
a request: `nl_role` returns `Role(fn=role_fn, ...)`, and `role_fn`
calls `backend.complete`. There is no LLM agent in the runtime to wrap;
there is only a function to compose with.

### The alternative that was rejected, and why

A guard could be **its own agent** — messages to the guard, to the
model agent, back to the guard. That form has one real advantage: the
guard is visible in the drawing, and `dsl check` could verify that one
sits between an untrusted source and an acting sink, which is pure
reachability and would be a genuinely useful check.

It was rejected because it **can be bypassed by rewiring**. Edit one
connection line and the guard is still there, still drawn, still
passing its tests, and no longer in the path. The composed form cannot
be bypassed, because there is no wire to move. It also triples the
message traffic for that step and puts a cycle in the diagram.

### Three decisions inside the mechanism

**Raise to reject.** No return convention, no sentinel values, and the
traceback names the user's own function.

**`after` receives the outbox as well as the message.** A useful output
check often wants to veto the *routing* — "this may be published, but
not to `publish`" — and passing only the message forecloses that for no
saving.

**Rejection drops the message and prints one line**, which is what
`nl_role` already does with a malformed reply, so it introduces no new
failure mode. An optional `on_reject="rejected"` gives the role an
extra outbox instead — and because an unwired outbox is an error (W2),
taking that option **forces the office to say where rejected messages
go**. That is how an opt-in guard becomes visible in `office.md`
without any grammar for it: not by being an agent, but by having a
port.

### One wrinkle with declared ports

Under the declared-ports design a role file states its `INBOXES` and
`OUTBOXES`, but a guarded role's ports are not its author's to choose —
they are the wrapped role's. The intended resolution is that the port
reader recognises `role = guard("<literal>", ...)` and inherits the
wrapped role's declaration. The name is a string literal, so this stays
statically readable without importing the file, which is the property
the whole port-reading design depends on.

---

## What to teach about the checks themselves

Three kinds. Two of them work.

**Form — where nearly all the value is.** Schema, types, enum
membership, length bounds, no unexpected keys, and that the chosen
outbox is one the role declares. Decidable, cheap, no false positives.

**Provenance — the underrated one.** Not *"is this output bad"* but
*"is this output derived from the input"*. Every URL in the reply must
appear in the incoming message. No email address that was not already
there. No new domain. This converts an unbounded question into set
membership, and it is the single most effective check against prompt
injection, because an injection's payload is almost always **a new
destination**.

**Semantics — a smell test, and it must be labelled one.** "Nothing
harmful", "no personal data", "no hallucinated citation". Not
decidable. Worth writing, worth never describing as more than a
heuristic.

### The strongest version is not a check at all

**Do not carry the free text.** If the agent downstream of the model
emits a score and a URL chosen from a list that arrived in the input,
nothing the model wrote can reach the sink, and there is nothing to
inspect. Checking is what one does when the dangerous thing is still in
the message; the stronger move is arranging that it is not.

Said as a sentence a student can keep: **Python decides what shape may
leave; the model only chooses among shapes Python already allowed.**

---

## Where this sits beside what already exists

- `trust.py` and **W11** ask whether text from the open web can reach a
  sink that acts. That is about the office's shape.
- `role_effects.py` and **W12** ask what a role's own Python reaches
  for. That is a lint, and it says so.
- **Guards** are the third thing: what happens to one message on its
  way through one agent. None of the three is a guarantee, and all
  three documents say so in the same words on purpose.

## The micro-course this belongs to

Roughly four sittings, in this order:

1. **The model as a subroutine.** Show `role_fn`. It takes a string and
   returns a string. Everything else follows from that.
2. **What it will do that you did not ask for.** Wrong shape, invented
   fields, an invented destination. Run one and watch.
3. **Guards.** Write `before` and `after` for an office she already
   built. Form first, then provenance.
4. **The limits.** Why a guard narrows and does not close; why the
   sinks are the real bound; why "no bad content" is not a check.
   Finish on the sentence above, not on a list of defences.
