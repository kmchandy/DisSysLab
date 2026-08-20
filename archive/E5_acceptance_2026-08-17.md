# E5 — the acceptance test, finally run (2026-08-17)

Issue E5 said: *hand the skill a description of `situation_room`, diff
against the real one.* It had never been run.

It was run today, and the first thing it produced was a problem with
itself.

## The test as written cannot work

`situation_room` **is worked example #2 inside the skill**, its full
`office.md` reproduced in both `references/worked_examples.md` and
`SKILL.md`. Handing an agent that description and diffing is not an
acceptance test; it is a copying exercise with the answer on the page. A
perfect diff would prove nothing.

Four offices are reproduced in the skill and are therefore unusable as
targets: `situation_room`, `periodic_brief`, `debate`, `recovery_demo`.

## What was run instead

Two trials, each in a sandbox containing only a copy of
`skills/office-builder/`, run by an agent instructed not to read the
repo or the installed package and not to run any `dsl` subcommand except
`check`.

**Trial A — `situation_room`** (the test as specified; kept as a floor).
Clean check on the first attempt, zero fix rounds. The result is
functionally identical to the real office — same sources, same six
agents, same synchronizer, same two sinks — differing only in the office
name and the order of two lines. As predicted: rename-and-go.

**Trial B — `competitor_watch`** (not mentioned anywhere in the skill;
same fan-out → enrich → synchronise → write shape, inferable from
prose). Also clean on the first attempt. Also structurally identical to
the real office, down to the arbitrary agent names — Sasha, Eve, Sam,
Tom, Sync, Riley — which come from the worked example.

**That last point is the real result, and it is a good one.** The
pattern transferred from a worked example to a problem the skill had
never seen, wired correctly, first try. Differences from the real
office were `max_articles=5` vs `10`, quote style, and the synchronizer's
inport names — cosmetic, self-consistent, unguessable from the
description.

The honest summary: **the skill's happy path works.** Both trials
produced a runnable office with no fix rounds. Everything below was
found because both agents, given nothing to fix, went looking for
trouble on their own — which is worth remembering about how to run this
test in future.

## What it found

Both agents independently reported the same top issue, and it is
serious.

### `dsl check` did not validate source or sink names

```
Sources: bbc_wolrd
Sinks: totally_fake_sink
```

`dsl check` → *no problems*, exit 0.
`dsl build` → wrote `run.py` without complaint.
`dsl run` → `NameError: name 'bbc_wolrd' is not defined`, in generated
code at `build/run.py:52`.

Check clean, build clean, traceback. That is the precise failure the
checker exists to prevent, delivered in the form a first-year is least
able to read, for the single most likely beginner mistake — a typo in a
feed name. W6 covered role names only; the skill's promise that the
check catches unknown names read as though it covered these too.

**Fixed:** W5. Every name in `Sources:` and `Sinks:` is resolved against
the registries, with a nearest-spelling suggestion. Its first run found
`salton_sea_dashboard`'s two unregistered sources, so the gallery is now
29/30 rather than 30/30 — correctly, since that office does not compile
and is already an xfail.

### Smaller, also fixed

- `allow_empty=true` is a **parse error**; arguments are Python
  literals. The skill said `true`, and so did two `OfficeRunError`
  messages written earlier the same day. Advice that fails if followed.
- The role count contradicted itself in adjacent lines — heading "check
  the thirteen you have" above "Nineteen names resolve". Both agents
  counted tables to resolve it.
- B3's "empty output is now an error" was true and silent about the
  error-message case, now that C3 exists.

### Reported, not yet acted on

- **No sink argument signatures in the skill.** Trial B needed
  `markdown_digest` and had to guess `path=` from neighbouring examples.
  The prose catalogue lives in the repo, which a wheel install cannot
  reach. This is the same shape as the gap W5 just closed: the skill
  points at authority the student does not have.
- **`deduplicator(by="url")` does not do what the student asked.** The
  request was "drop duplicate stories"; dedupe-by-url will not catch the
  same story covered by two publishers. It also has no reject port, so
  the skill's own "make dropped messages visible" rule cannot be applied
  to it.
- **Custom-sink guidance points at repo paths** unreachable from an
  install.

## How to run this test next time

1. **Never use an office that appears in the skill.** Clean targets with
   useful shapes: `competitor_watch`, `inbox_triage`, `arxiv_radar`,
   `wardrobe_assistant` (hardest — two unrelated sources, four custom
   roles), `job_hunter`.
2. **Sandbox it.** Copy the skill somewhere isolated; forbid reading the
   repo, the installed package, and every `dsl` subcommand except
   `check`. Arbitrary agent names make copying detectable.
3. **Ask for the friction, in writing.** Both agents produced their most
   valuable output in `NOTES.md` — the deliberate probing they did after
   succeeding. A trial that only diffs the artifact discards that.
4. **Expect the happy path to pass.** Budget the effort for what
   happens when a student is *wrong*, because that is where the
   instruments are missing.
