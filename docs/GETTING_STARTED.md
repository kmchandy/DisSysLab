# Getting started with DisSysLab

DisSysLab runs **offices**: small distributed systems in which **agents**
pass messages to each other. Some agents are language models following
instructions you write in English; others are a few lines of Python. A
**source** brings messages in, a **sink** writes results out, and a file
called `office.md` says who is connected to whom.

This guide takes you from installing DisSysLab to building an office of
your own, one step at a time. Do the steps in order and type the commands
yourself. Every output shown here was copied from a real run, so what you
see should match, with two exceptions: file paths that contain your own
folder names, and the words a language model writes, which vary from run
to run.

| Part | You will | Needs a model key? | Time |
|---|---|---|---|
| [1](#1-install) | install DisSysLab and check the install | no | 10 min |
| [2](#2-your-first-office) | copy, check, draw and run an office | no | 10 min |
| [3](#3-how-the-office-works) | read how it works, and change it | no | 15 min |
| [4](#4-when-things-go-wrong) | break it four ways, and read what DisSysLab tells you | no | 15 min |
| [5](#5-your-api-key) | get a key for the language model | yes | 5 min |
| [6](#6-build-your-own-office-the-inbox-sorter) | build an office from nothing, step by step | yes | 30 min |
| [7](#7-an-office-that-reads-the-news) | run an office on live news feeds | yes | 10 min |
| [8](#8-before-you-hand-in-homework) | the checklist for homework | | |

Commands are shown for macOS and Linux. On Windows they are the same,
except where noted; see also [WINDOWS.md](WINDOWS.md).

---

## 1. Install

You need **Python 3.10 or later** and a terminal (Terminal on macOS,
PowerShell on Windows).

**Step 1.1. Check your Python.**

```bash
python3 --version
```

It should say `Python 3.10` or higher. (On Windows, type `python` instead
of `python3`, here and below.)

**Step 1.2. Make a folder for the course, with its own Python
environment.** A *virtual environment* keeps DisSysLab and its packages
separate from everything else on your computer.

```bash
mkdir dsl_course
cd dsl_course
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

Your prompt now starts with `(.venv)`. **Each time you open a new
terminal, `cd` into `dsl_course` and run the `activate` line again.** If
`dsl` is ever "command not found", this is almost always why.

**Step 1.3. Install DisSysLab.**

```bash
pip install dissyslab
```

**Step 1.4. Check the install.**

```bash
dsl --version
dsl doctor
```

The first line `dsl doctor` prints should be:

```
Ready. You can build an office.
```

Below it, `dsl doctor` lists what is installed. Two lines will say
`not set` or `not installed` until later parts of this guide, and that is
fine: `ANTHROPIC_API_KEY` (part 5) and `yfinance` (only for the
stock-market office).

---

## 2. Your first office

This office is a refund desk. It needs no key and no network.

**Step 2.1. See what offices come with DisSysLab.**

```bash
dsl list
```

```
Offices shipped with dissyslab:

  The gallery (dissyslab/gallery/README.md says what each one teaches)
    arxiv_radar           New papers from three arXiv categories pass through two roles in a row:
    backyard_birds        Which birds are singing in these recordings? Each audio clip in
    ...
```

**Step 2.2. Copy one into a folder of your own.** You always work on a
copy: the originals live inside the installed package, and running an
office writes files next to it.

```bash
dsl init returns_desk my_desk
cd my_desk
```

```
Copied 'returns_desk' to /Users/you/dsl_course/my_desk

Next steps:
  cd /Users/you/dsl_course/my_desk
  dsl check .      every problem, without running anything
  dsl run .
```

**Step 2.3. Look at what you copied.**

```bash
ls -R
```

```
.:
README.md
office.md
roles
tickets.jsonl

./roles:
clerk.py
manager.py
```

- `office.md` says which agents exist and how they are connected.
- `roles/` holds what the agents do: here, two small Python files.
- `tickets.jsonl` is the input: four refund requests, one per line.

**Step 2.4. Check it.** `dsl check` reads the office and reports every
problem it can find, **without running anything**. Make it a habit: check
before every run.

```bash
dsl check .
```

```
my_desk/office.md:
  no problems found.
```

(`.` means "the office in this folder".)

**Step 2.5. Draw it.** `dsl draw` lists every agent with its kind, and
every connection, which DisSysLab calls an *arrow*.

```bash
dsl draw .
```

```
my_desk
  sources:
    tickets          file_source
  sinks:
    jsonl_recorder   jsonl_recorder
    console_printer  console_printer
  agents:
    Gate             gate
    Clerk            clerk
    Rex              router
    Manager          manager
  arrows:
    tickets -> Gate
    Gate -> Clerk
    Clerk -> Rex
    Rex.approve -> jsonl_recorder
    Rex.approve -> console_printer
    Rex.approve -> Gate.done
    Rex.escalate -> Manager
    Manager -> jsonl_recorder
    Manager -> console_printer
    Manager -> Gate.done
```

`dsl draw . --mermaid` prints the same office as a diagram, which GitHub
and many Markdown viewers display as a picture.

**Step 2.6. Run it.**

```bash
dsl run .
```

```
[FileSource] Loaded 4 items from tickets.jsonl (jsonl)
[1] {'ticket_id': 'T1', 'customer': 'Ana', 'amount': 20, 'item': 'book', 'reason': 'wrong item', 'clerk_decision': 'approve'}
[2] {'ticket_id': 'T2', 'customer': 'Ben', 'amount': 120, 'item': 'chair', 'reason': 'damaged', 'clerk_decision': 'escalate', 'manager_decision': 'approve'}
[3] {'ticket_id': 'T3', 'customer': 'Cy', 'amount': 35, 'item': 'lamp', 'reason': 'changed mind', 'clerk_decision': 'approve'}
[4] {'ticket_id': 'T4', 'customer': 'Dee', 'amount': 80, 'item': 'monitor', 'reason': 'defective', 'clerk_decision': 'escalate', 'manager_decision': 'approve'}

Run summary (messages):
  my_desk::Clerk             sent      4   received      4
  my_desk::Gate              sent      4   received      8
  my_desk::Manager           sent      2   received      2
  my_desk::Rex               sent      4   received      4
  my_desk::console_printer   sent      0   received      4
  my_desk::jsonl_recorder    sent      0   received      4
  my_desk::tickets           sent      4   received      0
```

How to read this:

- Each `[n]` line is one message reaching `console_printer`. A message is
  a set of named **fields**. Each ticket arrived with five fields
  (`ticket_id` to `reason`); the clerk added `clerk_decision`, and for the
  two large refunds the manager added `manager_decision`.
- The **run summary** counts, for every agent, the messages it sent and
  received. Use it to see where messages went. Here the gate received 8:
  4 tickets, and 4 "done" signals.
- The office **stopped by itself** when every ticket had been dealt with.
  You do not need to press Ctrl-C.

**Step 2.7. Look at the file it wrote.**

```bash
cat outcomes.jsonl
```

The same four messages, one per line: the `jsonl_recorder` sink wrote
them there. (Windows: `type outcomes.jsonl`.)

---

## 3. How the office works

**Step 3.1. Read `office.md`.** Open it in any text editor (VS Code is a
good choice).

```
# returns_desk: one refund at a time; small ones approved, large ones escalated.

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

There are two kinds of line.

**Declarations**, `name: kind(arguments)`, under `sources:`, `sinks:`
and `agents:`:

- `tickets: file_source(path="tickets.jsonl")`: a source called
  `tickets`, which sends each line of the file as one message.
- `jsonl_recorder(path="outcomes.jsonl")`: a sink that writes each
  message it receives to a file. With no `name:` in front, its name is its
  kind, `jsonl_recorder`.
- `Clerk: clerk(limit=50)`: an agent called `Clerk`, which plays the role
  in `roles/clerk.py`, built with the argument `limit=50`.
- `Rex: router(on="clerk_decision")`: a **router**. It looks at the field
  `clerk_decision` of each message and sends the message to the outbox
  with that name: `approve` or `escalate`.
- `Gate: gate`: a **gate** admits one ticket, then waits for a message on
  its `done` inbox before admitting the next. It keeps one refund in
  progress at a time.

**Connections**, `a -> b`, under `connections:`:

- `tickets -> Gate -> Clerk -> Rex` is a chain: tickets go to the gate,
  the gate to the clerk, the clerk to the router.
- `Rex.approve -> jsonl_recorder, console_printer, Gate.done`: a message
  whose `clerk_decision` is `approve` goes to all three. Writing
  `Gate.done` means "the gate's `done` inbox"; with no dot, the default
  inbox or outbox is meant.

**Step 3.2. Read `roles/clerk.py`.**

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

- The block between the `---` lines is the **front matter**. `in:` names
  the fields the role reads; `out:` names the field it adds, and lists the
  only two values it may have. DisSysLab checks every reply against `out:`
  (part 4).
- The class is built once, with the arguments from `office.md`
  (`limit=50`), and then called once per message. Each call receives one
  message, `item`, and returns a dict whose fields are added to that
  message.
- The decision itself is in a plain function, `step`, so you can test it
  without running the office.

A role like this, which adds fields to the message it received, is called
an **annotator**. You will also meet **authors**, which send new messages
instead; `dsl grammar roles` explains both.

**Step 3.3. Change something.** In `office.md`, change `clerk(limit=50)`
to `clerk(limit=100)`. Before running, predict: which tickets will the
clerk now approve? Then:

```bash
dsl check .
dsl run . --quiet
```

```
[FileSource] Loaded 4 items from tickets.jsonl (jsonl)
[1] {'ticket_id': 'T1', 'customer': 'Ana', 'amount': 20, 'item': 'book', 'reason': 'wrong item', 'clerk_decision': 'approve'}
[2] {'ticket_id': 'T2', 'customer': 'Ben', 'amount': 120, 'item': 'chair', 'reason': 'damaged', 'clerk_decision': 'escalate', 'manager_decision': 'approve'}
[3] {'ticket_id': 'T3', 'customer': 'Cy', 'amount': 35, 'item': 'lamp', 'reason': 'changed mind', 'clerk_decision': 'approve'}
[4] {'ticket_id': 'T4', 'customer': 'Dee', 'amount': 80, 'item': 'monitor', 'reason': 'defective', 'clerk_decision': 'approve'}
```

Ticket T4, for $80, is now approved by the clerk. (`--quiet` leaves out
the run summary.)

**Exercise 3.4.** Open `roles/manager.py`. The manager approves
everything. Make it refuse refunds over $100: its `out:` already allows
`approve | refuse`, so you only need to change `step`. Run it, and check
that T2 ($120) is refused and T4 is still approved.

To start over at any time, copy a fresh version under a new name:
`cd ..` then `dsl init returns_desk my_desk2`.

---

## 4. When things go wrong

Every office you build will go wrong at some point. This part breaks the
refund desk on purpose, four ways, so that you know what DisSysLab tells
you and how to read it. After each one, undo the change (or make a fresh
copy with `dsl init`).

### 4.1 A misspelt name

In `office.md`, change `Clerk: clerk(limit=50)` to `Clerk: clerck(limit=50)`.

```bash
dsl check .
```

```
my_desk/office.md:
  problem: line 12: no agent called 'clerck' in roles/ or the built-ins. Did you mean 'clerk'?
```

Every problem names its **line** in `office.md`. `dsl run` refuses to
start an office with a problem, and says the same:

```
dsl run: my_desk cannot start.
  line 12: no agent called 'clerck' in roles/ or the built-ins. Did you mean 'clerk'?
(`dsl check .` lists every problem at once.)
```

### 4.2 A misspelt router value

Undo 4.1. Now change `Rex.approve ->` to `Rex.aprove ->` on the first
`Rex` line.

```bash
dsl check .
```

```
my_desk/office.md:
  note: line 13: Rex has no outbox for clerk_decision 'approve' (declared by Clerk) and no otherwise; such a message would fail at run time.
  note: line 18: Rex.aprove can never be used: Clerk declares clerk_decision as approve | escalate. Did you mean 'approve'?
  no other problems.
```

These are **notes**, not problems: the office could still run, but
something is probably wrong. `dsl check` knows the clerk's two values
because the clerk lists them in its `out:` line. Without that line it
could not have told you. Writing `out:` with its values is one of the
**guardrails** this course is about: optional, and worth it.

What happens if you run it anyway? Try `dsl run .` and look at the end of
the output:

```
  my_desk::Rex failed on 1 message(s) and they were not processed.
    first failure: 'clerk_decision' is 'approve', which has no outbox here and there is no otherwise. Outboxes: aprove, escalate.
  The office finished; this work did not. `dsl run` exits non-zero.
```

You will also see a report starting `Stalled:`; that is the subject of
4.4.

### 4.3 A role that crashes

Undo 4.2. In `roles/clerk.py`, add two lines at the start of `step`, so
that it reads:

```python
def step(item, settings):
    if item["amount"] > 100:
        raise ValueError(f"no refunds over 100 here, got {item['amount']}")
    if item["amount"] < settings["limit"]:
```

Run it:

```
[AnnotatorAgent 'my_desk::Clerk'] ValueError: no refunds over 100 here, got 120
Traceback (most recent call last):
  ...
  File "/Users/you/dsl_course/my_desk/roles/clerk.py", line 14, in step
    raise ValueError(f"no refunds over 100 here, got {item['amount']}")
ValueError: no refunds over 100 here, got 120
This message was not processed while my_desk::Clerk was doing its role. The office carries on; the run summary counts the rest.
```

The traceback ends at the line of **your** file that raised the error.
The office carries on, but the message that failed is lost, and the run
summary says so:

```
  my_desk::Clerk             sent      1   received      2   failed      1
  ...
  my_desk::Clerk failed on 1 message(s) and they were not processed.
    first failure: ValueError: no refunds over 100 here, got 120
  The office finished; this work did not. `dsl run` exits non-zero.
```

Look at the counts: the clerk received 2 tickets, not 4. Why only two?
Read on.

### 4.4 A stall

The failed message in 4.3 was ticket T2. Because it was lost, nothing ever
told the gate that T2 was done, so the gate never admitted T3 or T4. The
office was stuck, and DisSysLab reported it:

```
Stalled: my_desk::Gate holds an item it admitted, until done arrives; it will never arrive.
  my_desk::Gate.done <- my_desk::Rex.approve: empty; my_desk::Rex is idle, waiting on in
  my_desk::Gate.done <- my_desk::Manager.out: empty; my_desk::Manager is idle, waiting on in
  my_desk::Rex.in <- my_desk::Clerk.out: empty; my_desk::Clerk is idle, waiting on in
  my_desk::Manager.in <- my_desk::Rex.escalate: empty; my_desk::Rex is already on this path
  my_desk::Clerk.in <- my_desk::Gate.out: empty; my_desk::Gate is already on this path
  2 message(s) wait unread on my_desk::Gate.in.
```

How to read it:

- The first line says **who** is stuck and **what for**: the gate holds a
  ticket and waits for `done`.
- Each indented line follows a connection **backwards**. `Gate.done <-
  Rex.approve: empty` means: the connection from the router's `approve`
  outbox into the gate's `done` inbox holds no message, and the router is
  idle, waiting for its own input. Then the router's input comes from the
  clerk, which is also idle, waiting for its input, which comes from the
  gate: **a cycle**. Every agent on the path is waiting for another one on
  the path, and no message is on its way. Nothing can ever move.
- The last line says what was never done: 2 tickets were never admitted.

Now make a stall without a crash. Undo 4.3, and in `office.md` remove
`, Gate.done` from the end of the `Rex.escalate` line, so the manager no
longer tells the gate it is done. Then `dsl check .` (no problems: every
name and port is valid) and `dsl run .`:

```
Stalled: my_desk::Gate holds an item it admitted, until done arrives; it will never arrive.
  my_desk::Gate.done <- my_desk::Rex.approve: empty; my_desk::Rex is idle, waiting on in
  my_desk::Rex.in <- my_desk::Clerk.out: empty; my_desk::Clerk is idle, waiting on in
  my_desk::Clerk.in <- my_desk::Gate.out: empty; my_desk::Gate is already on this path
  2 message(s) wait unread on my_desk::Gate.in.
```

Compare it with the stall in 4.3. The manager has disappeared from the
path: nothing connects it to `Gate.done` any more. When a report like
this surprises you, look for the agent you expected on the path and
cannot find. The run summary ends with:

```
  Stalled: my_desk::Gate holds an item it admitted, until done arrives; it will never arrive.
    (the path that proves it is printed above, under 'Stalled:')
  The office finished; this work did not. `dsl run` exits non-zero.
```

**What to take from part 4:**

| You see | It means | Do |
|---|---|---|
| `problem:` from `dsl check` | the office is wrong and will not run | fix the line it names |
| `note:` from `dsl check` | probably a mistake; read it | fix it, or be sure you meant it |
| `failed on N message(s)` | a role crashed or its reply broke its `out:` | read the first failure; fix the role |
| `Stalled:` | an agent waits for a message that can never come | follow the path backwards; find what is missing |
| exit status not 0 | some work was not done | the summary says which |

---

## 5. Your API key

Parts 6 and 7 use a language model, Anthropic's Claude, which needs a key.
Each request costs a fraction of a cent; the offices in this guide cost a
few cents to run.

**Step 5.1.** Go to [console.anthropic.com](https://console.anthropic.com/),
sign in, and create an API key. It starts with `sk-ant-`. Copy it: it is
shown only once.

**Step 5.2.** Put it in a file called `.env` in your **course folder**,
`dsl_course`. DisSysLab looks for `.env` in the folder you run `dsl` from
and in every folder above it, so one file there serves all your offices.

```bash
cd ~/dsl_course                    # or wherever you made it
echo "ANTHROPIC_API_KEY=paste-your-key-here" > .env
```

Replace `paste-your-key-here` with your key, with no spaces or quotes.
The file must be plain text: on a Mac, do not use TextEdit (it saves rich
text); use VS Code or the command above.

**Step 5.3.** Check it:

```bash
dsl doctor
```

The `Credentials:` section should show `[SET ] ANTHROPIC_API_KEY`, with
the first few characters of the key. [API_KEY_SETUP.md](API_KEY_SETUP.md)
covers what to do if it does not.

**Never share your key, and never commit `.env` to git.** Anyone with the
key can spend money on your account.

---

## 6. Build your own office: the inbox sorter

Now you build an office from nothing. The course staff receive messages
from students. Some are urgent (the homework is due in two hours and
nothing installs); most can wait (when are office hours?). The office
reads the messages, asks a language model how urgent each one is, and
sorts them into two files.

You will build it in six steps, checking and running after each one, so
that every step works before you take the next. If you get stuck,
`dsl init inbox_sorter finished_sorter` gives you the finished office to
compare with.

**Step 6.1. Make the folder and the input.**

```bash
cd ~/dsl_course
mkdir inbox_sorter
cd inbox_sorter
```

Create a file `messages.jsonl` with these four lines, one message per
line:

```
{"id": 1, "subject": "Lab 2 deadline", "text": "My laptop died last night and I lost my work. Can I get an extension for Lab 2? It is due tomorrow morning."}
{"id": 2, "subject": "Office hours", "text": "Are office hours on Thursday this week?"}
{"id": 3, "subject": "Cannot install", "text": "pip install dissyslab fails with a permission error and the homework is due in two hours."}
{"id": 4, "subject": "Reading", "text": "Is there a book you recommend on distributed algorithms?"}
```

**Step 6.2. The smallest office: a source and a sink.** Create
`office.md`:

```
# inbox_sorter: messages to the course staff, sorted by how soon they need an answer.

sources:
    inbox: file_source(path="messages.jsonl")

sinks:
    console_printer

connections:
    inbox -> console_printer
```

Check it and run it:

```bash
dsl check .
dsl run .
```

```
inbox_sorter/office.md:
  no problems found.
```

```
[FileSource] Loaded 4 items from messages.jsonl (jsonl)
[1] {'id': 1, 'subject': 'Lab 2 deadline', 'text': 'My laptop died last night and I lost my work. Can I get an extension for Lab 2? It is due tomorrow morning.'}
[2] {'id': 2, 'subject': 'Office hours', 'text': 'Are office hours on Thursday this week?'}
[3] {'id': 3, 'subject': 'Cannot install', 'text': 'pip install dissyslab fails with a permission error and the homework is due in two hours.'}
[4] {'id': 4, 'subject': 'Reading', 'text': 'Is there a book you recommend on distributed algorithms?'}

Run summary (messages):
  inbox_sorter::console_printer   sent      0   received      4
  inbox_sorter::inbox             sent      4   received      0
```

Nothing is decided yet, but the input reaches the screen. Always start
like this: when something goes wrong later, you know the input is fine.

**Step 6.3. Plan an agent before you write it.** Put an agent between the
source and the sink, without saying yet what it does. `unassigned` means
"to be decided":

```
# inbox_sorter: messages to the course staff, sorted by how soon they need an answer.

sources:
    inbox: file_source(path="messages.jsonl")

sinks:
    console_printer

agents:
    Tri: unassigned

connections:
    inbox -> Tri -> console_printer
```

```bash
dsl check .
dsl draw .
```

```
inbox_sorter/office.md:
  note: line 10: Tri is unassigned, so this office is a draft: it can be checked, not run.
  no other problems.
```

An office with an unassigned agent is a **draft**. You can check and draw
it, which is how you design the shape of an office before writing any
role. `dsl run .` refuses it:

```
dsl run: inbox_sorter cannot start.
  line 10: Tri is unassigned; a draft office can be checked and drawn, but not run. Give it a role first.
```

**Step 6.4. Write the role.** Make a folder `roles` and in it a file
`triage.md`:

```
---
emits: how soon a message to the course staff needs an answer
in: subject, text
out: urgency (urgent | routine)
---
You read one message that a student sent to the staff of a course. It is
a JSON object; "subject" and "text" are the message.

Decide how soon it needs an answer. It is urgent if the student cannot
make progress on work that is due within a day without our help: a lost
assignment near a deadline, an install that fails before a due date.
Everything else is routine: questions about schedules, readings, grading
policy, or work due later.

Return only a JSON object with one field, "urgency", whose value is
"urgent" or "routine".
```

This is an **English role**. The language model receives exactly the
text after the second `---`, followed by the message. Three things make
it work well:

- It says what the model receives ("a JSON object; subject and text").
- It gives the rule for deciding, with examples on both sides.
- It ends by saying exactly what to return. The front matter's `out:` line
  says the same thing to DisSysLab, which checks every reply against it.

In `office.md`, change `Tri: unassigned` to `Tri: triage`. Then:

```bash
dsl check .
dsl run .
```

```
[FileSource] Loaded 4 items from messages.jsonl (jsonl)
[1] {'id': 1, 'subject': 'Lab 2 deadline', 'text': 'My laptop died last night and I lost my work. Can I get an extension for Lab 2? It is due tomorrow morning.', 'urgency': 'urgent'}
[2] {'id': 2, 'subject': 'Office hours', 'text': 'Are office hours on Thursday this week?', 'urgency': 'routine'}
[3] {'id': 3, 'subject': 'Cannot install', 'text': 'pip install dissyslab fails with a permission error and the homework is due in two hours.', 'urgency': 'urgent'}
[4] {'id': 4, 'subject': 'Reading', 'text': 'Is there a book you recommend on distributed algorithms?', 'urgency': 'routine'}

Run summary (messages):
  inbox_sorter::Tri               sent      4   received      4
  inbox_sorter::console_printer   sent      0   received      4
  inbox_sorter::inbox             sent      4   received      0
```

Each message now has an `urgency` field. These are the model's decisions:
yours may differ, especially on borderline messages. If every message
fails with `ANTHROPIC_API_KEY not set`, go back to part 5.

**Step 6.5. Sort with a router.** The role decides; a **router** acts on
the decision. Add a router on `urgency`, and two files:

```
# inbox_sorter: messages to the course staff, sorted by how soon they need an answer.

sources:
    inbox: file_source(path="messages.jsonl")

sinks:
    console_printer
    urgent: jsonl_recorder(path="urgent.jsonl")
    later: jsonl_recorder(path="later.jsonl")

agents:
    Tri: triage
    Rex: router(on="urgency")

connections:
    inbox -> Tri -> Rex
    Rex.urgent -> urgent, console_printer
    Rex.routine -> later
```

Two copies of `jsonl_recorder` need two names, `urgent` and `later`.

```bash
dsl check .
dsl draw .
dsl run .
```

```
[FileSource] Loaded 4 items from messages.jsonl (jsonl)
[1] {'id': 1, 'subject': 'Lab 2 deadline', 'text': 'My laptop died last night and I lost my work. Can I get an extension for Lab 2? It is due tomorrow morning.', 'urgency': 'urgent'}
[2] {'id': 3, 'subject': 'Cannot install', 'text': 'pip install dissyslab fails with a permission error and the homework is due in two hours.', 'urgency': 'urgent'}

Run summary (messages):
  inbox_sorter::Rex               sent      4   received      4
  inbox_sorter::Tri               sent      4   received      4
  inbox_sorter::console_printer   sent      0   received      2
  inbox_sorter::inbox             sent      4   received      0
  inbox_sorter::later             sent      0   received      2
  inbox_sorter::urgent            sent      0   received      2
```

Only the urgent messages reach the screen. Look in the two files:

```bash
cat urgent.jsonl
cat later.jsonl
```

**Step 6.6. See the guardrails work.** Language models do not always do
as they are told. Two things can happen, and DisSysLab handles both.

*The model adds a field you did not ask for*, say a `reason`. Because
`out:` lists only `urgency`, the extra field is **dropped** before the
message goes on, and the summary tells you:

```
  note: inbox_sorter::Tri's replies had fields its out: does not declare; they were dropped: reason (1).
```

*The model answers with a value you did not allow*, say
`"urgency": "whenever"`. That reply does not fit `out:`, so the message
is not passed on:

```
[inbox_sorter::Tri] its reply does not fit its front matter: 'urgency' is 'whenever', which is not one of urgent, routine.
This message was not processed. The office carries on; the run summary counts the rest.
```

and the run ends with `failed 1` for `Tri` and a non-zero exit status.

Without the `out:` line, the extra `reason` would travel on to the files,
and `whenever` would reach the router, which has no outbox for it. The
`out:` line catches both at the agent that caused them, with a message
that names it. To see this for yourself, change the last paragraph of
`triage.md` to ask for a `reason` as well, run, and read the summary.

**Your office works.** Exercises:

1. Add a third value, `spam`, for messages that are not about the course:
   add it to `out:` and to the text, add a message to `messages.jsonl` to
   test it, and send spam to the `discard` sink (declare `discard` under
   `sinks:`). Run `dsl check .` *before* adding the router line, and read
   the note it gives you.
2. Add the built-in `summarizer` role (`dsl roles` lists the built-in
   roles) between `Rex.urgent` and the `urgent` file, so that urgent
   messages are saved with a one-sentence summary.
3. Replace `triage.md` with a Python role, `triage.py`, that calls a
   message urgent if its text contains "due" and "today", "tomorrow" or
   "hours". Compare its decisions with the model's. Which is right more
   often on messages you write yourself?

---

## 7. An office that reads the news

This office reads two live news feeds, asks a model whether each article
is about a topic, and shows only those that are. It needs a key and an
internet connection.

```bash
cd ~/dsl_course
dsl init org_news_filter news
cd news
dsl check .
dsl run .
```

You will see up to four articles, each a line like
`[1] {'source': 'bbc_world', 'title': '...', 'text': '...', 'url': '...', 'timestamp': '...', 'on_topic': 'yes'}`:
the news changes, so yours will differ. Only articles the model marked
`on_topic: yes` reach the screen; the rest go to `discard`.

Open `office.md` and `roles/topic_filter.md`. It is the same shape as
your inbox sorter: an English role adds a decision, and a router acts on
it. To change the topic, edit one paragraph of `topic_filter.md`, the one
that begins "The topic is the Americas", and run again.

If a feed cannot be reached, the run ends with a message naming the feed
and the reason, rather than an empty screen.

---

## 8. Before you hand in homework

1. `dsl check .` reports **no problems**, and you have read every note.
2. `dsl run .` **ends with exit status 0**: no `failed`, no `Stalled:`.
   (After a run, `echo $?` prints the exit status; on Windows,
   `echo $LASTEXITCODE`.)
3. Every role says what it adds or sends in an `out:` line, with values
   wherever the role chooses from a list.
4. Your folder contains `office.md`, `roles/`, and any input files, and
   **not** your `.env`.
5. If the assignment asks for a picture, `dsl draw . --mermaid`.

---

## 9. Where to go next

The full reference ships with DisSysLab, so it always matches the version
you installed:

```bash
dsl grammar              # how office.md is written
dsl grammar roles        # writing roles, in English or in Python
dsl grammar sources      # every source and sink, and their arguments
dsl grammar examples     # four offices explained in full
dsl roles                # the built-in roles
dsl show summarizer      # one built-in role, whole
```

The gallery, in the order the course uses it:

| Office | What it teaches |
|---|---|
| `inbox_sorter` | the office you built in part 6 |
| `org_news_filter` | a router: an English role decides, a router routes |
| `returns_desk` | one item at a time: a gate, and escalation |
| `room_climate_monitor` | joining two streams with a synchronizer |
| `situation_room_pro` | built-in roles working in parallel, then joined |
| `arxiv_radar` | two English roles you write, in a row |
| `debate` | three models, a moderator, and a loop for another round |
| `org_two_office_news` | an office used as one agent of another |
| `backyard_birds` | an agent that is a classifier, not a language model |
| `mac_speed_suite` | a larger application: trading strategies, backtested |

For each: `dsl init <office> <folder>`, read its `README.md`, then
`dsl check .`, `dsl draw .` and `dsl run .`.

---

## 10. If something goes wrong

**`command not found: dsl`.** The virtual environment is not active.
`cd` to your course folder and run the `activate` line from step 1.2.

**Every message fails with `ANTHROPIC_API_KEY not set`.** DisSysLab did
not find your `.env`. Run `dsl doctor` from the folder you ran `dsl run`
in; its `Local .env` and `Credentials` sections say what it found. The
`.env` must be in that folder or a folder above it.

**`Error code: 401`.** The key is wrong or has been revoked. Make a new
one (step 5.1).

**`rate_limit_error` or `429`.** Too many requests in a short time. Wait
a minute and run again; offices with many agents are the usual cause.

**`dsl run` prints nothing for a long time.** A language model is slow,
or an office is reading a live source that keeps going. Press Ctrl-C to
stop it; the summary shows which agents had done what.

**`dsl run: ... is a gallery office inside the installed package`.** You
named an office instead of a folder. Copy it first with `dsl init`, as
the message says.

**`the office ran but produced nothing`.** A source sent no messages:
a file path that does not exist, or a feed that returned nothing. The
message names the source.

**Anything else.** Run `dsl doctor` and include its output when you ask
for help.
