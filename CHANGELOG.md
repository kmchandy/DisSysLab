# Changelog

All notable changes to DisSysLab are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/);
versions follow [SemVer](https://semver.org/).


## [1.10.1] — 2026-08-29

### Fixed — `dsl run <name>` no longer writes inside the installed package

`dsl run periodic_brief` resolves a name against the shipped gallery,
which lives in site-packages — and wrote its generated `build/run.py`
there, then printed

```
Run with:  python /.../site-packages/dissyslab/gallery/apps/periodic_brief/build/run.py
      or:  dsl run /.../site-packages/dissyslab/gallery/apps/periodic_brief
```

Three things wrong with that, for the one command a student is most
likely to run first: it teaches a beginner that their office lives
inside the package, it points them at a file the next
`pip install --upgrade` deletes, and it fails outright where
site-packages is read-only. Output already landed in the right place;
the artifact did not.

A packaged office's artifact now goes to `./build/<office_name>/run.py`
in the current directory — named by office, so running two gallery
offices from one folder does not collide — and the printed hint says
`dsl run <name>`, the form they used and the one that keeps working.
An office you own is unchanged: `build/run.py` beside it, which is the
point of generating readable Python.

Two consequences that had to move with it, both found by running the
command rather than reading the code:

- **The working directory is decided at build time.** The artifact used
  to test `_pkg not in _HERE.parents` at run time, asking where
  `run.py` sat as a proxy for whether the office was packaged. Moving
  the artifact inverted the proxy, which would have sent a gallery
  office's output into the build folder. Codegen knows which case it is
  emitting, so it emits the answer instead of the question.
- **A packaged office finds its roles through `dissyslab`.** The
  artifact located them relative to its own `__file__`, correct while
  it sat at `<office>/build/run.py`. Once the two were in unrelated
  directories every lookup resolved wrongly and `dsl run
  my_first_office` died with `KeyError: 'analyst'`. Anchored to the
  package rather than to an absolute path, so it survives the package
  being in a different virtualenv.

`test_a_packaged_office_does_not_chdir_into_site_packages` asserted the
old mechanism by name. It asserts the behaviour now, for both cases —
a mechanism test cannot survive a change of mechanism, which is the
whole reason to change it.

## [1.10.0] — 2026-08-29

**Two things a student could hit on their first afternoon, and both
were silent.** An ordinary Python mistake in a role hung the office for
ever; an annotator's field could go missing without a trace. Neither
had a test, because neither was visible from inside the process it
broke. Both were found by running the software rather than reading it.

### Fixed — a role that fails no longer hangs the office

`Role.run` ended with `print(...)` and `return`. The `return` ends the
thread, so the agent never reaches the shutdown protocol, termination
detection waits for an agent that is gone, and **the office runs for
ever** — for any exception, in any role. A first-year's `1 / 0`
produced a program that never stopped, having printed the reason into a
stream of other agents' output, spliced mid-line because threads share
one stdout:

```
...division by zero[1] {'n': 2}
```

`dsl check` said "no problems", correctly: it is a runtime fact.

One bad message now costs that message. The failure is counted, the
loop continues so shutdown still arrives, the run summary says how many
failed and quotes the first, and **`dsl run` exits non-zero** — so does
`python build/run.py`, because `run_network()` returns the code and the
generated artifact raises `SystemExit` with it. A run that limped is
never mistaken for one that worked. The report is a single write to
stderr, so redirecting the office's output to a file still leaves the
failure on the terminal, and it names the student's own file and line.

### Breaking — the output contract is generated from `adds:`

A role declares the fields it puts on the message, beside its ports:

```
---
emits: one plain-English sentence saying what the item is about
outboxes: out
adds: summary
---
```

Until now an annotator said so in prose — *"Return a single JSON object
containing every field of the input plus `summary`"* — while the
framework appended, as the last thing the model reads:

```
Return JSON only, no explanation, no nested JSON:
{"send_to": "<one of: out>", "text": "<content>"}
```

Two keys. Not `summary`. A model obeying the last line returns those
two and the field the role exists to add never appears; a model obeying
the role ignores the contract. Which wins is up to the model, and the
twelve shipped annotators worked only because capable models follow the
longer, more specific block — not a guarantee, and weakest on exactly
the small local models a beginner is pointed at.

A second collision sat in those same two lines. `text` meant the
article's body in the role's input shape and the role's own output in
the contract, so a model obeying the contract **overwrote the body** —
in roles promising, in the same prompt, to preserve every field.

The contract is now generated from `outboxes` and `adds` and is the
only statement of the reply shape anywhere:

```
relevance_filter  {"send_to": "<one of: keep, discard>"}
summarizer        {"summary": <summary, as described above>}
evaluator         {"send_to": ..., "verdict": ..., "feedback": ...}
```

There is no generic content slot, so `text` never appears except where
a role genuinely writes and declares `adds: text` — which is what the
sinks read; `gmail_sink` uses it as the email body. The collision is
impossible by construction rather than renamed, so the 67 files that
mention a `text` key are untouched.

Three things follow. A filter is asked for `send_to` and nothing else;
it decides, it does not produce, and asking invited the model to invent
content. A single-outbox role is not asked to choose. And a reply
missing a declared field is now an error — until now a missing
annotation and a null one were the same thing.

**What breaks.** A `.md` role that adds a field must declare it, or the
model is never asked for it. All 44 prose roles in this repository were
migrated. `nl_role` takes `adds=`.

### Changed — report, do not repair

The rule Mani set, applied to the Python/LLM boundary:

- **`send_to` naming an outbox the role does not have** used to be
  passed through to the crash above. It now stops, naming the value,
  the declared outboxes, and the nearest match. An earlier draft routed
  it to the default and counted it — worse than the crash it replaced:
  a model answering `discrad` would have had the item it decided to
  discard passed on as *kept*, the office would have exited 0, and
  nothing on screen would be wrong. A hang at least stops.
- **`send_to` absent** now defaults only where there is no choice to
  get wrong — a single outbox. With two or more the model did not
  decide, and nothing is entitled to decide for it.
- **An exception in the call** used to print and return `[]`, dropping
  the message and letting the office exit 0 having quietly produced
  less than it should have.

A plain-text reply is unchanged. The role's prompt did not necessarily
ask for JSON, so it violates nothing.

### Fixed — an argument a component does not have

```
Sources: file_source(path="items.jsonl")
```

checked clean and died at run time with `TypeError: FileSource.__init__()
got an unexpected keyword argument 'path'` — from inside generated code
the student did not write, naming a keyword they did type. It is
`filepath`. `dsl build` now says so, with the nearest name.

It is a build-time check and not a `dsl check` code deliberately:
answering it needs the call codegen actually emits — a registry entry
maps `web(url=...)` onto `MCPSource(server=, tool=, args=)` — and
rendering imports the office's Python roles, which `dsl check` must
never do.

### Fixed — `relevance_filter` discarded what it promised to keep

`out_ports[0]` is where a message goes when the model does not choose.
The role declared `outboxes: discard, keep`, so an unclassified item
was thrown away — by a role whose own text says twice that discarding a
borderline item is the worse mistake. The cause was a line wrap: ports
used to be built by scanning each line for `send to <name>`, and the
sentence that decides this one wrapped between `send to` and `keep`.

Found by comparing a shipped role against one an assistant wrote in a
student session, which had put `keep` first and explained why. A test
now asks whether a role's declared first outbox is the fallback its
prose promises, reading the body unwrapped.

### Changed — `dsl doctor` reads the hash, not the date

The staleness check compared the hand-written date half of a skill
version and discarded the hash — the half `stamp_skills.py` calls
*"what proves an install took"*. On one machine that produced both
wrong answers at once: a skill byte-identical to the release was told
to reinstall, and one genuinely a commit behind passed in silence.
Equal hashes are now silent whatever the dates say; a newer date is
silent too, since a save that did not take cannot carry a future date.

The short form also printed `None` for a skill with no version line,
and printed a duplicated skill twice with no comment.

### Also

- `dsl roles` prints the declared fields. `emits:` says what a value
  *means* and no longer names it — it had already drifted twice.
- `dsl grammar roles` documents `adds:` and says not to write an
  Output section.
- `roles.md`'s claim that rejects sent to `discard` are invisible was
  wrong: the sink counts them and the run summary prints the count.
  What is lost is *which*, not how many.

## [1.9.0] — 2026-08-29

**An agent's interface is now written down.** Every role declares its
inboxes and outboxes, and the framework reads the declaration instead
of guessing from English prose. That one change closes a trap, makes
three checks possible that could not exist before, and is the reason
this is 1.9.0 rather than 1.8.1.

### Breaking — roles declare their ports

A prose role declares in its front matter, beside `emits:`:

```
---
emits: decides whether an item is worth passing on
inboxes: in_
outboxes: keep, discard
---
```

`inboxes:` may be omitted and defaults to `in_`. A Python role already
declared, in the `AgentRoleEntry` it builds — nothing was added to
those files.

**What breaks.** A `.md` role with no `outboxes:` in its front matter
now fails to load, with an error naming the block to add. `nl_role()`
takes `outboxes=` and `inboxes=` and raises without them. Every role
in this repository — all 98 — was migrated, and **all 40 shipped
offices compile to byte-identical code**, so an office is affected only
through its own `roles/` folder.

**What it fixes.** Ports used to come from a regular expression over
the role's prompt: a line containing `send to` contributed every
`to <name>` on it. So writing ``send to `keep` `` — backticks, as any
careful writer puts round a port name — created no port at all. The
office checked clean, built clean, ran clean, and produced nothing. No
check could see it, because there was nothing for the wiring to
disagree with: the prose *was* the declaration.

It also meant `office.md` could not be understood by reading it.
`Screen is a relevance_filter.` says nothing about Screen having an
outbox called `discard`, and finding out meant opening a file that
might be inside the installed package.

Declarations are read **statically, never by importing** — `dsl check`
has to be safe to run on code you did not write, and a Python role's
ports are read out of its `AgentRoleEntry(...)` by AST.

### Added — W13: a message sent to an inbox that does not exist

```
Screen's inbx is ...
```

was silent, in the worst way. The check passed, the build emitted a
connection to a port that was never created, and the run failed with
*"Agent 'Screen' inport 'in_' is not connected to any queue"* — naming
`in_`, a port the writer never typed, about a line they did type.

W13 names the line, the sender and the inboxes the agent actually has,
and suggests the nearest spelling. A typo now produces **one** finding:
a misspelled destination leaves the real inbox unwired by construction,
so W1 would say the same thing a second way, and fixing the spelling
fixes both.

### Changed — W1 reaches every agent, and W2 works at all

**W1** (an inbox nothing writes to — the usual reason an office hangs)
used to reach only the three coordinator kinds that spell their inboxes
on the agent line. It now covers every agent whose role declares
inboxes, which is all of them. It stands down for an agent nothing
reaches at all: W3 says that once and says why, and one W1 per inbox on
top of it buries the finding that leads somewhere.

**W2** (an outbox wired to nothing) was reserved for years on the
grounds that it needed a resolved shape nothing had. It has one now.
An unwired inbox blocks, which at least stops; an unwired outbox raises
the first time it is used, so a filter wired only on `keep` passed
every check and stopped on the first item it wanted to discard.

Both are silent on all 40 shipped offices, pinned by a test.

### Changed — `dsl draw` prints text by default

`dsl draw <dir>` now prints the wiring as a table, both ports named on
every edge, followed by what is unconnected. `--mermaid` gives the old
diagram. **This is a breaking change to the command's output**, and it
is the right default: a Mermaid diagram is something you paste into
another program, and the question someone asks `dsl draw` is *where
does this message go*.

The picture and the checker now read ports through the same function,
so a port drawn as unconnected is the port W1, W2 or W13 will name.

### Changed — the office-builder skill is 84 lines

It was 1,597, across five files. The grammar, the role list, the
sources and sinks and the worked examples now ship **inside the
package** and are printed by `dsl grammar`, `dsl grammar roles`,
`dsl grammar sources` and `dsl grammar examples`.

The reason is not brevity. A skill installs from GitHub and the package
installs from PyPI, so anything written in both is a second copy on a
second release path, and the two go out of step the first time either
moves. A user with yesterday's skill was being taught a language their
install did not have — silently, because nothing compared them.

What is left is a version string derived from the file's own content, a
retargeted `description:`, the command list, and "if a command below is
missing, this install predates it". A test asks the CLI parser whether
every command named in the file is real.

### Added — `guard()`: your own checks around a model call, opt-in

`guard(role, before=..., after=..., on_reject=...)` composes a check
before a role and a check after it **inside one agent**, not three. The
rejected alternative — a guard as its own agent — is written down in
`docs/internals/design/guard_rails.md` along with why, and with a
four-sitting micro-course on what these can and cannot do.

### Fixed

- **The skill search walked past where skills actually are.** Cowork
  stores them at `~/.claude/skills/synced/<uuid>/<name>/SKILL.md`, and
  `dsl doctor` reported "not installed" for a skill sitting on disk.
  That produced a loop with no way out: doctor says install it,
  installing changes nothing, doctor says it again. The search now
  matches a known skill name with a `SKILL.md` under any parent at any
  depth.
- **`dsl doctor` is quiet when healthy.** It printed a wall of green
  ticks that a beginner had to read to find the one line that mattered.
  `--full` restores the detail. Its verdict no longer says "not
  installed" for a skill that is in the repository but not installed —
  those are different sentences and the fix for each is different.
- **A packaged office no longer writes into itself.** `dsl run
  periodic_brief` wrote `brief.html` inside site-packages, because the
  generated artifact `chdir`s to the office so relative paths resolve
  beside it. The artifact now decides for itself, so `python
  build/run.py` behaves the same way. (`dsl run` still writes the
  generated `build/run.py` into the installed package; that is
  outstanding.)
- **`dsl list` no longer describes offices by their own wiring**, and
  `roles_catalogue` no longer runs a second, differently-ordered prose
  scan of its own — it calls the same reader the loader calls, so the
  catalogue cannot describe a role differently from the office that
  uses it.
- **`dsl doctor`'s staleness check was inverted, on both sides at
  once.** It compared the hand-written date half of a skill version and
  discarded the hash half — the half `stamp_skills.py` describes as
  *"what proves an install took"*. On one machine on release day that
  produced both wrong answers together: `sensor-office-builder`, whose
  installed copy was byte-identical to what the release was built with
  (`935f28d` either side), was told to reinstall; `office-builder`,
  which was genuinely a commit behind, was passed in silence because
  both strings began `2026-08-26`.

  Equal hashes are now silent whatever the dates say. A newer date is
  silent too — a save that did not take cannot carry a future date. An
  older date is the fault it always was. The same day with different
  content is the one case nothing can resolve, since two hashes cannot
  be ordered, so it gets one line naming both readings rather than a
  guess.
- **The short `dsl doctor` printed `None`** for a skill whose SKILL.md
  has no version line, and printed a duplicated skill name twice with
  no comment. The long form already handled both. A summary that drops
  the finding is worse than one that is long, because it is believed:
  two installed copies of one skill means an assistant loads one of
  them and which one is not the user's to choose.

## [1.8.0] — 2026-08-27

Fifty-five commits, and one theme runs through most of them: **the
software says out loud what it knows, in a channel where it can be
checked.** Every entry below that reads as a bug fix is an instance of
the same failure — a document promising behaviour the code did not
have, a program reporting a fact in a place nobody would look, an
assistant summarising a warning into "all good". The corrections are
mostly checks, because a check in a prompt is a request and a check in
code is a fact.

Nothing in this release changes the Python API. Offices written for
1.7.2 run unchanged.

### Added — G1, G2 and the draft office: one you have not finished writing

`Jay is unassigned.` is now a line you can write. It parses as a
decision not yet made rather than as a role named `unassigned`, and an
office holding one is a **draft** — a property of the office, not a
flag somebody has to remember to pass.

`dsl check` on a draft reports the same findings in different words and
**exits 0**. *"'Dan' is unreachable — no path from any source"* becomes
*"nothing reaches Dan yet"*; the header reads `draft, 4 things still to
do`. Two findings are new: **G1**, an agent with a name and no job, and
**G2**, nothing leaves this office. `dsl run` and `dsl build` refuse a
draft, naming the agents whose job is undecided.

The reason is pedagogical and it is the point of the feature: an
unfinished office is not a broken one, and reporting it as broken
teaches a beginner that building is a sequence of errors.

### Added — five commands, so an assistant can ask instead of guessing

- **`dsl checks`** — what a check code means. `dsl checks W11` explains
  one; `dsl checks` lists all thirteen. `dsl check`'s own output now
  ends with a line naming the command and a code from that report, so
  the code is resolvable at the moment you meet it.

  The codes were opaque to everyone, the author of this project
  included: their meanings lived in the nine hundred lines that raise
  them and in CHANGELOG entries filed by release, so "what does W11
  mean?" had no answer short of a search. The descriptions are pinned
  to the checker by a test that reads `check_wiring.py` — a code raised
  with no entry fails, and so does an entry for a code nothing raises.
  A reference that can drift is worse than none, because it is
  believed.
- **`dsl roles`** — the built-in roles and, for each, the field it adds
  to a message. Every role file now opens with `emits:` front matter,
  in the file whose behaviour it describes, so changing a role and
  changing its description are one edit. Before this, an assistant
  asked "what roles are there?" read thirteen prompt files and
  paraphrased them afresh, and no two students were told the same thing
  about `summarizer`. The emitted field is the fact you actually need:
  something wired downstream of `severity_classifier` reads `severity`.
- **`dsl draw`** — the office's network as a Mermaid diagram.
- **`dsl skills`** — which skills ship with DisSysLab, which are
  installed, and **the folder each was found in**.
- **`dsl fetch-prices`** — the price downloader, previously a script
  inside one gallery folder that you had to `cd` into. With no tickers
  named it reads the basket out of the office's own
  `csv_stock_history(...)` line, so what is fetched is what will later
  be looked for. A capability an assistant cannot reach is one the user
  has to reach themselves.

### Fixed — `dsl list` was describing offices by their own wiring

The catalogue a beginner picks from, read as a new user for the first
time — by installing the wheel into an empty virtualenv, which is how
all three of these were found:

- **Eight offices were described as "Sources: starter"**. Their prose
  sat in `#` comment lines under the title, and the extractor skipped
  every `#` line as a markdown heading. In a README `#` is a heading; in
  an office.md only the first one is, and the rest are comments.
- **Ten more carried a leading `> `** into the terminal.
- **`salton_sea_dashboard` was listed under "ready to run"** while
  `dsl check` reports two faults on it. It has carried a `WIP` marker
  for months and the test sweeps honour it — `dsl list` did not read it.
  It is now marked `(unfinished)`, and `dsl init` on an unfinished
  office says so and says why.

Three offices that had no description anywhere now have one. A test
requires every shipped office to say what it is, and cannot be
satisfied by suppressing the line.

The section headings said **"Apps (for Pat)"** and **"Examples (for
Builders)"**. Pat and Builders are who this project designs for; a
student reading `dsl list` has never met them. Naming someone the
reader cannot ask about is the same defect as printing `W11` with
nowhere to look it up.

### Added — W11: text from the open web reaching something that acts

A note, not a fault. An agent whose job is a paragraph of English is
run by a model, and a model that can be instructed can be instructed by
its input; prompt injection is not something care in the role file
prevents. What *can* be bounded is the damage, and an office's declared
power is its sinks. So `dsl check` now answers the question that is
actually answerable — *can text a stranger wrote reach a sink that
sends mail, posts to chat, or calls a URL?* — which is reachability on
a graph it already computes.

All 46 shipped sources are classified trusted or untrusted, and all 26
sinks inert or acting, in `dissyslab/office/trust.py`, explicitly
rather than by name pattern. A test fails when a component is
registered without an entry, so adding one forces the decision.
An unknown name is **not** treated as untrusted: a check that fires on
everything it has not heard of is one people learn to skim.

Five shipped offices report it: `inbox_triage`, `job_hunter`,
`lead_qualifier`, `situation_room_requests`, `ticket_router`.

### Added — W12: what a role's own Python reaches for

W11 is complete only while an agent's body cannot act on its own. Once
roles are Python, an agent can open a socket without going near a sink,
and the graph check quietly becomes a check on one of two channels with
nothing announcing it.

W12 reads a role's imports and a handful of call names — network,
another process, code built at run time. It is **a lint, and it is
there to teach**: it cannot see what code does, cannot follow an alias,
and can be evaded by anyone trying. The hint says so, in the output
rather than only in a docstring.

The exposure is not this project's — any student running any
assistant-written Python has it. What is this project's is the claim
that an office's power is readable in four lines, and this is what
keeps that sentence honest. `import os` is deliberately not flagged
(fifteen shipped roles use it for paths); `os.system` is. Exactly one
shipped office reports it, and correctly: `periodic_brief`'s sink
shells out to `open` to show you the brief.

### Changed — one name per concept

*Org chart* is gone; it is a **network**. An org chart shows authority
and is a tree; an office shows dataflow and may contain cycles, so "the
org chart has a loop" was incoherent beside a README that said networks
need not be acyclic. *Inport* and *outport* are gone; they are
**inbox** and **outbox**, which is what the office metaphor already
called them.

Documents and skills only — no Python name changed. A vocabulary check
now fails the build if a retired word comes back.

### Changed — `Eve is summarizer.` and `Eve is a summarizer.` are the same line

The article used to be the only thing separating a role from a
sub-office, which is not a distinction anyone means to draw with one
character — and it produced three different outcomes for one dropped
`a`, chosen by which library the name happened to belong to.
**`office at` now marks a sub-office**, two words that say what they
mean. A line matching none of the three agent forms is a parse error
that names all three, instead of a silent reinterpretation.

### Changed — `dsl doctor` leads with a verdict

Its first line is now `Ready. You can build an office.` or `Not ready:`
and the one thing that is wrong, and the verdict is repeated at the
end. This is a fix for a real failure: doctor reported a missing skill
in the middle of its output, ended with "All required checks passed",
and an assistant reading it told the user everything was fine.

Its **Skills** section names each skill, its version, and the folder it
was found in. If the usual folders do not have it, doctor searches your
home folder before concluding anything. It **never says "not
installed"** — it knows where it looked, not what exists. Cowork stores
skills two UUID levels down inside Application Support, which is how a
skill that was demonstrably in use got reported as absent.

The **verdict line** said "the office-builder skill is not installed"
whatever the reason, which is the exact wording the section below it
had been rewritten to stop using — the rule was applied to the long
output and not to the sentence a reader sees first. Two situations now
get two sentences: *"office-builder is only in the repository, not
installed"* when doctor read a clone and found it there, and *"I could
not find the office-builder skill"* when it found nothing, with the
list of everywhere it looked. The second is weaker on purpose. A test
pins both, including that the not-found verdict does not contain the
words "not installed".

### Changed — `dsl --version` names the code it is actually running

An editable install records its version once, at install time, so
`dsl --version` said 1.6.1 while running code nine commits later. It
now appends the source folder and the commit — read from `.git`
directly, without running `git`.

### Fixed — a timed-out office stops instead of hanging

`run(timeout=T)` raised `TimeoutError` and told nobody: shutdown was
sent only when termination was *declared*, and a timeout is exactly the
case where it was not. Agent threads are non-daemon, so they stayed
parked in `recv` and the process could not exit — the timeout was
printed and then the program hung. A student meets that in the first
hour and concludes Ctrl-C is broken.

Every agent is now stopped before the raise, on both channels agents
listen on. And a third thing the written-down diagnosis did not have,
found only by running it: `os_agent`'s own loop returns only on
termination, so the manager outlived every agent it managed. It now
waits on a stop event.

### Changed — termination detection proves idleness instead of inferring it

The old predicate asked "did every agent answer this round, and are all
channels empty?" That worked only because every agent was reactive — a
reactive agent can answer a poll from inside `recv`, at a point where
it owes nothing, so answering *is* the proof. That is an accident of
the agent's shape, not a property of the protocol.

Agents now report an explicit `idle` bit, and the manager believes an
agent is idle only if it said so this round. The default is `False`,
which is the conservative direction: a false idle discards real work,
a false active only delays termination.

`Alarm` is the first non-reactive agent that is not a Source. It takes
a `wake_me_in` request and its worker's only action is to put a message
on the alarm's own inbox, so every message event stays on the agent's
thread.

### Added — a strategy shows its working, bar by bar

`explain_strategy` writes an Excel workbook in which every intermediate
column is a live formula. Click a shaded cell and the formula bar reads
`=MAX(C2:C21)` — the channel is built from the twenty rows *above* this
one, not including this one. That boundary convention is ambiguous in
English, invisible in a chart, and decides whether a backtest was
honest. Turtle and RS now show their working too, and `--peers` sets
the RS comparison basket.

Two honesty fixes in the same area, both found by recalculating the
sheets by hand: the signal column is a value rather than a formula (for
two of the four strategies the position depends on the whole path, and
no cell formula can compute it), and four documents that promised a
signal column you could watch move now say what actually happens.
Synthetic prices print a warning to **stdout**, not only into the file.

### Added — the look-ahead check runs itself

The no-lookahead, determinism and finiteness checks were a script
somebody had to remember to run. A signal computer now verifies its
strategy on the first real message it sees and raises
`StrategyContractError` if it fails, with the offending bar and both
values named. Sampled after that, so the cost is bounded. `checks="off"`
is available and is an explicit choice.

The checker lives in one place and the copy bundled with the skill is
pinned to it byte-for-byte by a test — the previous arrangement had a
correct checker in one app and a weaker copy in another.

### Changed — skills live in `skills/` and say what they build

`backtest-strategy-builder` moved out of the gallery to where the
install instruction can find it. Each skill's front matter now names
the kind of office it builds, and `office-builder` carries an index of
the domain skills, so an assistant meeting an unfamiliar request has
somewhere to look. Two rules the skill installer never documented —
no angle-bracket tokens in a description, and at most 1024 characters —
are now checked by a test, having each cost a failed save.

`office-builder` itself was rewritten around transcribing what the user
said. Asked for *"an office with Dan and Jay"* it writes two agents with
unassigned roles and invites the next sentence, rather than offering a
menu of jobs the user did not ask about.


## [1.7.2] — 2026-08-18

### Changed — market data comes from Yahoo via yfinance, and you fetch your own

Stooq is gone. Its quote endpoint was removed (404 for every ticker
spelling) and its historical endpoint now answers with a JavaScript
proof-of-work browser challenge, so every Stooq-backed source was dead —
not only quotes, as issue C1 had recorded. `stocks` now reads Yahoo
Finance through `yfinance`.

**The licensing constraint is now the design, stated everywhere it is
read.** Yahoo's terms do not permit redistributing their market data, so
this project ships none: no prices, no cached quotes, no sample market
CSVs. Every user fetches their own. `mac_speed_suite` already worked this
way with `download_stock_history_from_yf.py`; that is now the only way,
and the reason is written down rather than implied.

- **`yfinance` is an optional extra, not a core dependency** —
  `pip install "dissyslab[market]"`. Two reasons, the second
  load-bearing: it pulls pandas, and the offices a first-year runs first
  need no market data at all; and a tool whose whole point is that the
  user fetches their own data should be installed deliberately rather
  than arriving by accident.
- **The import is deferred to the first fetch.** `SOURCE_REGISTRY`
  imports the module to resolve the name `stocks`, so a top-level
  `import yfinance` would break `dsl check` for every office in the
  gallery, market or not, on any machine without the extra. A student who
  wires up `stocks` without it gets the `pip install` line, not an
  ImportError at module load.
- **Message shape is unchanged**, so no sink or downstream agent had to
  move. Two deliberate differences: `previous_close` is new, and
  `change` / `change_pct` are measured against the previous close rather
  than the session open — "up 2% today" means since yesterday's close
  everywhere else a student will meet it.
- Tickers are written as Yahoo writes them (`AAPL`, `BP.L`, `7203.T`). A
  trailing `.us`, the Stooq convention that appeared in this repository's
  own examples for months, is stripped rather than rejected.

### Removed — `stock_history` and `synthetic_stock_history`

The first read Stooq's historical endpoint; the second existed only as a
stand-in while the first was broken. Neither was used by any office.
`csv_stock_history` is now the only history source, and reading from disk
is the design rather than a fallback — a backtest that re-downloads on
every run is slow, non-reproducible, and hostage to a vendor's uptime.

An `office.md` naming either one now fails `dsl check` with W5 and a
spelling suggestion, which is the fix.

### Changed — `periodic_brief` drops its stock tickers

Three of its six sources were the dead Stooq ones, so half the office
produced nothing. Rather than move them to yfinance, they are gone:
`periodic_brief` is the office that has to run with **nothing** installed
beyond `dissyslab`, no key and no account, because its job is being the
thirty seconds that show the framework works before anyone believes
anything else about it. It is news + weather, and it runs clean.

The README shows the one-line edit to add `stocks` back once yfinance is
installed — which is a better lesson than shipping it wired.

Synthetic prices were considered and rejected. `periodic_brief` renders
real headlines and a real forecast; fabricated numbers in the next column
of the same page, with nothing saying which is which, is the exact defect
the rest of this changelog is about, pointed at the student.

### Changed — the empty-run guard quotes the component instead of guessing

The message added by the error counting below told a student whose problem
was an uninstalled package that "an endpoint that has moved is the usual
cause" — confidently wrong, which is worse than silent. `Agent` now keeps
the first error report's own text, and the guard prints it. A missing
`yfinance` now ends the run with the `pip install` command in the failure
message.


Also in 1.7.2, from the 2026-08-17 student walk-through issue list
(`archive/ISSUES_walkthrough_2026-08-17.md`):

### Added — the run summary can see failure reported as data (C2, C3)

A source that catches a bad fetch and emits
`{"type": "<name>_error", ...}` keeps the office alive through a
transient failure, which is right. It also defeated every guard we had.
`sent` was non-zero, so the empty-source check passed. Sinks route on
`type` and ignore what they don't recognise, so nothing printed. Three
consecutive HTTP 404s from the stocks source produced a clean, silent,
entirely empty morning brief that reported success.

- `Agent.errors` counts messages matching that convention, per outport.
- `Network.run_report()` gains `all_error_sources` and
  `some_error_sources`. The split matters: a source whose output was
  *entirely* error reports is indistinguishable from a dead feed and is
  now as loud as one — `OfficeRunError`, naming the source and the
  count. A source with *some* errors is reported and does not raise,
  because one flaky feed must not abort an office whose other output is
  fine.
- `allow_empty` covers the all-errors case too. It already means
  "producing nothing useful is legitimate here"; nobody should have to
  opt out twice.
- The predicate is deliberately narrow — a string `type` ending in
  `_error`, nothing else. An office summarising bug tickets does not
  read as broken.

### Added — mechanical checks that the prose matches the code (F)

`tests/integration/test_docs_match_code.py`. Six of the eleven
walk-through issues were one failure: a document asserted something the
system does not do, and nothing detected the divergence. Three of the
six are decidable by machine, and now are — every component the
catalogue promises exists in the registry; every registry entry is
findable in the catalogue; every `dsl` subcommand named in a skill or
course doc exists in `cli.py`; every office in START_HERE's catalogue
ships. The first run found two real divergences (below).

A doc may describe something unbuilt, as long as it says so: a heading
carrying "not yet registered" is exempt, and the marker must be in the
heading rather than buried in the body.

### Fixed — the skill version is now derived, not typed

The version marker added earlier the same day did not work, and failed
in the way it existed to prevent. The skill was edited three times on
2026-08-17 and the string stayed `2026-08-17b` throughout, so a marker
whose entire purpose was answering *"did the update take?"* could not
distinguish the three versions — and the test suite stayed green,
because the test asserted a string was **present**, which it was.

An assertion that cannot fail usefully is the same defect §F is about,
wearing a test's clothes.

So the version is now `YYYY-MM-DD.<7-hex>`, where the hash is computed
over the skill's own bytes with the version line excluded (otherwise it
would never converge). `scripts/stamp_skills.py` writes it;
`--check` reports staleness without rewriting.
`test_skill_version_matches_its_content` recomputes and fails by name
if a skill was edited without re-stamping — verified by appending a
blank line to a reference and watching it fire.

The date half stays hand-written, for humans reading a changelog. The
hash half is what proves an install took.

### Fixed — the three gaps E5 reported but did not close

- **Sink arguments are now in the skill**, as a signature table, because
  a wheel install cannot reach `docs/SOURCES_AND_SINKS.md` and the skill
  is what the agent has. Trial B needed `markdown_digest`, found only
  its name, and guessed `path=`. It guessed right and would still have
  shipped a competitor report headed *"Morning digest — 2026-08-17"*,
  because `title` defaults to that and nothing said so.
- **`markdown_digest` and `report_html` are documented** in
  `SOURCES_AND_SINKS.md` and off the `UNDOCUMENTED_BY_DESIGN` allowlist.
  Putting them there as "app-local" was a mistake made the same morning:
  a sink belonging to an app students are told to copy is not app-local,
  and the allowlist hid exactly the gap the trial then walked into.
- **`deduplicator` now says what it does not catch.** A user asking to
  "drop duplicate stories" means something `by="url"` cannot do — the
  same event from two publishers has two URLs, so both pass. All three
  `by=` options are described by real behaviour, with the honest
  conclusion that no option deduplicates by *story*; that needs a role.
  Also recorded: a non-dict message or a missing field passes through
  silently, so a typo in `by=` makes the agent a no-op that still checks
  clean, and `deduplicator` has no reject port, so the "wire rejects
  somewhere readable" rule cannot be applied to it — the message counts
  either side are the only evidence it worked.
- **The custom-sink examples are findable.** They do ship, at
  `<site-packages>/dissyslab/gallery/apps/...`, but the skill printed
  bare relative paths, so an agent running `cat gallery/apps/...` from
  the student's folder concluded they did not exist. Replaced with a
  snippet that resolves the package location, verified against the PyPI
  wheel. `docs/SOURCES_AND_SINKS.md` genuinely does not ship, and the
  skill now says so and links it instead of sending students hunting.

### Added — `dsl check` W5: no such source or sink (E5)

Found by running E5, the acceptance test that had never been run. It is
the worst gap the checker had:

```
Sources: bbc_wolrd
```

`dsl check` reported *no problems*, exit 0. `dsl build` then wrote
`run.py` without complaint. `dsl run` died with
`NameError: name 'bbc_wolrd' is not defined`, pointing at line 52 of
generated code the student never wrote. Check clean, build clean,
traceback — the exact sequence the checker exists to prevent, and the
one a first-year is least equipped to read.

W6 covered *role* names only, and the skill's promise that the check
catches unknown names read as though it covered these too. W5 now
resolves every name in `Sources:` and `Sinks:` against the registries
and suggests the nearest spelling (`bbc_wolrd` → "Did you mean
'bbc_world'?"). Skipped entirely if the registries cannot be read —
same rule as W6, since a false "no such source" on a working office is
worse than the gap.

It found a real one on its first run: `salton_sea_dashboard` names two
unregistered sources, so the gallery is 29/30 rather than 30/30 clean.
That is correct — the office genuinely does not compile, which is why
it is already an xfail. Two independent instruments now agree about it.

### Fixed — three things the E5 trials tripped over

- **`allow_empty=true` is a parse error.** Arguments are Python
  literals, so it must be `allow_empty=True`. The lowercase form was in
  the skill reference *and* in two `OfficeRunError` messages added
  earlier today — advice that fails if followed.
- **The role count contradicted itself** in adjacent lines: a heading
  saying "the thirteen you have" above a sentence saying "Nineteen names
  resolve". Nineteen is right — thirteen semantic plus six structural.
  Both trials wasted effort counting tables to find out.
- **B3: "empty output is now an error" gave false comfort.** True, and
  silent about the case C3 just fixed. The reference now states both.

### Added — skills can say which version they are

Both `SKILL.md` files now carry `**Skill version: \`2026-08-17b\`.**`
near the top, with an instruction to answer with it when asked. A skill
update can report success while the previous version stays resident;
without a marker in the text there was no way to tell from the outside,
and the wrong version once ran for a whole test round. Bump the string
whenever a skill changes.

Two tests enforce the pair: every `.skill` bundle must match the
directory it was built from, byte for byte, and every skill must declare
a version. Editing a reference and forgetting to repackage produced a
bundle that existed nowhere in git, with no error, because both files
were individually fine — the same two-artifacts-nobody-compares shape as
§F above. The first run of the bundle test caught exactly that, on the
version strings added in this entry.

### Added — tests for `dsl check` (E1 regression)

`tests/unit/test_check_wiring.py`. The checker shipped in 1.7.0 with no
unit tests; its acceptance was four deliberate breaks run by hand. Good
acceptance, no regression value. Now pinned.

### Changed — W4 reports the cascade frontier, not every casualty (E1)

Cutting one wire into the sinks of `situation_room` reported seven dead
ends, one per upstream agent. Correct, and for a first-year worse than
useless: seven findings for one missing wire reads as seven problems and
none of them says where to look. Every successor of a dead agent is
itself dead, so the frontier is exactly the dead agents with no dead
successor — that is where the path to a sink actually stops. The rest
are counted and named in the hint rather than listed as faults. A dead
cycle has no frontier, and is reported whole.

### Fixed — documentation that contradicted the code

- **B1: the output-path direction was reversed.** `SOURCES_AND_SINKS.md`
  said a bare filename resolves against the directory you ran `dsl run`
  from. It resolves against the *office folder* — `build/run.py` does
  `os.chdir()` there before starting. The doc's remedy ("pass an
  absolute path for predictability") described the one form that
  escapes the office folder. Both the `jsonl_recorder` `path` entry and
  the `csv_stock_history` `directory` entry are corrected, and the
  consequence C4 named — running a *shipped* office in place writes
  into `site-packages` — is now stated where it will be read.
- **B2: `rss` was undocumented.** The generic `rss(url=...)` existed,
  worked, and appeared only in a Python docstring, while the catalogue
  said "adding a new one is close to a one-line change" — which reads to
  a student as *the framework needs changing*. `rss` now leads the
  sources section, and that line is gone.
- **`salton_wind` and `synthetic_salton_h2s` were documented but never
  registered.** The implementations exist; the registry entries do not,
  which is why `salton_sea_dashboard` is an xfail. Both headings now say
  so and give the direct-wrapping workaround.
- **Eighteen registered sources appeared nowhere in the catalogue** —
  the five arXiv feeds, `starter` / `session_starter`, the four audio
  and image sensor sources, `file_source`, `kalshi`, `weatherapi`,
  `remoteok`, `we_work_remotely`. All documented. A component a student
  cannot find is worse than one that does not exist: the catalogue's
  silence reads as "not possible" rather than "look elsewhere".

### Fixed — the skill taught `discard` without its cost (D3)

`discard` is a real sink and wiring rejects to it is a decision rather
than a fault — that much the reference said. It did not say that
`discard` destroys the only evidence of a filter dropping the wrong
thing, which is exactly the tier-3 failure the walk-through hit: a
`\bneural operator\b` regex silently dropped every paper titled "Neural
Operators". The reference now teaches routing rejects to a readable file
while developing, and states the general rule — you cannot automate a
check for "the answer is wrong", so build offices whose wrong answers
are visible.


## [1.7.1] — 2026-08-17

### Fixed — the wheel no longer ships generated output

1.7.0 was built from a working tree that had run the gallery, and shipped
71 files that do not belong in a release. `dsl init` copied them into
every student's folder:

- **`paper_trader/book/book.json`** — a live paper-trading ledger (cash,
  five open positions, a realized P&L of −$51.7M). Every `dsl init
  paper_trader` started from someone else's book instead of a fresh one.
- **`recovery_demo/snapshots/checkpoints/000000`–`000005`** — six
  checkpoints from 2026-06-15. `dsl run recovery_demo --resume latest`
  would silently resume one of them rather than reporting that no
  snapshot exists, which inverts the lesson the office exists to teach:
  you take a checkpoint, then you resume from *it*.
- **64 `build/run.py` and `build/__init__.py` files** — stale codegen.
  `dsl run` regenerates these, so the practical risk was low, but
  `cli.py` already carries a dedicated error for "stale build/run.py".

Root cause, in two parts. `[tool.setuptools.package-data]` globs read the
working tree and have never consulted git, so `.gitignore` did nothing to
stop them; fixed with `[tool.setuptools.exclude-package-data]`. And
`dsl build` writes a `build/__init__.py`, which made the codegen output
look like a real sub-package to `packages.find` — so it shipped as
*source*, where `exclude-package-data` has no effect; fixed by excluding
`dissyslab.gallery.apps.*.build` in `packages.find`.

No source file changed between 1.7.0 and 1.7.1. If you have 1.7.0
installed and have not run `dsl init paper_trader` or `dsl init
recovery_demo`, upgrading changes nothing you can observe.

### Fixed — the test that should have caught it

`tests/integration/test_wheel_contents.py` had a forbidden-paths test,
and it passed, because `_copy_source_tree` skipped every directory named
`build` at any depth on its way into the test. The test was sanitising
the exact input it existed to inspect. It now skips `build/` and `dist/`
only at the source root, and a new `dirty_tree_wheel` fixture plants
generated output before building — so the guard runs against the
condition that caused the leak rather than against a clean checkout,
where it passed vacuously. A companion test checks the exclusions do not
overshoot into `office.md` and the files we do ship.


## [1.7.0] — 2026-08-17

*(This section was previously headed "Unreleased — will become 1.6.0",
which was never accurate: 1.6.1 shipped on 2026-06-23 while this content
was still unreleased. It is 1.7.0.)*

### Added — office checking, skills, and course material

- **`dsl check <office_dir>`** — structural checks over an office's whole
  org chart, without running it. Reports every fault at once: a declared
  inport nothing writes to (W1), unreachable agents (W3), dead ends (W4),
  missing role files (W6), feedback loops and whether they are gated (W7),
  unfed sinks and destination-less sources (W8), and names in connections
  that are not declared anywhere (W9). Exit 0 clean, 1 on faults, 2 on a
  bad path. Implemented in `dissyslab/office/check_wiring.py`; the analysis
  is importable as `check_office_dir()` / `format_report()`.
  Explicitly *structural*: it cannot see deadlock, since whether a buffered
  message is ever readable depends on execution history rather than on the
  graph.
- **`skills/office-builder/`** — an Agent Skill (the `SKILL.md` open format)
  that teaches an AI agent to build offices: the `office.md` grammar, the
  thirteen shipped roles, sources and sinks, worked examples, the Python
  role contract, and the build loop. Ships as `skills/office-builder.skill`.
- **`skills/sensor-office-builder/`** — the same for offices that classify
  audio, images, or sensor signals.
- **`course/`** — `START_HERE.md` (what the course builds, how to set up by
  talking to Cowork, and the full catalogue of shipped examples) and
  `SETUP.md`.

### Known limitations in this release

- **`mac_speed_suite` and `paper_trader` ship but do not run from a wheel
  install.** Both read `directory='../../../../sp100_data'`, which resolves
  to the repository root — outside the installed package. The CSVs are also
  `.csv`, which no `package-data` glob matches. Clone the repository to run
  either. Deferred rather than fixed: outside testers currently hold links
  to those two offices at their present paths.
- **The `stocks` source is dead upstream.** Stooq's free CSV quote endpoint
  now returns HTTP 404, so `periodic_brief`'s Markets section is empty and
  `stocks_monitor` reports errors. The source catches the failure and emits
  a `stocks_error` message, which nothing consumes and no sink renders — so
  the office exits 0 and says nothing. Both the endpoint and the
  unconsumed-error path are open issues; see
  `archive/ISSUES_walkthrough_2026-08-17.md`.

### Fixed — gallery offices that produced nothing

- `stocks_monitor`, `weather_monitor` and `kalshi_market_watch` each declared
  a `jsonl_recorder` that no connection ever wrote to, so the `.jsonl` file
  each names stayed empty. The analyst's briefing now goes to both the
  console and the recorder. Found by `dsl check` on its first run across all
  31 shipped offices.
- `wardrobe_assistant` declared a `discard` sink with nothing routed to it —
  no filter, no gate, no reject port in any of its agents. Declaration
  removed rather than wired.

### Changed

- **An office that produces nothing now fails instead of reporting
  success.** A source signals exhaustion by returning `None`, and
  error paths returned `None` too, so a source pointed at a file that
  did not exist was indistinguishable from one read to completion: the
  office terminated correctly, printed nothing, and exited 0. For
  anything numeric this is worse than a crash — all-zero output looks
  like a result. `run_network()` now raises `OfficeRunError` when a
  source crashed or emitted no messages at all. Mark a source
  `allow_empty=true` in `office.md` where producing nothing is a
  legitimate outcome (a feed with nothing new), or pass
  `require_source_output=False` to disable the check for a run.
  Reported by an outside tester on `recovery_demo`.
- `dsl run` prints a per-agent message-count summary when the run
  finishes, so "everything produced nothing" is visible at a glance.
  Suppress with `dsl run --quiet`.
- `Source` records a failure rather than swallowing it. `run()` still
  sends its termination message on error — `os_agent` would otherwise
  wait forever — but the failure is now visible to `run_network()`.

### Fixed

- `recovery_demo` ran on a fresh clone printing nothing and exiting 0:
  `samples/points.txt` was gitignored, so every clone got a broken
  demo of the framework's headline feature. The file is deterministic
  (seed=42) and is now committed.
- `CSVPointsSource` raised nothing on a missing file; it now raises
  `FileNotFoundError` naming the path and the fix.

### Added

- **Distributed snapshot checkpoint-recovery** for offices —
  implementation of the Chandy-Lamport (1985) distributed snapshot
  algorithm, adapted for DSL's office-shaped systems. Algorithm
  authored by K. Mani Chandy with implementation help from Claude.
  Specification in
  [docs/algorithms/CHECKPOINT_RESUME.md](docs/algorithms/CHECKPOINT_RESUME.md).
- New `dsl run` flags:
  - `--snapshot-interval <seconds>` — initiate a distributed
    snapshot every N seconds while running. Snapshots persist
    under `<office_dir>/snapshots/checkpoints/<N>/`.
  - `--resume <N|latest>` — restart from a saved snapshot. Each
    agent reloads its checkpoint state; each channel's in-flight
    messages are replayed into its inport queue; the office
    continues from the consistent cut.
- New gallery office: **`recovery_demo`** — a Monte Carlo π
  estimator that demonstrates the protocol end-to-end. Three
  stateful agents (Alex, Bob, Pi) with auto-inserted Broadcast
  and MergeAsynch. Each stateful agent overrides `save_state` /
  `load_state` in five lines.
- New framework primitives:
  - `dissyslab/snapshot.py` — on-disk persistence layer
    (manifest.json + per-agent pickles + per-channel pickles).
  - `dissyslab/components/sources/csv_points_source.py` — a
    checkpoint-aware CSV source.
  - `Agent.save_state()` / `Agent.load_state()` — overridable
    hooks on the base class (defaults are no-ops, so existing
    agents work unchanged).
  - `Agent._poll_os()` — source-side polling for OS messages.
  - `Agent._snapshot_state` (enum: NORMAL, RECORDING,
    RECOVER_WAITING) — explicit state machine for the snapshot
    protocol.
  - 5 new `_OsMessage` subclasses (`_Checkpoint`, `_Reply`,
    `_PrepareRecover`, `_RecoverReady`, `_StartRecover`).

### Changed

- `Source.run()` polls for OS messages between iterations and
  blocks during `RECOVER_WAITING`. Backward compatible: when no
  snapshot is configured, `_poll_os` is a no-op.
- Generated `build/run.py` artifacts read three new environment
  variables (`DSL_SNAPSHOT_INTERVAL`, `DSL_RESUME`,
  `DSL_SNAPSHOT_DIR`) set by `dsl run` and configure the
  network's snapshot attributes before calling `run_network()`.
- `MergeAsynch.__init__` upgrades its inherited `_NO_LOCK`
  singleton to a real `threading.Lock` — the only multi-threaded
  agent in the framework needs real synchronisation on shared
  snapshot state.

### Documentation

- New `docs/algorithms/` directory; first occupant is the
  checkpoint-resume algorithm specification.
- README gains a *Current limitations* subsection naming what
  the framework does **not** do (multi-machine, scheduling,
  opt-in checkpointing, LLM non-determinism, no first-party
  web UI).
- README gallery table lists `recovery_demo` as the v1.6 demo
  office.

### Verified

- 417 unit tests pass (was 406; +9 new checkpoint tests + 2
  additions from the parameterised gallery-compiles test
  picking up `recovery_demo`).
- All 20 gallery offices build cleanly via `dsl build`.
- `dsl run periodic_brief` produces identical output to v1.5
  (backward compatibility).
- End-to-end `recovery_demo` with periodic snapshots: all four
  agents (plus auto-inserted Broadcast and MergeAsynch) appear
  in each snapshot's manifest; agent state correctly persisted.

### Out of scope for 1.6 (named honestly in `dev/POST_HN_BACKLOG.md`)

- Multi-machine snapshots
- Multi-process snapshots (`dsl run --processes`)
- Snapshot timeout / queue-failure detection
- Encrypted snapshots
- Schema evolution across snapshots

## [1.6.1] — 2026-06-23

### Fixed

- `gallery/apps/debate/roles/gate.py`: when the problem bank is
  exhausted, the gate role now `continue`s in its `recv()` loop
  instead of returning. Returning voluntarily killed the agent's
  thread before `os_agent` could finish polling it; termination
  detection stayed blocked indefinitely. Also dropped the now-
  unnecessary `{"end_of_stream": True}` sentinel emission, which
  was being mis-processed as a real problem by downstream
  panellists. Net effect: the gallery debate office terminates
  cleanly when its bank is exhausted.
  
## [1.4.0] — pre-1.6 baseline

Tagged at commit `547827d`. Pre-checkpoint-recovery snapshot of
the framework — sense-and-respond positioning, gallery of audio
+ image + text apps, English office grammar with mix-and-match
per-agent LLM backends, library of specialist agents
(`confidence_filter`, English roles), `dsl new`, the office
microcourse. See git history between `547827d` and the v1.6
commit for the full set of changes since the last tagged
release.

A formal changelog for 1.5.x was never published as a release;
the work that would have been 1.5 — alpha contract refactor,
debate office, audio + image gallery apps, Nyasha's React
deployment pattern, specialist-agents README rewrite — is
folded into the 1.6 release notes above.
