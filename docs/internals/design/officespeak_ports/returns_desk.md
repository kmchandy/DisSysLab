# Paper port 4 of 5: `returns_desk`

Ported by hand against `officespeak_revised.md` (with ports 2 and 3's
additions). Nothing here runs yet.

A clerk handles refund tickets one at a time. Small refunds the clerk approves
on the spot; larger ones go to a manager, and the desk does not take the next
ticket until the manager has answered. It is the spec's worked example for
`select` (section 12).

## Before

```
Sources: starter
Sinks: jsonl_recorder(path='outcomes.jsonl'), console_printer

Agents:
TICKETS is a tickets.
SELECT is a select(inboxes=['ticket', 'manager_reply'], command='command').
CLERK is a clerk.
MANAGER is a manager.

Connections:
starter's destination is TICKETS.
TICKETS's out is SELECT's ticket.
MANAGER's out is SELECT's manager_reply.
SELECT's out is CLERK.
CLERK's to_manager is MANAGER.
CLERK's to_log are jsonl_recorder and console_printer.
CLERK's command is SELECT's command.
```

All three roles are Python, generated, and import `dissyslab`:

- `tickets.py` holds four tickets in the code and emits them when `starter`
  fires.
- `clerk.py` has three outboxes. On a ticket under $50 it sends an outcome
  to the log and the command `{"next": "ticket"}`. On a larger one it keeps
  the ticket in a hidden `pending` variable, sends it to the manager, and
  sends `{"next": "manager_reply"}`. On the manager's reply (recognised
  because the message has an `approved` field) it builds the outcome from
  `pending` and the reply, and commands `{"next": "ticket"}`.
- `manager.py` approves everything: `{"ticket_id": …, "approved": true}`.

## Port A: faithful, with `select`

```
sources:
    tickets: file_source(path="tickets.jsonl")

sinks:
    jsonl_recorder(path="outcomes.jsonl")
    console_printer

agents:
    Sel: select
    Clerk: clerk
    Manager: manager
    Rex: router(on="msg_type")

connections:
    tickets -> Sel.ticket
    Manager -> Sel.reply
    Sel -> Clerk -> Rex
    Rex.log -> jsonl_recorder, console_printer
    Rex.ask -> Manager
    Rex.command -> Sel.command
```

(Not adopted: `select` was removed from the spec after this port.)

Clerk becomes a stateful author returning two messages per step, with
`out: msg_type (log | ask | command)` and three conditional `out if` lines.
It works, but it runs into three problems:

1. **Clerk receives two kinds of message through one inbox.** A ticket and a
   manager's reply both arrive from `Sel`. Clerk can tell them apart only by
   whether `approved` is present, and that field is optional, which the spec
   no longer has. Fixing it needs a field common to both kinds (a `msg_type`
   on every ticket in the file) or a conditional `in if` form.
2. **Hidden state that is not needed.** Clerk keeps `pending` only to rebuild
   the outcome from the reply. If the manager returns the ticket with its
   decision added, nothing needs remembering.
3. **The command is wiring.** `{"next": "ticket"}` names one of `Sel`'s
   inboxes, so Clerk's code knows the office's topology. Section 0 says
   roles know nothing of the office.

## Port B: recommended, with a gate

The desk's real rule is: **one ticket at a time, finished before the next.**
That is exactly the built-in gate.

```
sources:
    tickets: file_source(path="tickets.jsonl")

sinks:
    jsonl_recorder(path="outcomes.jsonl")
    console_printer

agents:
    Gate: gate
    Clerk: clerk(limit=50)
    Rex: router(on="clerk_decision")
    Manager: manager

connections:
    tickets -> Gate -> Clerk -> Rex
    Rex.approve -> jsonl_recorder, console_printer, Gate.done
    Rex.escalate -> Manager -> jsonl_recorder, console_printer, Gate.done
```

(Written in the line form of spec §3.0, settled 16 October.)

```
tickets → Gate → Clerk → Rex ─ approve ──→ log, Gate.done
           ↑               └─ escalate → Manager → log, Gate.done
           └────────────────────────────────────────────┘
```

`tickets.jsonl` (the four tickets that were in the code):

```
{"ticket_id": "T1", "customer": "Ana", "amount": 20, "item": "book", "reason": "wrong item"}
{"ticket_id": "T2", "customer": "Ben", "amount": 120, "item": "chair", "reason": "damaged"}
{"ticket_id": "T3", "customer": "Cy", "amount": 35, "item": "lamp", "reason": "changed mind"}
{"ticket_id": "T4", "customer": "Dee", "amount": 80, "item": "monitor", "reason": "defective"}
```

`roles/clerk.py`

```python
"""
---
emits: approves small refunds; escalates the rest
in: amount
out: clerk_decision (approve | escalate)
---
Arguments: limit -- the largest refund the clerk may approve, in dollars
(default 50).
"""

def step(item, settings):
    if item["amount"] < settings["limit"]:
        return {"clerk_decision": "approve"}
    return {"clerk_decision": "escalate"}


class Clerk:
    def __init__(self, limit=50):
        self.settings = {"limit": limit}

    def __call__(self, item):
        return step(item, self.settings)
```

`roles/manager.py` (approves everything, as before)

```python
"""
---
emits: the manager's decision on an escalated refund
in: amount
out: manager_decision (approve | refuse)
---
"""

def step(item, settings):
    return {"manager_decision": "approve"}


class Manager:
    def __init__(self):
        self.settings = {}

    def __call__(self, item):
        return step(item, self.settings)
```

Both are stateless annotators, so the outcome log holds the whole ticket plus
the decisions, as an audit trail:

```
{"ticket_id": "T1", ..., "amount": 20,  "clerk_decision": "approve"}
{"ticket_id": "T2", ..., "amount": 120, "clerk_decision": "escalate", "manager_decision": "approve"}
```

The manager is the natural place for judgement. An English `manager.md`
deciding from `item` and `reason` would drop in with the same `in:`/`out:`.
I left it as Python to keep the port faithful.

What disappears: `starter`, three generated files that import `dissyslab`,
`select`, the hidden `pending` variable, three outboxes, the command
messages, and field-presence tests. The `print` calls go too; the trace and
the console sink show the same thing.

## Findings for the spec

1. **Neither gallery use of `select` needs it.** `returns_desk` and
   `trading_room` (the only other office using `select`) both have the same
   shape: take one item, perhaps make one round trip, finish, take the next.
   In both, the replier can return the item with its answer added, so the
   asker keeps no state, and a gate plus a router expresses it with
   annotators only. **Decision needed:** (a) keep `select` in the language
   but drop it from the first release's examples and teaching order; or (b)
   remove it from the kept set until an example needs it. I lean to (b):
   fewer concepts, and its one real use (reading inputs in an order the
   agent chooses) can return with an example that needs it.

2. **If `select` stays, its command is wiring.** A role that sends
   `{"next": "reply"}` names an inbox of another agent, against Principle 0.
   It would also need its command inbox named like the gate's `done`
   (`command`, fixed), not set by an argument.

3. **A role that receives two kinds of message.** This appears whenever two
   streams merge in front of one role. Under "no optional fields" the two
   kinds must share a field that tells them apart, declared in `in:`. Port B
   avoids it: each role sees one kind. Worth one sentence in the
   role-writing guide; no spec change unless we keep `select`.

4. **Escalation as a teaching pattern.** Two annotators, each adding its own
   decision field (`clerk_decision`, `manager_decision`), instead of the
   manager overwriting the clerk's verdict. That is "an annotator only adds"
   (4.1) giving an audit trail for free.

5. **Roles that print.** The generated roles printed progress lines to the
   console. That is output outside the office's sinks. **Proposal for the
   role-writing guide:** roles do not print; what a student wants to see goes
   to a sink, and `--trace` shows every message.

6. **The gate's `done` inbox takes any message.** Here it receives outcome
   records, discarded. Consistent with section 6; no change.
