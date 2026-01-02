<!--  modules.ch02_sources.README_Weather.md    -->

# 2.3 • RSS Weather Alerts

This page is an example of generating a stream of weather alerts. This stream is used by first responders. Please use this RSS feed carefully. Do not poll it too frequently.

---

## What you’ll do

Create a network with two agents. One agent gets a stream of alerts from weather.gov. The other agent prints the stream.

---

## Setup (once)

```bash
pip install feedparser requests beautifulsoup4 rich
```

## The RSS Weather Alerts Demo

```python
# modules/ch02_sources/rss_weather.py

from dsl import network
from dsl.connectors.rss_in import RSS_In           # << simplified connector
from .live_kv_console import kv_live_sink             # pretty-print messages live

# ────────────────────────────────────────────────────────────────────────────
# Configure the RSS source (connector)
# ────────────────────────────────────────────────────────────────────────────
# Key parameters:
#   fetch_page    – also fetch the linked article and extract plain text
#   poll_seconds  – how often to check the feed (watchable pace)
#   life_time     – how long to run before stopping (seconds)
rss = RSS_In(
    url="https://api.weather.gov/alerts/active.atom/",
    fetch_page=True,
    poll_seconds=4,
    life_time=10,
)

# ────────────────────────────────────────────────────────────────────────────
# Make network: source → sink, i.e. rss.run → kv_live_sink Then run network
# ────────────────────────────────────────────────────────────────────────────
g = network([(rss.run, kv_live_sink)])
g.run_network()

```

## Run the demo
Execute the following from the DisSysLab directory.

```
python -m modules.ch02_sources.rss_weather
```

You will see a growing list of weather alerts. You may have to wait several few seconds for the site to be polled and return values.

## 👉 Next
Look at [more examples of RSS feeds](./README_RSS_General.md) or jump ahead to streams from posts to [**social media**](./README_posts.md).