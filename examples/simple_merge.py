"""
Simple Merge Example - Merging Multiple Data Streams

This example demonstrates the basic pattern for building distributed systems:
1. Write ordinary Python functions
2. Create nodes of a network by wrapping the functions
3. Specify a network as a list of edges. Each edge is directed from a node to a node.
4. Run the network

Data flow: ["a", "b"] → UPPERCASE → collector
           ["x", "y", "z"] → ADD "!!" → collector
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Sink, Transform

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

list_0 = ListSource(items=["a", "b"])
list_1 = ListSource(items=["x", "y", "z"])


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
source_0 = Source(
    fn=list_0.run,
    name="list_source_0"
)

# Source node
source_1 = Source(
    fn=list_1.run,
    name="list_source_1"
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

# Define a network g: Two sources merge at collector
g = network([
    (source_0, uppercase),        # a, b → A, B
    (source_1, add_emphasis),     # x, y, z → x!!, y!!, z!!
    (uppercase, collector),       # A, B → results
    (add_emphasis, collector),    # x!!, y!!, z!! → results (fanin)
])

# Run network g. Nodes execute concurrently.
g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print(f"Results: {results}")
    assert set(results) == {'A', 'B', 'x!!', 'y!!',
                            'z!!'}, f"Expected {{'A', 'B', 'x!!', 'y!!', 'z!!'}}, got {set(results)}"
    print("✓ Merge completed successfully!")
