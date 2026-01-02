# modules/ch02_sources/rss_NASA.py

from dsl import network
from dsl.connectors.rss_in import RSS_In           # << simplified connector
from .live_kv_console import kv_live_sink             # pretty-print messages live

# ────────────────────────────────────────────────────────────────────────────
# Configure the RSS source (connector)
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
# Connect source → sink (i.e rss.run  → kv_live_sink) and run the network
# ────────────────────────────────────────────────────────────────────────────

g = network([(rss.run, kv_live_sink)])
g.run_network()
