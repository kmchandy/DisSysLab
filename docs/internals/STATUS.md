# Where the project is — 2026-10-17

One page. What is true now, what is open, and in what order. This is the
only status document kept current; the history is in git and in
[design/restructure_plan.md](design/restructure_plan.md).

If you are picking the project up cold, read this, then
[design/officespeak_revised.md](design/officespeak_revised.md) (the
language), then [reference/architecture.md](reference/architecture.md)
(how the pieces fit), then the module you are about to change.

## The measure of success

> A first-year builds an app they care about, then studies the
> algorithms underneath it.

**The course runs 4 January – 10 March 2027.** Its goal: students run
distributed systems of several language-model agents, learn to impose
guardrails, and learn ways agents can collaborate. Everything below is
ordered against that.

**People.** Mani Chandy (maintainer; merges). Jeffrey Zhou (TA; works on
branches and pull requests, see [CONTRIBUTING.md](../../CONTRIBUTING.md)).

## What is true now (2.0.0.dev0 on `main`)

- **The office language is 2.0**, as specified in
  `officespeak_revised.md`: `name: kind(args)` declarations and `a -> b`
  connections; annotator and author roles in English or Python; routers;
  the keyed synchronizer and the gate; nested offices; drafts. Version 1
  (the sentence form) is on the `v1` branch and the `v1.10.2` tag, and
  does not run on `main`.
- **One build path, in memory:** `office/syntax` → `resolve` → `build`.
  No generated `build/run.py`.
- **Guardrails** (all optional, Principle 6): every reply checked against
  the role's `out:` (undeclared fields dropped and counted, bad values
  failed and counted); `needs:` checked before a run; `dsl check` notes
  for untrusted text reaching an acting sink, Python reaching past the
  sinks, and router outboxes that no declared value can reach.
- **The runtime is frozen** (`dissyslab/runtime/`), with two approved
  exceptions: the dropped-fields note, and the **stall report** (a walk
  back from held work proving it can never be released).
- **Ctrl-C** stops a running office with its summary (fixed 17 Oct; it
  used to hang).
- **The gallery** (`dissyslab/gallery/`): ten offices, each with a README
  and an end-to-end test, from `inbox_sorter` to `mac_speed_suite`.
- **Docs:** `docs/GETTING_STARTED.md` (the student guide; its outputs are
  re-checked by `tests/integration/test_getting_started.py`), the
  `dsl grammar` reference (shipped in the package, also what `dsl new`
  gives the model), recipes, and the three skills, all in 2.0.
- **CI:** Linux 3.10–3.14, macOS, Windows (advisory), mypy on the strict
  modules. The suite is about 720 tests and runs in under a minute.

## Open, in order

1. **Finish 6c:** the microcourse and the course pages (`course/`) still
   teach version 1.
2. **Model reliability check** (spec §11), before release: every English
   role, old prompt form against new, on a small local model and a
   frontier model; tune the closing sentences; check every example in a
   role against its own `out:`. Needs a key and a small budget.
3. **Release 2.0.0** and **rehearse the install**: wheel into an empty
   virtualenv, then `docs/GETTING_STARTED.md` followed literally, parts 1
   to 8, on a clean machine, with a real key (part 6 has only been run
   against a scripted model).
4. **Thirty students installing at once** has never been tried. Windows
   is the sharp end. Do it before 4 January; what it finds needs a
   release.
5. **Lab 1 needs a real-model rehearsal.** Built: `course/lab1.html` (the
   one-dollar Tahoe), the `car_dealer` gallery office, `chat_page` /
   `chat_reply`, `grade.py`, and a reference guard in
   `tests/e2e/car_dealer_guarded/`; all tested against a scripted model.
   Not yet known: whether the starter is vulnerable *enough* to the
   default model (if Sal resists every attack in `attacks.jsonl`, Step 5
   teaches nothing), and how often the grader misjudges real replies.
6. **Cost guard on generated offices.** `dsl new` is told to prefer a
   file source and small `max_articles`; nothing enforces it. A student
   who leaves a generated office polling a hosted model over a weekend
   finds out.

## Not built yet (spec, deferred)

- `dsl try <role> <input>` and `dsl show <role> --prompt` (spec §10).
- The whole-network checks (an unreachable agent, a sink nothing feeds:
  W1–W4, W7, W8) and the field-flow checks (W21–W31).
- `checkpoint`/`restore` for stateful Python roles, `--trace`,
  `--resume` and `--snapshot-interval`: the runtime has them; the 2.0
  build does not wire them, and `dsl run` refuses the flags.
- **Backtesting testers:** the 2.0 `mac_speed_suite` has no
  `explain_strategy.py` (the per-day Excel workbook Vikram uses). Testers
  on 1.x keep it; porting it is open.
- Renaming "office" to "network of agents" (spec §15): last, in one pass.

## Two that may not be features

**Deadlock detection beyond stalls.** A structurally correct office can
still deadlock, because whether a message is ever readable can depend on
execution history rather than on the graph. The stall report proves a
stall when it happens; detecting one before it happens is a different
question, and the boundary is itself something the course teaches.

**Processes.** An office in one process is simpler to reason about while
students learn termination detection. Multi-process is the sequel.

## The standing rule

When a document and the code disagree, the fix is not only to correct
the document. It is to ask what would have caught it, and add that. Every
section of `tests/integration/test_docs_match_code.py`, and
`test_getting_started.py`, came from a divergence that shipped or nearly
did.
