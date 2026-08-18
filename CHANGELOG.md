# Changelog

All notable changes to DisSysLab are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/);
versions follow [SemVer](https://semver.org/).


## [Unreleased]

Work from the 2026-08-17 student walk-through issue list
(`docs/internals/ISSUES_walkthrough_2026-08-17.md`).

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
  `docs/internals/ISSUES_walkthrough_2026-08-17.md`.

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
  [`docs/algorithms/CHECKPOINT_RESUME.md`](docs/algorithms/CHECKPOINT_RESUME.md).
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
