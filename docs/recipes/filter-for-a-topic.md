# Filter news for a topic

**Goal.** Watch news feeds and keep only the articles about a topic you
choose. One English role decides whether each article is on the topic;
a router keeps it or drops it.

Needs: an Anthropic key ([GETTING_STARTED.md](../GETTING_STARTED.md),
part 5) and an internet connection.

## 1. Start from the gallery

```bash
dsl init org_news_filter my_filter
cd my_filter
dsl check .
dsl draw .
```

The office:

```
sources:
    al_jazeera(max_articles=2)
    bbc_world(max_articles=2)

sinks:
    console_printer
    discard

agents:
    Felix: topic_filter
    Rex: router(on="on_topic")

connections:
    al_jazeera, bbc_world -> Felix -> Rex
    Rex.yes -> console_printer
    Rex.no -> discard
```

`Felix` adds `on_topic: yes | no` to each article; `Rex` sends `yes` to the
screen and `no` to `discard`. Run it with `dsl run .`.

## 2. Change the topic

Open `roles/topic_filter.md`. The topic is one paragraph:

```
The topic is the Americas: North, Central and South America and the
Caribbean, for example Canada, the United States, Mexico and Brazil.
```

Replace it with yours, with examples on both sides of the line:

```
The topic is artificial intelligence: machine learning, language
models, robotics and the companies that build them. Articles that only
mention a technology company in passing are not on the topic.
```

Nothing else changes: the field is called `on_topic`, not
`about_americas`, so a new topic is an edit to one paragraph. Run again.

## 3. Keep the rejects where you can read them

While you are tuning the topic, you need to see what was dropped: a
filter that drops the wrong articles checks clean and runs clean. Send
the rejects to a file instead of `discard`:

```
sinks:
    console_printer
    rejected: jsonl_recorder(path="rejected.jsonl")

connections:
    al_jazeera, bbc_world -> Felix -> Rex
    Rex.yes -> console_printer
    Rex.no -> rejected
```

`dsl check .`, `dsl run .`, then read `rejected.jsonl`. When every
rejected article deserved it, switch back to `discard`, or keep the file.

## 4. Watch more feeds

Add sources under `sources:` and name them in the fan-in line:

```
sources:
    al_jazeera(max_articles=2)
    bbc_world(max_articles=2)
    npr_news(max_articles=2)
    tech: rss(url="https://techcrunch.com/feed/", name="techcrunch", max_articles=2)

connections:
    al_jazeera, bbc_world, npr_news, tech -> Felix -> Rex
```

`dsl grammar sources` lists the built-in feeds;
[add-an-rss-source.md](add-an-rss-source.md) covers any other feed.

## What to check

- `dsl check .` reports no problems. If it notes that `Rex` has no outbox
  for a value, the role's `out:` line and the router's outboxes disagree.
- The run summary shows `Felix` received as many articles as the sources
  sent. A `failed` count means some replies did not fit `out:`; the first
  one is quoted.
