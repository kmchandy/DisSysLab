# How to filter for a topic

**Goal.** An office that watches a stream of items — news
articles, tweets, emails, job postings — and only forwards the
ones about a topic you care about. Everything else goes to a file
you can spot-check later.

## Run a working example

DisSysLab ships with a one-agent filter office. Try it:

```bash
dsl init org_news_filter my_filter
cd my_filter
dsl run .
```

Articles about the Americas stream to your terminal; everything
else lands in `filtered_output.jsonl`. Press `Ctrl+C` to stop.
Look at `filtered_output.jsonl` to ensure that it contains
articles that are not about the Americas.

## Change the topic

Open `roles/filter.md`. The topic is right at the top:

```
Your job is to decide if each article is about the americas:
canada, usa, brazil, ..
```

Rewrite it for whatever you care about:

```
Your job is to decide if each article discusses developments in
artificial intelligence — new models, research breakthroughs,
or major product launches.
```

Save and run `dsl run .` again. No rebuild — just edit and re-run.

## The pattern, in a sentence

A filter is an agent whose job is to send each incoming item to
one of two destinations: `keep` or `discard`. The job description
in the role spells out the criteria for `keep` and `discard`.
The org chart in `office.md` shows how the mailboxes `keep` and `discard`
are connected to agents including sinks.

## The minimal office, from scratch

If you'd rather build from scratch instead of editing the gallery
example, here are the two files you need.

`roles/filter.md`:

```
# Role: filter

You are a content filter. For each item you receive, decide if it
matches the topic below. Send matches to keep. Send everything
else to discard.

Topic: [DESCRIBE YOUR TOPIC IN ONE OR TWO SENTENCES]
```

`office.md`:

```
# Office: my_filter

Sources: bbc_world(max_articles=10, poll_interval=600)
Sinks: console_printer, jsonl_recorder(path="discards.jsonl")

Agents:
Felix is a filter.

Connections:
bbc_world's destination is Felix.
Felix's keep is console_printer.
Felix's discard is jsonl_recorder.
```

Run it with `dsl run .`.

## Variations

**Tighter or looser criteria.** If too many irrelevant items slip
through, give Felix sharper instructions:

```
Topic: articles about climate change. Strictly: the article must
discuss specific climate-related research, policy, or events.
Passing mentions in unrelated articles do not count.
```

**Two filters in series.** Filter on geography first, then on
topic. Each filter is its own agent with its own role file. Wire
the `keep` of the first filter into the input of the second
filter.

**More than two buckets.** Replace `discard` with
finer destinations (e.g., `routine`, `archive`). The job description
in the filter role spells out the mailboxes to which each item goes.
The org chart in `office.md` shows the connections of the mailboxes
to the inputs of agents including sink agents.

## See also

- [Sources and sinks reference](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
  — every source you can plug in as input to your filter, every
  sink for routing `keep` and `discard`.
- [`org_news_filter` in the gallery](https://github.com/kmchandy/DisSysLab/tree/main/dissyslab/gallery/org_news_filter)
  — the working example used in this recipe.
- [How to add a new RSS source](add-an-rss-source.md) — for
  filtering a feed that isn't yet shipped with DisSysLab.
- [How to chain offices](chain-offices.md) — pipe filtered output
  into a follow-up office that summarizes or rewrites.
- [How to send messages to the outside world](send-messages-outside.md)
  — route `keep` to email, Slack, or a file.
