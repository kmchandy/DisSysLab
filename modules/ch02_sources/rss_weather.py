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
