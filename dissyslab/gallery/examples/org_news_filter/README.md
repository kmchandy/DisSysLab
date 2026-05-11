# News Filter

The simplest possible office — a single agent named Felix who sorts
incoming articles. Articles about the Americas go to the console;
everything else goes to a file and is dropped from the live display.

**Tags:** rss, single-agent, filter

## What it does

```
al_jazeera ─┐
             ├→  Felix  ─→  console            (articles about the Americas)
bbc_world  ─┘          └→  filtered_output.jsonl  (everything else)
```

- Polls Al Jazeera and BBC World for the latest articles
- Felix (a filter) decides whether each article is about the Americas
- Articles about the Americas go to your terminal; the rest go to
  `filtered_output.jsonl` for later inspection

## Files in this office

```
news_filter/
    office.md          ← the org chart: sources, agent, sinks
    roles/
        filter.md      ← what Felix does, in plain English
```

A `filtered_output.jsonl` file appears in the folder once you run
the office; it holds the articles Felix discarded.

## Try it

```bash
dsl init org_news_filter my_filter
cd my_filter
dsl run .
```

The compiler shows you the routing and asks "Does this look right?"
Say yes and your office starts.

## Make it yours

**Change the filter topic.** Open `roles/filter.md` and change the
geography to anything you care about:

```
Your job is to decide if each article is about climate change or
renewable energy.
```

**Change the sources.** In `office.md`, replace `al_jazeera` and
`bbc_world` with any sources from the framework:

```
Sources: hacker_news(max_articles=5), techcrunch(max_articles=5)
```

**Add more agents.** Once an article passes Felix's filter, you could
send it to a second agent that summarizes it, rates its significance,
or translates it. That's the next example —
[Intelligence Briefing](../org_intelligence_briefing/).

**More to swap in.** See [`docs/SOURCES_AND_SINKS.md`](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
for the full list of sources and sinks shipped with the framework.

**Recipes.**

- [How to filter for a topic](https://github.com/kmchandy/DisSysLab/blob/main/docs/recipes/filter-for-a-topic.md)
  — walks through this office's pattern step by step.
- [How to send messages to the outside world](https://github.com/kmchandy/DisSysLab/blob/main/docs/recipes/send-messages-outside.md)
  — uses this office's `console_printer` + `jsonl_recorder` pair
  as the starting point.

---

## The role

Felix's job description, in plain English:

```
# Role: filter

You are a content filter who receives news articles and sends
articles to a keeper or a discard.

Your job is to decide if each article is about the americas: canada, usa, brazil, ..
If the article is about the americas, send to keeper.
Otherwise send to discard.
```

An office may have many agents with the same role — for example,
many editors and many copywriters. A role is defined once, in
`roles/<role>.md`. Each agent in `office.md` is then declared with
"X is a <role>".

## The org chart

The whole office, in one file:

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

## What you built

Felix runs in his own thread, processing articles the moment they
arrive. This is a distributed system running on your laptop — one
agent, two sources streaming concurrently, two sinks recording the
results. Later examples scale this up to multiple agents, feedback
loops, and offices wired into networks.
