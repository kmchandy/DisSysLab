# The Sense → Think → Respond Pattern

Some patterns of agent networks are used in a variety of applications.
One pattern is **sense → think → respond**: agents moitor streams of
data sources, a collection of parallel agents analyze the data in the streams,
and other agents compose responses and send responses to consoles, devices and actuators.
You build an app by merely filling four slots of the pattern.


## A Schematic of the Pattern

```
        ┌──────────┐ ┌──────────┐ ┌──────────┐
SENSE   │ source 1 │ │ source 2 │ │ source 3 │     (SLOT 1)
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             └────────────┼────────────┘
                          ▼
                  ┌───────────────┐
                  │ deduplicator  │   ← Gate keeper for thinkers
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
                  │ synchronizer  │   ← Merge streams
                  └───────┬───────┘
                          ▼
                  ┌───────────────┐
                  │    writer     │              (SLOT 3)
                  └───────┬───────┘
                          ▼
RESPOND        ┌──────────┐ ┌──────────┐         (SLOT 4)
               │ sink A   │ │ sink B   │
               └──────────┘ └──────────┘
```



## Example: Situation Room 
```
        ┌──────────┐ ┌──────────┐ ┌──────────┐
SENSE   │ bbc_news │ │ npr_news │ │  al_jaz  │     (SLOT 1)
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             └────────────┼────────────┘
                          ▼
                  ┌───────────────┐
                  │ deduplicator  │   ← Gate keeper for thinkers
                  └───────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
THINK   ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ extract  | |determine | |  topic   |
        |entities  │ │ urgency  │ | tagger   |   (SLOT 2)
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             └────────────┼────────────┘
                          ▼
                  ┌───────────────┐
                  │ synchronizer  │   ← Merge streams
                  └───────┬───────┘
                          ▼
                  ┌───────────────┐
                  │    writer     │              (SLOT 3)
                  └───────┬───────┘
                          ▼
RESPOND        ┌──────────┐ ┌──────────┐        
               │ display  │ │ archive  │          (Slot 4)
               └──────────┘ └──────────┘
```

---

## The four edit slots

Inside a working office that follows this pattern, you change one or
more of just four things to make it yours:

1. **Sources and Sinks** Add, remove, modify sources that the office
  monitors and the destinations of office outputs.
2. **Parallel thinkers.** The operations executed in parallel per item.
   For instance: determine sentiment. Replace `geolocator` with
   `customer_tier_classifier`. Drop `severity_classifier`.
3. **Writer.** The prompt that composes the output. Switch from
   "intelligence briefing" to "support reply" to "executive
   summary" to "competitor digest."

The gate and the merge are the same in instances of this pattern.
You don't modify them except to specify the names of the inboxes of
the merge.

Open
[`dissyslab/gallery/apps/situation_room/office.md`](../dissyslab/gallery/apps/situation_room/office.md)
and you'll see the four slots explained in situation_room/README.md's 'Make it yours' section. 


labelled with `# SLOT N:` comments.
That annotated office is your starting point for any office in the
family.

---

---

## Gallery instances

Offices that follow this pattern:

- **[`situation_room`](../dissyslab/gallery/apps/situation_room/)**
  — three news feeds → deduplicator → four parallel thinkers
  (entity, severity, topic, location) → synchronizer → writer →
  intelligence display + JSONL. The canonical instance.

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

## How to build offices in this family

To build a new office in this family:

1. Run `dsl list`; pick the closest gallery instance to your use case.
2. `dsl init <office_name> my_office`.
3. Open `my_office/office.md` in your editor.
4. Edit each slot for your domain:
   - SLOT 1 (sources): point at the feeds you want to watch.
   - SLOT 2 (parallel thinkers): swap or extend the extractors.
   - SLOT 3 (writer): edit `roles/writer.md` for the style of
     output you want.
   - SLOT 4 (sinks): pick where the output goes.
5. `dsl run .`

The gate/deduplicator and synchronizer agents and the wiring
between them stays the same. The result is a new office, written
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
