# examples.jetstream_demo

from dsl.connectors.jetstream_in import Jetstream_In
import time
import json
from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
from .live_kv_console import kv_live_sink


jetstream = Jetstream_In(
    wanted_collections=("app.bsky.feed.post",),  # posts
    life_time=20,
    max_num_posts=100
)


def from_jetstream():
    jetstream_results = jetstream.run()
    for item in jetstream_results:
        print(f"item = {item}")
        yield item


def to_result(v):
    result.append(v)


result = []
g = network([(from_jetstream, to_result)])
g.run_network()

if __name__ == "__main__":
    g.run_network()
    for item in result:
        print(f"{item}")
        print(f"")
