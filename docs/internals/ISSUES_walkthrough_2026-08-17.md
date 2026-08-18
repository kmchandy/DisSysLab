# Issues from the student walk-through — 2026-08-17

Found by playing a first-year against `course/START_HERE.md` with the
`office-builder` skill installed.

> **Status as of 2026-08-18.** The per-issue text below is the original
> diagnosis, kept as written; resolved items are struck through in place.
> This table is the summary — read it first.
>
> | Closed | How |
> |---|---|
> | A1, A2, A3, B5 | released — 1.7.0, then 1.7.1 for the packaging leak it introduced |
> | A4 | `26abd4a` — the skill's version guard |
> | B1, B2, B3, C4 | documentation corrected against the code |
> | C2, C3 | error-message counting in the run summary |
> | D3, D5, D6 | skill references |
> | E1 | W4 reports the cascade frontier |
> | E5 | run — see `E5_acceptance_2026-08-17.md`; produced W5 |
> | §F | `tests/integration/test_docs_match_code.py` |
>
> | Open | Why it is still open |
> |---|---|
> | **Release 1.7.2** | W5 and C3 are in the repo, not in the wheel a student installs. Highest priority: W5 is a prerequisite-for-course fix |
> | **C1 / B4** | needs a data-provider decision, not a patch — three options costed in the update section below |
> | **D1** | tier-2 hang diagnosis — plan item 2, days |
> | **D2 / D4** | tier-3 instrument in the foundation skill |
> | **E2** | W2 — needs resolved role shapes |
> | **E3** | `sensor-office-builder` has no `references/` |
> | **E4** | move the three `gallery/apps/*/skill*/` bundles — after 25 Aug |
> | **E6** | retire OfficeSpeak |
> | **E7** | `\b` will bite again on possessives and hyphenation |
> | **E5 leftovers** | closed 2026-08-18 (`c183e32`); nothing outstanding |

**One pattern runs through most of it:** a document asserts something about
the system that the system does not do, and nothing detects the divergence.
Four of the doc issues below are instances. The cheapest durable fix is at the
bottom (§F).

---

## A. Release gap — blocks everything student-facing

The docs and the skill describe the repo; a student installs the wheel.

| # | Issue | Evidence |
|---|---|---|
| A1 | ~~**`dsl check` does not exist in PyPI 1.6.1**~~ **DONE — 1.7.0.** — and the skill mandates it before every run | `dsl: error: invalid choice: 'check' (choose from list, init, show, new, edit, run, build, doctor)` |
| A2 | ~~**10 of 30 apps are not in the wheel**~~ **DONE — 1.7.0 ships all 30.** — `adaptive_tutor`, `investment_club`, `mac_speed_suite`, `paper_trader`, `returns_desk`, `room_climate_monitor`, `salton_sea_dashboard`, `shipment_release`, `situation_room_requests`, `trading_room` | `dsl list` shows 20 apps; repo has 30 |
| A3 | ~~**The four unfed-sink fixes are not in the wheel**~~ **DONE — 1.7.0.** — a student's `stocks_monitor` still writes an empty `.jsonl` | committed `08bfe4c`, unreleased |
| A4 | ~~**The skill has no version guard.**~~ **DONE — 26abd4a.** Mandating a possibly-absent command led the agent to try patching `site-packages` | student session: *"the installed wheel lacks it, so let me fix that here"* |

**A4 is the one to fix even if you release today.** Thirty students each
patching their own install differently is unreproducible by design. The skill
should detect the absence, say so, and continue — never patch.

---

## B. Documentation contradicts the code

| # | Issue | Location |
|---|---|---|
| B1 | ~~**Output-path direction is reversed.**~~ **DONE.** Doc says a bare filename resolves against the invoking directory; `codegen.py` emits `os.chdir(_HERE.parent)` so it resolves against the *office* folder. The doc's remedy — "pass an absolute path for predictability" — now describes the one form that escapes it | `docs/SOURCES_AND_SINKS.md:591` vs `codegen.py:~618` |
| B2 | ~~**RSS is undersold, then mis-signposted.**~~ **DONE.** Section reads "RSS feeds (10 named)"; the generic `rss(url="...")` appears only in the code docstring. A later line — "Any additional RSS feed at all … adding a new one is close to a one-line change" — reads to a student as *the framework needs changing*, when they just need `rss(url=...)` in their own `office.md` | `docs/SOURCES_AND_SINKS.md:28`, `:790` |
| B3 | ~~**"Empty output is now an error" gives false comfort."**~~ **DONE** — the reference now states the error-message case too. True, and it does not fire when a source emits *error* messages — which is the common case | `skills/office-builder/references/sources_and_sinks.md` |
| B4 | **`START_HERE` promises stock prices** that do not appear (see C1) | `course/START_HERE.md` §2 |
| B5 | ~~**`START_HERE` catalogues 38 examples**~~ **DONE — 1.7.0, and now tested mechanically (§F).**; a wheel install can reach 28 | `course/START_HERE.md` §5 |

B4 and B5 are mine. I had the failing output in front of me and described it
as working.

---

## C. Silent-failure paths in the framework

| # | Issue |
|---|---|
| C1 | **The Stooq quote endpoint returns 404.** `https://stooq.com/q/l/?...` → `HTTP Error 404`. All three `stocks` sources are dead. Unauthenticated free feed; it will break again |
| C2 | ~~**`stocks_error` has no consumer.**~~ **DONE** — the run summary is now its consumer. `StocksSource` catches failures and yields `{"type": "stocks_error", ...}` — the string appears exactly once in the repository, at the line that emits it. The brief sink's own docstring: *"messages with no recognised source or type are silently ignored"*. The mechanism written to surface failure is what buries it |
| C3 | ~~**The health check counts messages, not health.**~~ **DONE.** `OfficeRunError` fires when a source sends zero. These sent three — three errors. The guard built for exactly this class of silent failure is defeated by a source that reports failure as data. Counting `*_error` messages separately would have made it visible in the first run |
| C4 | ~~**Running a shipped office writes into `site-packages`.**~~ **DONE** — stated in SOURCES_AND_SINKS.md and the skill, where it is read. Same `chdir` mechanism as B1: a shipped office's folder *is* the install. `dsl init` avoids it; nothing warns |

C2 and C3 are framework-level, not `periodic_brief`-level. Any source using
the `<type>_error` convention fails the same way.

---

## D. The tier taxonomy — the architectural finding

The walk-through produced a three-tier failure model that maps onto the skill
architecture and names the hole precisely:

| Tier | Structure | Run | Answer | Instrument | Status |
|---|---|---|---|---|---|
| 1 | ✗ | — | — | `dsl check` | **exists** |
| 2 | ✓ | ✗ | — | health / hang diagnosis | **missing** (plan item 2) |
| 3 | ✓ | ✓ | ✗ | domain check | exists per-domain; **missing** in the foundation skill |

- **D1 — Tier 2 has no instrument.** Clean check, clean exit, no output. The
  `my_brief` case.
- **D2 — Tier 3 has no instrument in `office-builder`.** Clean check, clean
  run, wrong answer. The `\bneural operator\b` regex that silently dropped
  "Neural Operators". Every *domain* skill ships a tier-3 check —
  `strategy_selfcheck.py`, `check_no_lookahead.py`,
  `check_problem_ground_truth.py`. The foundation skill ships none, and the
  agent improvised one. Improvised tests will vary per student.
- **D3 — DONE.** ~~The design rule that makes tier 3 visible is undocumented.~~
  `examples/org_news_filter` already does it: `Felix's discard is
  jsonl_recorder.` — rejects go to a *readable* file, not to `discard`. Run
  the buggy filter that way and the dropped headline is sitting in the
  rejects file. Nothing states this. My own reference says "`discard` is a
  decision, not an unwired port" and misses that `discard` still hides the
  data
- **D5 — DONE (fc42b08).** ~~The skill has no catalogue of the shipped roles.~~ `dissyslab/roles/`
  holds 13 ready-made roles — `relevance_filter`, `topic_tagger`,
  `category_classifier`, `sentiment_classifier`, `urgency_classifier`,
  `evaluator`, `summarizer`, `summary_writer`, `entity_extractor`,
  `geolocator`, `severity_classifier`, `writer`, and the Python
  `confidence_filter`. The references cover sources, sinks, grammar and
  worked examples — never roles. So the agent wrote a custom regex filter
  while `relevance_filter.md` sat unused, which already does the job in
  English, has no plural bug, and already sends to `keep` / `discard` (the
  D3 pattern). **This one caused the D2 episode.** Cheapest fix in the whole
  list relative to what it prevents
- **D6 — DONE (10aa9d3).** ~~The English-vs-Python rule needs one refinement.~~ The skill says
  "prefer Python whenever the job can be stated exactly." *Exactness is a
  property of the criterion, not of the implementation.* "About computer
  science" feels exactly statable as a keyword list and is not — a keyword
  list is an exact implementation of a fuzzy criterion, and that mismatch is
  where this class of bug lives. Ordering to teach: fuzzy criterion → shipped
  English role, edited; exact criterion → Python, plain string operations
  before regex; genuinely need robust term matching at volume → then a
  library, and say what it costs
- **D4 — Tier 3 cannot be automated in general.** No checker knows you meant
  plurals. The achievable goal is legibility, not detection

---

## E. Carried over, not from the walk-through

- ~~**E1** W4 reports a cascade~~ **DONE** — frontier only, casualties counted
- **E2** W2 (outport nothing reads) not implemented; needs resolved role shapes
- **E3** `sensor-office-builder` has no `references/`
- **E4** Three skills still under `gallery/apps/*/skill*/` — move after 25 Aug
- ~~**E5** The acceptance test never ran~~ **DONE** — see `E5_acceptance_2026-08-17.md`. The test as written could not work (`situation_room` is a worked example inside the skill); two sandboxed trials were run instead, and produced W5. Original text: hand the skill a description of
  `situation_room`, diff against the real one
- **E6** OfficeSpeak not yet retired — `guides/` (six walkthroughs incl. the
  tester manual), `course/COURSE_MEDIA_STRATEGY.md`, `paper/` still only there
- **E7** `s?` patches one regex; `\b` will bite again on possessives and
  hyphenation

---

## F. The meta-fix

Six issues above are the same failure: prose asserting something the code does
not do. Three would be caught mechanically by a cheap test —

- every source and sink named in `SOURCES_AND_SINKS.md` exists in the registry,
  **and every registry entry appears in the doc** (catches B2)
- every `dsl` subcommand named in the skills and course docs exists in
  `cli.py` (catches A1 before a student does)
- every office named in `START_HERE`'s catalogue is present in the built wheel
  (catches A2, B5)

`dsl check` does this for offices. Nothing does it for prose, and this session
is the argument that something should.

---

## Update — 2026-08-17, later the same day

Done: **B1, B2, C2, C3, D3, E1, F**, plus the release (A1/A2/A3/B5 via
1.7.0, then 1.7.1 to fix the packaging leak that release introduced —
see `CHANGELOG.md`).

**F landed and immediately earned its keep.** The first run of
`tests/integration/test_docs_match_code.py` found two divergences the
walk-through had not: `salton_wind` and `synthetic_salton_h2s` are
documented sources with no registry entry, and *eighteen* registered
sources appeared nowhere in the catalogue — including `rss` itself,
which is B2. Six issues in this file are the "prose asserts what the
code does not do" pattern; the test found two more of the same in
under a second, which is the argument §F was making.

### C1 is worse than recorded, and needs a decision

The issue says the Stooq **quote** endpoint returns 404. Re-checked
2026-08-17: still 404, and it is not a ticker-format problem — `aapl`,
`aapl.us` and `AAPL.US` all 404. The whole `/q/l/` path is gone.

The **history** endpoint `/q/d/l/` is no longer usable
programmatically either: it now serves a JavaScript proof-of-work
browser challenge instead of CSV. That is presumably the same symptom
`synthetic_stock_history` was added for on 2026-07-28.

So every Stooq-backed source is dead, not only quotes. Replacing the
provider is a durable choice for a course rather than a bug fix, so it
is left open deliberately:

- **Yahoo's chart endpoint** (`query1.finance.yahoo.com/v8/finance/chart/`)
  works today with no key — verified. It is undocumented and
  unofficial, which is the same class of fragility that has now broken
  twice in two months.
- **A keyed provider** (Alpha Vantage, Finnhub, Twelve Data) is stable
  and free at low volume, but adds a signup to the on-ramp — and the
  no-key property is most of why `periodic_brief` is the first thing a
  student runs.
- **Offline-first**, extending what `csv_stock_history` and
  `synthetic_stock_history` already do: ship the data, treat live
  quotes as opt-in. Nothing to break during a lecture. Costs the
  liveness that makes a market office feel real.

C3 makes the failure loud either way: a stocks source returning nothing
but `stocks_error` now raises instead of producing a silent empty
brief. That buys time to choose rather than forcing it.

---

## Suggested order

1. ~~**A4** — the skill's version guard~~ **— done, 26abd4a**
2. **D5** — a roles catalogue in the skill's references. Promoted: it is
   smaller than a release and prevents the failure that produced D2/D3
3. **Cut a release** — resolves A1, A2, A3, B5 at once and makes the docs true
4. **B1, B2** — two wrong sentences costing beginners real time
5. **C3** — count error messages in the health summary; makes C1/C2 visible
   rather than silent
6. **F** — the doc-vs-registry test, so §B stops recurring
7. **D1/D2** — the missing instruments; these are plan items, not fixes
