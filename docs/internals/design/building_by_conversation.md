# Building an office by conversation

A design note. **Sections 3 and 4 are now built** — see the status
line at the head of each section, and `tests/unit/test_draft_office.py`.
The rest is still design.

The `office-builder` skill assumes an office is drafted whole and then
checked. A student building one by talking does the opposite: names
first, behaviour next, wiring last, a sentence at a time. This note
describes what the framework needs so that conversation can be written
down as it happens, and `office.md` can be the record of it from the
first sentence rather than only at the end.

Status: §3 and §4 are built. `Jay is unassigned.` parses as undecided
rather than as a sub-office path, an office holding one is a draft,
`dsl check` reports its findings as remaining work and exits 0, and
`dsl run` and `dsl build` refuse with a sentence naming every agent
whose job has not been decided. §5 (the turn protocol) and §7 are not
built; neither is the office rename.

One deliberate divergence from §3. The role is the reserved string
`unassigned`, not `None`. `None` is tidier and it is what §3 argued
for, but `role_name` is a non-empty `str` read in 82 places across
nine modules, and widening it would touch the compiler, codegen and
every consumer to express something three of them care about. The
reserved name costs one test, which keeps a role file of that name
from shadowing it.

---

## 1. What is missing

The skill's loop is: draft `office.md` and the role files, run
`dsl check`, fix, run. That is right for an office whose shape is
known. It has two consequences for a conversation.

The user must specify everything before anything is written, because a
partial `office.md` is not writable — every agent line requires a
role. So the office lives in the assistant's head until it is
finished, and the artifact-of-record property is lost exactly when the
user most needs to see what has been understood.

And `dsl check` treats incompleteness as failure. For a finished
office that is correct. For one under construction its findings are
not errors; they are **the remaining work**, and they are already the
right list.

## 2. Three mismatches between the user's model and the grammar

**Name first, role later.** *"Make an office with Jay, Dan and
Vikram."* There is no way to write an agent down without giving it a
role. §3 fixes this.

**Behaviour, not role name.** *"Jay evaluates the sentiment of
messages it receives."* The user describes what an agent does; the
grammar names a role defined elsewhere. The user never says the word
*role*, and should not have to. §5 covers the translation and what the
assistant owes the user when it makes one.

**Sources are named by what they fetch.** *"Make Vikram a source"*
does not fit: sources are library components named `bbc_world`,
`gmail`, `audio_folder`, and it is that name that appears in the
wiring. Only the middle agents take names like Jay. This wants a
source alias — `bbc_world as Vikram` — and is deliberately **out of
scope here**; it touches the parser, the spec, `check_wiring` and
codegen, and should land as its own change.

## 3. `unassigned`

```
Jay is unassigned.
```

**Parsing is not free, and I checked rather than assumed.**
`_AGENT_LINE_RE` is

```
^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(?:is|are)\s+an?\s+(.+?)\s*$
```

The article is mandatory, so `Jay is unassigned.` does **not** match
this pattern.

**And that was the wrong thing to check.** An earlier version of this
note stopped there and concluded the line is rejected today. It is
not. `_AGENT_LINE_RE` is tried first and fails, and the parser then
falls back to a legacy form, `name is <path>`, for sub-offices written
without the `office at` phrase. So the line parses, and produces

```
RoleRef(agent_name='Jay', role_name='unassigned', path='unassigned')
```

— an agent whose job is a sub-office in a directory called
`unassigned`. Nothing says so. `dsl check` then reports W6, *"'Jay' is
a 'unassigned', but there is no roles/unassigned.md"*, which is a
comprehensible sentence about the wrong thing: the office is not
missing a file, it is missing a decision.

Two lessons, and the second is the general one. Testing a regex is not
testing a parser — the fallback was ten lines further down and would
have been found by running the line through `parse_office_dir`, which
is what "I checked rather than assumed" should have meant. And a
silent misparse is a worse starting position than a clean rejection,
so this is more urgent than the earlier version made it look, not
less.

Three ways out:

- `Jay is a placeholder.` parses right now, with no change at all. It
  reads slightly worse and it is a real role name that could collide.
- Make the article optional. One character, and it loosens the grammar
  everywhere — `Jay is deduplicator.` would then parse. Strictness is
  the point, so no.
- Add `unassigned` as its own branch. The trailing full stop has to
  be consumed by the branch, because the existing one captures it into
  the role and strips it downstream:

  ```
  (?:an?\s+(.+?)|unassigned\.?)
  ```

  Verified: this matches `Jay is unassigned.` with group 2 `None`,
  still matches `Dan is a router.`, `X is an office at ../news.` and
  `Sync is a synchronizer(inboxes=['a']).`, and still rejects
  `Jay is deduplicator.` A `None` role is then the signal for
  unassigned, which is cleaner than a reserved name that could
  collide with a real one.

Take the third — and note that the branch has to be tried *before*
the legacy path fallback, or the fallback keeps swallowing the line
and nothing changes. Then the rest of the meaning is still missing:

- a reserved entry in the role library that refuses to run;
- `check_wiring` reporting it as a gap — *"Jay has no role yet"* —
  rather than W6, *missing role file*;
- `dsl run` declining with that message rather than a lookup failure.

**Draft mode is not a flag.** An office containing an unassigned agent
*is* a draft. `dsl check` then reports gaps in draft language and
exits 0; `dsl run` refuses. Nothing for the user to remember, and
nothing the assistant can forget to pass.

`Sources:` and `Sinks:` may be absent — the parser already allows an
empty section — so the first turn of a conversation produces a legal
file.

## 4. The gap list

The findings do not change. Their framing does.

| Finding | As an error | As a gap |
|---|---|---|
| (new) | — | Jay has no role yet |
| W1 | declared inbox nothing writes to | nothing is connected to Dan's `in_` |
| W3 | unreachable agent | nothing reaches Vikram yet |
| W4 | dead end | Dan's `immediate` goes nowhere yet |
| W6 | missing role file | (only after a role is named) |
| W8 | source with no destination, sink nothing feeds | — |
| (new) | — | no sink: nothing leaves the office yet |

Two of these are new. *"Jay has no role yet"* follows from
`unassigned`. **"No sink" deserves its own line** because it is the
one gap a student will not notice: an office with no sink runs,
finishes, and appears to do nothing.

## 5. What the assistant owes the user

**Write only what was said.** Never invent an agent, a role, a source
or a connection the user did not ask for. This is the rule the whole
design rests on. A helpful assistant, told *"make an office with Jay,
Dan and Vikram"*, will want to supply a source and a sink; that ends
the conversation, because the user stops building and starts
reviewing.

**Say what a library role emits.** When *"Jay evaluates the
sentiment"* becomes `Jay is a sentiment_classifier.`, the user has
been handed a component they have never seen. Unless they are told it
adds a `sentiment` field taking three values, they will wire the next
agent to it blind and meet the mismatch at run time. One sentence,
every time a library role is assigned.

**Keep the user's words in the role file.** When no library role fits,
the English role is written from the user's own sentence, as close to
verbatim as the output contract allows. The role file should read back
to them as something they said.

**Three outcomes, and name which one you took.** A library role
matches; nothing matches, so write an English role; close but not
exact, so propose it, state the difference, and ask.

**Every turn ends the same way.** One line on what changed; the
current `office.md`; the gap list; at most one question, and only if
it blocks writing the next line. Three questions a turn kills the
flow.

## 6. A worked conversation

Every line below is accepted by the parser as it stands, except
`unassigned`, which needs §3.

---

**"Make an office with Jay, Dan and Vikram."**

```
# Office: draft

Agents:
Jay is unassigned.
Dan is unassigned.
Vikram is unassigned.
```

> Three agents, no roles yet. Still to do: Jay, Dan and Vikram have no
> role; no source; no sink; nothing is connected.

Do not ask for an office name here. The user does not yet know what
the office does. `draft` is renamed when the purpose appears.

---

**"Jay evaluates the sentiment of messages it receives."**

```
Jay is a sentiment_classifier.
```

> Jay is a sentiment_classifier from the role library — it adds a
> `sentiment` field with values positive, negative or neutral.
> Still to do: Dan and Vikram have no role; no source; no sink;
> nothing is connected.

---

**"Dan has two outboxes, `immediate` and `delay`. Dan puts urgent
messages in `immediate` and the rest in `delay`."**

`roles/router.md`:

```
# Role: router

Decide whether each message is urgent.

If the message is urgent, send to immediate.
Otherwise, send to delay.
```

```
Dan is a router.
```

This works today and needs nothing new. `nl_role` extracts an English
role's outboxes from the prompt by a strict `send to <name>` rule — no
model involved — so **the user's sentence declares the outboxes**.
`job_hunter/roles/screener.md` ends the same way: *"If the job is
relevant, send to relevant… if not, send to discard."*

It also means the checker knows Dan has two unwired outboxes before
any connection exists, so the gap list is right at this turn:

> Dan routes to `immediate` and `delay`. Still to do: Vikram has no
> role; no source; no sink; Dan's `immediate` and `delay` go nowhere;
> nothing is connected.

---

**"Connect Jay's outbox to Dan's inbox."**

```
Connections:
Jay's out is Dan.
```

The default outbox is `out` and the default inbox `in_`. The user
never needs to know that; the assistant does.

## 7. What this does not settle

**Source aliasing**, deferred above, and the reason *"make Vikram a
source"* still cannot be written.

**Renaming the office.** `draft` has to become something, and the
natural moment is when a sink appears — the office is named for what
it produces. Whether the assistant proposes a name or asks is open.

**When to stop being a draft.** Removing the last `unassigned` makes
the office runnable, but it may still have no sink. Whether draft mode
ends at the last `unassigned` or at the first clean `dsl check` is a
decision with consequences for `dsl run`'s refusal message.

## 8. Implementation checklist

Not done.

- [ ] `unassigned` as a reserved role that refuses to run
- [ ] draft detection: an office with any unassigned agent
- [ ] the two new findings, and draft framing for the existing ones
- [ ] `dsl run` refusal naming the unassigned agents
- [ ] the turn protocol and the three rules in `office-builder`
- [ ] this conversation as the skill's worked example
- [ ] tests: a draft parses, checks clean-with-gaps, and refuses to run

---

See also: `readers_and_surfaces.md`, which argues that `office.md`'s
grammar is narrow so `dsl check` can catch what a language model got
wrong. Draft mode is the same argument applied while the office is
still being written.
