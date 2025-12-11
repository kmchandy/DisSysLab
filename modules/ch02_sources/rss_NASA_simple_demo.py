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
