# Paper port 7: `org_two_office_news` (the composition example)

Ported by hand against `officespeak_revised.md`. Nothing here runs yet. The
name is kept because `course/labs.html` refers to it; the inside is rebuilt
from roles students have already met.

## Before

`network.md`, with an `Offices:` section:

```
Sources: al_jazeera(max_articles=5), bbc_world(max_articles=5), npr_news(max_articles=5)
Sinks: intelligence_display

Offices:
  news_monitor is news_monitor
  news_editor is news_editor

Connections:
al_jazeera's destination is news_monitor's article_in.
bbc_world's destination is news_monitor's article_in.
npr_news's destination is news_monitor's article_in.
news_monitor's article_out is news_editor's article_in.
news_editor's article_out is intelligence_display.
```

- `news_monitor/` has two local roles, `correspondent` and `analyst`, each
  with a `discard` outbox chosen by `send_to`.
- `news_editor/` has `editor` (routes by topic) and `rewriter`, whose
  `adds: text` overwrites the article with the briefing.

## After

```
org_two_office_news/
    office.md
    news_monitor/
        office.md
        roles/topic_filter.md      (the role from org_news_filter)
    news_editor/
        office.md
```

`office.md` (the outer office):

```
sources:
    al_jazeera(max_articles=5)
    bbc_world(max_articles=5)
    npr_news(max_articles=5)

sinks:
    intelligence_display(title="title", text="summary")

agents:
    monitor: office(path="news_monitor")
    editor: office(path="news_editor")

connections:
    al_jazeera, bbc_world, npr_news -> monitor.articles
    monitor.kept -> editor.articles
    editor.briefings -> intelligence_display
```

`news_monitor/office.md`: `org_news_filter`'s network, with boundary ports
in place of sources and sinks:

```
inputs:
    articles

outputs:
    kept

sinks:
    discard

agents:
    Felix: topic_filter
    Rex: router(on="on_topic")

connections:
    articles -> Felix -> Rex
    Rex.yes -> kept
    Rex.no -> discard
```

`news_editor/office.md`: the built-in `summarizer`, so there is no
`roles/` folder:

```
inputs:
    articles

outputs:
    briefings

agents:
    Sue: summarizer

connections:
    articles -> Sue -> briefings
```

```
al_jazeera ─┐       ┌──────── monitor ────────┐      ┌──── editor ────┐
bbc_world  ─┼→ articles → Felix → Rex ─ yes → kept → articles → Sue → briefings → intelligence_display
npr_news   ─┘       │               └ no → discard │      └────────────────┘
                    └──────────────────────────────┘
```

What `dsl check` reports at the boundaries (derived, 3.4):
`monitor.articles` receives `source, title, text, url, timestamp`;
`monitor.kept` sends those plus `on_topic`; `editor.briefings` sends those
plus `summary`, which the display's `text="summary"` uses.

Old: a separate `network.md` file type, 4 local roles, 2 routing decisions
made by `send_to`, one overwrite. New: three ordinary `office.md` files,
1 local role (already known), 1 built-in role, 1 router.

## Findings

1. **The lesson is now composition alone.** Every role and router inside has
   been met in earlier examples, so the only new idea is that an office can
   be one agent of a bigger office.

2. **The outer office has no agents of its own** besides the two offices.
   That is legal and clean; no spec change.

3. **An office used inside another cannot be the same folder as a
   stand-alone one.** `org_news_filter` has sources and sinks;
   `news_monitor` has inputs and outputs. So `topic_filter.md` exists in two
   places. The README should say so. **Question for later, not now:** whether
   an office may declare both (sources when run alone, inputs when nested).
   It would add a rule, so I recommend not doing it in the first release.

4. **The built-in `summarizer`** must get the new front matter
   (`in: title, text`, `out: summary`), like every built-in role. No new
   finding.

5. **`labs.html`** refers to this example by name. Its text will need
   updating with the new layout (one `office.md` at the top, no
   `network.md`).
