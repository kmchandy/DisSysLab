# 2.3 • Source: Social Media (e.g Bluesky) Feeds

This page just shows you how to use a **connector** to a social media feed.
This example uses the feed **Bluesky Jetstream**. You can build connectors to
many social media feeds; however, several social media organizations have
regulations on how their social media feeds are accessed, and you are responsible 
for following the regulations.

Connectors are described in module 7.

---
## What you’ll do

Run a tiny script that listens to the **Bluesky Jetstream** and prints posts.

---

## Setup (once)

```bash
pip install websockets rich
```


## The Bluesky Feed Demo

```python
# modules.ch02_sources.feed_from_posts

from dsl import network
# dsl.connectors has connectors to different sources of data and sinks
# including consoles. jetstream_in connects to the Bluesky Jetstream feed.
from dsl.connectors.jetstream_in import Jetstream_In
# simple sink that prints dicts live
from dsl.connectors.live_kv_console import kv_live_sink

# ----------------------------------------------------
# 1) Configure the Jetstream source
# ----------------------------------------------------
# Key params:
# - wanted_collections: tuple of Bluesky NSIDs to pass through.
#     Common examples:
#       "app.bsky.feed.post"   -> posts
#       "app.bsky.feed.like"   -> likes
# - life_time: stop after N seconds (handy for short demos).
# - max_num_posts: stop after N posts (safety guard for lessons).

jetstream = Jetstream_In(
    wanted_collections=("app.bsky.feed.post",),  # filter to posts only
    life_time=20,          # run ~20 seconds then stop (adjust as needed)
    max_num_posts=25      # or stop after 100 posts, whichever comes first
)

# ----------------------------------------------------
# 2) Source function, from_jetstream(), is an iterator
# ----------------------------------------------------
# Yields a dict per post.


def from_jetstream():
    for item in jetstream.run():
        # item is typically a dict with nested fields.
        # We trim the dict for the demo.
        yield {
            "uri": item.get("uri"),
            "author": item.get("author_handle") or item.get("author"),
            "text": item.get("text"),
            "created_at": item.get("created_at"),
        }


def print_sink(v):
    print(v)
    print("-" * 40)


# ----------------------------------------------------
# 3) Connect nodes and run
# ----------------------------------------------------
g = network([(from_jetstream, print_sink)])
g.run_network()
```

## Run the demo
Execute the following from the DisSysLab directory:
```bash
python -m modules.ch02_sources.feed_from_posts
```

You will see a growing list of items like:
```bash
----------------------------------------
author
@alice.bsky.social

text
Just launched a new project! 🚀

uri
at://did:plc:.../app.bsky.feed.post/3k2...

indexedAt
2024-05-12T18:42:03.000Z

```

Newest items appear at the top.

If nothing shows immediately, wait a few seconds for the site to be polled
and return values.

## Parameters you can modify

- poll_seconds: how often to check the feed (e.g., 4 seconds).

- life_time: how long to run before stopping (e.g., 20 seconds).

- fetch_page: set to True to also fetch the linked article text.

- output_keys: choose which fields to print (keep it small for readability).

## 👉 Next
[**Poll from REST sites** Poll numeric data from REST →](./README_4_REST.md)

