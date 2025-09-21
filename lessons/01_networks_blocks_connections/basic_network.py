# lessons.01_networks_blocks_connections.basic_network.py

from dsl.core import Network
from dsl.ops.sources.common_sources import from_list
from dsl.ops.transforms.common_transforms import uppercase
from dsl.ops.sinks.common_sinks import record_to_list
from dsl.blocks.source import Source
from dsl.blocks.transform import Transform
from dsl.blocks.sink import Sink


def basic_network():
    results = []  # Holds results sent to sink

    net = Network(
        blocks={
            "source": Source(fn=from_list(items=['hello', 'world'])),
            "upper_case": Transform(fn=uppercase),
            "sink": Sink(fn=record_to_list(results)),
        },
        connections=[
            ("source", "out", "upper_case", "in"),
            ("upper_case", "out", "sink", "in"),
        ],
    )

    net.compile_and_run()
    print("Results:", results)
    assert results == ['HELLO', 'WORLD']


if __name__ == "__main__":
    basic_network()
