# Roles

A role is what an agent does. It knows nothing about DisSysLab: one JSON
object comes in, JSON goes out. The office decides where messages go; the
role only decides what to say about each one.

## Two kinds

| | Annotator (the default) | Author (`kind: author`) |
|---|---|---|
| Returns | one JSON object | a list of JSON objects |
| Effect | its fields are **added** to the incoming message, which goes on | each object is sent as a **complete new message** |
| None, or several | -- | `[]` sends nothing; a list of several sends several |
| `out:` lists | the fields it adds | the fields of each object it returns |
| Typical | classifiers, summarizers, scorers | splitters, filters, the step that starts a loop's next round |

- **An annotator only adds.** A reply that would change a field already in
  the message is a failure.
- An author that returns what it received, unchanged, is a filter:
  `[item]` keeps it, `[]` drops it.
- The kind is about what the role returns, not its language. A Python role
  can be either; so can an English one.

In dataflow terms, an annotator is a *map* and an author is a *flat-map*.

## English roles

A `.md` file: front matter between `---` lines, then the instruction. This
is `org_news_filter`'s `roles/topic_filter.md`:

```
---
emits: whether a news article is on the topic
in: title, text
out: on_topic (yes | no)
---
You read one news article, given as a JSON object. Its "title" and "text"
fields are the headline and the body.

The topic is the Americas: North, Central and South America and the
Caribbean, for example Canada, the United States, Mexico and Brazil.

Decide whether the article is mainly about the topic.

Return only a JSON object with one field, "on_topic", whose value is "yes"
or "no".
```

- **The model receives exactly the text after the front matter, followed by
  the incoming message as JSON.** Nothing is added. So the text is a
  complete instruction, including what to return, and ends with the closing
  sentence for its kind:
  - annotator: "Return only a JSON object with the fields `a` and `b`."
  - author: "Return only a JSON list of objects, each with the fields ..."
- No wiring in the text: no "send to", no outbox names. Deciding is the
  role's job; routing is a router's (`dsl grammar`).
- No parameters in the text. In `office.md` an English role takes only
  `ai=`, which picks the model for that agent.

## Python roles

A `.py` file defining **exactly one class**, with no DisSysLab import.

```python
"""
---
emits: approves small refunds; escalates the rest
in: amount (number, >= 0)
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

- `__init__` receives the arguments written in `office.md`
  (`Clerk: clerk(limit=100)`). It builds settings, and any resource the role
  needs (a model, a connection).
- `__call__(self, item)` returns a dict (annotator) or a list of dicts
  (author). An exception raised here costs that one message, and is reported.
- Keep the logic in a plain function, as `step` above, so it can be tested
  without the office:
  - stateless: `step(item, settings)`;
  - keeping state: all of it in one dict, `self.state`, and
    `step(item, state, settings)`;
  - calling a model or a service: call it in `__call__`, pass its result to
    `step(item, result, ...)`. `backyard_birds` does this with BirdNET.
- A package the role imports goes inside the method that uses it, and in
  `needs:`. `dsl check` then says which are missing, with the
  `pip install` line, without importing anything.
- A file in `roles/` whose name starts with `_` is a helper module the roles
  can import (`from _signal_common import ...`).

## Front matter

In a `.md` file, the block between `---` lines; in a `.py` file, the same
block inside the module docstring. It is read by Python only and never sent
to a model.

| Key | Meaning |
|---|---|
| `emits:` | one line, shown by `dsl roles` |
| `kind:` | `author`; absent means annotator |
| `in:` | the fields the role needs; checked before the role is called |
| `out:` | annotator: the fields it adds; author: the fields of each object |
| `needs:` | Python only: the packages it imports |

- **What a field holds.** In `in:` or `out:`, a field may say, in
  parentheses, what it may hold. These are contracts: Python checks them,
  every message, whatever the model wrote.

  | Written | Means |
  |---|---|
  | `verdict (publish \| revise)` | one of these values |
  | `price (number)` | a number (not the text `"62400"`) |
  | `score (0..10)` | a number from 0 to 10, ends included |
  | `price (number, >= 0)`, `temp (<= 40)` | a number with one bound |
  | `count (integer, 1..5)` | a whole number |
  | `reply (text, at most 600 chars)` | text no longer than 600 characters |
  | `reply (text)` | text |

  A field with nothing in parentheses may hold anything. Write the same
  thing in the role's instruction, too: the model never sees the front
  matter.
- **`in:` is checked first.** A message without every field of `in:`, or
  with one that does not hold what it says, is not given to the role: a
  model never sees it. List only the fields the role cannot do without.
  `in:` does not trim the message; the role still receives all of it.
- **Conditional lines**, for an author whose messages differ by a value:
  ```
  out: next (finish | continue), problem_id, problem, history
  out if next is finish: final_answer, agreement, rounds_used
  out if next is continue: round
  ```
- **Pass-through.** An author that returns its input unchanged (a filter)
  says `out: same as in`.
- **All optional.** Guardrails are recommended, never required. Without
  `in:` every message is given to the role; without `out:` the reply is
  not checked and nothing is dropped. The role still runs.

## What happens to a message

0. Before the role is called, the message is checked against `in:`. A
   message that does not fit is refused (4, below), and the role never
   sees it.
1. The reply is read as one JSON value. A reply wrapped in one code fence is
   unwrapped. Anything else is refused.
2. An annotator's reply must be an object with every field of `out:`, each
   holding what it declares: a listed value, a number in its range, text
   within its length. An author's must be a list of such objects.
3. Fields the reply carries that `out:` does not declare are **dropped and
   counted**. The message goes on; the run summary names the fields. This
   is the guardrail: a model that writes more than it was asked cannot pass
   the extra along.
4. A message or reply that does not fit is a **refusal**, and a refusal
   stops the whole office: it may be an attack. No role runs again; work
   finished before it is kept; the message, the reason and the reply go to
   `refused.jsonl` in the office's folder; the summary ends with
   `Stopped:`; `dsl run` exits non-zero. **Unless** the office connects the
   agent's `refused` outbox (`Clerk.refused -> Log`): then the refused
   message goes there, with a field `refusal` giving the reason, it is
   still written to `refused.jsonl`, and the office carries on. What a
   refusal should do is then part of the design, in `office.md`.
5. A Python role that raises is different: that is a bug, not an attack. It
   costs that one message, which is counted and quoted in the summary; the
   office carries on, and `dsl run` exits non-zero.

## The built-in roles

```
dsl roles             the list, with the fields each one adds
dsl show summarizer   one of them, whole
```

`entity_extractor`, `severity_classifier`, `topic_tagger`, `geolocator`,
`summarizer` and `writer` are English annotators; `deduplicator` is a
Python author that drops repeats (`deduplicator(by="url")`).

To change one, copy it into the office's `roles/` folder **under a new
name** and edit it there. A local file with a built-in's name is an error,
not an override, so it is always clear which one runs.

## Advice from the gallery

- Let the model judge and Python keep the rules. In `debate` the moderator
  judges agreement; a Python referee applies the round limit.
- A loop needs an author to start the next round: an annotator only adds, so
  the next round's message has to be built fresh.
- Escalation is two annotators each adding its own decision
  (`clerk_decision`, `manager_decision`): an audit trail for free.
- Name fields for the decision, not the topic (`on_topic`, not
  `about_americas`), so changing the topic is an edit to one paragraph.
- Prefer string values to booleans (`yes`/`no`): they read the same in the
  role, the router line and the output.
- Roles do not print. What you want to see goes to a sink.
- A role should see one kind of message. Where two streams meet in front of
  one role, give them a field that tells them apart.
