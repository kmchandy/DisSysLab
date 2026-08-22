# Where the project is — 2026-08-20

One page. What is true now, what is open, and what to read first.
Everything dated and finished lives in [archive/](../../archive/);
this file is the only status document that is kept current.

If you are picking the project up cold, read this, then
[reference/architecture.md](reference/architecture.md), then the
overview half of whichever module you are about to change.

---

## The measure of success

> A first-year builds an app they care about, then studies the
> algorithms underneath it.

The course runs 4 January – 10 March 2027. Everything below is
prioritised against that sentence: a change that makes a first-year's
first hour work beats a change that makes the framework more general.

---

## Released

**1.7.1 is on PyPI.** It carries `dsl check`, all thirty gallery
apps, the four unfed-sink fixes, and the skill's version guard.

**1.7.2 is not released and needs to be.** The repository is ahead of
the wheel by, among other things:

- W5 — a source or sink name in no registry is now reported with a
  nearest-spelling suggestion. This is the prerequisite-for-course
  fix: a typo currently reads to a student as a missing feature.
- The yfinance change (below) — the stock sources in 1.7.1 are dead.
- Error-message counting in the run summary.

## Open, in the order I would do them

1. **A timed-out office cannot be shut down.** `run_network(timeout=T)`
   raises `TimeoutError`, but nothing tells the agents to stop —
   `os_agent` sends `_Shutdown` only when it *declares termination*,
   and the timeout path does not. Agent threads are `daemon=False`, so
   they stay parked in `recv` and **the process cannot exit**.
   Confirmed with `faulthandler`. Not specific to any agent; any office
   that times out does it, and it is why Ctrl-C on a hung office
   appears to do nothing. The fix is small — send `_Shutdown` to every
   agent on the timeout path before raising — but it changes
   `Network.run` for every caller. See the note at the foot of
   `tests/unit/test_alarm.py`.

2. **Release 1.7.2.**

3. **Offices as processes, steps 3–5** — `Channel` / `PipeChannel` and
   the boundary agents, the cut and flatten, the network-level
   detector. Design in
   [design/process_per_office_design.md](design/process_per_office_design.md)
   and
   [design/termination_detection_design.md](design/termination_detection_design.md)
   §5.4–§5.5. Start with `PipeChannel`; `SocketChannel` is the same
   interface when a second machine is wanted.

4. **D1 — the tier-2 hang.** Undiagnosed. Days, not hours.

5. **E2 — W2** needs resolved role shapes before it can say anything
   useful.

6. **E3 —** `sensor-office-builder` has no `references/` directory,
   where `office-builder` has four.

7. **D2 / D4 —** a tier-3 instrument in the foundation skill.

8. **E4 —** move the three `gallery/apps/*/skill_for_testers/`
   bundles out of the package. Deliberately held until after 25 Aug,
   because testers are using them where they are.

9. **E7 —** the `\b` in the vocabulary check will bite again on
   possessives and hyphenation.

10. **Renames that are pure debt.** `office/utils.py` →
    `office/registry.py` (16 import sites); `start_gallery/` →
    `chat/`; the `OfficeSpeakSpec` / `from_officespeak.py` internals,
    which are the last place the retired word survives.

## Recently closed, and worth knowing why

- **Stooq is gone.** Every endpoint the stock sources used returns
  404. yfinance is now the only path, as an optional `[market]`
  extra, and each user downloads their own data — nothing in this
  repository ships market data. Worth re-checking that
  `course/START_HERE.md` §2 does not promise a first-year stock
  prices they will not get without the extra (this was issue B4).

- **Termination detection has an explicit idleness bit.** The old
  predicate worked only because every agent was reactive. Alarms are
  the first agent that can answer a poll while owing a send. See
  [design/termination_detection_design.md](design/termination_detection_design.md).

- **The vocabulary pass.** "OfficeSpeak" named nothing a reader could
  point at, so it became the name for the whole system — which is how
  a tester's question about the runtime arrived as a question about
  the chat. There are now four nameable parts: the `office.md` you
  write, the Python roles, the `dsl` command, and the skill Claude
  reads.

- **The documentation is testable.**
  `tests/integration/test_docs_match_code.py` checks the source and
  sink catalogues against the registry in both directions, the
  documented `dsl` subcommands against the CLI, the `START_HERE`
  catalogue, the `.skill` bundles against their sources, the internals
  index against the modules on disk, and every relative link in every
  tracked markdown file. This exists because the same failure kept
  recurring: a document asserts something the system does not do, and
  nothing detects the divergence.

## The standing rule

When a document and the code disagree, the fix is not only to correct
the document. It is to ask what would have caught it, and add that.
Every section of `test_docs_match_code.py` came from a divergence that
shipped.
