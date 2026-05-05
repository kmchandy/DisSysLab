# An Office can be a Network of Offices

**An office can contain other offices.**

You can build a law office, a news office, a financial analysis office —
each one independently described, compiled, and tested. Then wire them
together into an organization of any size. Each office is a black box:
the organization only knows what goes in and what comes out, nothing
about the agents inside.

This is how large organizations work in the real world. A CEO doesn't
need to know every employee's job description — just what each
department accepts and delivers. DSL works the same way.

This example shows two offices wired together. `news_monitor` filters
articles for significance. `news_editor` routes by topic and rewrites
each article as a briefing note. Each office was built and tested
independently. The network connects them without knowing their internals.

**Tags:** rss, network-of-offices

## What it does

```
al_jazeera ─┐
bbc_world  ─┼→  news_monitor  →  news_editor  →  intelligence_display
npr_news   ─┘
```

- Three RSS feeds stream articles into `news_monitor`
- `news_monitor` (two agents inside) filters articles for significance
  and adds context
- `news_editor` (two agents inside) routes by topic and rewrites as
  briefing notes
- Briefings stream to a live display

## Files in this office

```
org_two_office_news/
    network.md                       ← the org chart at the network level
    news_monitor/
        office.md                    ← news_monitor's org chart
        roles/
            correspondent.md         ← what Alex does
            analyst.md               ← what Morgan does
    news_editor/
        office.md                    ← news_editor's org chart
        roles/
            editor.md                ← what Jordan does
            rewriter.md              ← what Riley does
```

The two sub-offices are themselves valid offices. You can compile and
run either one on its own. After you run `dsl build` on each
sub-office, an `app.py` appears alongside its `office.md` — that's the
compiled output the network loads.

## Try it

> **Note.** Running a network of offices is currently easiest from a
> cloned dissyslab repository. We are smoothing this for the pip-install
> experience.

Build the network — `dsl build` walks the parent office and its
sub-offices in one pass:

```bash
dsl build dissyslab/gallery/org_two_office_news/
```

Run it:

```bash
dsl run dissyslab/gallery/org_two_office_news/
```

`dsl run` rebuilds automatically when any source file (an office.md
or a roles_lib/ entry, in the parent or a sub-office) is newer than
`build/run.py`. To inspect the generated wiring, open
`dissyslab/gallery/org_two_office_news/build/run.py` — one
`build_<office>()` function per office, in topological order.

## Make it yours

**Swap one office for another.** The network only knows that
`news_monitor` accepts `article_in` and produces `article_out`. You
could replace `news_monitor` with a completely different office —
one that filters by geography, by source credibility, or by keyword —
without changing the network spec or `news_editor` at all.

**Add a third office.** Wire a translation office after `news_editor`,
or a summary office that batches briefings into a daily digest.

**Build your own offices.** Write new role files, new office specs,
compile each as a black box, and wire them together in a `network.md`.
The pattern scales to any number of offices.

**More to swap in.** See [`docs/SOURCES_AND_SINKS.md`](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
for the full list of sources and sinks shipped with the framework.

**Recipe.** [How to chain offices](https://github.com/kmchandy/DisSysLab/blob/main/docs/recipes/chain-offices.md)
walks through this office's pattern — `Inputs:`/`Outputs:` at the
office level, the `network.md` spec, and the build steps.

---

## The network

`network.md` describes sources, sinks, and how offices connect — and
nothing about what happens inside each office. Component offices may
even come from a library built by someone else. Your job is to specify
how they connect.

```
# Network: two_office_news

Sources: al_jazeera(max_articles=5), bbc_world(max_articles=5), npr_news(max_articles=5)
Sinks: intelligence_display

Offices:
  news_monitor is gallery/org_two_office_news/news_monitor
  news_editor is gallery/org_two_office_news/news_editor

Connections:
al_jazeera's destination is news_monitor's article_in.
bbc_world's destination is news_monitor's article_in.
npr_news's destination is news_monitor's article_in.
news_monitor's article_out is news_editor's article_in.
news_editor's article_out is intelligence_display.
```

## Inside news_monitor

`news_monitor` has two agents. Alex decides what's worth reporting.
Morgan assesses significance and adds context.

```
article_in  →  Alex  →  Morgan  →  article_out
                  └→  discard       └→  discard
```

**Alex's job — correspondent:**

```
# Role: correspondent

You are a news correspondent who receives articles and sends
articles to an analyst or a discard.

Your job is to decide if each article is worth reporting on —
covering significant world events: major political developments,
conflicts, economic shifts, scientific breakthroughs, or
natural disasters.

Exclude celebrity gossip, entertainment news, sports, and
opinion pieces with no broader significance.

If the article is worth reporting, send to analyst.
Otherwise send to discard.
```

**Morgan's job — analyst:**

```
# Role: analyst

You are a news analyst who receives articles and sends
articles either to an output or to discard.

Your job is to assess the significance of each article and
add context. Add a "significance" field: CRITICAL, HIGH,
MEDIUM, or LOW. Add a "summary" field: one sentence capturing
the core news. Preserve all existing fields.

If significance is CRITICAL, HIGH, or MEDIUM, send to output.
Otherwise send to discard.
```

**`news_monitor`'s org chart:**

```
Inputs: article_in
Outputs: article_out

Sinks: discard

Agents:
Alex is a correspondent.
Morgan is an analyst.

Connections:
article_in's destination is Alex.
Alex's analyst is Morgan.
Alex's discard is discard.
Morgan's output is article_out.
Morgan's discard is discard.
```

## Inside news_editor

`news_editor` has two agents. Jordan routes by topic. Riley rewrites
as a briefing note.

```
article_in  →  Jordan  →  Riley  →  article_out
                    └→  discard
```

**Jordan's job — editor:**

```
# Role: editor

You are a news editor who receives articles and sends
articles to a rewriter or a discard.

Your job is to route each article by topic. Add a "topic"
field with one of: politics, economics, technology, science,
environment, conflict, other.

If the topic is politics, economics, technology, science,
environment, or conflict, send to rewriter.
Otherwise send to discard.
```

**Riley's job — rewriter:**

```
# Role: rewriter

You are a news rewriter who receives articles and sends
articles to an output.

Your job is to rewrite each article as a crisp one-paragraph
briefing note. Begin with the significance rating from the
"significance" field if present. Write clearly and concisely
for a busy reader. Put your rewritten text in the "text" field.
Preserve the source, url, topic, and significance fields.

Always send to output.
```

**`news_editor`'s org chart:**

```
Inputs: article_in
Outputs: article_out

Sinks: discard

Agents:
Jordan is an editor.
Riley is a rewriter.

Connections:
article_in's destination is Jordan.
Jordan's rewriter is Riley.
Jordan's discard is discard.
Riley's output is article_out.
```

## What you built

Four agents running in four threads, organized into two black-box
offices, wired together by a network spec written in plain English.
Each office was described, compiled, and tested independently.
The network connects them without knowing their internals.

This is composability — the same principle that makes large software
systems manageable. Offices can be reused, swapped, and combined
into organizations of arbitrary complexity.
