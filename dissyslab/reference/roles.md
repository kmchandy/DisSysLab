# Roles you already have

**Read this before writing a role.** **Nineteen names resolve without any
file in the office's own `roles/` folder** — thirteen *semantic* roles that
decide or describe something, and six *structural* ones that route, join, gate
or store. Name one in `Agents:` and it works.

Most user requests are one of these, possibly with its criteria edited. Writing
a fresh role for a job one of these already does costs the user time and
introduces bugs the shipped role does not have.

## Get the live list from the install

This file can go stale; the install cannot. Give an office a role name that
exists nowhere and the error prints every resolvable name:

```bash
dsl build <office_dir>     # after putting `X is a nonesuch.` in Agents:
```

```
roles_lib keys:              [category_classifier, confidence_filter, ...]
fn_lib keys:                 [deduplicator]
PARAMETERIZED_LIBRARY keys:  [synchronizer, router, select, gate, record]
```

If this page and that output disagree, believe the output.

## The shape they share

Every English role here takes one item at a time as a JSON object with
`title`, `text`, `source`, `url`, `timestamp` — the shape RSS, web, and most
other sources emit — **preserves every existing field**, and adds its own. That
is what makes them composable: chain four and each one's annotation survives
the next.

```
Sasha's out is Eve, Sam, Tom.      # same item, three annotations, in parallel
```

## Annotators — add a field, always send to `out`

| Role | Adds | Values |
|---|---|---|
| `topic_tagger` | `topic` | one of eight: politics, business, technology, science, health, sports, entertainment, other |
| `category_classifier` | `category` | ANNOUNCEMENT, ANALYSIS, NEWS, DISCUSSION, OFFER, OTHER |
| `severity_classifier` | `severity` | CRITICAL, HIGH, MEDIUM, LOW |
| `urgency_classifier` | `urgency` | HIGH, MEDIUM, LOW — time-sensitivity *for the reader*, not importance |
| `sentiment_classifier` | `sentiment`, `sentiment_score` | POSITIVE / NEGATIVE / NEUTRAL, plus a float in [-1.0, +1.0] |
| `entity_extractor` | `entities` | object with `people`, `organizations`, `places`, `events` lists |
| `geolocator` | `location` | object with `country` and `region` (one of eight region strings) |
| `summarizer` | `summary` | one sentence, 12–30 words |

Note `severity` and `urgency` differ: a distant war is CRITICAL severity and
LOW urgency; a bill due today is the reverse.

## Writers — turn annotations into prose

| Role | Produces |
|---|---|
| `writer` | headline + 2–4 sentence briefing; weaves in whichever enrichment fields are present and ignores those that are not |
| `summary_writer` | a short scannable paragraph, drawing on whatever upstream agents added |

Both degrade gracefully — put them after any subset of the annotators.

## Filters — two outboxes, and this is the important part

| Role | Outboxes | Decides |
|---|---|---|
| `relevance_filter` | `keep`, `discard` | whether an item is worth forwarding at all |
| `evaluator` | `publish`, `revise` | whether a written briefing is good enough, or needs another pass |

**`relevance_filter` is the one most often reimplemented by mistake.** It
carries an editable *"Default criteria for relevance (edit this section to fit
your office)"* block. When a user says *"keep only the items about X"*, the
right move is almost always: copy `relevance_filter.md` into the office's
`roles/`, rewrite that block in English, and wire `keep` and `discard`.

Not: write a Python role with a keyword list. That is an exact implementation
of a fuzzy criterion, and it fails in ways nobody sees — a `\b` word boundary
that refuses to match a plural, a term the user did not think to list, a
casing difference. The office runs clean and quietly keeps too little.

`evaluator` is what makes a revision loop work: send `revise` back upstream,
`publish` onward. It also counts `revisions` and force-publishes past a
ceiling, so the loop terminates.

## The Python role

`confidence_filter` (`in_`, `out`) — passes through only messages whose
confidence exceeds a threshold, with an optional category whitelist. Its
contract is on *shape*, not content, so it works after any classifier: vision,
audio, sentiment, anomaly. Use it rather than putting a threshold inside a
classifier role — one agent, one job, and the user can then change the
threshold without touching the model.

## The other six — structural roles

These have no `.md` file. They are built by the framework from the arguments
given in `office.md`, and they are what make an office anything other than a
straight line.

| Name | Declared as | Does |
|---|---|---|
| `synchronizer` | `synchronizer(inboxes=["a","b"])` | waits for one message on each named inbox and joins them into a single message. The fan-in half of a fan-out |
| `gate` | `gate(data="data", control="control")` | admits one item at a time, releasing the next only when told. **This is what lets a loop terminate** — `dsl check`'s W7 warns about a loop with no gate |
| `select` | `select(inboxes=[...], command="command")` | a commanded traffic controller: reads whichever inbox its state points at |
| `router` | `router(routes=[...])` | forwards each message to a named outbox by rule |
| `record` | `record(initial={...})` | a shared keeper — store and reply, for state several agents consult |
| `deduplicator` | `deduplicator(by="url")` | drops repeats by a named field |

`synchronizer` and `gate` are the two worth knowing cold. A fan-out to four
enrichers needs a `synchronizer` to recombine them (`situation_room`), and any
loop needs a `gate` or it never stops (`debate`).

### `deduplicator` — say what it does *not* catch

`by="url"` means *drop a message whose `url` field I have seen before*.
Nothing more. When a user says **"drop duplicate stories"**, they usually
mean something `by="url"` will not do: the same event covered by two
publishers has two different URLs, so both pass through. Tell them that
rather than letting them discover it in the output.

The options, and their real behaviour:

- `by="url"` — same link twice. Catches a feed repeating itself between
  polls, which is the common case and why it is the default.
- `by="title"` — same headline twice. Catches syndicated copy that ran
  verbatim. Misses anything reworded, and will wrongly drop two genuinely
  different items that share a generic headline.
- `by="id"` / `by="message_id"` — for sources that carry an explicit
  identifier. Exact, when it exists.

There is **no option that deduplicates by story**. That needs a semantic
judgment, so it needs a role — an English one, comparing an item against
what came before. Do not pretend `by=` covers it.

Two more things to say out loud:

- A message that is **not a dict, or has no such field, passes through
  untouched.** No error. A typo in `by=` means the deduplicator silently
  does nothing, and the office still checks clean.
- `deduplicator` has **no reject port**, so the "wire rejects somewhere
  readable" rule below cannot be applied to it. What it drops is gone. If
  it matters whether dedup is behaving, compare the message counts either
  side of it in the run summary — that difference is the only evidence
  there is.

## While you are tuning a filter, wire its rejects somewhere readable

```
Felix's keep is Riley.
Felix's discard is jsonl_recorder.     # not `discard` — while you develop
```

`examples/org_news_filter` does this. Sending rejects to a recorder rather
than to the `discard` sink is what lets you read what the filter threw away.
Swap to `discard` once the criteria are trusted.

**The `discard` sink is not a blind spot, though — only a silent one.** It
counts what it swallows and the run summary prints the count:

```
Run summary (messages):
  Felix    sent     50   received     50
  discard  sent      0   received     47
```

A filter that rejected 47 of 50 announces itself, and so does one that
rejected none. What you lose is *which* items, not *how many*, and that is
the whole difference: the count tells you the filter is roughly sane, and a
recorder tells you whether it was right. Several shipped offices wire
rejects to `discard` for exactly that reason — their criteria have been run
and the count is enough.

## When to write your own instead

Write a new role when the job is genuinely not on this list:

- a domain vocabulary these do not know (species, tickers, part numbers)
- arithmetic over a stream — a moving average, an RMS, a rate of change
- wrapping a model or a library
- reshaping records into a form a specific sink needs

Say which of these applies — if you cannot, one of the nineteen above
probably fits.

## Writing a role file

A role goes in the office's `roles/` folder and is named after the role:
`roles/screener.md` is the role `screener`, used as `Alex is a screener.`

**In English — `roles/<name>.md`.** Front matter first, then the prompt:

```markdown
---
emits: whether a posting is open to someone with no experience
outboxes: keep, discard
---
# Role: screener

You read one job posting at a time and decide whether it is worth
passing on.

Input shape. Each item is a JSON object with `title`, `text`, `url`.

If the posting is for a new graduate, send to keep.
Otherwise send to discard.
```

An annotator — a role that adds a field rather than deciding where a
message goes — declares that field too:

```markdown
---
emits: one plain-English sentence saying what the item is about
outboxes: out
adds: summary
---
```

- **`outboxes:` is required.** It is the role's interface: what the
  framework builds, what `dsl check` compares the wiring against, and
  what `dsl draw` shows. In order — the first name is the default
  destination when a single-outbox role's model does not choose one.
- **`adds:` is the fields the role puts on the message**, in order.
  Leave it out for a role that only routes: a filter decides, it does
  not add. This is what the output contract is generated from, so it
  is the only place the reply shape is stated.
- **`inboxes:` may be omitted** and defaults to `in_`, which is what
  almost every role wants.
- `emits:` says what the value *means* — the half no declaration can
  carry. It does **not** name the field; `adds:` does that, and a
  sentence naming it too is a second copy that drifts.
- The prompt is prose for the model. It does **not** decide the ports
  or the fields. Write `send to keep` in it because it tells the model
  what to do, not because the framework reads it — it does not.

## Never write the output shape yourself

The framework appends a contract generated from `outboxes` and `adds`,
and that is the **only** statement of the reply shape:

```
a filter        {"send_to": "<one of: keep, discard>"}
an annotator    {"summary": <summary, as described above>}
```

A role that adds nothing is asked for no content. A role with one
outbox is not asked to choose. Neither is asked for `text` unless it
declares `adds: text`, which is what a role that genuinely writes
should declare — the sinks read that field.

Do not add an "Output." paragraph, and do not tell the model to
preserve the input's fields. Every shipped role used to do both, and
the result was two statements in one prompt asking for different
things: the role wanted every input field plus `summary`, the appended
contract wanted `send_to` and `text`. Which the model obeyed decided
whether the annotation existed at all. **The framework merges the
upstream message with the reply, in code** — so a model returning
strictly `{"summary": "..."}` still produces a message carrying
`title`, `url` and `timestamp`. Asking for them back costs tokens and
buys nothing.

If your role's output genuinely needs a shape the contract cannot
express — a specific top-level key, a nested object — set
`contract: structured` in the front matter. Nothing is appended then,
and your prose is the whole statement. Tests exempt those roles from
the rule above for exactly that reason.

**In Python — `roles/<name>.py`.** The module builds one top-level
`role`, and the ports are the declaration:

```python
from dissyslab.office.library import AgentRoleEntry

role = AgentRoleEntry(
    name="threshold",
    in_ports=("in_",),
    out_ports=("high", "low"),
    factory=lambda: ...,
)
```

`dsl check` reads those two arguments **without importing the file** —
it must be safe to check code you did not write. So spell them as
literals. If the ports are computed and nothing readable is left, put
the same front matter as a prose role at the top of the module
docstring.

**English or Python?** English for a judgment — relevance, tone, whether
a briefing is good enough. Python for anything exact — arithmetic, a
threshold, reshaping a record. A Python role costs nothing to run and
gives the same answer every time; an English one costs a model call and
is the only thing that can handle a fuzzy criterion. Writing a keyword
list in Python to do an English role's job is the common mistake, and it
fails quietly.

## Editing a shipped role — and the name-collision trap

Copy it into the office's `roles/` folder under the same name and edit. A
local file wins over the shipped one, so the office gets your version and
every other office keeps the original. The precedence, from
`dissyslab/office/library.py`:

```
1. the office's own roles/X.md or roles/X.py
2. the framework's dissyslab/roles/X.md
3. PARAMETERIZED_LIBRARY[X]        (synchronizer, router, select, gate, record)
4. dissyslab.fn_lib[X]             (deduplicator)
```

**That override is a feature when deliberate and a trap when accidental.**
Writing a new role and giving it one of the nineteen names *silently replaces*
the shipped one for that office. A hand-written `roles/topic_tagger.md` does
not sit alongside the framework's 55-line version — it displaces it. The
office builds clean, `dsl check` passes, the run succeeds, and the tagging is
quietly worse, with nothing anywhere to say why.

**So: never give a new role one of the nineteen names.** Override only when
you mean to override — when you have copied a shipped role and edited it — and
say plainly to the user that you have done so.

```bash
cp $(python3 -c "import dissyslab,pathlib;print(pathlib.Path(dissyslab.__file__).parent/'roles'/'relevance_filter.md')") my_office/roles/
```

Say plainly that you have done this, and show the user the criteria block you
rewrote — it is the part they will want to adjust.
