# modules/ch02_sources/rss_general.py

# Contains several examples of RSS feeds.

from pprint import pprint
import time
from dsl import network
from dsl.connectors.rss_in import RSS_In           # << simplified connector
from .live_kv_console import kv_live_sink             # pretty-print messages live


def print_sink(msg):
    print()
    pprint(msg)
    print()
    print("-" * 40)


def rss_demo(url, poll_seconds=4, life_time=20):
    rss = RSS_In(
        url=url,
        fetch_page=True,
        output_keys=["title", "link", "summary"],
        poll_seconds=poll_seconds,
        life_time=life_time,
    )

    g = network([(rss.run, print_sink)])
    g.run_network()

# --------------------------------------------------------------
# EXAMPLES OF RSS FEEDS


# Example usage:
# The Guardian newspaper
rss_demo(url="https://www.theguardian.com/world/rss")

# More examples:
# Security and Exchange Commission filings
# rss_demo(
#     url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&count=40&output=atom"
# )

# Ars Technica technology news
# rss_demo(
#     url="https://feeds.arstechnica.com/arstechnica/index"
# )

# USGS Significant Earthquakes in the Past Day
# rss_demo(
#     url="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.atom"
# )
#
# An important application is to monitor and respond to weather alerts.
# This feed from the US National Weather Service provides active alerts and is used
# by first responders. So, use this feed with care and do not spam it!
# See rss_weather_simple_demo.py
#
# NEXT: SOCIAL MEDIA FEEDS
# go to modules.ch02_sources.README_3_posts.md
