# office.md -- the grammar

An office is a folder. Its `office.md` says which sources, sinks and agents
exist and how they are connected. The roles the agents play are files in
`roles/` (section [Roles](#roles) below, and `dsl grammar roles`).

`office.md` is a data file, not a program: it cannot run anything, so
`dsl check` can find every problem in it before anything runs, and its
errors talk about agents and ports.

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

The office's name is its folder's name; there is no title line. `#` starts
a comment, outside quotes.

## Sections

`sources:`, `sinks:`, `agents:`, `connections:`, and, for an office meant to
sit inside another, `inputs:` and `outputs:` ([Nested offices](#nested-offices)).
Each heading stands alone on its line; the items go on the lines below it.

## Declarations

One per line, under `sources:`, `sinks:` and `agents:`.

| Line | Means |
|---|---|
| `name: kind(arg=value, ...)` | a `kind` called `name`, built with these arguments |
| `name: kind` | the same with no arguments |
| `kind(arg=value, ...)` or `kind` | a `kind` whose name is the kind itself: `console_printer`, `bbc_world(max_articles=3)` |

- Names are Python identifiers and are case-sensitive. **Every name used in
  a connection must be declared**, including `discard`. Nothing is created
  implicitly.
- Two of the same kind need two names:
  `briefings: jsonl_recorder(path="briefings.jsonl")` and
  `archive: jsonl_recorder(path="archive.jsonl")`.
- Arguments are named, as in a Python call: strings in either quote style,
  numbers, lists, `true`/`false` (or `True`/`False`). They are read with
  Python's `ast.literal_eval`, never executed.
- Every component that reads or writes a file takes it as `path=`. A path is
  relative to the office's folder.
- A declaration continues onto the next line while a parenthesis or bracket
  is open, as in Python.

The agent declarations:

| Line | Means |
|---|---|
| `Name: role` | an English or Python role ([Roles](#roles)) |
| `Name: role(k=v, ...)` | a Python role, constructed with these keyword arguments |
| `Name: role(ai="openai")` | an English role, naming the model behind this agent |
| `Name: router(on="field")` | a router ([Routers](#routers)) |
| `Name: synchronizer(on="field")`, `Name: gate` | coordinators ([Coordinators](#coordinators)) |
| `Name: office(path="../other")` | a nested office |
| `Name: unassigned` | an agent whose role is not decided yet ([Drafts](#drafts)) |

An English role takes one argument only, `ai=`. It chooses the model for
that agent and never reaches the prompt. Without it, the agent uses the
default model (`DSL_BACKEND`, normally Anthropic's).

## How a kind is found

`router`, `synchronizer`, `gate`, `office` and `unassigned` are reserved
words. Every other kind -- a role, source or sink -- is looked for first in
the office's own folder (`roles/`, `sources/`, `sinks/`), then among the
built-ins (`dsl roles`, `dsl grammar sources`).

- A local file may not reuse a built-in name or a reserved word. That is an
  error, not an override: to change a built-in role, copy it under a new
  name.
- A file whose name starts with `_` is a **helper module**, not a role or
  component. The folders are on the import path, so a role can say
  `from _signal_common import make_signal`.

## Connections

One or more per line, under `connections:`.

| Line | Means |
|---|---|
| `a -> b` | `a.out -> b.in` |
| `Rex.yes -> console_printer` | from a named outbox (a router's value) |
| `temp_sensor -> Join.temp` | into a named inbox (a coordinator's, or a nested office's input) |
| `Join -> Checker -> Rex` | a chain: `Join -> Checker` and `Checker -> Rex` |
| `Gate -> Qwen, GPT, Claude` | fan-out: one connection to each |
| `bbc_world, npr_news -> Sasha` | fan-in: one connection from each |

A port is written only when it is not the default, `out` or `in`, after a
dot. A list (`a, b`) may stand only at either end of a chain.

**Ports:**

- A role has one inbox, `in`, and one outbox, `out`.
- A source has one outbox, `out`; a sink has one inbox, `in`.
- A router's outboxes are named by values.
- A synchronizer's inboxes are the names its connections use:
  `temp_sensor -> Join.temp` creates the inbox `temp`.
- A gate's inboxes are `in` and `done`.
- A nested office's ports are its `inputs:` and `outputs:`.

Each agent receives its own copy of every message. Messages on one
connection arrive in the order sent; between different connections there is
no order.

## Routers

```
agents:
    Rex: router(on="verdict")

connections:
    Eve -> Rex
    Rex.publish -> Editor
    Rex.revise -> Writer
    Rex.otherwise -> Archive     # optional
```

A router tests one field for equality and sends the message on. It decides
nothing: a role decides, by adding the field, and the router routes.

- Every router names its field; there is no default.
- Its outboxes are named by values; several values to one place are
  several lines. A value is a name (letters, digits, `_`) or `true`/`false`.
- `otherwise` takes the values with no outbox of their own.
- A missing field, or a value with no outbox and no `otherwise`, is a
  reported failure. To drop messages on purpose, route them to `discard`.
- The field stays in the message.

## Coordinators

**`synchronizer(on="key")`** joins messages that belong together. For each
value of the key field it waits until a message with that value has arrived
on **every** inbox, merges them into one, and sends it.

```
agents:
    Sync: synchronizer(on="url")
connections:
    stories -> Eve, Sam
    Eve -> Sync.entities
    Sam -> Sync.severity
    Sync -> Riley
```

- The key is a design decision: a value both sides share. Two sensors never
  stamp exactly the same time, so `room_climate_monitor` joins on the
  minute a reading belongs to (`slot`).
- A field carried by two inputs with the **same** value is fine (parallel
  roles each get a copy of the same item). The same field with **different**
  values is a reported failure naming both inboxes; the framework never
  chooses.
- If one branch drops a message, only that key's group stays incomplete.
  Incomplete groups are reported when the run ends.
- **The collected form,** `synchronizer(on="span", collect="results")`, for
  many identical workers: the message sent is the key plus one field,
  `results`, mapping each inbox name to its message. Nothing is merged.

**`gate`** keeps one item in progress at a time. It admits one message from
`in`, then waits for a message on `done` (which it throws away) before
admitting the next.

```
connections:
    tickets -> Gate -> Clerk -> Rex
    Rex.approve -> jsonl_recorder, Gate.done
    Rex.escalate -> Manager -> jsonl_recorder, Gate.done
```

## Nested offices

An office can be one agent of a bigger office:
`news_monitor: office(path="news_monitor")`.

- The inner office names its boundary under `inputs:` and `outputs:`.
  Inside it, an input behaves as a source (`articles -> Felix`) and an
  output as a sink (`Rex.yes -> kept`).
- From outside, those are its ports:
  `bbc_world -> news_monitor.articles`,
  `news_monitor.kept -> news_editor.articles`.

`dissyslab/gallery/org_two_office_news` is built this way.

## Drafts

`Jay: unassigned` marks an agent whose role is not decided yet. An office
with one is a **draft**: `dsl check` and `dsl draw` work on it, and say what
is still to do; `dsl run` refuses it. A role name with no file behind it is
an error, never a silent draft.

## Forgiving, and not

Forgiving of: spacing and indentation, blank lines, comments, either quote
style, `true` or `True`, a trailing comma, `->` or `→`, `kind` or `kind()`,
the case of section headings.

Not forgiving of: an unknown kind, name or argument, or a port that does not
exist. Each is an error naming the line, with the nearest word suggested.
Nothing is guessed. The version 1 sentence form (`Alex is a writer.`) is
reported as such, with the line it was found on.

## Roles

What an agent does is a role: a file in the office's `roles/` folder, or a
built-in (`dsl roles`). `dsl grammar roles` has the whole story; in short:

- An **English role** is a `.md` file: front matter, then the instruction the
  model receives, word for word, followed by the message as JSON.
- A **Python role** is a `.py` file with exactly one class: built with the
  arguments from `office.md`, called with each message.
- An **annotator** (the default) returns one object whose fields are added
  to the message. An **author** (`kind: author`) returns a list of complete
  new messages.
- The front matter's `in:` and `out:` are **contracts**, checked by Python
  on every message: `in:` before the role is called, `out:` on its reply. A
  field may say what it holds: `verdict (yes | no)`, `price (number, >= 0)`,
  `score (0..10)`, `reply (text, at most 600 chars)`.

## Checking it

```
dsl check .
```

reports every problem at once, by line, without running anything or
loading any model:

```
broken/office.md:
  problem: line 6: a gate takes no arguments.
  problem: line 7: no agent called 'clerck' in roles/ or the built-ins. Did you mean 'clerk'?
  problem: line 9: roles/manager.py: front matter line 3: 'decision (yes | no' is not a field, or a field with values like 'verdict (yes | no)'.
  problem: line 11: an English role takes only ai=, not style. See `dsl grammar roles`.
  problem: line 14: Gate has inboxes in and done; it has no 'finished'. See `dsl grammar`, Ports.
  problem: line 16: Manager has one outbox, out; it has no 'yes'. See `dsl grammar`, Ports.
  note: line 10: Jay is unassigned, so this office is a draft: it can be checked, not run.
```

It checks the syntax, that every kind exists, every role's front matter,
the packages a Python role `needs:`, the arguments of routers,
synchronizers, gates and English roles, nested offices, and every port.

**Notes** are things that are probably mistakes, or worth knowing; they
never fail the check. A router whose outbox names a value that the role
feeding it never produces (`Rex.aprove`, when the role declares
`approve | escalate`) gets a note naming the nearest value, and so does a
declared value with no outbox and no `otherwise`. This works when the
role lists its values in `out:`.

Two notes are about what an office can do rather than whether it runs.
Guardrails are recommended, never required, so they never fail the check:

- **Text from the open web can reach something that acts.** A source that
  carries other people's words (a news feed, an inbox) has a path to a sink
  that sends mail, posts to Slack, or calls out. Whoever writes those words
  is writing to a model, and through it to that sink. If that is not what
  you meant, put an **author** role before the sink that sends on only the
  fields you chose -- a label, a score, a URL -- listed in its `out:`. Fields
  it does not list are dropped, so the original text stops there, and the
  note goes away. An annotator cannot do this: the message it passes on
  still carries everything that came in.
- **A Python file reaches past the office's sinks.** It imports a network or
  process module, or calls `eval` and the like. The check reads imports; it
  cannot see what the code does. If you did not write the file, read it.

## Running it

```
dsl run .
```

builds the office in memory and runs it until every source has finished and
every message has been dealt with, then prints a summary:

```
Run summary (messages):
  returns_desk::Clerk             sent      4   received      4
  returns_desk::Gate              sent      4   received      8
  ...
```

- A message that does not fit a role's `in:`, a reply that does not fit
  its front matter, or Python that raises, costs that one message: it is
  reported, the office carries on, and `dsl run` exits non-zero.
- An agent left holding work it can never finish -- a gate whose `done`
  never comes, a synchronizer group that never completes -- is reported as
  **Stalled**, with the path of empty connections and idle agents that
  proves nothing can release it.
- `dsl run --quiet` leaves out the summary.

## The other commands

```
dsl draw .              every declaration and arrow, and what is connected to nothing
dsl draw . --mermaid    the same as a Mermaid diagram (paste into GitHub)
dsl roles               the built-in roles and the fields each one adds
dsl show summarizer     a built-in role, whole
dsl list                the gallery
dsl init debate my_debate    copy a gallery office into a folder of your own
dsl doctor              whether this install can run an office
```
