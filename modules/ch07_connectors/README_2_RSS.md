# 2.2 RSS Sources 

This module shows how to stream items from an RSS/Atom feed using a **minimal** connector: `RSS_In`.  
It’s example-first on purpose: copy it, tweak two lines, and you’ve got your own source.

---

## `RSS_In`: A connector for RSS is:

A tiny connector that:
- polls an RSS/Atom URL every _N_ seconds,
- yields **one dict per new entry** (item mode only),
- optionally fetches the linked page to attach plain `page_text`,
- can prune fields via `output_keys`.

A source has a `run` function (a zero-argument iterator) which yields dicts.  

---

## Requirements

```bash
pip install feedparser requests beautifulsoup4 rich
```

- feedparser — parse RSS/Atom feeds

- requests + beautifulsoup4 — (optional) fetch + extract article text

- rich — pretty console output for the live sink

## Run the example

We’ll use NASA’s public site feed.

```bash
python -m modules.ch02_sources.rss_NASA_simple_demo
```

After a few seconds you should see a growing list of items: title + (extracted text if enabled).
If nothing shows extend life_time in the demo.

## What it emits

Each item is a small dict (exact keys depend on output_keys). Typical fields:

- title: entry title

- link: URL to the article/post

- updated: feed’s published/updated text (best-effort)

- summary: short blurb from the feed (if present)

- page_text: optional plain text from the linked article (when fetch_page=True)

- Keep messages small (3–6 fields) so sinks remain readable.

## Customize the demo for your RSS feed

Change just these parameters in rss_NASA_simple_demo:

- Feed URL
Replace url="https://www.nasa.gov/feed/" with any RSS/Atom URL.

- Pace & duration
poll_seconds=4 (check every 4s), life_time=20 (stop after ~20s).
Set life_time=None to run until you stop it.

- Include article text
fetch_page=True to fetch and extract the linked page’s text (bounded by fetch_max_bytes).

- Trim fields
output_keys=["title","link","page_text"] to keep the message tidy.

## Modify to Build your own RSS feed.

- Duplicate the rss_in.py file and rename the class/file (e.g., MyFeed_In).

- Keep the interface: __init__(...) + run() yielding dicts.

- Swap the URL and fields you care about (3–6 fields).

- Add timeouts and a small byte cap (already in the example).

Quick test before connecting in the network:

```python
for i, item in zip(range(3), rss.run()):
    print(item)
```

## Using RSS Feeds

- Set a descriptive User-Agent (with a contact email/URL) to avoid throttling.

- Keep poll_seconds reasonable (seconds, not milliseconds).

- Respect site terms; some feeds rate-limit or change formats.

- **check usage restrictions**

## Troubleshooting

- “Only one item appears”
Your sink might redraw a single live panel. Use a simple print sink to verify multiple items are emitted. e.g. ```def print_sink(v): print(v) ``` instead of using ```kv_live_sink```.

- “Nothing shows up”
• Extend life_time, or try a busier feed.
• Check network/firewall.
• Temporarily set fetch_page=False to isolate feed vs. page fetch issues.

- Garbled text
Linked pages vary. The example uses HTML parsing and strips scripts/styles.

## 👉 Next
[Feeds from Social Media Posts](./README_3_Bluesky.md) with fanout (the output of node is connected to the inputs of two or more nodes) and fanin (the input of a node is connected to the outputs of more than one node).