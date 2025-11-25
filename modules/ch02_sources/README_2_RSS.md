# 2.2 • RSS feeds

This page just shows you how to use a **connector** to an RSS (Real Simple Syndication) feed to create a source of data.
An RSS feed checks a source of data, such as a website, regularly and displays new its in the feed. 

---

## What you’ll do

Run a tiny script that reads NASA’s public RSS feed and prints items.

---

## Setup (once)

```bash
pip install feedparser requests beautifulsoup4 rich
```

## The RSS Feed Demo

```python
# modules/ch02_sources/rss_NASA_simple_demo.py

import time
from dsl import network
from dsl.connectors.rss_in import RSS_In           # << simplified connector
from .live_kv_console import kv_live_sink             # pretty-print messages live

# ────────────────────────────────────────────────────────────────────────────
# 1) Configure the RSS source (connector)
# ────────────────────────────────────────────────────────────────────────────
# Key knobs:
#   url           – which RSS/Atom feed to poll (NASA)
#   fetch_page    – also fetch the linked article and extract plain text
#   output_keys   – keep only these fields from each item/page
#   poll_seconds  – how often to check the feed (watchable pace)
#   life_time     – how long to run before stopping (seconds)
rss = RSS_In(
    url="https://www.nasa.gov/feed/",
    fetch_page=True,
    output_keys=["title", "link", "page_text"],
    poll_seconds=4,
    life_time=20,
)

# ────────────────────────────────────────────────────────────────────────────
# 2) Source function: turn the connector into a generator
# ────────────────────────────────────────────────────────────────────────────
# A source function is a zero-argument callable that yields dicts.
# We keep only "title" and "page_text" to keep the console tidy.


def from_rss():
    for news_item in rss.run():     # iterator of dicts from the connector
        yield {
            "title": news_item.get("title"),
            "page_text": news_item.get("page_text"),
        }
        # Tiny pause so items don't scroll too fast during the demo
        time.sleep(0.1)

# ────────────────────────────────────────────────────────────────────────────
# 3) Connect source → sink and run the network
# ────────────────────────────────────────────────────────────────────────────


def print_sink(msg):
    print(msg)
    print("-" * 40)


g = network([(from_rss, print_sink)])

g.run_network()



```

## Run the demo
Execute the following from the DisSysLab directory.

```bash
python -m modules.ch02_sources.rss_NASA_simple_demo
```

You will see a growing list of items like:
```bash
----------------------------------------
title
NASA Updates on [recent story title]

link
https://www.nasa.gov/...

summary
A short blurb from the feed...

page_text
(First part of the article text, if enabled)
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
[**Social Media** sources →](./README_3_posts.md)