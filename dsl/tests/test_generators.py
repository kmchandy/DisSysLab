import tempfile
import unittest
import os
from dsl.core import SimpleAgent, Agent, Network
from dsl.utils.visualize import print_block_hierarchy, print_graph_connections_only
from dsl.block_lib.stream_generators import StreamGenerator, GenerateNumberSequence
from dsl.block_lib.stream_recorders import StreamToList
from dsl.block_lib.stream_generators import GenerateRandomIntegers, GenerateFromList
from dsl.block_lib.stream_generators import GenerateFromFile
# =================================================
#          StreamGenerator                        |
# =================================================
# -------------------------------------------------
# Test 1:


def count_up_to(n):
    for i in range(n):
        yield i


net = Network(
    blocks={
        'gen': StreamGenerator(generator_fn=count_up_to, kwargs={'n': 3}),
        'receiver': StreamToList(),
    },
    connections=[
        ('gen', 'out', 'receiver', 'in')]
)

net.compile()
net.run()
assert net.blocks['receiver'].saved == [0, 1, 2]


# -------------------------------------------------
# Test 2
def yield_words(sentence):
    """
    Yields one word at a time from the given sentence.
    Words are separated by whitespace.
    """
    for word in sentence.split():
        yield word


net = Network(
    blocks={
        'gen': StreamGenerator(
            generator_fn=yield_words,
            kwargs={"sentence": "Today is the first day of the rest of my life!"}
        ),
        'receiver': StreamToList(),
    },
    connections=[
        ('gen', 'out', 'receiver', 'in')]
)

net.compile()
net.run()
assert net.blocks['receiver'].saved == [
    'Today', 'is', 'the', 'first', 'day', 'of', 'the', 'rest', 'of', 'my', 'life!']


# =================================================
#        GenerateNumberSequence                   |
# =================================================

# -------------------------------------------------------------------
# Test 1: Test GenerateNumberSequence. low=0, high=3, step_size=1
net = Network(
    blocks={
        'gen': GenerateNumberSequence(low=0, high=3, step_size=1),
        'receiver': StreamToList(),
    },
    connections=[('gen', 'out', 'receiver', 'in')]
)
net.compile()
net.run()
assert net.blocks['receiver'].saved == [0, 1, 2]

# -------------------------------------------------------------------
# Test 2: Test GenerateNumberSequence. Test low=10, high=40, step_size=10

net = Network(
    blocks={
        'gen': GenerateNumberSequence(low=10, high=40, step_size=10),
        'receiver': StreamToList(),
    },
    connections=[('gen', 'out', 'receiver', 'in')]
)
net.compile()
net.run()
assert net.blocks['receiver'].saved == [10, 20, 30]


# -------------------------------------------------------------------
# Test 3: Test GenerateNumberSequence. Negative numbers low=-10, high=-30, step_size=-10
net = Network(
    blocks={
        'gen': GenerateNumberSequence(low=-10, high=-30, step_size=-10),
        'receiver': StreamToList(),
    },
    connections=[('gen', 'out', 'receiver', 'in')]
)
net.compile()
net.run()
assert net.blocks['receiver'].saved == [-10, -20]

net = Network(
    blocks={
        'gen': GenerateNumberSequence(low=10, high=40, step_size=10),
        'receiver': StreamToList(),
    },
    connections=[('gen', 'out', 'receiver', 'in')]
)
net.compile()
net.run()
assert net.blocks['receiver'].saved == [10, 20, 30]


# =================================================
#      GenerateRandomIntegers                     |
# =================================================

# -------------------------------------------------------------------
# Test 1: Test GenerateNumberSequence. count=3, lo=10, hi=20
net = Network(
    blocks={
        'gen': GenerateRandomIntegers(count=3, lo=10, hi=20),
        'receiver': StreamToList(),
    },
    connections=[('gen', 'out', 'receiver', 'in')]
)
net.compile()
net.run()
assert len(net.blocks['receiver'].saved) == 3


# =================================================
#          GenerateFromList                        |
# =================================================

net = Network(
    name="net",
    blocks={
        'gen': GenerateFromList(items=[
            "What is the capital of France?",
            "What did Joan of Arc do?"
        ]),
        'receiver': StreamToList(),
    },
    connections=[('gen', 'out', 'receiver', 'in')]
)
net.compile()
net.run()
assert net.blocks['receiver'].saved == [
    'What is the capital of France?',
    'What did Joan of Arc do?'
]

# =================================================
#         GenerateFromFile                        |
# =================================================


with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
    tmp.write("apple\nbanana\ncarrot\n")
    tmp_path = tmp.name

try:
    net = Network(
        name="net",
        blocks={
            'gen': GenerateFromFile(filename=tmp_path),
            'receiver': StreamToList(),
        },
        connections=[('gen', 'out', 'receiver', 'in')]
    )
    net.compile()
    net.run()
    assert net.blocks['receiver'].saved == ['apple', 'banana', 'carrot']
finally:
    os.remove(tmp_path)
