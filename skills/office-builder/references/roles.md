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

## Filters — two outports, and this is the important part

| Role | Outports | Decides |
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
| `synchronizer` | `synchronizer(inports=["a","b"])` | waits for one message on each named inport and joins them into a single message. The fan-in half of a fan-out |
| `gate` | `gate(data="data", control="control")` | admits one item at a time, releasing the next only when told. **This is what lets a loop terminate** — `dsl check`'s W7 warns about a loop with no gate |
| `select` | `select(inports=[...], command="command")` | a commanded traffic controller: reads whichever inport its state points at |
| `router` | `router(routes=[...])` | forwards each message to a named outport by rule |
| `record` | `record(initial={...})` | a shared keeper — store and reply, for state several agents consult |
| `deduplicator` | `deduplicator(by="url")` | drops repeats by a named field |

`synchronizer` and `gate` are the two worth knowing cold. A fan-out to four
enrichers needs a `synchronizer` to recombine them (`situation_room`), and any
loop needs a `gate` or it never stops (`debate`).

## Always wire the reject port somewhere readable

```
Felix's keep is Riley.
Felix's discard is jsonl_recorder.     # not `discard` — while you develop
```

`examples/org_news_filter` does exactly this. Sending rejects to a recorder
rather than to the `discard` sink is what turns an invisible mistake into a
visible one: if the filter is dropping items it should keep, they are sitting
in the rejects file where the user can see them. Swap to `discard` once the
criteria are trusted.

## When to write your own instead

Write a new role when the job is genuinely not on this list:

- a domain vocabulary these do not know (species, tickers, part numbers)
- arithmetic over a stream — a moving average, an RMS, a rate of change
- wrapping a model or a library
- reshaping records into a form a specific sink needs

Then follow the English-or-Python guidance in `SKILL.md`. But say which of
these applies — if you cannot, one of the thirteen above probably fits.

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
