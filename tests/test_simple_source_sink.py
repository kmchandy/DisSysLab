from dsl.blocks.sink import Sink
from dsl.blocks.source import Source
from dsl.core import Network
from dsl.ops.sources.lists import from_list
from dsl.ops.sinks.lists import to_list


def test_simple_source_sink():
    result = []
    net = Network(
        blocks={
            "source": Source(fn=from_list(["hello", "world"])),
            "sink": Sink(fn=to_list(result))
        },
        connections=[
            ("source", "out", "sink", "in")
        ]
    )
    net.compile_and_run()
    print(f"Result: {result}")
    assert result == ["hello", "world"]


if __name__ == "__main__":
    test_simple_source_sink()
