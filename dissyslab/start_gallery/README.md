# start_gallery — worked examples for `dsl new` / `dsl edit`

Curated teaching examples for the Claude chat loop behind `dsl new` and
`dsl edit` (`dissyslab/cli_chat.py`), loaded alongside
`start_instructions.md`. Named to match OfficeSpeak's `start_gallery/`
— same role, same name, different repo.

## Why this exists, and why it isn't just the real gallery

`dissyslab/gallery/apps/` and `dissyslab/gallery/examples/` are real,
runnable offices for Pat and for builders. They're organized by
audience and setup cost, they mix several patterns together the way a
real app has to, and their README/role files carry setup instructions,
cost tables, and narrative asides that a person needs but that only
dilute what a generation model needs. This folder exists to hold a
*different* thing: small, isolated, one-pattern-at-a-time examples,
each naming which real gallery app it's distilled from, ordered from
simplest to most complex.

Duplication has a cost — an excerpt here can drift from how the real
role actually behaves once the framework changes. Two rules to manage
that: (1) every example names its source app, so drift is at least
checkable; (2) keep the office.md and role files here real and
literal — copy-and-trim from the actual source, don't paraphrase or
invent a syntax variant.

## Format

There are two kinds of example here, and a file should say which kind
it is up front.

**Type A — pattern reference.** Shows the destination, not the road.
Use when the pattern itself is the point and there's nothing genuinely
ambiguous to resolve.

1. **Pat's description** — the English ask, written the way Pat would
   actually say it (DSL register — source/sink/agent, even if loose),
   not the way a builder would spec it.
2. **The office** — the real `office.md`, plus any real role files
   that aren't already framework defaults. This is the literal target
   artifact, not pseudocode — DSL's chat loop produces exactly this
   shape, so the example should look exactly like what a correct
   response looks like.
3. **Explanation for Pat** — the plain-English explain-back a
   correct `dsl new`/`dsl edit` conversation should produce: what the
   office does, walked through for one item start to finish.
4. **Source** — which real gallery app this was distilled from.

**Type B — resolving an ambiguous ask.** Shows the road: an initial
structural description that's genuinely incomplete or ambiguous (not
just under-specified in some abstract sense — specifically, a missing
*decision* that changes the office's structure), the wrong or
under-determined first reading, the clarifying exchange that closes
it, and only then the resolved office and explain-back. Use when the
point is the disambiguation itself. See `02_dynamic_subscriptions_
ambiguity.md` for the shape.

## An honest gap: nothing here is from a real Pat yet

Every example so far is either invented for illustration (`01`'s Pat
quote was written for this file, not spoken by anyone) or distilled
from an expert design session (`02` is a real transcript, but between
Mani — this system's designer — and a Claude holding a full session's
accumulated context, not between a non-technical Pat and a Claude
grounded only on these two files). Neither is a substitute for an
actual cold test: a fresh Claude with only `start_instructions.md` +
`start_gallery` loaded, talking to something playing a genuinely
non-technical Pat, the way OfficeSpeak already cold-tests its own
instructions. Until that's been done, treat every Type B example's
*structural* content as trustworthy and its register/pacing as
unverified — see the caveat at the top of `02` for the long version.

## What's here so far

- `01_single_agent.md` (Type A) — one source, one agent, one sink. No
  fan-out, no coordinator. Distilled from
  `gallery/examples/my_first_office`.
- `02_dynamic_subscriptions_ambiguity.md` (Type B, expert session —
  see the gap above) — a dynamic, compute-once pub/sub registry with
  no new coordinator. Distilled from the real conversation that built
  `situation_room_requests`; also covers the "resolved at the
  description stage" vs. "correct once actually run" distinction (a
  silently-unwired outport, a source with no `poll_interval`).
- `03_al_subscriber_handler.md` (Type B, authored Al persona, not a
  cold test — see the gap above) — the same compute-once/push pattern
  as `02`, reached with no wrong first draft this time, because Al's
  description stated the wiring directly instead of leaving it
  implicit. Verified with `dsl build`. Also models two different kinds
  of incompleteness ("and so on" vs. a genuinely unresolved worker
  responsibility) and a flagged-but-not-added gap (no cross-feed
  deduplication).

## What's still needed, and an open question about how much is enough

Type A: candidates remain for `merge_synch`, `gate`, `select`, a
shared `record`, per-role backend override.

Type B: more disambiguation examples as real ones surface.

But it's worth questioning the plan itself before adding much more.
OfficeSpeak's own gallery is deliberately small — three combined
examples, each demonstrating several techniques together (`investment_club`
alone covers `merge_synch`, a shared record, a gate, *and* a
wrong-reading-corrected beat, all in one), not one isolated example
per primitive. That's real, working precedent for "few and rich" over
"many and isolated," and it directly answers the size-vs-noise
tradeoff: fewer, denser examples may teach more per token than many
single-pattern ones, precisely because each one shows how patterns
combine, which isolated examples can't. Worth deciding whether to
follow that model here rather than filling out one file per remaining
primitive.

**Highest priority regardless of the above:** an actual cold test,
once `start_instructions.md` exists — a fresh Claude grounded only on
these two files, given a genuinely non-technical Pat description
(real or carefully simulated), to produce at least one Type B example
that isn't an authored or expert-session stand-in for one. That test
is also the real way to find out whether this folder's size is right
— not guessing at a number in advance.
