# dsl.examples.simple_entity_extractor

from dsl import network
from dsl.ops.transforms.simple_entity_extractor import extract_entity

# Define functions.


def src():
    for x in messages:
        yield x


results = []


def snk(v):
    results.append(v)


messages = [
    {"text": "Obama was the President of the USA."},
    {"text": "Charles is the King of the UK."},
]

# Define the network
g = network([(src, extract_entity), (extract_entity, snk)])
g.run_network()

if __name__ == "__main__":
    for result in results:
        print(result)
