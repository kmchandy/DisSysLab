# modules.ch02_sources.feed_from_posts

from dsl import network
# dsl.connectors has connectors to different sources of data and sinks
# including consoles. jetstream_in connects to the Bluesky Jetstream feed.
from dsl.connectors.jetstream_in import Jetstream_In
# simple sink that prints dicts live
from dsl.connectors.live_kv_console import kv_live_sink

# ----------------------------------------------------
# Configure the Jetstream source
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
    life_time=60,          # run ~60 seconds then stop (adjust as needed)
    max_num_posts=100      # or stop after 100 posts, whichever comes first
)

# ----------------------------------------------------
# Source function, from_jetstream(), is an iterator
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


# ------------------------------------------------------
# Create and run network: from_jetstream  →  kv_live_sink
# ------------------------------------------------------
g = network([(from_jetstream, kv_live_sink)])
g.run_network()
