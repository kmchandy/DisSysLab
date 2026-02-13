"""
Simple Pipeline Example - Data Transformation Chain

This example demonstrates a data processing pipeline:
1. Source generates data
2. Multiple transforms process data in sequence
3. Sink collects final results

Data flow: ["hello", "world"] → UPPERCASE → ADD "!!" → results
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Sink, Transform

# ==============================================================================
# STEP 1: Write Ordinary Python Functions
# ==============================================================================
# These are regular Python functions - they know nothing about the network.


def get_items_from_list():
    """Generate items from a list, one at a time."""
    items = ["hello", "world"]
    source = ListSource(items=items)
    return source.run()


def convert_to_upper_case(text):
    """Convert text to uppercase."""
    return text.upper()


def add_emphasis(text):
    """Add emphasis markers to text."""
    return text + "!!"


def collect_result(item):
    """Collect an item into the results list."""
    results.append(item)


# ==============================================================================
# STEP 2: Wrap Functions in Network Blocks
# ==============================================================================
# Transform ordinary functions into network nodes.

# Source block: Generates data
source = Source(
    fn=get_items_from_list,
    name="list_source"
)

# Transform blocks: Process data in sequence
uppercase = Transform(
    fn=convert_to_upper_case,
    name="uppercase"
)

emphasize = Transform(
    fn=add_emphasis,
    name="emphasize"
)

# Sink block: Collects results
results = []
collector = Sink(
    fn=collect_result,
    name="collector"
)


# ==============================================================================
# STEP 3: Build and Run the Network
# ==============================================================================
# Connect blocks to define data flow, then run the network.

# Define the pipeline: source → uppercase → emphasize → collector
g = network([
    (source, uppercase),        # "hello" → "HELLO"
    (uppercase, emphasize),     # "HELLO" → "HELLO!!"
    (emphasize, collector)      # "HELLO!!" → results
])

# Run the network (blocks execute concurrently)
g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print(f"Results: {results}")
    assert results == [
        "HELLO!!", "WORLD!!"], f"Expected ['HELLO!!', 'WORLD!!'], got {results}"
    print("✓ Pipeline completed successfully!")
