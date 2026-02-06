"""
Merge Synch Example - Synchronized Message Merging

This example demonstrates the merge_synch pattern:
- One source produces messages
- Messages split to two processing paths
- Merge_synch recombines results while maintaining message pairing

Data flow:
                    → uppercase → ──┐
    ["hello"] ─────┤                ├──→ merge_synch → results
                    → length ────────┘

Result: Each word paired with both its uppercase version AND its length.
Example: ("hello", "HELLO", 5)
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Transform, Sink, MergeSynch

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

word_source = ListSource(items=["hello", "world", "python"])


def to_uppercase(text):
    """Convert text to uppercase."""
    return text.upper()


def get_length(text):
    """Get length of text."""
    return len(text)


def format_result(merged_data):
    """
    Format the merged data into a tuple.

    Args:
        merged_data: List of [original, uppercase, length]

    Returns:
        Tuple of (original, uppercase, length)
    """
    return tuple(merged_data)


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

# Source node: generates words
source = Source(
    fn=word_source.run,
    name="word_source"
)

# Transform nodes: two parallel processing paths
uppercase_transform = Transform(
    fn=to_uppercase,
    name="uppercase"
)

length_transform = Transform(
    fn=get_length,
    name="length"
)

# MergeSynch node: synchronizes and merges results from both paths
# num_inputs MUST match the number of input connections
merger = MergeSynch(
    num_inputs=3,  # Will receive: original + uppercase + length
    name="merge_synch"
)

# Transform to format the merged result
formatter = Transform(
    fn=format_result,
    name="formatter"
)

# Sink node: collect final results
results = []
collector = Sink(
    fn=results.append,
    name="collector"
)


# ==============================================================================
# STEP 3: Build and Run the Network
# ==============================================================================
# MergeSynch uses PORT REFERENCES for inputs: merger.in_0, merger.in_1, merger.in_2

g = network([
    # Source fans out to two transforms
    (source, uppercase_transform),
    (source, length_transform),

    # Both transforms AND original connect to merger
    (source, merger.in_0),                    # Original text
    (uppercase_transform, merger.in_1),       # Uppercase result
    (length_transform, merger.in_2),          # Length result

    # Merger output goes to formatter, then collector
    (merger, formatter),
    (formatter, collector)
])

# Run the network
g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print("Results:", results)

    expected = [
        ("hello", "HELLO", 5),
        ("world", "WORLD", 5),
        ("python", "PYTHON", 6)
    ]

    assert results == expected, f"Expected {expected}, got {results}"

    print("✓ Merge Synch completed successfully!")
    print(f"  Each word was processed in parallel:")
    for original, upper, length in results:
        print(f"    '{original}' → '{upper}' (length: {length})")
