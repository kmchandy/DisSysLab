# The Sense → Think → Respond Pattern

Some patterns of agent networks are used in a variety of applications.
One pattern is **sense → think → respond**: agents monitor streams of
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



## Example: `situation_room_pro`

Three news feeds; a deduplicator; four built-in annotators working on
each article at the same time; a synchronizer that joins their four
copies of the article back into one; a writer; a display and a file.

`dissyslab/gallery/situation_room_pro/office.md`:

```
# situation_room_pro: news from three feeds, analysed four ways at once,
# joined, and written up as briefings by a stronger model.

sources:
    bbc_world(max_articles=3)
    npr_news(max_articles=3)
    al_jazeera(max_articles=3)

sinks:
    intelligence_display(title="headline", text="summary", color="severity")
    jsonl_recorder(path="briefings.jsonl")

agents:
    Sasha: deduplicator(by="url")
    Eve: entity_extractor
    Sam: severity_classifier
    Tom: topic_tagger
    Greta: geolocator
    Sync: synchronizer(on="url")
    Riley: writer(ai="anthropic")

connections:
    bbc_world, npr_news, al_jazeera -> Sasha -> Eve, Sam, Tom, Greta
    Eve -> Sync.entities
    Sam -> Sync.severity
    Tom -> Sync.topic
    Greta -> Sync.location
    Sync -> Riley -> intelligence_display, jsonl_recorder
```

The slots, in that file:

| Slot | Lines |
|---|---|
| 1. Sense | the three sources under `sources:` |
| 2. Think | `Eve`, `Sam`, `Tom`, `Greta`: one field each (entities, severity, topic, location) |
| 3. Compose | `Riley: writer(...)` |
| 4. Respond | the two sinks under `sinks:` |

The deduplicator (`Sasha`) and the synchronizer (`Sync`) are the same in
every office of this family. The only thing you change in them is the
synchronizer's inboxes, which are named by the connections into it:
`Eve -> Sync.entities` creates the inbox `entities`.

---

## The four edit slots

Inside a working office that follows this pattern, you change one or
more of just four things to make it yours:

1. **Sources.** The feeds the office watches: replace or add lines under
   `sources:` (`dsl grammar sources` lists them; `rss(url=...)` takes any
   feed).
2. **Parallel thinkers.** The analyses run on each item, each adding one
   field. Swap a built-in role (`dsl roles`) for one you write, add one,
   or drop one; give each its own synchronizer inbox.
3. **Writer.** The role that composes the output. To change its style
   (an executive summary, a support reply, a competitor digest), copy
   `writer` into `roles/` under a new name and edit the text
   (`dsl show writer` prints it).
4. **Sinks.** Where the output goes, and which fields the display shows
   (`intelligence_display(title=..., text=..., color=...)`).

---

## Gallery offices of this shape

- **`situation_room_pro`**: the full pattern, above.
- **`arxiv_radar`**: sense three arXiv categories, then two thinkers *in
  a row* rather than in parallel (classify the paper, then rate its
  relevance), and respond with a display. When each thinker needs the
  last one's field, chain them and drop the synchronizer.
- **`org_news_filter`**: the thinker layer is one decision, and the
  respond layer is a router: keep or discard.
- **`room_climate_monitor`**: sense two sensors, join their readings by
  the minute they belong to, decide, alert. The synchronizer joins
  different *sources* rather than different thinkers.
- **`backyard_birds`**: the thinker is a classifier (BirdNET), not a
  language model.

---

## How to build an office in this family

1. `dsl list`, and pick the gallery office closest to what you want.
2. `dsl init situation_room_pro my_room` (or your pick), then `cd my_room`.
3. Edit each slot in `office.md` and, for slot 3, the writer's role.
4. `dsl check .` after every edit: a thinker you added but did not
   connect to the synchronizer, or a misspelt inbox, is reported by line.
5. `dsl draw . --mermaid` to see the shape, and `dsl run .`.

---

## Where this pattern doesn't fit

Sense → think → respond covers most continuous information work,
but not all of it:

- **Real-time conversational agents.** A chatbot has a
  request-response shape, not a continuous stream. dsl can model
  these too (`webhook` source, writer, `webhook_sink`), but the
  four-slot framing isn't the most natural fit.
- **Multi-stream coordination across offices.** When two
  independent offices need to share state — a price monitor that
  informs a buying agent, an inventory tracker that wakes a
  reorder agent — the right structure is multiple offices joined
  by a shared queue, not one big office. dsl supports this with
  nested offices (`org_two_office_news`).
- **Hard-deadline systems.** dsl offices aim at minutes-to-hours
  latency. Sub-second response (trading, security alerts) wants a
  different runtime.

When you find a job that needs one of these, nested offices and your
own roles let you reach for the shape that fits. This pattern
isn't a wall; it's a starting line.
