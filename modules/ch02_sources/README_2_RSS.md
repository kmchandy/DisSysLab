# 2.2 • RSS feeds

This page just shows you how to use a **connector** to an RSS (Real Simple Syndication) feed to create a source of data.
An RSS feed checks a source of data regularly and displays new values in its in the feed.
You may have to wait for several seconds to the see output.

---

## What you’ll do

Create a network with two agents. One agent gets a stream of documents from NASA’s public RSS feed. The other agent prints the stream. Later we will work with networks that get RSS feeds and analyze the RSS stream.

---

## Setup (once)

```bash
pip install feedparser requests beautifulsoup4 rich
```

## The RSS Feed Demo

```python
# modules/ch02_sources/rss_NASA_simple_demo.py

from pprint import pprint
import time
from dsl import network
from dsl.connectors.rss_in import RSS_In           # << simplified connector
from .live_kv_console import kv_live_sink             # pretty-print messages live

# ────────────────────────────────────────────────────────────────────────────
# 1) Configure the RSS source (connector)
# ────────────────────────────────────────────────────────────────────────────
# Key parameters:
#   url           – which RSS/Atom feed to poll (NASA)
#   fetch_page    – also fetch the linked article and extract plain text
#   output_keys   – keep only these fields from each item/page
#   poll_seconds  – how often to check the feed (watchable pace)
#   life_time     – how long to run before stopping (seconds)
rss = RSS_In(
    url="https://www.nasa.gov/feed/",
    fetch_page=True,
    output_keys=["title", "link", "summary"],
    poll_seconds=4,
    life_time=20,
)

# ────────────────────────────────────────────────────────────────────────────
# 3) Connect source → sink and run the network
# ────────────────────────────────────────────────────────────────────────────

def print_sink(msg):
    print()
    pprint(msg)
    print()
    print("-" * 40)


g = network([(rss.run, print_sink)])
g.run_network()

# Experiment with the following:
# • Change the feed URL to any RSS/Atom you like.
# • Set fetch_page=False for speed and fewer deps.
# • Edit output_keys and the yielded dict to show different fields.
# • Change life_time (or None to run until Ctrl-C).

```

## Run the demo
Execute the following from the DisSysLab directory. Remember to install the services (eg feedparser) required to run the demo.

```bash
pip install feedparser requests beautifulsoup4 rich
```

## 💻 dsl program
```
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

[**Social Media**](./README_3_posts.md)

You can also see [several examples of RSS feeds](./rss_general.py)