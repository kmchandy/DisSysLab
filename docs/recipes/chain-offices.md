# How to chain offices

> **Heads up.**  Most people creating offices don't need this
> pattern which builds a network of offices.
> A single office with several
> agents is adequate for most people. 
> Build yourself a network of offices, each office specializing
> in some activity, when you want to build complex distributed
> systems.

**Goal.** 
Corporations have multiple offices that specialize in certain
activities. An HR office doesn't work directly
with the patents office. And the patents office is independent of
the buildings maintenance office. Similarly, you can build an office for each
role in your organization and then connect your smaller offices
to build a bigger office. 

You can nest organizations repeatedly: you can have a network of 
offices where each office in the network is itself a network of
organizations.


## Run a working example

DisSysLab ships with a two-office network — `news_monitor`
filters articles for significance, then `news_editor` rewrites
them as briefing notes.

> **Note.** Running a chained-office network is currently easiest
> from a cloned dissyslab repository. The pip-install experience
> for networks is being improved.

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
dsl build dissyslab/gallery/org_two_office_news/news_monitor/
dsl build dissyslab/gallery/org_two_office_news/news_editor/
python -m dissyslab.office.make_network dissyslab/gallery/org_two_office_news/
python3 -m dissyslab.gallery.org_two_office_news.app
```

Briefings stream to your terminal. Each one passed through four
agents in two offices.

## What's new in an office that gets chained

Inside a chainable office, two extra lines appear at the top of
`office.md`:

```
Inputs: article_in
Outputs: article_out
```

These are the office's external mailboxes. `article_in` is where
messages from outside arrive; `article_out` is where messages
leave. In `Connections:`, the input behaves like a source and the
output behaves like a sink:

```
article_in's destination is Alex.       ← incoming message goes to Alex
Morgan's output is article_out.         ← Morgan's mailbox 'output' leaves the office
```

A standalone office (one that isn't chained) has no `Inputs:` or
`Outputs:` — its sources and sinks are real RSS feeds and real
files. A chainable office replaces those with named ports.

## The network spec

The network is a separate file, `network.md`, that lives in a
folder above the offices. It looks like an `office.md` but its
"agents" are whole offices:

```
# Network: two_office_news

Sources: al_jazeera(max_articles=5), bbc_world(max_articles=5)
Sinks: intelligence_display

Offices:
  news_monitor is gallery/org_two_office_news/news_monitor
  news_editor is gallery/org_two_office_news/news_editor

Connections:
al_jazeera's destination is news_monitor's article_in.
bbc_world's destination is news_monitor's article_in.
news_monitor's article_out is news_editor's article_in.
news_editor's article_out is intelligence_display.
```

Each office is referenced by its folder. The network only knows
each office's inputs and outputs — never its agents, never its
roles. You could replace `news_monitor` with a totally different
office that accepts `article_in` and produces `article_out`, and
nothing else in the network would change.

## The pattern, in a sentence

A chainable office declares external `Inputs:` and `Outputs:` at
the top of its `office.md`. A `network.md` wires offices together
by name, treating each one as a black box. The org chart at the
network level shows how offices connect; the org chart inside
each office is hidden from the network.

## Build and run, step by step

Chained offices need an extra build step compared to a single
office, because each sub-office is compiled independently first.

**Step 1 — compile each sub-office.** This produces an `app.py`
inside each office folder:

```bash
dsl build path/to/network/office_a/
dsl build path/to/network/office_b/
```

**Step 2 — compile the network.** This stitches the sub-offices
together and produces a top-level `app.py`:

```bash
python -m dissyslab.office.make_network path/to/network/
```

**Step 3 — run the network.**

```bash
python3 -m path.to.network.app
```

(Replace the slashes with dots, drop the trailing `/app.py`. So
`gallery/org_two_office_news/` becomes
`gallery.org_two_office_news.app`.)

## Variations

**Swap one office for another.** Because each office is a black
box, you can build a replacement office with the same `Inputs:`
and `Outputs:` and drop it in by changing one line of `network.md`:

```
Offices:
  news_monitor is gallery/my_alternative_monitor   ← was: org_two_office_news/news_monitor
  news_editor is gallery/org_two_office_news/news_editor
```

The other office, and every agent inside both offices, is
unaffected.

**Add a third office.** Append it after the second:

```
Offices:
  news_monitor is gallery/org_two_office_news/news_monitor
  news_editor is gallery/org_two_office_news/news_editor
  translator is gallery/my_translator

Connections:
news_editor's article_out is translator's article_in.
translator's article_out is intelligence_display.
```

**Build a library of reusable offices.** Once an office is
black-boxed by its `Inputs:` and `Outputs:`, you (or a teammate)
can paste it into any network with no changes to its internals.
Job descriptions in `roles/` and the org chart in `office.md` stay
private to that office.

## When *not* to reach for this

If your whole pipeline fits comfortably in one `office.md`, keep
it there. Chaining is worth the extra build step when:

- You want to test a chunk of the pipeline in isolation.
- You want to swap one chunk for an alternative implementation.
- The pipeline has grown to more than five or six agents and
  reading the org chart has become a chore.

For everything else, one office is simpler.

## See also

- [`org_two_office_news` in the gallery](https://github.com/kmchandy/DisSysLab/tree/main/dissyslab/gallery/org_two_office_news)
  — the working example used in this recipe, with all four agents
  and both office org charts.
- [Sources and sinks reference](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
  — every shipped source and sink, for the network's outer layer.
- [How to filter for a topic](filter-for-a-topic.md) — the simpler
  one-office pattern that's enough for most classroom use.
- [How to write a custom role](write-a-custom-role.md) — for
  designing the job descriptions inside each office.
