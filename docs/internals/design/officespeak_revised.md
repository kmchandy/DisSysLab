# OfficeSpeak, revised: specification

Status: **settled 16 October 2026; implemented 17 October** (Phases 2-6b
of `restructure_plan.md`). Not built yet: `dsl try` and `dsl show --prompt`
(section 10), `checkpoint`/`restore` for Python roles (4.3, 8), and the
whole-network checks W1-W4, W7, W8 and W16-W31 (section 9); `dsl check`
reports syntax, kinds, front matter, `needs:`, arguments and ports, by
line, and the two guardrail notes (W11, W12). The paper ports that tested
the spec, and the reasons behind many decisions, are in `officespeak_ports/`.

Written in today's vocabulary (office, `office.md`). The renaming to *a network
of agents* is deferred and will be a mechanical pass over this document.

Audience: students who know Python, or write it with Claude.

---

## 0. Principles

1. **Three layers, each ignorant of the one above.**
   - **Roles**: one JSON object in, JSON out. They know nothing about DisSysLab.
   - **The office**: agents, routers, coordinators, sources, sinks, and the
     connections between them. Topology is data, written in `office.md`.
   - **The operating system**: delivery, checking, traces, logical clocks,
     checkpoints. Separate Python code; its information never travels inside
     the message JSON.
2. **Nothing out of sight.** The framework does only the steps listed in
   section 8, and each one can be observed.
3. **Compute in roles, route in routers.** A role decides; a router only tests
   one field for equality.
4. **Topology is data, behaviour is code.** `office.md` is declarative and can
   be checked and drawn without running anything. Behaviour lives in roles.
5. **Use a model only where judgement is needed;** use Python everywhere else.
6. **Guardrails are recommended, never required.** Declarations that enable
   checks (`in:`, `out:`, value lists, `needs:`, `emits:`) are optional. The
   requirements on a student are kept to an absolute minimum; the examples
   and the role-writing guide use the guardrails and say why.

## 1. Vocabulary

Six words: **role** (what an agent does), **agent** (a named worker playing a
role), **router**, **coordinator**, **source**, **sink**. Roles come in two
kinds: **annotator** and **author**.

## 2. Messages

- Every message is a JSON object. No strings, numbers or lists as messages.
- Standard field names: `text`, `title`, `source`, `url`, `timestamp`.
- `msg_type` is the *recommended* name for an author's type field. It is not a
  default anywhere.
- Each agent receives its own copy of a message.
- Channels are FIFO. Between different destinations there is no order.

## 3. The office file

### 3.1 Syntax

`office.md` has two kinds of line, declarations (`name: kind(args)`) and
connections (`a -> b`), and borrows Python's syntax for arguments. It is a data
file, not a Python file: it cannot run anything, so `dsl check` can reason
about it statically, and its errors talk about agents and ports.

```
# room_climate_monitor: alert when the room is both hot and humid

sources:
    temp_sensor: file_source(path="temp.jsonl")
    humidity_sensor: file_source(path="humidity.jsonl")

sinks:
    console_printer
    discard

agents:
    Join: synchronizer(on="slot")
    Checker: checker(max_temp=80, max_humidity=60)
    Rex: router(on="alert")

connections:
    temp_sensor -> Join.temp
    humidity_sensor -> Join.humidity
    Join -> Checker -> Rex
    Rex.yes -> console_printer
    Rex.no -> discard
```

**Sections:** `sources:`, `sinks:`, `agents:`, `connections:`, and, for an
office meant to sit inside another, `inputs:` and `outputs:` (3.4). The
office's name is its folder's name; there is no title line. `#` starts a
comment, outside quotes.

**Declarations**, one per line, in `sources:`, `sinks:` and `agents:`:

| Line | Means |
|---|---|
| `name: kind(arg=value, …)` | a `kind` called `name`, built with these arguments |
| `name: kind` | the same with no arguments |
| `kind(arg=value, …)` or `kind` | a `kind` whose name is the kind itself (`console_printer`, `bbc_world(max_articles=3)`) |

- Names are Python identifiers and are case-sensitive. Every name used in a
  connection must be declared, including `discard`; nothing is created
  implicitly.
- Two of the same kind need two names:
  `briefings: jsonl_recorder(path="briefings.jsonl")` and
  `archive: jsonl_recorder(path="archive.jsonl")`.
- Arguments are named, as in a Python call: strings in either quote style,
  numbers, lists, `true`/`false` (or `True`/`False`). They are read with
  Python's `ast.literal_eval`, never executed.
- Every component that reads or writes a file takes it as `path=`.
- As in Python, a declaration continues onto the next line while a
  parenthesis or bracket is open, so a long argument list can be split.
- A kind declared in the wrong section (`file_source` under `sinks:`) is an
  error.

The agent declarations:

| Line | Means |
|---|---|
| `Name: role` | an English or Python role (section 4) |
| `Name: role(k=v, …)` | a Python role constructed with these keyword arguments |
| `Name: role(ai="<backend>")` | an English role, naming the model behind this agent |
| `Name: router(on="<field>")` | a router (section 5) |
| `Name: synchronizer(on="<field>")`, `Name: gate` | coordinators (section 6) |
| `Name: office(path="<path>")` | a nested office (3.4) |
| `Name: unassigned` | a draft agent (3.5) |

An English role takes one argument only, `ai=`. It chooses the model for that
agent and never reaches the prompt (4.2).

**Connections**, one or more per line, in `connections:`:

| Line | Means |
|---|---|
| `a -> b` | `a.out -> b.in` |
| `Rex.yes -> console_printer` | from a named outbox (a router's value) |
| `temp_sensor -> Join.temp` | into a named inbox (a coordinator's, or a nested office's input) |
| `Join -> Checker -> Rex` | a chain: `Join -> Checker` and `Checker -> Rex` |
| `Gate -> Qwen, GPT, Claude` | fan-out: one connection to each |
| `bbc_world, npr_news -> Sasha` | fan-in: one connection from each |

- A port is written only when it is not the default `out` or `in`, with a dot,
  as for a Python attribute. This is the notation of the lecture figures
  (`A.out_0 -> B.in_0`).
- A list (`a, b`) may stand only at either end of a chain.

**Forgiving of:** spacing and indentation, blank lines, comments, either quote
style, `true` or `True`, a trailing comma or period, `->` or `→`, `kind` or
`kind()`, the case of section headings.

**Not forgiving of:** an unknown kind, name or argument, or a port the
component does not have. Each is an error naming the line and suggesting the
nearest word. The parser never guesses.

YAML was considered and rejected: connections do not fit it, and it reads
`yes`, `no` and `on` as booleans.

### 3.2 How a kind is found

`router`, `synchronizer`, `gate`, `office` and `unassigned` are
reserved words, built in. A nested office is found by its path. Every other
kind (a role, source or sink) is searched for first in the office's own folder
(`roles/`, `sources/`, `sinks/`), then in the built-ins. A local file may not
reuse a built-in name or a reserved word: that is an error, not an override.

Local sources and sinks follow the rules for Python roles (4.3): one class per
file, no DisSysLab import.

A file in `roles/`, `sources/` or `sinks/` whose name starts with `_` is a
**helper module**, not a role or component. The framework puts these folders
on the import path, so a role writes `from _signal_common import …` with no
path trick.

### 3.3 Ports

- A role has one inbox, `in`, and one outbox, `out`. Anything with more than
  one inbox is a coordinator.
- A source has one outbox, `out`; a sink has one inbox, `in`.
- A router's outboxes are named by values (section 5).
- A synchronizer's inboxes are the names used in its connections:
  `temp_sensor -> Join.temp` creates the inbox `temp`. `dsl check` lists the
  inboxes it found.
- A gate's inboxes are `in` and `done`.
- A nested office's ports are its declared inputs and outputs (3.4).

### 3.4 Nested offices

- **One form of composition:** an agent line,
  `news_monitor: office(path="../news_monitor")`.
- **An office's boundary ports always have explicit names,** declared under
  `inputs:` and `outputs:` (for example `articles`, `briefings`). They are the
  office's interface, like a function's parameter names. The `in`/`out`
  convention is for the single ports of agents, sources and sinks only.
- **Inside the office,** an input behaves like a source with one outbox,
  `out`: `articles -> Alex`. An output behaves like a sink:
  `Morgan -> briefings`.
- **From outside,** the office's ports are named like any agent's:
  `bbc_world -> news_monitor.articles`,
  `news_monitor.briefings -> news_editor.articles`.
- **Fields across the boundary:** `dsl check` derives which fields enter and
  leave through each boundary port from the inner office's own sources, roles
  and sinks, and shows them in its report. No new declaration.

### 3.5 Drafts

`Jay: unassigned` marks an agent whose role is not decided yet. An office
holding one is a **draft**: `dsl check` and `dsl draw` work on it and list
what is still to do; `dsl run` refuses it. This supports top-down design
(writing and checking the topology before any role exists) and conversational
building (`dsl new`, `dsl edit`, the `office-builder` skill). A role name with
no file is an error, with the nearest name suggested, never a silent draft:
undecided is said explicitly, with `unassigned`.

## 4. Roles

### 4.1 Two kinds

| | Annotator (default) | Author (`kind: author`) |
|---|---|---|
| Returns | one JSON object | a list of JSON objects, always |
| Effect | the object's fields are added to the incoming message; one message out | each object is sent as a complete new message; nothing is merged |
| One message / none | — | a list of one / the empty list |
| Front matter `out:` | the fields it adds | the fields of each object it returns |
| Typical | classifiers, summarizers, evaluators | protocol agents, splitters, filters, the step that starts a loop's next round |

- The kind is about what the role returns, not its language. A Python
  annotator returns a dict; a Python author returns a list and says
  `kind: author` in its docstring, exactly as an English author does.
- **An annotator only adds.** A field in its `out:` that is already produced
  upstream is a `dsl check` error, and at run time a reply that would change a
  field already in the message is a failure (4.5).
- An author's messages to the same destination arrive in the order listed.
- An author that returns an object it received, unchanged, passes it on as it
  is: `[item]` or `[]` is a filter.

### 4.2 English roles

- A role is a `.md` file. **The prompt the model receives is exactly the file's
  text (after the front matter), followed by the incoming message as JSON.**
  The framework appends nothing.
- The text is a complete instruction, including what to return, ending with
  the standard closing sentence for its kind (section 14).
- No wiring words in the text: no "send to", no outbox names.
- No parameters in the text. To adapt a built-in role, copy it into the
  office's `roles/` folder **under a new name** and edit it. The `ai=`
  argument (3.1) is not a parameter of the text.

### 4.3 Python roles

- A role is a `.py` file defining **exactly one class**. No DisSysLab base
  class and no DisSysLab import. It may inherit from a class in the office's
  own helper modules (3.2).
- `__init__(self, **kwargs)` receives the arguments from `office.md`. It builds
  **settings** (fixed for the run) and **resources** (models, connections;
  rebuilt at start, never saved). Only `dsl run` and `dsl try` construct a
  role; `dsl check` reads the constructor's signature and never constructs.
- `__call__(self, item)` returns a dict (annotator) or a list of dicts
  (author). An exception raised here is a failure of that one message (4.5).
- A role that keeps **state** provides `checkpoint(self)`, returning plain
  data, and `restore(self, saved)`. A class without them is stateless.
- A package a role imports is imported inside the method that needs it and
  listed in `needs:` (4.4).
- Examples are always written with the logic in a pure function, which is what
  students test and prove:
  - stateless: `step(item, settings) -> out`;
  - stateful: all state in one serializable dict, `self.state`, and
    `step(item, state, settings) -> (out, new_state)`;
  - calling a model or outside service: the resource is called in
    `__call__` and its result passed in, `step(item, result, …)`, so `step`
    is tested without the service.

```python
"""
---
emits: approves small refunds; escalates the rest
in: amount
out: clerk_decision (approve | escalate)
---
Arguments: limit -- the largest refund the clerk may approve (default 50).
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

### 4.4 Front matter

Read only by Python, never turned into prompt text. In a `.md` file it is the
block between `---` lines; in a `.py` file, the same block in the module
docstring.

| Key | Meaning |
|---|---|
| `emits:` | one line, shown by `dsl roles` |
| `kind:` | `author`; absent means annotator |
| `needs:` | Python only: the packages it imports (`needs: birdnetlib, librosa`). `dsl check` reports any not installed, with the `pip install` line, without importing them; `dsl run` stops before starting if one is missing |
| `in:` | the fields the role needs from its input; checked before the role is called (4.5) |
| `out:` | annotator: the fields it adds; author: the fields of each object it returns |

- **What a field holds** (added 18 Oct 2026). A field in `in:` or `out:` may
  say, in parentheses, what it may hold. These are contracts, checked by
  Python on every message:
  - values: `verdict (publish | revise)`; a single word that is not a type
    is one value, `verdict (yes)`;
  - a number: `price (number)`; a range, ends included, `score (0..10)`;
    one bound, `price (number, >= 0)` or `temp (<= 40)`; `integer` for a
    whole number. A range or bound alone implies `number`. A JSON string
    is not a number, nor is `true`, `NaN` or `Infinity`;
  - text: `reply (text)`, `reply (text, at most 600 chars)`.

  Nothing else: relations between fields (a price above the floor for that
  car) are a Python role's job. The language stays small on purpose; a
  contract that could express anything would need a program to check it.
  Bounded fields are the basis of the planned per-field taint check
  (STATUS): a field with values or a range cannot carry instructions.
- **Conditional lines.** An author whose messages differ by a listed value adds
  `out if` lines below its ordinary `out:`:
  ```
  out: next (finish | continue), problem_id, problem, history
  out if next is finish: final_answer, agreement, rounds_used
  out if next is continue: round
  ```
  Every message has the fields of the first line; a message whose `next` is
  `finish` also has those of the second, and so on. A condition names a field
  and value listed on the first line. `dsl check` uses this to know which
  fields travel down each router branch.
- **Pass-through.** An author that returns its input objects unchanged (a
  filter such as `deduplicator`) says `out: same as in`. The check carries the
  incoming fields through it.
- **No optional fields.** A declared field is required. Data the office does
  not need stays outside it.
- `in:` and `out:` are statements about the role's own input and output, like
  a function's signature. They say nothing about routers, outboxes or
  DisSysLab. They are optional (Principle 6): without them the role runs, and
  only the checks that use them are lost. A check that needs a declaration
  that is absent is skipped, not failed: a router fed by a role with no `out:`
  is not reported by W21.
- `in:` is for checking only; it does not trim the prompt. An English role
  always receives the whole incoming message. A role with no `in:` accepts any
  object, and the end-to-end check skips it. A role fed two kinds of message
  lists in `in:` only the fields both carry, or has no `in:`.
- A role whose input field is chosen by an argument
  (`deduplicator(by="url")`) has no `in:`; its docstring names the argument.
- The same two words are used for sources (`out:`) and sinks (`in:`), and they
  match the port names `in` and `out`.

Removed: `outboxes:`, `inboxes:`, `contract:`, `adds:`.

### 4.5 Checking a role's input and reply

0. Before the role is called, the message must have every field of `in:`,
   each holding what it declares (4.4). A message that does not is a failure
   (5 below), and the role is not called: a model never sees it.
1. Parse the reply as one JSON value. A reply inside a single code fence is
   unwrapped (a declared framework step). Anything else is a failure.
2. Annotator: the value must be an object. Every field in `out:` must be
   present, holding what it declares; a field with listed values must have
   one of them (the error names the closest). It may not change a field
   already in the message.
3. Author: the value must be a list of objects. Each object must have the
   fields of `out:`, plus those of any `out if` line whose condition it meets,
   each holding what it declares.
4. Fields the reply carries but `out:` does not declare are **dropped and
   counted**, for English and Python roles alike. This is not a failure: the
   message continues, and the run summary shows the count as a note naming
   the fields. (Not applied to `out: same as in`.)
5. A failure drops that one message, is counted, and the office continues.
   `dsl run` exits non-zero, and the summary quotes the first failure. An
   exception raised by a Python role's `__call__` is a failure in the same
   way, quoted with the exception.
6. **A stalled office is reported.** A dropped message can leave a loop
   waiting for ever (a gate whose `done` never comes, a synchronizer group
   that never completes). When the office goes quiet, the run summary lists
   every agent still waiting and on which inbox, and every incomplete
   synchronizer group, next to the first failure. Nothing is retried or
   invented.

## 5. Routers

```
agents:
    Rex: router(on="verdict")

connections:
    Eve -> Rex
    Rex.publish -> Editor
    Rex.revise -> Writer
    Rex.otherwise -> Archive     # optional
```

- Every router names its field. There is no default field.
- Its outboxes are named by values. Several values to one place: several
  lines.
- A value used for routing must be a name (letters, digits and `_`, not
  starting with a digit) or `true`/`false`. It matches exactly. A decision that
  is a number is turned into a named value by the role that makes it.
- `otherwise` catches values with no outbox of their own.
- A missing field, or a value with no outbox and no `otherwise`, is a reported
  error. Messages are dropped only by routing them to the `discard` sink.
- The field stays in the message.

## 6. Coordinators

Two: **synchronizer** and **gate**.

| Coordinator | Line | Behaviour |
|---|---|---|
| synchronizer | `Sync: synchronizer(on="url")` | inboxes are the names used in its connections (`Eve -> Sync.entities`); for each value of its key field, waits until a message with that value has arrived on every inbox, merges them into one, sends it |
| gate | `G: gate` | inboxes `in` and `done`: admits one item from `in`, then waits for a message on `done` (which it discards) before admitting the next |

**The synchronizer:**

- **It always names its key,** as a router names its field. With a key, a
  dropped message (4.5) leaves one incomplete group, reported when the run
  ends; the other groups are unaffected. (Pairing the k-th message of each
  inbox would merge different items from then on.)
- No two items in progress at the same time may share a key; a key may recur
  once its group has been sent. A missing key field is a reported error.
- It merges its inputs. A field carried by two inputs with the **same** value
  is not a conflict (parallel annotators each receive a copy of the same item,
  so its original fields are identical). The same field with **different**
  values is a reported error naming the field and the two inboxes; the
  framework never chooses.
- **The collected form,** `synchronizer(on="span", collect="results")`, for
  many identical workers: the message sent is the key plus one field,
  `results`, mapping each inbox name to the message that arrived on it.
  Nothing is merged, so nothing can conflict. (Port 9: 11 backtesters, each
  saying which variant it is in its own `variant` field.)

`select` was removed (port 4): its gallery uses were "one item at a time,
perhaps with one round trip", which a gate and a router express with
annotators only, and its commands put another agent's inbox name inside a
role's code. If it returns, that is the first thing to redesign.

`record` was removed (17 October): no kept example uses it. Shared state
lives in a Python role and travels in the messages (as the debate's
`history` does).

## 7. Sources and sinks

- Every source emits JSON objects. **To fix:** `console_input` (sends a
  string), `natural_numbers` (numbers), `list_source` (whatever it is given).
- A source declares the fields it produces with `out:`, and a sink the fields
  it uses with `in:`, in the component's docstring. With the roles' `in:` and
  `out:`, the whole office's data flow is checked end to end. All RSS sources
  share `rss_normalizer.py`; one declaration there,
  `out: source, title, text, url, timestamp`, covers them all.
- A source whose fields come from data, not code (`file_source`,
  `list_source`), declares no `out:`. `dsl check` reads the data and reports
  the fields it finds; every item must have the same fields.
- A sink that uses no particular field (`console_printer`, `jsonl_recorder`)
  has no `in:` and accepts any object.
- A sink that shows particular fields takes them as arguments, with defaults
  in its docstring, and never guesses field names:
  `intelligence_display(title="headline", text="summary", color="severity")`.
  Its `in:` is whatever those arguments name. `intelligence_display` also
  takes `lines=[…]`, fields printed on their own labelled lines:
  `intelligence_display(title="title", text="abstract", color="relevance",
  lines=["authors", "paper_type", "reason"])`.
- A stand-in source (`file_source`) and a real one (`sources/temp_sensor.py`
  declaring `out: slot, temp`) are interchangeable: only the declaration
  changes.
- A local source or sink is one class, built with its arguments like a
  Python role. A source's instance is called with no arguments and returns
  the next message, or `None` when it has no more; a sink's instance is
  called with each message.
- A local sink's `in:` is checked on arrival, as a role's is (4.5, step 0;
  added 18 Oct 2026): a message that does not fit is a failure and the
  sink does not act on it. Built-in sinks have no front matter yet and are
  not checked.
- `starter` is retired. In all seven offices that use it, it only wakes a role
  standing in for a source.
- The sink aliases that exist only to give a second copy a name
  (`jsonl_recorder_briefing`, `slack_sink_alerts`, `gmail_sink_match`, …,
  about fifteen) are retired: two copies get two names (3.1).

## 8. What the framework does: the complete list

| # | The framework… | Seen with |
|---|---|---|
| 1 | finds a role, source or sink by name: the office's `roles/`, `sources/` or `sinks/`, else the built-ins (3.2) | `dsl check` shows the file each one uses |
| 2 | finds the one class in a Python file; at `dsl run`, constructs it with the `office.md` arguments | `dsl check` (signature only) |
| 3 | gives each agent its own copy of the message | documentation |
| 4 | sends an English role's text unchanged, followed by the message as JSON | `dsl show <role> --prompt` |
| 5 | reads the reply as JSON, unwrapping one code fence, and checks it against the front matter | run summary, `--trace` |
| 6 | annotator: adds the reply's fields; author: sends each object | `--trace` |
| 7 | calls `checkpoint` and `restore` on stateful Python roles | `dsl show-checkpoint` |
| 8 | on a failed message (bad reply or exception): drops and counts it, continues, exits non-zero | run summary |
| 9 | when the office goes quiet: reports the agents still waiting and the incomplete groups (4.5) | run summary |

Everything else in an office is written by the student.

## 9. Checks (`dsl check`, before running)

Codes follow the rule in `check_catalogue.py`: a code means one thing for
ever, and a retired code is never reused. Severity is **error** (the office is
wrong) or **note** (read it).

**Kept, meaning unchanged:** W1 an inbox nothing writes to; W2 an outbox wired
to nothing; W3 an unreachable agent; W4 a dead end; W5 no such source or sink;
W6 no file behind a role; W7 a feedback loop (note); W8 a source with no
destination, or a sink nothing feeds; W9 a name that is nothing at all; W10 a
sub-office that is not there; W11 text from the open web reaching something
that acts (note); W12 a role's own Python reaching outside (note); W13 a
message sent to an inbox that does not exist; W14 sending from an outbox that
does not exist; G1 an agent with no role yet; G2 nothing leaves this office.
The explanations of W2, W13 and W14 are rewritten for single-outbox roles and
routers' value outboxes; their meaning is the same.

**Retired:** W15 (a role file that does not say what its ports are). Roles no
longer declare ports.

**New:**

| Code | Severity | Finding |
|---|---|---|
| W16 | error | the office file is in the old English form (points to 3.1) |
| W17 | error | a kind declared in the wrong section |
| W18 | error | a local role, source or sink reuses a built-in name or a reserved word |
| W19 | error | an argument the component's constructor does not take (nearest name suggested) |
| W20 | error | a Python file defines no class, or more than one |
| W21 | error | a router's field is not produced upstream |
| W22 | error | a field in a role's or sink's `in:` is not produced upstream |
| W23 | error | an annotator's `out:` names a field already produced upstream |
| W24 | error | a synchronizer's key field is not produced on every input |
| W25 | error | a data-driven source's items do not all have the same fields |
| W26 | note | a value listed in the upstream `out:` has no router outbox, and there is no `otherwise` |
| W27 | note | a router outbox names a value not listed in the upstream `out:` (unreachable) |
| W28 | note | a role's text contains wiring words ("send to", outbox names) |
| W29 | note | a declared field or value never appears in the role's text |
| W30 | note | a role adds a field and, on some path from it to a sink that declares `in:`, no step lists the field in its `in:` (a sink with no `in:` uses every field) |
| W31 | note | two inputs of a synchronizer can carry the same field |
| W32 | error | a package in a Python file's `needs:` is not installed (the `pip install` line given) |

## 10. Tools

- `dsl try <role> <input.json>`: run one role on one input, with no office;
  show the prompt (English roles), the raw reply, and the result of the checks.
- `dsl show <role> --prompt`: print exactly what a model receives.
- A round-trip checkpoint test for Python roles: run a sample sequence,
  checkpoint midway, restore into a fresh object, continue, compare with an
  uninterrupted run.
- A run-time note when a class without `checkpoint` changes its own attributes
  between calls.

## 11. Model reliability evaluation (required before release)

Removing the appended contract changes every English role's prompt. Before
release:

- run every built-in and example English role on a fixed set of inputs, old
  form and new form;
- on one small local model and one frontier model;
- several repetitions each; measure valid replies, declared fields present,
  listed values valid, and code fences;
- tune the standard closing sentences until the new form is at least as
  reliable as the old;
- check every example inside a role against that role's own front matter:
  its output has exactly the fields of `out:`, with listed values (port 6
  found a MEDIUM example returning HIGH).

## 12. Examples

About eight, each teaching one idea, rewritten by hand in the new form. The
rest of the gallery and apps moves to an archive (not deleted, not converted)
once the dependencies (tests, skills, lectures, testers) are checked. `paxos`
and `recovery_demo` wait until everything else is done.

| Idea | Example |
|---|---|
| a pipeline of roles | `arxiv_radar` |
| a router (keep/discard) | `org_news_filter` |
| fan-out and a synchronizer | `situation_room_pro` |
| a loop stopped by a gate | `debate` |
| one item at a time with escalation | `returns_desk` |
| a sensing Python role with a resource | `backyard_birds` |
| composing offices | `org_two_office_news`, rebuilt from `org_news_filter`'s filter and the built-in `summarizer` |
| a larger application | `mac_speed_suite` |

Six have been ported on paper (`officespeak_ports/`), together with
`room_climate_monitor`; their new office files and roles are the starting
point. `backyard_birds` and `mac_speed_suite` are not yet ported.

`arxiv_radar` needs its sources fixed first: the arXiv listing scraper
produces no abstract (port 6). The arXiv sources will read arXiv's RSS feed
(`rss.arxiv.org/rss/<category>`), which carries the abstract in each item's
description and the authors in `dc:creator` (checked 16 October), and emit
`out: source, title, authors, abstract, url, timestamp`.

## 13. Migration (one release)

| From | To |
|---|---|
| the English sentence form (`X is a Y.`, `X's out is Y.`) | the line form of 3.1 |
| `Riley's AI is anthropic.` | `Riley: writer(ai="anthropic")` |
| `Sync is a synchronizer(inboxes=[…])` | `Sync: synchronizer(on="<key>")`, inboxes from the connections |
| `merge_synch` | `synchronizer` |
| `network.md` with an `Offices:` section | `Name: office(path="<path>")` in an ordinary `office.md` |
| a source's or input's `destination` outbox | `out` |
| English role with several outboxes and `send_to` | annotator adding a decision field, followed by a router |
| `outboxes:` / `inboxes:` / `contract:` / `adds:` in front matter | `in:`, `out:`, `kind:` |
| "Always send to out", "preserve other fields" in role text | removed |
| framework-appended "Return JSON only…" | the role's own closing sentence |
| Python roles importing `Role` / `AgentRoleEntry`, returning (msg, port) pairs | one class returning a dict or a list |
| a Python role returning `None` to drop a message | an annotator adding a decision field, a router, and `discard` |
| local roles overriding built-in names | renamed |
| roles standing in for sources, woken by `starter` | a local source in `sources/`, or `file_source` with a data file |
| `select` with `{"next": …}` commands | a gate, with a router and annotators |
| sink aliases (`jsonl_recorder_briefing`, …) | named declarations |
| `router_role` | retired |

Only the examples in section 12 are rewritten. `dsl check` on an old-form file
reports W16. The release changes together: wheel, `office-builder` skill,
grammar, reference, toolkit page, microcourse, examples. Install rehearsed
before tagging.

## 14. Teaching order and the role-writing guide

**Order.** Lab 1 uses annotators, routers and the built-in coordinators.
Authors and stateful Python roles come later, with the protocol algorithms.
The dataflow lecture can name the two kinds once: an annotator is a *map*, an
author is a *flat-map*.

**Standard closing sentences:**

- annotator: "Return only a JSON object with the fields `a` and `b`."
- author: "Return only a JSON list of objects, each with the fields …"

**Guidelines** (from the ports; advice, not rules):

- Roles do not print. What a student wants to see goes to a sink, and
  `--trace` shows every message.
- A role should see one kind of message. Where two streams meet in front of
  one role, the two kinds must share a field that tells them apart.
- Let the model judge and Python keep the rules: in `debate` the moderator
  judges agreement, and a Python referee applies the round limit.
- A loop needs an author to start the next round: annotators only add, so the
  next round's message is built fresh.
- Escalation is two annotators each adding its own decision
  (`clerk_decision`, `manager_decision`), which leaves an audit trail.
- A synchronizer's key is a design decision. Independent sensors never stamp
  exactly the same time, so the key must be a value both sides share, such as
  the minute a reading belongs to.
- Name fields for the decision, not the topic (`on_topic`, not
  `about_americas`), so changing the topic is an edit to one paragraph.
- Prefer string values to booleans (`yes`/`no`): they read the same in the
  role, the router line and the trace.
- Near-identical roles (the three `debate` panellists) stay separate files;
  the README says why.
- Swap a stand-in source for a real one without touching the network.
- Teach one connection style: `->` with commas.

## 15. Deferred

- Renaming: office → network of agents, across course pages, CLI text, skill,
  microcourse, toolkit page. Done last, in one release.
- `paxos` and `recovery_demo` as examples.
- Documentation reduced to: a tutorial (the rewritten microcourse), one
  reference, the toolkit page, one setup and troubleshooting page.

## 16. Open

Nothing. All nine paper ports are done, and their proposals were accepted on
16 October. The clean-up of `mac_speed_suite`'s code and its skill (port 9,
findings 6–9) belongs to the code restructuring, not this spec.

## Appendix: two ported offices

`situation_room_pro`:

```
sources:
    bbc_world(max_articles=3)
    npr_news(max_articles=3)
    al_jazeera(max_articles=3)

sinks:
    intelligence_display(title="headline", text="summary", color="severity")
    jsonl_recorder(path="briefings.jsonl")

agents:
    Sasha: deduplicator(by="url")
    Eve: entity_extractor
    Sam: severity_classifier
    Tom: topic_tagger
    Greta: geolocator
    Sync: synchronizer(on="url")
    Riley: writer(ai="anthropic")

connections:
    bbc_world, npr_news, al_jazeera -> Sasha -> Eve, Sam, Tom, Greta
    Eve -> Sync.entities
    Sam -> Sync.severity
    Tom -> Sync.topic
    Greta -> Sync.location
    Sync -> Riley -> intelligence_display, jsonl_recorder
```

`debate`:

```
sources:
    problems: file_source(path="problems.jsonl")

sinks:
    answers: jsonl_recorder(path="debate_answers.jsonl")
    transcript: jsonl_recorder(path="debate_transcript.jsonl")
    debate_display

agents:
    Gate: gate
    Qwen: qwen(ai="openrouter")
    GPT: gpt(ai="openai")
    Claude: claude(ai="anthropic")
    Sync: synchronizer(on="problem_id")
    Riley: moderator
    Ref: referee(max_rounds=2)
    Rex: router(on="next")

connections:
    problems -> Gate -> Qwen, GPT, Claude
    Qwen -> Sync.qwen
    GPT -> Sync.gpt
    Claude -> Sync.claude
    Sync -> Riley -> Ref -> Rex, debate_display
    Sync -> transcript
    Rex.continue -> Qwen, GPT, Claude
    Rex.finish -> answers, Gate.done
```

A throwaway parser read these two and `room_climate_monitor` and produced the
expected 14, 17 and 6 connections, with the synchronizer inboxes derived
correctly.
