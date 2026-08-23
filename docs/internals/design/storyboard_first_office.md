# Storyboard: a first-year's first office

A storyboard, not a specification. It shows the conversation we want
to be possible, at the level of what appears on the screen, so that
the design that follows has something to be judged against.

Nothing here is a promise. Some of it works today; most of it does
not. [§12](#12-what-this-storyboard-costs) lists what each panel would
cost, and that list is the output of the exercise — the panels are how
we found it.

Read with [building_by_conversation.md](building_by_conversation.md),
which is the design this storyboard is meant to test. Where the two
disagree, the storyboard is the requirement and the design is the
attempt.

---

## Who she is

Six weeks of Python. Loops, lists, functions, one file at a time. She
has never run two things at once on purpose. She has not read the
documentation and will not read it before she starts; she will ask the
assistant instead, and she will ask *while building*, not before.

She has been told in class: *build something that watches something
you care about.* She is applying for internships and is tired of
scrolling job boards.

She does not know what an office is. She has been told her agents can
have names, and that is the only thing she remembers.

---

## 1. Cold open

> **"I want an office with Dan and Jay."**

```
# Office: draft

Agents:
Dan is unassigned.
Jay is unassigned.
```

> Two agents, no roles yet.
>
> **Still to do:** Dan and Jay have no role; no source; no sink;
> nothing is connected.

**Why this panel.** She said one thing and one thing was written. No
question came back, no form appeared, and nothing was invented on her
behalf — no source she did not ask for, no plausible guess at what Dan
might do. The first thing she learns is that **what she says becomes
the document**, which is the only reason she will trust the document
later.

**The gap list is the tutorial.** It is not an error report. It is the
syllabus for the next four minutes, in her own office's terms, and it
appears without her asking.

---

## 2. "What is an office?"

She asks *after* the file exists, not before. This is the normal case
and the design has to expect it.

> An office is a group of agents that keep running and pass messages
> to each other. Yours has two, Dan and Jay. Each one will be given a
> job, and each runs on its own — they do not take turns, and they do
> not share any variables. They only see what is sent to them.
>
> Right now yours has nobody doing anything and nothing coming in,
> which is what the list above is telling you.

**Why this panel.** Three sentences, then back to her office. The
answer is **about what is on her screen**, not about distributed
systems in general. A definition she cannot point at is a definition
she will not keep.

**The rule this sets.** Any "what is …" question is answered in at
most three sentences, followed by the state of her office and the gap
list. Never a lecture; never a link as the whole answer.

---

## 3. "What roles are already shipped?"

> Thirteen come with the library. Each reads one message and adds
> something to it:
>
> | Role | What it adds |
> |---|---|
> | `summarizer` | a one-sentence `summary` |
> | `sentiment_classifier` | `sentiment`: positive, negative, neutral |
> | `severity_classifier` | `severity`: how urgent it looks |
> | `urgency_classifier` | `urgency` |
> | `topic_tagger` | `topic` |
> | `category_classifier` | `category` |
> | `entity_extractor` | the people, places and organisations named |
> | `geolocator` | where the item is about |
> | `relevance_filter` | sends to `keep` or `discard` |
> | `confidence_filter` | drops items below a confidence you set (Python, free) |
> | `evaluator` | scores an item against criteria you give |
> | `writer` | turns a batch into a written page |
> | `summary_writer` | one page summarising many items |
>
> If none of them fits, describe what you want in a sentence and I
> will write the role from your words.

**Why this panel.** She cannot want a component she does not know
exists. Two things make this table work and both are load-bearing: the
column is **what it adds to the message**, not what it "does" — that
is the thing she needs in order to wire the next agent — and the last
line tells her the library is not the boundary of what she can have.

**What is missing today.** There is no way to produce this list.
Library roles are files in [dissyslab/roles/](../../../dissyslab/roles/)
found by a directory scan; there is no registry, no `dsl roles`
command, and **no one-line statement of what each role emits** that an
assistant could quote. Today it would read the prompt files and
paraphrase, which means the description a student is given is
improvised afresh each time.

---

## 4. She takes one

> **"Jay does the summarizing one."**

```
Jay is a summarizer.
```

> Jay is a `summarizer` — it adds a one-sentence `summary` field and
> passes everything else through unchanged. It uses a language model.
>
> **Still to do:** Dan has no role; no source; no sink; nothing is
> connected.

**Why this panel.** She is told what Jay emits *at the moment Jay is
assigned*, not when something fails. She is also told, in passing and
without ceremony, that this one costs money to run. That fact belongs
here, attached to the decision, rather than in a section about
pricing.

---

## 5. "I want to define a role"

Nothing in the library knows what she means by a job she could
actually get.

> **"Dan reads job posts. If a post doesn't want more than two years
> of experience, send it to `worth_a_look`. Otherwise send it to
> `too_senior`."**

`roles/dan.md`, written from her sentence:

```
# Role: dan

You read one job post at a time.

Decide whether the post requires more than two years of experience.

If it does not, send to worth_a_look.
Otherwise, send to too_senior.
```

```
Dan is a dan.
```

> Dan's job is the file `roles/dan.md` — that is your sentence, and
> you can open and edit it. Dan has two outboxes, `worth_a_look` and
> `too_senior`, because you named them.
>
> **Still to do:** no source; no sink; Dan's `worth_a_look` and
> `too_senior` go nowhere; Jay's output goes nowhere.

**Why this panel.** This is the moment the system stops being magic.
Her sentence *is* the program for Dan: she can open it, read it, and
change a word. Nothing was translated into something she cannot read.

**And her sentence declared the interface.** The two outbox names came
out of her own "send to …" phrasing by a fixed textual rule, with no
model asked to guess. That is why the gap list can say Dan has two
unwired outputs before a single connection exists. This part works
today.

**Open, and awkward.** `Dan is a dan.` is what the grammar produces
when the role is named after the agent. It reads badly enough that a
student will notice. Either roles get named for the job rather than
the agent — the assistant proposing `experience_filter` and saying so
— or the grammar grows a form for "Dan's job is this file". A decision
is needed; this storyboard does not make it.

---

## 6. "What is a source?"

She asks because the gap list has said *no source* four times.

> A source is where messages come into your office from the outside —
> a news feed, a folder of files, your email, a job board. Your office
> has none, so nothing would ever arrive and Dan would sit waiting
> forever.
>
> For job posts there are `python_jobs`, `remoteok` and
> `we_work_remotely`.

> **"python_jobs."**

```
Sources: python_jobs(poll_interval=600)
```

> Checking every ten minutes. Say if you want it faster or slower.
>
> **Still to do:** no sink; `python_jobs` has no destination; Dan's
> `worth_a_look` and `too_senior` go nowhere; Jay's output goes
> nowhere.

**Why this panel.** The definition arrives at the moment she needs it,
and it is followed immediately by the two or three real names that
apply to *her* problem — not the full catalogue of forty-five.

**Why the interval is stated and not asked.** A default is chosen, the
choice is made visible, and she is invited to overrule it. Asking
would have cost a turn to establish something she has no opinion
about yet.

---

## 7. She wires it backwards

> **"Connect Jay's outbox to Dan's inbox."**

```
Connections:
Jay's out is Dan.
```

> Done — Jay's output now goes to Dan.
>
> **Still to do:** no sink; `python_jobs` has no destination; nothing
> reaches Jay; Dan's `worth_a_look` and `too_senior` go nowhere.

She reads *nothing reaches Jay* and works out that she has it round
the wrong way.

> **"No — the other way. Dan first."**

```
Connections:
python_jobs's destination is Dan.
Dan's worth_a_look is Jay.
```

**Why this panel.** She was not corrected. She said something, it was
written exactly as said, and the consequence appeared in the gap list
one line later — where she found it herself. That is worth more than
being told, and it is the same mechanism that will catch her when
nobody is watching.

**The line it draws.** The assistant does not silently improve what
she said, and it does not refuse it either. It writes it and reports
what follows. The gap list is the feedback, not the assistant's
opinion.

**What this panel needs.** *"Nothing reaches Jay"* is finding W3,
unreachable agent, in draft language. It exists as an error today and
would have to be reframed rather than invented.

---

## 8. It runs and does nothing

> **"Run it."**

She has no sink. Three ways this could go, and only one is acceptable:

- it runs, finishes, prints nothing, and she concludes the framework
  is broken — **this is what happens today**;
- it refuses with a stack trace;
- it refuses in a sentence:

> Nothing leaves this office yet — there is nowhere for Jay's
> summaries to go, so running it would do work you would never see.
> Add `console_printer` to print them, or `markdown_digest` to write
> them to a file.

> **"Both."**

```
Sinks: console_printer, markdown_digest(path="internships.md")

Connections:
python_jobs's destination is Dan.
Dan's worth_a_look is Jay.
Dan's too_senior is discard.
Jay's out is console_printer, markdown_digest.
```

**Why this panel.** *No sink* is singled out in the design because it
is the one gap a student cannot diagnose: the office is structurally
fine, runs cleanly, exits zero, and produces silence. Every other
mistake announces itself.

**And she connected one outbox to two sinks** without being told she
could. The grammar allowed it because she tried it. Worth noticing:
the fan-out she just used is the same primitive the four-way briefing
office is built from.

---

## 9. It works

Posts scroll past. Two are worth a look. `internships.md` exists.

This is the moment the course is for, and it arrived in nine turns
without her writing a line of Python or reading a page of anything.

---

## 10. "Why did it stop?"

> It stopped after five cycles. Everything here does that unless you
> say otherwise, so that an office you forget about does not run all
> weekend against a paid model. Say *run it until I stop it* and it
> will.

**Why this panel.** The limit is met as a fact about her office, at
the moment it bites, rather than as a warning she read and forgot.

---

## 11. The door

> **"How does it know when it's finished?"**

She has asked, without knowing it, the question the second half of the
course answers.

> Harder than it sounds. Dan can see that Dan has nothing to do. Dan
> cannot see whether Jay is about to send him something. Nobody in
> your office can see the whole office at once — that is what makes
> this a distributed system rather than a program — and yet the office
> as a whole worked out that it was done and exited cleanly.
>
> There is an algorithm for that, and you have been running it. Want
> to see it?

**Why this panel.** The measure of success for the whole project is
*a first-year builds an application they care about, and then studies
the algorithms underneath it.* This panel is the hinge between the two
halves, and it is the reason the storyboard does not end at panel 9.

The hinge has to be **her question**, prompted by something she
observed, not a section she was sent to read.

---

## 12. What this storyboard costs

| Panel | What it needs | State |
|---|---|---|
| 1 | `Dan is unassigned.` parses; a draft office is a legal file | designed, [building_by_conversation.md §3](building_by_conversation.md) |
| 1, 4–8 | `office.md` written from the first sentence and shown every turn | designed, §1 |
| 1, 4–8 | The gap list: draft framing, plus "no role yet" and "no sink" | designed, §4 |
| 1, 7 | Write only what was said; never invent; never silently correct | designed, §5 — not in the skill |
| 2, 6 | "What is …" answered in ≤3 sentences, in terms of her office, then straight back to the build | **not designed** — a turn protocol exists (§5) but says nothing about teaching turns |
| 3 | A way to list library roles, and **one line per role saying what it emits** | **does not exist.** No registry, no `dsl roles`, no summary line. Proposed: a required front-matter line in each role file, and `dsl roles` to print it |
| 3, 6 | Naming only the two or three components relevant to her problem, not the catalogue | **not designed** |
| 4 | Saying what a library role emits when it is assigned | designed, §5 |
| 5 | An English role written from her words; outboxes taken from her "send to" phrasing | **works today** |
| 5 | What to call a role invented for one agent — `Dan is a dan.` is not acceptable | **open** |
| 6 | A default poll interval stated rather than asked | **not designed** |
| 7 | W3 reframed as "nothing reaches Jay yet" | designed, §4 |
| 8 | `dsl run` refusing an office with no sink, in that sentence | **not designed.** §4 lists "no sink" as a gap; refusing to run on it is a further step |
| 10 | The run summary saying why it stopped, in her language | **not built** |
| 11 | Nothing — it is a conversation. But it needs [docs/algorithms/](../../algorithms/) to be readable by a first-year | **unknown** |

---

## 13. What she says that does not work

Worth listing, because each one will be said in the first week.

**"Make Vikram a source."** Sources are library components with fixed
names; only middle agents take names like Dan. Needs source aliasing —
`python_jobs as Vikram` — which touches the parser, the spec, the
checker and codegen. Out of scope in the design, and it will be asked
for on day one, because the whole surface has taught her that things
have the names she gives them.

**"Run Dan on my laptop and Jay in the cloud."** One process, agents
in threads. Not a bug, and answering it well is a teaching moment
about what an office is.

**"Why is it stuck?"** Structurally correct and deadlocked. `dsl check`
cannot see it, deliberately, and the honest answer is a course topic
rather than a fix.

**"Undo that."** Nowhere in the design. She will say it in the first
ten minutes. `office.md` under version control would answer it, and
nothing currently puts it there.

---

## 14. What this storyboard deliberately leaves out

**A second student.** One path, followed to the end, is more useful
than three sketched. The panels that generalise are the shapes — cold
open, definition-on-demand, catalogue, own words, wrong wiring, silent
run, the door — not the internship office.

**Everything visual.** No diagram is shown at any point. Whether she
should see the graph, and when, is a real question and is not settled
here.

**The instructor.** Thirty of these happen at once in a room, and
someone marks the results. Assessment is in
[../STATUS.md](../STATUS.md) and is not part of this.
