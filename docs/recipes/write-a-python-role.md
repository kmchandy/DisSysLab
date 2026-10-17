# Write a role in Python

**Goal.** Give an agent a job that needs no judgement, a rule, a count,
a calculation, by writing it in Python instead of English. A Python role
is free, instant, gives the same answer every time, and can be tested
like any other Python.

**Use a model where judgement is needed; use Python everywhere else.**

No key needed: this recipe runs without a model.

## 1. A rule instead of a model

Copy the inbox sorter, which you built in
[GETTING_STARTED.md](../GETTING_STARTED.md), part 6:

```bash
dsl init inbox_sorter rules
cd rules
```

Its `Tri` agent asks a model whether each message is urgent. Here is the
same decision as a rule, in `roles/rule_triage.py`:

```python
"""
---
emits: urgent if the message says work is due within a day
in: text
out: urgency (urgent | routine)
---
Arguments: soon -- words that mean "within a day"
(default: today, tomorrow, hours).
"""


def step(item, settings):
    text = item["text"].lower()
    due_soon = "due" in text and any(word in text for word in settings["soon"])
    return {"urgency": "urgent" if due_soon else "routine"}


class RuleTriage:
    def __init__(self, soon=("today", "tomorrow", "hours")):
        self.settings = {"soon": list(soon)}

    def __call__(self, item):
        return step(item, self.settings)
```

The rules for a Python role:

- **Exactly one class**, and no DisSysLab import.
- **The front matter** goes in the module's docstring, between `---`
  lines, as in an English role. `out:` is checked against every reply.
- **`__init__`** receives the arguments written in `office.md`:
  `Tri: rule_triage(soon=["today", "tonight"])`.
- **`__call__(self, item)`** receives one message and returns a dict
  whose fields are added to it (an annotator).
- **The decision lives in a plain function, `step`,** so you can test it
  without the office.

In `office.md`, change `Tri: triage` to `Tri: rule_triage`. Then:

```bash
dsl check .
dsl run .
```

```
[FileSource] Loaded 4 items from messages.jsonl (jsonl)
[1] {'id': 1, 'subject': 'Lab 2 deadline', 'text': 'My laptop died last night and I lost my work. Can I get an extension for Lab 2? It is due tomorrow morning.', 'urgency': 'urgent'}
[2] {'id': 3, 'subject': 'Cannot install', 'text': 'pip install dissyslab fails with a permission error and the homework is due in two hours.', 'urgency': 'urgent'}

Run summary (messages):
  rules::Rex               sent      4   received      4
  rules::Tri               sent      4   received      4
  rules::console_printer   sent      0   received      2
  rules::inbox             sent      4   received      0
  rules::later             sent      0   received      2
  rules::urgent            sent      0   received      2
```

The same two messages are urgent, every time, at no cost. Write a message
of your own that the rule gets wrong; then you know what the model was
for.

## 2. Test it

Because `step` is a plain function, you can test it. `roles/test_rule_triage.py`:

```python
from rule_triage import step

SETTINGS = {"soon": ["today", "tomorrow", "hours"]}


def test_work_due_tomorrow_is_urgent():
    assert step({"text": "Lab 2 is due tomorrow and I lost it"}, SETTINGS) == {"urgency": "urgent"}


def test_a_question_about_office_hours_is_routine():
    assert step({"text": "Are office hours on Thursday?"}, SETTINGS) == {"urgency": "routine"}


def test_due_next_week_is_routine():
    assert step({"text": "Lab 3 is due next week"}, SETTINGS) == {"urgency": "routine"}
```

```bash
pip install pytest      # once
cd roles
python -m pytest
```

```
3 passed
```

## 3. A role that remembers: state

Some jobs depend on what came before. This role drops a message whose
subject it has already seen, so a student who writes twice is answered
once. `roles/once.py`:

```python
"""
---
emits: each subject once; a later message with the same subject is dropped
kind: author
in: subject
out: same as in
---
"""


def step(item, state):
    if item["subject"] in state["seen"]:
        return [], state
    return [item], {"seen": state["seen"] + [item["subject"]]}


class Once:
    def __init__(self):
        self.state = {"seen": []}

    def __call__(self, item):
        out, self.state = step(item, self.state)
        return out
```

Three new things:

- **`kind: author`.** An author returns a **list** of messages to send:
  `[item]` passes the message on unchanged, `[]` sends nothing. That is
  how a role filters. (An annotator always sends exactly one message on.)
- **`out: same as in`** says the messages it sends have the fields of the
  messages it received.
- **All the state is in one dict, `self.state`**, and `step` takes the old
  state and returns the new one, so it is still a plain function you can
  test: `step(item, {"seen": ["Lab 2 deadline"]})` should return
  `([], ...)`.

Add the agent before `Tri`:

```
agents:
    First: once
    Tri: rule_triage
    Rex: router(on="urgency")

connections:
    inbox -> First -> Tri -> Rex
    Rex.urgent -> urgent, console_printer
    Rex.routine -> later
```

and a repeat at the end of `messages.jsonl`:

```
{"id": 5, "subject": "Lab 2 deadline", "text": "Sorry to write again: my Lab 2 is due tomorrow morning and my laptop is dead."}
```

```bash
dsl check .
dsl run .
```

```
Run summary (messages):
  rules::First             sent      4   received      5
  ...
```

`First` received five messages and sent four. (The built-in role
`deduplicator(by="subject")` does the same job; `dsl show deduplicator`
prints it.)

## 4. A role that needs a package

If a role imports a package that is not part of Python, import it inside
the method that uses it, and list it in the front matter:

```
---
needs: numpy
in: readings
out: average
---
```

`dsl check` then tells a user who does not have it what to install,
without running anything:

```
problem: line 12: roles/average.py needs numpy, not installed. Run: pip install numpy
```

## More

- `dsl grammar roles`: everything about roles, English and Python.
- `dissyslab/gallery/returns_desk` (`dsl init returns_desk`): two Python
  roles and a gate. `debate`'s `roles/referee.py`: a Python author that
  starts the next round of a loop.
