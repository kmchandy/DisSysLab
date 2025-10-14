# examples.jetstream_demo
from dsl import network
# dsl.connectors has connectors to different sources of data and sinks
# including consoles. jetstream_in connects to the Bluesky Jetstream feed.
from dsl.connectors.jetstream_in import Jetstream_In
# simple sink that prints dicts live
from dsl.connectors.live_kv_console import kv_live_sink

# ----------------------------------------------------
# 1) Configure the Jetstream source
# ----------------------------------------------------
# Key params:
# - wanted_collections: tuple of Bluesky NSIDs to pass through.
#     Common examples:
#       "app.bsky.feed.post"   -> posts
#       "app.bsky.feed.like"   -> likes
#       "app.bsky.graph.follow"-> follows
# - life_time: stop after N seconds (handy for short demos).
# - max_num_posts: stop after N posts (safety guard for lessons).

jetstream = Jetstream_In(
    wanted_collections=("app.bsky.feed.post",),  # filter to posts only
    life_time=2,          # run ~2 seconds then stop (adjust as needed)
    max_num_posts=10      # or stop after 10 posts, whichever comes first
)

# ----------------------------------------------------
# 2) Source function: from_jetstream()
# ----------------------------------------------------
# Returns a clean dict per post so the console output is readable
# and students see the “shape” of a message clearly.


def from_jetstream():
    for item in jetstream.run():
        # item is typically a dict with nested fields. We trim the most
        # useful bits for a quick demo; keep .get() to avoid KeyErrors.
        yield {
            "uri": item.get("uri"),
            "author": item.get("author_handle") or item.get("author"),
            "text": item.get("text"),
            "created_at": item.get("created_at"),
        }


# ----------------------------------------------------
# 3) Connect nodes and run
# ----------------------------------------------------
g = network([(from_jetstream, kv_live_sink)])
g.run_network()
