# Changelog

All notable changes to DisSysLab are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/);
versions follow [SemVer](https://semver.org/).


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
