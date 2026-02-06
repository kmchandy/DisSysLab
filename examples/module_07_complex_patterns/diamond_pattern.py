"""
Diamond Pattern - Fork, Process in Parallel, Then Merge

Pattern: Source forks to multiple processors, then results merge back together.

Topology:
        ┌→ uppercase ─┐
source ─┤             ├→ merge_synch → formatter → collector
        └→ length ────┘

Use case: Process data in multiple ways, then combine results synchronously.

Example: Analyze text for uppercase version AND length, then merge into tuple.
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
    Format merged data into a tuple.

    Args:
        merged_data: List [original, uppercase, length]

    Returns:
        Tuple (original, uppercase, length)
    """
    return tuple(merged_data)


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

source = Source(
    fn=word_source.run,
    name="word_source"
)

# Two parallel processing transforms
uppercase_transform = Transform(
    fn=to_uppercase,
    name="uppercase"
)

length_transform = Transform(
    fn=get_length,
    name="length"
)

# MergeSynch: waits for all inputs, then outputs synchronized list
merger = MergeSynch(
    num_inputs=3,  # original + uppercase + length
    name="merge_synch"
)

# Formatter converts list to tuple
formatter = Transform(
    fn=format_result,
    name="formatter"
)

# Collector
results = []
collector = Sink(
    fn=results.append,
    name="collector"
)


# ==============================================================================
# STEP 3: Build and Run the Network - Diamond Pattern
# ==============================================================================

g = network([
    # Fork: source to both processors AND to merger
    (source, uppercase_transform),
    (source, length_transform),
    (source, merger.in_0),           # Original goes directly to merger

    # Both transforms send to merger (completing the diamond)
    (uppercase_transform, merger.in_1),
    (length_transform, merger.in_2),

    # Merger output goes to formatter then collector
    (merger, formatter),
    (formatter, collector)
])

g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print("Diamond Pattern Results")
    print("=" * 50)
    print("Results:", results)

    expected = [
        ("hello", "HELLO", 5),
        ("world", "WORLD", 5),
        ("python", "PYTHON", 6)
    ]

    assert results == expected, f"Expected {expected}, got {results}"

    print("\n✓ Diamond pattern completed successfully!")
    print(f"  Each word was processed in parallel:")
    for original, upper, length in results:
        print(f"    '{original}' → '{upper}' (length: {length})")
    print(f"\n  Pattern: Fork → Parallel Processing → Merge → Format → Collect")
