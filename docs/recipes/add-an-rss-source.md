# Read any RSS feed

**Goal.** Bring a feed DisSysLab does not name into an office.

Most news sites, blogs, podcasts and journals publish an RSS or Atom feed.
The `rss` source reads any of them:

```
sources:
    lab_blog: rss(url="https://example.com/feed.xml", name="lab_blog", max_articles=5)
```

- `url` is the feed's address. Look for an RSS icon, a link called "Feed"
  or "RSS", or try adding `/feed` or `/rss` to the site's address.
- `name` is the value of the `source` field of each message, so you can
  tell feeds apart downstream.
- `max_articles` caps how many items one run reads; `poll_interval`
  (seconds) makes the source keep checking for new items until you stop
  the office with Ctrl-C.

## Try it

In any office, add the source and connect it. In `org_news_filter`
([filter-for-a-topic.md](filter-for-a-topic.md)):

```
sources:
    al_jazeera(max_articles=2)
    bbc_world(max_articles=2)
    tech: rss(url="https://techcrunch.com/feed/", name="techcrunch", max_articles=2)

connections:
    al_jazeera, bbc_world, tech -> Felix -> Rex
```

```bash
dsl check .
dsl run .
```

## What each item becomes

Every feed, named or not, produces messages with the same five fields, so
a role written for one feed works on all of them:

```python
{
    "source":    "techcrunch",
    "title":     "...",        # the item's title
    "text":      "...",        # its summary or description
    "url":       "https://...",
    "timestamp": "...",
}
```

## If a feed gives nothing

The run ends with a message naming the feed and the reason, for example
`0 entries from https://... feed parse error`. The usual causes: the URL
is the site's page rather than its feed, or the site blocks automated
readers. Open the URL in a browser: a feed shows as XML.

The named feeds (`bbc_world`, `npr_news`, `hacker_news` and the rest; see
`dsl grammar sources`) are `rss` with the URL filled in.
