# lessons.01_networks_blocks_connections.basic_network.py

from dsl import network


def from_list(items=["hello", "world"]):
    """Generator that yields items from a list."""
    for item in items:
        yield item


def uppercase(item):
    """Function to convert a string to uppercase."""
    return item.upper()


result_list = []


def to_list(item, results=result_list):
    """Function to record items in a list."""
    results.append(item)


g = network([(from_list, uppercase), (uppercase, to_list)])

g.run_network()
print(result_list)  # Output: ['HELLO', 'WORLD']
