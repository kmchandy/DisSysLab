# OfficeSpeak, revised — specification draft

Status: **draft, 15 October 2026.** Nothing here is implemented. Every item is
marked **Settled** (agreed with Mani) or **Open** (needs a decision). Written
in today's vocabulary (office, office.md); the renaming to *a network of
agents* is deferred and will be a mechanical pass over this document.

Audience for the system: students who know Python, or write it with Claude.

---

## 0. Principles (Settled)

1. **Three layers, each ignorant of the one above.**
   - **Roles**: one JSON object in, JSON out. They know nothing about DisSysLab.
   - **The office**: agents, routers, coordinators, sources, sinks, and the
     connections between them. Topology is data, written in `office.md`.
   - **The operating system**: delivery, checking, traces, logical clocks,
     checkpoints. Separate Python code; its information never travels inside
     the message JSON.
2. **Nothing out of sight.** The framework does only the steps listed in
   section 8, and each one can be observed.
3. **Compute in roles, route in routers.** A role decides; a router only
   tests one field for equality.
4. **Topology is data, behaviour is code.** `office.md` is declarative and can
   be checked and drawn without running anything. Behaviour lives in roles.
5. **Use a model only where judgement is needed;** use Python everywhere else.

## 1. Vocabulary (Settled)

Six words: **role** (what an agent does), **agent** (a named worker playing a
role), **router**, **coordinator**, **source**, **sink**. Roles come in two
kinds: **annotator** and **author**.

## 2. Messages (Settled)

- Every message is a JSON object. No strings, numbers or lists as messages.
- Standard field names: `text`, `title`, `source`, `url`, `timestamp`.
- `msg_type` is the *recommended* name for an author's type field. It is not
  a default anywhere.
- Each agent receives its own copy of a message.
- Channels are FIFO. Between different destinations there is no order.

## 3. The office file

### 3.0 Syntax (Settled, 16 October: replaces the English sentence form)

The students know Python. The office file therefore drops the English
sentences (`Rex is a router(…)`, `Eve's out is Rex.`) for a format with two
kinds of line, and borrows Python's syntax for arguments. It is a data file,
not a Python file: it cannot run anything, so `dsl check` can reason about it
statically and its errors talk about agents and ports. (YAML was considered
and rejected: connections do not fit it, and it reads `yes`/`no`/`on` as
booleans.)

**Example** (`room_climate_monitor`):

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

**Sections.** `sources:`, `sinks:`, `agents:`, `connections:`, and for an office
meant to sit inside another, `inputs:` and `outputs:`. The office's name is its
folder's name; there is no title line. `#` starts a comment, outside quotes.

**Declarations:** one per line, in `sources:`, `sinks:` and `agents:`.

| Line | Means |
|---|---|
| `name: kind(arg=value, …)` | a `kind` called `name`, built with these arguments |
| `name: kind` | the same with no arguments |
| `kind(arg=value, …)` or `kind` | a `kind` whose name is the kind itself (`console_printer`, `bbc_world(max_articles=3)`) |
| `Jay: unassigned` | a draft agent (3.5) |
| `monitor: office(path="../news_monitor")` | a nested office (3.4) |

- Names are Python identifiers and are case-sensitive. Every name used in a
  connection must be declared; nothing is created implicitly.
- Arguments are named, as in a Python call: strings in either quote style,
  numbers, lists, `true`/`false` (or `True`/`False`). They are read with
  Python's `ast.literal_eval`, never executed.
- An English role takes one argument, `ai="<backend>"`: the model behind that
  agent (`Riley: writer(ai="anthropic")`). It is about the agent, not the
  prompt, so 4.2's "no parameters" still holds for the text. This replaces
  `Riley's AI is anthropic.`
- A kind declared in the wrong section (`file_source` under `sinks:`) is an
  error.

**Connections:** one or more per line, in `connections:`.

| Line | Means |
|---|---|
| `a -> b` | `a.out -> b.in` |
| `Rex.yes -> console_printer` | a named outbox (a router's value) |
| `temp_sensor -> Join.temp` | a named inbox (a coordinator's, or an inner office's input) |
| `Join -> Checker -> Rex` | a chain: `Join -> Checker` and `Checker -> Rex` |
| `Gate -> Qwen, GPT, Claude` | fan-out: one connection to each |
| `bbc_world, npr_news -> Sasha` | fan-in: one connection from each |

- A port is written only when it is not the default `out` or `in`, with a dot,
  as for a Python attribute. This is the notation of the lecture figures
  (`A.out_0 -> B.in_0`).
- A list (`a, b`) may stand only at either end of a chain.
- **A synchronizer's inboxes are the names used in its connections.**
  `temp_sensor -> Join.temp` creates the inbox `temp`; there is no
  `inboxes=[…]` argument, so each name is written once. `dsl check` lists the
  inboxes it found. A gate's inboxes are always `in` and `done`.
- **A router's outboxes are its values** (section 5), so a value used for
  routing must be a name: letters, digits and `_`, not starting with a digit,
  or `true`/`false`. A role whose decision is a number routes on a field it
  names instead. (This narrows 5's "numbers by their written form".)

**Forgiving of:** spacing and indentation, blank lines, comments, either quote
style, `true` or `True`, a trailing comma or period, `->` or `→`, `kind` or
`kind()`, the case of section headings.

**Not forgiving of:** an unknown kind, name or argument, or a port the
component does not have. Each is an error naming the line and suggesting the
nearest word. The parser never guesses.

**Migration.** The English form is not accepted after the release. Only the
examples kept for the first release (section 12) are rewritten, by hand; the
rest of the gallery and apps is archived as it stands, not converted. There is
no `dsl convert`. `dsl check` on an old file says it is in the old form and
points to this section.

| Old | New |
|---|---|
| `Sinks: briefings is a jsonl_recorder(path=…)` | `briefings: jsonl_recorder(path=…)` under `sinks:` |
| `Rex is a router(on="verdict").` | `Rex: router(on="verdict")` |
| `Sync is a synchronizer(inboxes=["a", "b"], on="url").` | `Sync: synchronizer(on="url")`, inboxes from the connections |
| `Riley's AI is anthropic.` | `Riley: writer(ai="anthropic")` |
| `news_monitor is an office at ../news_monitor.` | `news_monitor: office(path="../news_monitor")` |
| `Eve's out is Rex.` | `Eve -> Rex` |
| `Rex's publish is Editor.` | `Rex.publish -> Editor` |
| `Eve's out is Sync's entities.` | `Eve -> Sync.entities` |
| `Sasha's out is Eve, Sam.` | `Sasha -> Eve, Sam` |

The rest of this document uses this form. The meanings settled in 3.1–3.5
before 16 October are unchanged; only the spelling changed.

**Tests of the syntax.** A throwaway parser (about 100 lines) read the three
files below and produced the expected declarations and connections: 6, 17 and
14 connections, with the synchronizer inboxes derived correctly.

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

What the tests showed:

- The connections section shrinks from 10 sentences to 8 lines in `debate`,
  and from 10 to 6 in `situation_room_pro` (fan-in on one line); the loop in
  `debate` reads in two lines
  (`Rex.continue -> …`, `Rex.finish -> …, Gate.done`).
- `file_source` takes `filepath=` today and `jsonl_recorder` takes `path=`.
  **To fix:** one name, `path`, for every component that reads or writes a
  file.
- `#` inside a quoted argument (`path="notes#1.txt"`) must not start a
  comment; the parser must strip comments outside quotes only.

### 3.1 Sections (Settled)

`sources:`, `sinks:`, `agents:`, `connections:`, and, for an office meant to
sit inside another, `inputs:` and `outputs:` (3.0).

**Settled (port 2):** a source or sink may be named like an agent, so one
office can hold two of the same kind:

```
sinks:
    briefings: jsonl_recorder(path="briefings.jsonl")
    archive: jsonl_recorder(path="archive.jsonl")
    console_printer
```

An unnamed one is called by its component name. The aliases that exist only to
give a second copy a name (`jsonl_recorder_briefing`, `slack_sink_alerts`,
`gmail_sink_match`, …, about fifteen) retire.

### 3.2 Agent lines (Settled)

| Form | Means |
|---|---|
| `Name: role` | an English or Python role |
| `Name: role(k=v, …)` | a Python role constructed with these keyword arguments |
| `Name: role(ai="<backend>")` | an English role with the model behind it named |
| `Name: router(on="<field>")` | a router (section 5) |
| `Name: synchronizer(on="<field>")`, `Name: gate`, `Name: record(…)` | coordinators (section 6) |
| `Name: office(path="<path>")` | a nested office (3.4): the only form of composition |
| `Name: unassigned` | a draft agent (3.5) |

English roles take no arguments except `ai` (3.0, 4.2).

**Settled (port 3): how the kind after the colon is found.** `router`,
`synchronizer`, `gate`, `record`, `office` and `unassigned` are reserved
words, built in. A nested office is found by its path. Every other name (a
role, source or sink) is searched for first in the office's own folder
(`roles/`, `sources/`, `sinks/`), then in the built-ins. A local file may not
reuse a built-in name or a reserved word: that is an error, not an override.
Local sources and sinks follow the Python-role rules (4.3): one class per file,
no DisSysLab import.

### 3.3 Connections

- Form: `a -> b`, with chains, fan-out and fan-in (3.0). A named port is
  written with a dot: `Rex.publish -> Editor`, `Eve -> Sync.entities`.
- **A role has one outbox, always called `out`:** `Eve -> Rex`. (Settled)
- **A router's outboxes are named by values:** `Rex.publish -> Editor`.
  (Settled)
- A role and a sink each have one unnamed inbox. Coordinators have named
  inboxes. (Settled)
- **Settled:** a source's outbox is `out` only. `destination` is reported by
  `dsl check` with the replacement. Same convention wherever possible: a
  single outbox is `out`, a single inbox is `in`.

### 3.4 Nested offices (Settled)

- **One form of composition:** an agent line,
  `news_monitor: office(path="../news_monitor")`. The separate `network.md`
  file with its own `Offices:` section is retired.
- **An office's boundary ports always have explicit names,** declared in its
  `inputs:` and `outputs:` sections (for example `articles` under `inputs:`,
  `briefings` under `outputs:`). They are the office's interface, like a
  function's parameter names. The `in`/`out` convention is for the single
  ports of agents, sources and sinks only.
- **Inside the office, an input behaves like a source with one outbox, `out`:**
  `articles -> Alex`. An output behaves like a sink: `Morgan -> briefings`.
- **From outside,** the office's ports are named like any agent's:
  `bbc_world -> news_monitor.articles` and
  `news_monitor.briefings -> news_editor.articles`.
- **Fields across the boundary:** `dsl check` derives which fields enter and
  leave through each boundary port from the inner office's own sources, roles
  and sinks, statically, and shows them in its report. No new declaration.

### 3.5 Drafts (Settled: kept)

`Jay: unassigned` marks an agent whose role is not decided yet. An office
holding one is a **draft**: `dsl check` and `dsl draw` work on it and list
what is still to do; `dsl run` refuses it. This supports top-down design,
writing and checking the topology before any role exists, and conversational
building (`dsl new`, `dsl edit`, the `office-builder` skill). A role name with
no file is an error (with the nearest name suggested), never a silent draft:
undecided is said explicitly, with `unassigned`.

## 4. Roles

### 4.1 Two kinds (Settled)

| | Annotator (default) | Author (`kind: author`) |
|---|---|---|
| Returns | one JSON object | a list of JSON objects, always |
| Effect | the object's fields are added to the incoming message; one message out | each object is sent as a complete new message; nothing is merged |
| One message / none | — | a list of one / the empty list |
| Front matter `out:` | the fields it adds | the fields of each object it returns |
| Typical | English: classifiers, summarizers, evaluators | Python: protocol agents, splitters |

An author's messages to the same destination arrive in the order listed.

**Settled (port 2): an annotator only adds.** A field in its `out:` that is
already produced upstream (by a source or a role) is a `dsl check` error, and
at run time a reply that would change a field already in the message is a
failure (4.5). This is the old `adds: text` bug, which overwrote an article's
body.

Every role has exactly one inbox. Anything with more than one inbox is a
coordinator.

The two kinds are the same for English and Python roles: the kind is about
what the role returns, not the language it is written in. A Python
annotator returns a dict; a Python author returns a list and says
`kind: author` in its docstring, exactly as an English author does.

### 4.2 English roles (Settled)

- A role is a `.md` file. **The prompt the model receives is exactly the
  file's text (after the front matter), followed by the incoming message as
  JSON.** The framework appends nothing.
- The text is a complete instruction, including what to return. The
  role-writing guide gives one standard closing sentence per kind, for example:
  - annotator: "Return only a JSON object with the fields `a` and `b`."
  - author: "Return only a JSON list of objects, each with the fields …"
- No wiring words in the text: no "send to", no outbox names.
- **No parameters** in the text. (The one argument an English role takes,
  `ai=`, chooses the model and never reaches the prompt; 3.0.) To adapt a
  built-in role, copy it into the office's
  `roles/` folder **under a new name** and edit it.
- A local role may not reuse a built-in role's name: that is an error, not an
  override.

### 4.3 Python roles (Settled)

- A role is a `.py` file defining **exactly one class**. No base class, no
  DisSysLab import.
- `__init__(self, **kwargs)` receives the arguments from `office.md`. It builds
  **settings** (fixed for the run) and **resources** (models, connections;
  rebuilt at start, never saved).
- `__call__(self, item)` returns a dict (annotator) or a list of dicts (author).
- A role that keeps **state** provides `checkpoint(self)`, returning plain
  data, and `restore(self, saved)`. A class without them is stateless.
- Examples are always written with all state in one serializable dict,
  `self.state`, and the logic in a pure function
  `step(item, state, settings) -> (out, new_state)`, which is what students
  test and prove. A stateless role's example form is
  `step(item, settings) -> out` (port 3).

### 4.4 Front matter (Settled)

Read only by Python, never turned into prompt text. In a `.md` file it is the
block between `---` lines; in a `.py` file, the same block in the module
docstring.

| Key | Meaning |
|---|---|
| `emits:` | one line, shown by `dsl roles` |
| `kind:` | `author`; absent means annotator |
| `in:` | the fields the role uses from its input |
| `out:` | annotator: the fields it adds; author: the fields of each object it returns. A field may list its values, e.g. `out: verdict (publish \| revise), feedback` or `out: msg_type (log \| command)` |

`in:` and `out:` are statements about the role's own input and output, like a
function's signature. They say nothing about routers, outboxes or DisSysLab,
and they are optional: without them the role runs, and only the checks that
use them are lost. The same two words are used for sources (`out:`) and sinks
(`in:`), and they match the port names `in` and `out`.

`in:` is used for checking only; it does not trim the prompt. An English role
always receives the whole incoming message (4.2). A role or sink with no `in:`
accepts any object, and the end-to-end check skips it.

**Settled (port 2):**

- An author that returns its input objects unchanged (a filter, such as
  `deduplicator`, returning `[item]` or `[]`) says `out: same as in`. The
  check carries the incoming fields through it, and no field is dropped.
- A role whose input field is chosen by an argument
  (`deduplicator(by="url")`) has no `in:`; its docstring names the argument,
  and the check skips it.

**Settled (port 3):**

- **An author whose messages differ by a listed value** adds conditional
  `out:` lines below its ordinary one, in the same front matter:
  ```
  out: next (finish | continue), problem_id, problem, history
  out if next is finish: final_answer, agreement, rounds_used
  out if next is continue: round
  ```
  Every message has the fields of the first line; a message whose `next` is
  `finish` also has those of the second, and so on. A condition names a field
  and value already listed on the first line. `dsl check` uses this to know
  which fields travel down each router branch.
- **There are no optional fields.** A declared field is required. Data the
  office does not need stays outside it: in `debate`, the answer keys are in
  a separate file, joined with the results on `problem_id` after the run, so
  no model sees them.

Removed: `outboxes:`, `inboxes:`, `contract:`, `adds:`.

### 4.5 Checking a role's reply (Settled)

1. Parse the reply as one JSON value. A reply inside a single code fence is
   unwrapped (a declared framework step). Anything else is an error.
2. Annotator: the value must be an object. Every declared field must be
   present; a field with listed values must have one of them (the error names
   the closest). Undeclared fields are **dropped and counted**, for English
   and Python roles alike.
3. Author: the value must be a list of objects. Each object must have the
   fields declared in `out:`, plus those of any conditional `out if` line
   whose condition it meets; a field with listed values must have one of
   them. Undeclared fields are dropped and counted, as for an annotator.
4. A failure drops that one message, is counted, and the office continues;
   `dsl run` exits non-zero and the summary quotes the first failure.
5. Dropped undeclared fields are not failures: the message continues, the
   count appears in the run summary as a warning naming the fields, and the
   exit code is unaffected.

## 5. Routers (Settled)

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
- Outboxes are named by values. Several values to one place: several lines.
- Values match exactly; booleans and numbers by their written form (`true`, `3`).
- `otherwise` catches unnamed values. Messages are dropped only by routing them
  to the `discard` sink.
- A missing field, or a value with no outbox and no `otherwise`, is a reported
  error.
- The field stays in the message.
- The existing `router_role` (copy to every matching rule; unused) is retired.

## 6. Coordinators

The kept set: **synchronizer, gate, record**, as named recipes on one
general coordinator. `merge_synch` becomes `synchronizer`: one name for one
idea. (Settled)

**Settled (port 4): `select` is removed** until an example needs it. Its two
gallery uses (`returns_desk`, `trading_room`) are "one item at a time, perhaps
with one round trip", which a gate and a router express with annotators only.
Its commands (`{"next": "<inbox>"}`) also put another agent's inbox name
inside a role's code, against Principle 0. If it returns, that is the first
thing to redesign.

| Coordinator | Line | Behaviour |
|---|---|---|
| synchronizer | `Sync: synchronizer(on="url")` | inboxes are the names used in its connections (`Eve -> Sync.entities`); for each value of its key field, waits until a message with that value has arrived on every inbox, merges them into one, sends it |
| gate | `G: gate` | inboxes `in` and `done`: admits one item from `in`, then waits for a message on `done` (which it discards) before admitting the next |
| record | `R: record(…)` | keeps shared data; agents read and write it by request |

**Settled:** the synchronizer merges its inputs. A field carried by two inputs
with the **same** value is not a conflict (the usual case: parallel
annotators each receive a copy of the same item, so its original fields are
identical). The same field with **different** values is a reported error,
naming the field and the two inboxes; the framework never chooses. `dsl check`
warns in advance when two branches can add the same field.

**Settled (port 2): every synchronizer names its key,** as every router names
its field: `on="url"`. Pairing the k-th message of each inbox fails after one
dropped message (4.5): every later round would merge different items. With a
key, a dropped message leaves one incomplete group, which is reported when the
run ends, and the other groups are unaffected. No two items in progress at
the same time may share a key; a key may recur once its group has been sent
(in `situation_room_pro` the deduplicator makes `url` unique; in `debate`
`problem_id` recurs every round, and the gate keeps one problem in progress).
A missing key field is a reported error.

Teaching note (port 5): the key is a design decision. Independent sensors
never stamp exactly the same time, so the key must be a value both sides
share, such as the minute slot a reading belongs to.

## 7. Sources and sinks

- Every source emits JSON objects. **To fix:** `console_input` (sends a string),
  `natural_numbers` (numbers), `list_source` (whatever it is given). (Settled)
- **Settled:** a source declares the fields it produces with `out:`, and a sink
  the fields it uses with `in:`, in the component's docstring. With roles'
  `in:` and `out:`, the whole office's data flow can be checked end to end.
- A sink that uses no particular field (`console_printer`, `jsonl_recorder`)
  has no `in:` and accepts any object. All RSS sources share
  `rss_normalizer.py`; one declaration there,
  `out: source, title, text, url, timestamp`, covers them all.
- **Settled (port 5):** a source whose fields come from data, not code
  (`file_source`, `list_source`), declares no `out:`. `dsl check` reads the data
  and reports the fields it finds; every item must have the same fields, or it
  is an error. The check shows what it derived, as for a nested office's
  boundary fields (3.4).
- **Settled (port 5):** a stand-in source (`file_source`) and a real one
  (`sources/temp_sensor.py` declaring `out: slot, temp`) are interchangeable:
  only its line under `sources:` changes.
- **Settled (port 5):** `starter` is retired if the four gallery offices not
  yet checked use it, as the three ports did, only to wake a role standing in
  for a source.
- **Settled (port 2):** a sink that shows particular fields takes them as
  arguments, with defaults stated in its docstring, and never guesses field
  names: `intelligence_display(title="headline", text="summary",
  color="severity")`. Its `in:` is whatever those arguments name. (Today
  `intelligence_display` prints `title` and `text` and colours by the first of
  five field names it finds, so in `situation_room_pro` the writer's
  `headline` and `summary` never reach the screen.)

## 8. What the framework does — the complete list (Settled)

| # | The framework… | Seen with |
|---|---|---|
| 1 | finds a role, source or sink by name: the office's `roles/`, `sources/` or `sinks/`, else the built-ins (reusing a built-in name or reserved word is an error; 3.2) | `dsl check` shows the file each agent uses |
| 2 | finds the one class in a Python role file and constructs it with the `office.md` arguments | `dsl check` |
| 3 | gives each agent its own copy of the message | documentation |
| 4 | sends an English role's text unchanged, followed by the message as JSON | `dsl show <role> --prompt` |
| 5 | reads the reply as JSON, unwrapping one code fence, and checks it against the front matter | run summary, `--trace` |
| 6 | annotator: adds the reply's fields; author: sends each object | `--trace` |
| 7 | calls `checkpoint` and `restore` on stateful Python roles | `dsl show-checkpoint` |
| 8 | on a failed message: drops and counts it, continues, exits non-zero | run summary |

Everything else in an office is written by the student.

## 9. Checks (`dsl check`, before running)

New (Settled in principle; codes to be assigned):

| Severity | Finding |
|---|---|
| error | a router's field is not added upstream |
| error | a field in a role's or sink's `in:` is not produced upstream |
| error | `office.md` passes an argument the Python role's constructor does not take (nearest name suggested) |
| error | a Python role file defines no class, or more than one |
| error | a local role reuses a built-in role's name |
| error | an annotator's `out:` names a field already produced upstream (4.1) |
| error | a synchronizer's key field is not produced on every input |
| warning | a value listed in the upstream role's `out:` has no router outbox and there is no `otherwise` |
| warning | a router outbox names a value not listed in the upstream role's `out:` (unreachable) |
| warning | a role's text contains wiring words ("send to", outbox names) |
| warning | a declared field or value never appears in the role's text |
| warning | a role adds a field and, on some path from it to a sink that declares `in:`, no step lists the field in its `in:` (a sink with no `in:` uses every field) |
| warning | two inputs of a synchronizer can carry the same field |

Existing codes that read role-declared outboxes (W2, W13) change meaning or
retire. **Open:** the full renumbering.

## 10. Tools

- `dsl try <role> <input.json>`: run one role on one input, with no office;
  show the prompt (English roles), the raw reply, and the result of the checks.
- `dsl show <role> --prompt`: print exactly what a model receives.
- A round-trip checkpoint test for Python roles: run a sample sequence,
  checkpoint midway, restore into a fresh object, continue, compare with an
  uninterrupted run.
- A run-time warning when a class without `checkpoint` changes its own
  attributes between calls.

## 11. Model reliability evaluation (Settled: required before release)

Removing the appended contract changes every English role's prompt. Before
release:

- run every built-in and example English role on a fixed set of inputs, old
  form and new form;
- on one small local model and one frontier model;
- several repetitions each; measure valid replies, declared fields present,
  listed values valid, and code fences;
- tune the standard closing sentences until the new form is at least as
  reliable as the old.

## 12. Examples (Settled for the first release)

About eight, each teaching one idea: a pipeline of roles; a router
(keep/discard); fan-out and a synchronizer (`situation_room_pro`); a loop
stopped by a gate (`debate`); one item at a time with escalation, a gate and
two annotators (`returns_desk`); a
sensing Python role with a resource (`backyard_birds`); composing offices;
`mac_speed_suite`. The rest of the gallery moves to an archive (not deleted)
once the dependencies (tests, skills, lectures, testers) are checked.
`paxos` and `recovery_demo` wait until everything else is done.

Before implementation, five offices are ported **on paper** to test this
specification: `org_news_filter`, `situation_room_pro`, `debate`,
`returns_desk`, `room_climate_monitor`.

## 13. Migration (Settled: one release)

| From | To |
|---|---|
| English role with several outboxes and `send_to` | annotator adding a decision field, followed by a router |
| `outboxes:` / `inboxes:` / `contract:` / `adds:` in front matter | `in:`, `out:`, `kind:` |
| "Always send to out", "preserve other fields" in role text | removed |
| framework-appended "Return JSON only…" | the role's own closing sentence |
| `contract: structured` roles (debate panellists) | annotators with `out:` |
| Python roles importing `Role` / `AgentRoleEntry`, returning (msg, port) pairs | callable classes returning dicts or lists |
| `merge_synch` | `synchronizer` |
| `router_role` | retired |
| a source's or input's `destination` outbox | `out` |
| `network.md` with an `Offices:` section | `Name: office(path="<path>")` in an ordinary `office.md` |
| the English sentence form (`X is a Y.`, `X's out is Y.`) | the line form of 3.0; kept examples rewritten by hand, the rest archived unconverted |
| local roles overriding built-in names | renamed |
| `select` with commands `{"next": …}` (`returns_desk`, `trading_room`) | a gate, with a router and annotators (port 4) |
| roles standing in for sources, woken by `starter` | a local source in `sources/`, or `file_source` with a data file (port 5) |
| a Python role returning `None` to drop a message | an annotator adding a decision field, a router, and the `discard` sink (port 5) |

Old offices fail `dsl check` with a message saying how to convert them. The
release changes together: wheel, `office-builder` skill, grammar, reference,
toolkit page, microcourse, examples. Install rehearsed before tagging.

## 14. Teaching order (Settled)

Lab 1 uses annotators, routers and the built-in coordinators. Authors and
stateful Python roles come later, with the protocol algorithms. The
dataflow lecture can name the two kinds once: an annotator is a *map*, an
author is a *flat-map*.

## 15. Deferred

- Renaming: office → network of agents, across course pages, CLI text, skill,
  microcourse, toolkit page. Done last, in one release.
- `paxos` and `recovery_demo` as examples.
- Documentation reduced to: a tutorial (the rewritten microcourse), one
  reference, the toolkit page, one setup and troubleshooting page.

## 16. Open questions (summary)

Settled on 15 October: a source's outbox is `out` only; front matter uses
`in:` and `out:` everywhere; the synchronizer reports conflicting values.

Also settled: `unassigned` drafts are kept; nested offices use explicit
boundary names, `out` inside for inputs, one composition form, and derived
boundary fields.

From the paper ports (`officespeak_ports/`): `in:` does not trim the prompt;
dropped undeclared fields are a warning, not a failure; an annotator only
adds; `out: same as in`; every synchronizer names its key; display sinks take
field names as arguments; named sources and sinks; the unused-field warning;
reserved words and local `sources/`/`sinks/` folders; conditional `out if`
lines; no optional fields; synchronizer keys unique among items in progress;
stateless `step(item, settings)`; gate inboxes `in` and `done`. Teaching
notes, not rules: the three panellist files in `debate` stay three files; a
loop needs an author to start the next round; hidden switches such as
`DSL_DEBATE_STEP` are not ported. Port 4: `select` removed; for the
role-writing guide, roles do not print (what a student wants to see goes to a
sink), and a role sees one kind of message where possible. Port 5: fields of
data-driven sources derived by `dsl check`; stand-in and real sources
interchangeable; `starter` retired subject to checking four offices; one
connection form taught.

All five paper ports are done (`officespeak_ports/`).

1. Renumbering of the check codes.
