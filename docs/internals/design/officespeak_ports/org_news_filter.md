# Paper port 1 of 5: `org_news_filter`

Ported by hand against `officespeak_revised.md`. Nothing here runs yet.

## Before

`office.md`

```
# Office: news_filter

Sources: al_jazeera(max_articles=2), bbc_world(max_articles=2)
Sinks: console_printer, jsonl_recorder(path="filtered_output.jsonl")

Agents:
Felix is a filter.

Connections:
al_jazeera's destination is Felix.
bbc_world's destination is Felix.
Felix's keeper is console_printer.
Felix's discard is jsonl_recorder.
```

`roles/filter.md`

```
---
outboxes: keeper, discard
adds: text
---
# Role: filter

You are a content filter who receives news articles and sends
articles to a keeper or a discard.

Your job is to decide if each article is about the americas: canada, usa, brazil, ..
If the article is about the americas, send to keeper.
Otherwise send to discard.
```

## After

`office.md`

```
# Office: news_filter

Sources: al_jazeera(max_articles=2), bbc_world(max_articles=2)
Sinks: console_printer, jsonl_recorder(path="filtered_output.jsonl")

Agents:
Felix is a topic_filter.
Rex is a router(on="on_topic").

Connections:
al_jazeera's out is Felix.
bbc_world's out is Felix.
Felix's out is Rex.
Rex's yes is console_printer.
Rex's no is jsonl_recorder.
```

`roles/topic_filter.md`

```
---
emits: whether a news article is on the topic
in: title, text
out: on_topic (yes | no)
---
You read one news article, given as a JSON object. Its "title" and
"text" fields are the headline and the body.

The topic is the Americas: North, Central and South America and the
Caribbean, for example Canada, the United States, Mexico and Brazil.

Decide whether the article is mainly about the topic.

Return only a JSON object with one field, "on_topic", whose value is
"yes" or "no".
```

## What changed, and why

| Change | Rule in the spec |
|---|---|
| `destination` → `out` | 3.3: a source has one outbox, `out` |
| Felix now decides; Rex routes | 0: compute in roles, route in routers; 5 |
| No "send to keeper / discard" in the role text | 4.2: no wiring words |
| `adds: text` removed | 4.4. The old contract asked the model for `text`, so its reply **overwrote the article body**. Under 4.5 the reply may add only `on_topic`; the article is untouched. |
| The prompt ends with what to return | 4.2: the file is the whole prompt |
| Role renamed `filter` → `topic_filter` | The role no longer filters anything (the router does); it answers a question. Not forced: there is no built-in `filter`. |
| Field `on_topic`, not `about_americas` | "Make it yours" in the README is "change the topic". With a topic-neutral field, that edit stays inside one paragraph of one file; `office.md` and the router do not change. |
| `yes`/`no` strings, not `true`/`false` | 5 allows booleans, but strings read the same in the role, the router line and the trace. |

What a student sees in a trace for one article:

```
bbc_world → Felix   {"source": "bbc_world", "title": "...", "text": "...", "url": "...", "timestamp": "..."}
Felix     → Rex     {... same five fields ..., "on_topic": "no"}
Rex       → jsonl_recorder   (on_topic = no)
```

`dsl check` would confirm: `title`, `text` are produced by both sources;
`on_topic` is added upstream of Rex; both listed values have an outbox.

## Findings for the spec

1. **Sinks that take anything.** `console_printer` and `jsonl_recorder`
   print or write the whole object; they use no particular field. Section 7
   should say: a sink with no `in:` accepts any object, and the end-to-end
   check skips it. (Same for a role with no `in:`, already implied by 4.4.)
2. **Sources must declare `out:`** for the `in: title, text` check to work.
   All RSS sources share `rss_normalizer.py`, which produces `source, title,
   text, url, timestamp`; one docstring line there would cover ~40 sources.
   Add to the implementation list.
3. **Does a dropped undeclared field make `dsl run` exit non-zero?** If the
   model adds `"reason": "..."`, 4.5 drops and counts it. 4.5 item 4 makes
   only *failures* exit non-zero. Proposal: dropped fields are counted and
   shown in the summary as a warning; exit stays zero. Needs a sentence.
4. **The model sees the whole message**, including `url`, `source`,
   `timestamp`, although `in:` names two fields. That is right under 4.2
   (nothing invisible), and `in:` is a statement for checking, not a
   filter. Worth one sentence in 4.4 so nobody expects `in:` to trim the
   prompt.
5. **Field names should be topic-neutral** when the README invites the
   student to change the topic. A teaching guideline for the role-writing
   guide, not a spec rule.

None of these changes a settled decision. Findings 1, 3 and 4 are one
sentence each in sections 7, 4.5 and 4.4.
