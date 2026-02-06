"""
Simple Pipeline Example - Data Transformation Network

This example demonstrates the basic pattern for building distributed systems:
1. Write ordinary Python functions
2. Create nodes of a network by wrapping the functions
3. Specify a network as a list of edges. Each edge is directed from a node to a node.
4. Run the network

Data flow: ["hello", "world"] → UPPERCASE → ADD "!!" → results
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Sink, Transform

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

list_source = ListSource(items=["hello", "world"])


def convert_to_upper_case(text):
    """Function used in a transform node."""
    return text.upper()


def add_suffix(text, suffix):
    """Function used in a transform node."""
    return text + suffix


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

# Source node
source = Source(
    fn=list_source.run,
    name="list_source"
)

# Transform node: (function convert_to_upper_case has no parameters)
uppercase = Transform(
    fn=convert_to_upper_case,
    name="uppercase"
)

# Transform node: (function add_suffix has parameters)
add_emphasis = Transform(
    fn=add_suffix,
    params={"suffix": "!!"},
    name="add_emphasis"
)

# Sink node: Collect results
results = []
collector = Sink(
    fn=results.append,
    name="collector"
)


# ==============================================================================
# STEP 3: Build and Run the Network
# ==============================================================================
# Specify the network as a list of edges. Each edge (x, y) connects the output
# of node x to the input of node y.

# Define a network g: source → uppercase → add_emphasis → collector
g = network([
    (source, uppercase),          # hello → HELLO
    (uppercase, add_emphasis),    # HELLO → HELLO!!
    (add_emphasis, collector)     # HELLO!! → results list
])

# Run network g. Nodes execute concurrently.
g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print(f"Results: {results}")
    assert results == [
        "HELLO!!", "WORLD!!"], f"Expected ['HELLO!!', 'WORLD!!'], got {results}"
    print("✓ Pipeline completed successfully!")
