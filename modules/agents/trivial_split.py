# modules/agents/trivial_split.py

"""
Two way split
"""

from dsl.blocks import Source, Split, Sink
from dsl import network
from components.sources.natural_numbers_source import NaturalNumberGenerator


def f(msg):
    if msg % 2 == 0:
        return [msg, None]
    else:
        return [None, msg]


# Create source
num_gen = NaturalNumberGenerator(max_count=10)
source = Source(num_gen.run)

# num_outputs must be specified for splitter
odd_even_split = Split(fn=f, num_outputs=2)

# Make sinks
odds, evens = [], []
def append_to_odds(msg): odds.append(msg)
def append_to_evens(msg): evens.append(msg)


# Build network topology
g = network([
    (source, odd_even_split),
    (odd_even_split.out_0, Sink(append_to_evens)),
    (odd_even_split.out_1, Sink(append_to_odds)),
])

# Run the Network

if __name__ == "__main__":
    g.run_network()
    print("Evens:", evens)
    print("Odds:", odds)
