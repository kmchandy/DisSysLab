# The sense → think → respond pattern

DisSysLab offices follow a small handful of shapes. The most useful
one is **sense → think → respond**: the office watches a stream of
inputs, thinks about each one (often in parallel), and writes a
result somewhere. Most of what Pat builds — news monitoring, inbox
triage, ticket routing, competitor watch, lead qualification, RFQ
processing, alert filtering — instantiates this pattern with
different sources, thinkers, and sinks.

This page names the pattern, shows the four edit slots inside a
working office, lists the gallery instances that already exist, and
says where the pattern stops fitting.

---

## The three verbs

**Sense.** Where the office listens. RSS feeds, email, webhooks,
social streams, file watchers, periodic API polls, calendar reads.
A `Sources:` line in office.md names them; the framework ships a
library of source components you refer to by name
(`bbc_world`, `gmail`, `weather`, `webhook`, `mcp_source`, …).

**Think.** What the office does with each item it sensed.
Classifying, extracting structured fields, summarising, scoring,
deciding, routing. Some thinkers run in *parallel* — every item
gets four annotations at once. Others run in *sequence* — a writer
composes a draft, an evaluator decides whether to publish. When
the problem needs it, a thinker can route an item back to an
earlier thinker, forming a *feedback loop*. The same plain-English
grammar covers all three.

**Respond.** Where the office writes. A markdown file Pat opens in
the morning, a Slack channel, a Notion page, a JSONL archive, an
outbound webhook, another office downstream. A `Sinks:` line in
office.md names them; the framework ships a sink library too.

The three verbs are general enough to cover one-way pipelines
(*news → briefing*), branching responses (*publish vs. revise vs.
discard*), and feedback loops (*writer ↔ editor*). Anything that
fits the shape "sense the world, decide, write somewhere" fits
the pattern.

---

## The four edit slots

Inside a working office that follows this pattern, you change one or
more of just four things to make it yours:

1. **Sources.** Different feeds. Add, remove, replace.
2. **Parallel thinkers.** What annotations are extracted per item.
   Add a sentiment thinker. Replace `geolocator` with
   `customer_tier_classifier`. Drop `severity_classifier` if
   irrelevant.
3. **Writer.** The prompt that composes the output. Switch from
   "intelligence briefing" to "support reply" to "executive
   summary" to "competitor digest."
4. **Sinks.** Where output lands.

Everything else — the deduplicator, the synchronizer that fans the
parallel thinkers back together, the evaluator that gates
publish-worthiness, the wiring between them — is scaffolding. You
rarely touch it.

Open
[`dissyslab/gallery/apps/situation_room/office.md`](../dissyslab/gallery/apps/situation_room/office.md)
and you'll see the four slots labelled with `# SLOT N:` comments.
That annotated office is your starting point for any office in the
family.

---

## A schematic

```
        ┌──────────┐ ┌──────────┐ ┌──────────┐
SENSE   │ source 1 │ │ source 2 │ │ source 3 │     (SLOT 1)
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             └────────────┼────────────┘
                          ▼
                  ┌───────────────┐
                  │ deduplicator  │   ← scaffolding
                  └───────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
THINK   ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ thinker1 │ │ thinker2 │ │ thinker3 │  …  (SLOT 2)
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             └────────────┼────────────┘
                          ▼
                  ┌───────────────┐
                  │ synchronizer  │   ← scaffolding
                  └───────┬───────┘
                          ▼
                  ┌───────────────┐
                  │    writer     │              (SLOT 3)
                  └───────┬───────┘
                          ▼
                  ┌───────────────┐
                  │   evaluator   │   ← scaffolding
                  └───┬───────┬───┘
                publish     revise/discard
                      ▼          ▼
RESPOND        ┌──────────┐ ┌──────────┐         (SLOT 4)
               │ sink A   │ │ sink B   │
               └──────────┘ └──────────┘
```

A feedback edge from the evaluator back to the writer turns the
shape into a revise loop — same grammar, same office, one extra
line in `Connections:`.

---

## Gallery instances

Offices that follow this pattern:

- **[`situation_room`](../dissyslab/gallery/apps/situation_room/)**
  — three news feeds → deduplicator → four parallel thinkers
  (entity, severity, topic, location) → synchronizer → writer →
  evaluator → intelligence display + JSONL. The canonical instance.

- **[`situation_room_pro`](../dissyslab/gallery/apps/situation_room_pro/)**
  — same office, Claude as the writer, open-weight Qwen for every
  other agent. Demonstrates per-agent engine choice without
  changing the office shape.

- **[`periodic_brief`](../dissyslab/gallery/apps/periodic_brief/)**
  — a leaner instance: multiple sources go straight to a
  multi-source sink that buckets and arranges. When the response
  is "just collect and present," the thinker layer can collapse to
  nothing.

More offices in this family land in the gallery over time —
`inbox_triage`, `ticket_router`, `competitor_watch`, `lead_qualifier`,
others — each filling the four slots for a different domain. Each
is a known-good starting point you can `dsl init` and edit.

---

## How to remix

To build a new office in this family:

1. Run `dsl list`; pick the closest gallery instance to your use case.
2. `dsl init <office_name> my_office`.
3. Open `my_office/office.md` in your editor.
4. Find the four `# SLOT N:` comments.
5. Edit each slot for your domain:
   - SLOT 1 (sources): point at the feeds you want to watch.
   - SLOT 2 (parallel thinkers): swap or extend the extractors.
   - SLOT 3 (writer): edit `roles/writer.md` for the style of
     output you want.
   - SLOT 4 (sinks): pick where the output goes.
6. `dsl run .`

The scaffolding (deduplicator, synchronizer, evaluator, the wiring
between them) stays the same. The result is a new office, written
in plain English, that does what you need.

---

## Where this pattern doesn't fit

Sense → think → respond covers most continuous information work,
but not all of it:

- **Real-time conversational agents.** A chatbot has a
  request-response shape, not a continuous stream. dsl can model
  these too (webhook source, writer, webhook sink), but the
  four-slot framing isn't the most natural fit.
- **Multi-stream coordination across offices.** When two
  independent offices need to share state — a price monitor that
  informs a buying agent, an inventory tracker that wakes a
  reorder agent — the right structure is multiple offices joined
  by a shared queue, not one big office. dsl supports this via
  sub-offices.
- **Hard-deadline systems.** dsl offices aim at minutes-to-hours
  latency. Sub-second response (trading, security alerts) wants a
  different runtime.

When you find a job that needs one of these, sub-offices and
custom roles let you reach for the shape that fits. This pattern
isn't a wall; it's a starting line.

---

The spine **sense → think → respond** lives in the
[top-level README](../README.md) banner; this doc expands it; the
annotated
[`situation_room/office.md`](../dissyslab/gallery/apps/situation_room/office.md)
instantiates it. Same idea, three layers of detail.
