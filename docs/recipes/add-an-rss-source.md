# How to add a new RSS source

**Goal.** Plug a new feed — a publication, a journal, a subreddit,
a job board — into your office, so that articles from that feed
arrive on the same `Sources:` line as `bbc_world` or `hacker_news`.

This recipe has three steps, in increasing difficulty:

1. **Swap one shipped feed for another.** No code, just edit `office.md`.
2. **Point a shipped feed at a different URL.** One line of Python.
3. **Add a brand-new named feed.** A factory function and a registry entry.

Most students never need step 3. Steps 1 and 2 cover almost every classroom use.

## Run a working example

Start with a one-source office:

```bash
dsl init my_first_office my_feed
cd my_feed
dsl run .
```

Hacker News stories stream into your terminal. Press `Ctrl+C` to stop.

## Step 1 — swap one shipped feed for another

Open `office.md`. The first non-comment line names the source:

```
Sources: hacker_news(max_articles=10, poll_interval=600)
```

DisSysLab ships with ten named RSS feeds. Pick a different one:

```
Sources: bbc_world(max_articles=10, poll_interval=600)
```

The other nine names you can drop in:

```
al_jazeera   bbc_tech     mit_tech_review   nasa_news     npr_news
techcrunch   venturebeat_ai   python_jobs   hacker_news
```

Save and run `dsl run .` again. Same office, different feed.

The full list with descriptions is in
[`docs/SOURCES_AND_SINKS.md`](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md).

## Step 2 — point a shipped feed at a different URL

If the feed you want isn't one of the ten, you can still use it
without touching the framework — by reusing one of the named
feeds and giving it a different URL.

Every named feed is a thin wrapper around `RSSNormalizer`. Make
your own wrapper in a small Python file alongside `office.md`:

`my_source.py`:

```python
from dissyslab.components.sources.rss_normalizer import RSSNormalizer

def my_blog(max_articles=10, poll_interval=600):
    return RSSNormalizer(
        urls=["https://example.com/feed.xml"],
        source_name="my_blog",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )
```

Then write the office directly in Python — construct your `Network`
in code instead of using an `office.md`. The
plain-English `office.md` syntax only knows the ten shipped names;
once you've stepped outside the registry, you're writing the
office in Python instead.

This is the awkward middle case. If you find yourself doing this
often, it's worth doing step 3.

## Step 3 — add a brand-new named feed

Two small edits to the framework. After this, your new name works
on the `Sources:` line of any office, just like `bbc_world`.

**Edit 1 — register a factory function** in
`dissyslab/components/sources/rss_normalizer.py`. Add this at the
bottom, alongside the others:

```python
def my_blog(max_articles=10, poll_interval=None):
    return RSSNormalizer(
        urls=["https://example.com/feed.xml"],
        source_name="my_blog",
        max_articles=max_articles,
        poll_interval=poll_interval,
    )
```

**Edit 2 — register the name** in
`dissyslab/office/utils.py`. Find the `SOURCE_REGISTRY` and add a
line:

```python
SOURCE_REGISTRY = {
    "al_jazeera":      {"type": "rss"},
    "bbc_world":       {"type": "rss"},
    ...
    "my_blog":         {"type": "rss"},   # ← new
    ...
}
```

That's it. Now you can write:

```
Sources: my_blog(max_articles=10, poll_interval=600)
```

in any office.

## The pattern, in a sentence

A source is an agent that generates messages. The org chart in
`office.md` declares which sources flow into which agents. Each
named feed in `Sources:` is a registry entry that produces standard
five-key article dicts (`source`, `title`, `text`, `url`,
`timestamp`). To add a new feed you register a name in two places —
a factory function in `rss_normalizer.py` and a registry entry in
`office/utils.py`.

## Variations

**Multiple feeds into one agent.** List them comma-separated, then
wire each one's destination to the same agent:

```
Sources: bbc_world(max_articles=5),
         al_jazeera(max_articles=5),
         npr_news(max_articles=5)

Connections:
bbc_world's destination is Alex.
al_jazeera's destination is Alex.
npr_news's destination is Alex.
```

Three threads streaming concurrently into one agent. Alex sees
articles in whatever order they happen to arrive.

**One feed into many agents.** Wire one source's destination to
each agent:

```
Connections:
bbc_world's destination is Alex.
bbc_world's destination is Morgan.
```

Each article goes to both. Useful when two agents need to look at
the same item with different job descriptions.

**Polling vs. one-shot.** Omit `poll_interval` and the source
fetches once and stops — handy for quick tests and demos. Set
`poll_interval=600` and it re-fetches every ten minutes, running
forever.

## See also

- [Sources and sinks reference](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
  — every shipped source, every shipped sink.
- [`my_first_office` in the gallery](https://github.com/kmchandy/DisSysLab/tree/main/dissyslab/gallery/my_first_office)
  — the working example used in this recipe.
- [How to filter for a topic](filter-for-a-topic.md) — once you
  have the feed you want, route only the items you care about.
- *(coming next)* How to chain offices — pipe one office's output
  into the input of another.
