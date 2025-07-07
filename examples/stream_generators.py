import tempfile
import random
from typing import Optional, Union, Callable, Any
from dsl.core import Network, StreamToList
from dsl.stream_generators import StreamGenerator, GenerateNumberSequence


def random_integers(count: int, lo: int, hi: int):
    """
    Yields a sequence of `count` random integers in the range [lo, hi].

    Example:
        for value in random_integers(3, 10, 20):
            print(value)  # could print 14, 11, 19
    """
    for _ in range(count):
        yield random.randint(lo, hi)


net = Network(
    blocks={
        'gen': StreamGenerator(
            generator_fn=random_integers,
            kwargs={'count': 5, 'lo': 10, 'hi': 20}
        ),
        'receiver': StreamToList(),
    },
    connections=[('gen', 'out', 'receiver', 'in')]
)

net.run()
print("Generated random integers:", net.blocks['receiver'].saved)


def from_list(items):
    for item in items:
        yield item


net = Network(
    blocks={
        'gen': StreamGenerator(
            generator_fn=from_list,
            kwargs={'items': [
                "What is the capital of France?",
                "What are the two most important events in French history?",
                "What did Joan of Arc do?"
            ]
            }
        ),
        'receiver': StreamToList(),
    },
    connections=[('gen', 'out', 'receiver', 'in')]
)
net.run()
print("Items:", net.blocks['receiver'].saved)


def lines_from_file(filename):
    with open(filename) as f:
        for line in f:
            yield line.strip()


with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
    tmp.write("apple\nbanana\ncarrot\n")
    tmp_path = tmp.name  # Save the path before closing

net = Network(
    blocks={
        'gen': StreamGenerator(
            generator_fn=lines_from_file,
            kwargs={'filename': tmp_path}
        ),
        'receiver': StreamToList(),
    },
    connections=[('gen', 'out', 'receiver', 'in')]
)
net.run()
print("File Contents:", net.blocks['receiver'].saved)
