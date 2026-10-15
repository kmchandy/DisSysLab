# Paper port 2 of 5: `situation_room_pro`

Ported by hand against `officespeak_revised.md`. Nothing here runs yet.

```
bbc_world ─┐                ┌→ Eve   (entities) ─┐
npr_news  ─┼→ Sasha (dedup) ┼→ Sam   (severity) ─┼→ Sync → Riley (writer) ─┬→ intelligence_display
al_jazeera─┘                ├→ Tom   (topic)    ─┤                         └→ jsonl_recorder
                            └→ Greta (location) ─┘
```

## Before

`office.md` (identical to `situation_room` apart from the first line)

```
Sources: bbc_world(max_articles=3), npr_news(max_articles=3), al_jazeera(max_articles=3)
Sinks: intelligence_display, jsonl_recorder_briefing(path="briefings.jsonl")

Agents:
Sasha is a deduplicator(by="url").
Eve is an entity_extractor.
Sam is a severity_classifier.
Tom is a topic_tagger.
Greta is a geolocator.
Sync is a synchronizer(inboxes=["entities", "severity", "topic", "location"]).
Riley is a writer.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
al_jazeera's destination is Sasha.
Sasha's out is Eve, Sam, Tom, Greta.
Eve's out is Sync's entities.
Sam's out is Sync's severity.
Tom's out is Sync's topic.
Greta's out is Sync's location.
Sync's out is Riley.
Riley's out is intelligence_display, jsonl_recorder_briefing.
```

`roles/writer.py`, the only file that makes this office "pro": it imports
`dissyslab`, reads the built-in `writer.md`, and re-wraps it with
`nl_role(..., AI="claude")`, shadowing the built-in `writer`.

## After

`office.md`

```
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

(Written in the line form of spec §3.0, settled 16 October, and with the
display arguments of finding 4, since settled.)

`roles/` is empty and is deleted. "Pro" is now one visible argument,
`ai="anthropic"` on Riley. `on="url"` on Sync was finding 2, since settled.

### Built-in roles, new front matter

| Role | `in:` | `out:` |
|---|---|---|
| `entity_extractor` | title, text | entities |
| `severity_classifier` | title, text | severity (CRITICAL \| HIGH \| MEDIUM \| LOW) |
| `topic_tagger` | title, text | topic (politics \| business \| technology \| science \| health \| sports \| entertainment \| other) |
| `geolocator` | title, text | location |
| `writer` | title, text, severity, topic, location, entities | headline, summary |

The text of each built-in loses three things: "Always send to out.", "Preserve
every existing field exactly; only add …" (the framework merges; the model
returns only its own fields), and nothing else changes except a closing
sentence. `severity_classifier` as an example:

```
---
emits: how significant the item is: CRITICAL, HIGH, MEDIUM or LOW
in: title, text
out: severity (CRITICAL | HIGH | MEDIUM | LOW)
---
You read one news article, given as a JSON object. Its "title" and "text"
fields are the headline and the body.

Decide how significant it is:

- CRITICAL: events that affect many lives or markets at global scale
  (war, large-scale disaster, major political rupture).
- HIGH: major national-scale stories with clear ongoing impact.
- MEDIUM: newsworthy regional or sector-specific stories.
- LOW: entertainment, lifestyle, sport, minor local items.

Example. For the article
{"title": "UN Security Council emergency meeting on regional conflict", "text": "Diplomats convened in New York early Tuesday after fresh airstrikes..."}
return {"severity": "CRITICAL"}

Return only a JSON object with one field, "severity", whose value is one of
CRITICAL, HIGH, MEDIUM, LOW.
```

### `deduplicator`, a built-in Python role under 4.3

```python
"""
---
emits: each item once; later items with the same key are dropped
kind: author
---
Arguments: by -- the field that identifies an item (default "url").
"""

def step(item, state, settings):
    key = item[settings["by"]]
    if key in state["seen"]:
        return [], state
    return [item], {"seen": state["seen"] + [key]}


class Deduplicator:
    def __init__(self, by="url"):
        self.settings = {"by": by}
        self.state = {"seen": []}

    def __call__(self, item):
        out, self.state = step(item, self.state, self.settings)
        return out

    def checkpoint(self):
        return self.state

    def restore(self, saved):
        self.state = saved
```

An author returning `[item]` or `[]` is a filter. No new concept. (The
current one keeps a `set`, which is not serializable. This one keeps a list.)

## Findings for the spec

1. **Per-role backend is already settled.** `Riley's AI is anthropic.` (now `ai="anthropic"`, spec §3.0)
   replaces a 70-line override file that imported `dissyslab` and shadowed a
   built-in, both now errors. Good test of the spec: the "pro" idea becomes
   one visible line. *No change.*

2. **The synchronizer misaligns after one failure.** It pairs the k-th message
   on each inbox. Under 4.5 a failed reply drops that one message, so if Sam
   fails on article 3, every later round merges different articles. The
   "different values" rule (6) reports it, but on every round from then on.
   **Proposal:** the synchronizer names its key, like the router:
   `synchronizer(inboxes=[…], on="url")`. It merges the messages with the same
   key value once one has arrived on every inbox. An incomplete group is
   reported when the run ends. A synchronizer must always name its key, just
   as a router must always name its field. (The deduplicator upstream is what
   makes `url` unique, which gives Sasha a reason to be there.)

3. **Can an annotator overwrite a field?** 4.1 says its fields are "added".
   That is the `adds: text` bug from port 1. **Proposal:** `dsl check` error
   when a role's `out:` names a field produced upstream (by a source or a
   role), and at run time a reply that would change an existing field is a
   failure. The existing warning "two roles on one path add the same field"
   becomes this error.

4. **The display never shows Riley's work.** `intelligence_display` prints
   `title` and `text` (or `abstract`), and colours by the first of
   `significance, severity, impact, relevance, urgency` it finds. Riley's
   `headline` and `summary` reach only the jsonl file. Two lessons:
   - the end-to-end check should also **warn when a field is added and
     nothing downstream declares it in `in:`** (here `headline`, `summary`);
   - the sink's list of guessed field names is invisible behaviour. **Proposal:**
     a sink that shows fields takes them as arguments, with the defaults in
     its docstring:
     `intelligence_display(title="headline", text="summary", color="severity")`.
     Its `in:` is then whatever those arguments name.

5. **`out:` for a pass-through author.** The deduplicator returns its input
   unchanged. If `out:` is absent, 4.5 drops nothing (correct), but the
   data-flow check loses track of the fields after Sasha, so it cannot check
   Eve's `in:`. **Choice:** (a) the check carries fields through any author
   with no `out:` (simple, but it is a guess); (b) the front matter says so:
   `out: same as in`; (c) no filtering authors: the deduplicator becomes an
   annotator adding `duplicate (yes | no)` plus a router to `discard`. My
   preference is (b).

6. **`in:` that depends on an argument** (`by="url"`). The front matter is
   static. Proposal: such a role omits `in:`, and its docstring says which
   argument names the field. The check skips it. Minor.

7. **Two sinks of the same kind need names.** `jsonl_recorder_briefing` exists
   only so one office can have two `jsonl_recorder`s (likewise
   `slack_sink_alerts`, `gmail_sink_match`, …, about fifteen aliases).
   **Proposal:** sources and sinks may be named like agents:
   `briefings: jsonl_recorder(path="briefings.jsonl")` under `sinks:`; an unnamed
   one is called by its component name. The aliases retire. Not needed here,
   since this office has one recorder.

8. **The built-in `writer` assumes the enrichment fields may be missing**
   ("when a field is missing, ignore it"). With a strict `in:` it needs all
   four. Only `situation_room` and `situation_room_pro` use it, and both
   supply all four. (`org_news_editorial` has its own local `writer.md`, which
   shadows the built-in and so must be renamed under 4.2.) Keep it strict; an
   office without enrichments copies and edits it under a new name.
