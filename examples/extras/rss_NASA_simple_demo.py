# dsl.examples.rss_demo
#
# Goal:
# - Pull recent items from an RSS feed: NASA in this example.
# - Optionally fetch each article’s web page.
# - Stream a small dict (title + page_text) to a live console sink.
#
# How to run (from your repo root):
#   python -m dsl.examples.rss_demo
#
# What you should learn:
# - A "Source" that emits dictionaries (one per news item).
# - A simple generator function (from_rss) that yields messages.
# - A "Sink" that displays key/value pairs live in the console.
# - How to change the feed URL and output fields.
#
# Note:  Check use of RSS feeds. Some feeds are commercial and have limits
# on use. NASA's feed is public domain.

import time
# dsl.connectors has connectors to different sources of data and sinks
# including consoles.
from dsl.connectors.rss_in import RSS_In
# kv_live_sink receives dicts and prints key-value pairs in a live-updating table.
from dsl.connectors.live_kv_console import kv_live_sink
from dsl import network


# -------------------------------
# 1) Configure the RSS source
# -------------------------------
# RSS_In parameters used here:
# - url: RSS feed URL to poll.
# - emit_mode="item": emit one message as each RSS item is read.
#   (Alternative: "batch" emits **lists** of items at time/size intervals.)
# - batch_size=2: maximum items to emit together (relevant for "batch" and not "item").
# - batch_seconds=4: time-based flush  for "batch".
# - fetch_page=True: also fetch and parse the linked web page for each item.
# - output_keys: which fields to keep from each item/page.
# - life_time=5: stop after ~5 seconds. Normally run forever.
#
# Other useful RSS_In controls which are defaults in RSS_In
# - poll_seconds=15.0  # how often to poll the feed
# - emit_mode="batch"  # default is batch; we override to "item" here
# - since=None         # start point; connector handles dedupe by id/guid/link

rss = RSS_In(
    # <-- You can change this to any RSS feed
    url="https://www.nasa.gov/feed/",
    emit_mode="item",                        # per-item emissions for a steady trickle
    batch_size=1,                            # ok to leave as-is for "item" mode
    batch_seconds=4,                         # ok to leave as-is for "item" mode
    fetch_page=True,                         # also fetch the article page text
    output_keys=["title", "link", "page_text"],  # keep only these fields
    life_time=5                              # short demo run; increase for longer
)

# -------------------------------
# 2) Source function: from_rss()
# -------------------------------
# This function turns the connector into a generator that yields one dict per item.
# We intentionally yield only {"title", "page_text"} to keep the console output tidy.


def from_rss():
    news_items = rss.run()  # returns an iterator/generator of dictionaries
    for news_item in news_items:
        # Safely pick fields; .get() avoids KeyError if a key is missing.
        yield {
            "title": news_item.get("title"),
            "page_text": news_item.get("page_text"),
        }
        # Tiny sleep so that you can watch items flow in live
        time.sleep(0.05)


# ----------------------------------------------------------
# 3) Wire source (from_rss) -> sink (kv_live_sink) and run
# -----------------------------------------------------------
# network() accepts a list of edges. Each edge is (source_callable, sink_callable).
# kv_live_sink prints incoming dicts in a key:value table that updates in place.
g = network([(from_rss, kv_live_sink)])
g.run_network()  # blocking call until the source finishes (life_time reached)
