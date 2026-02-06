"""
Fanout Example - Broadcasting Messages to Multiple Destinations

This example demonstrates the fanout pattern:
- One source sends messages to multiple destinations
- Each destination receives a COPY of every message
- All destinations process messages independently and concurrently

Data flow:
                    → uppercase → results_upper
    ["hello"] ─────┤
                    → reverse → results_reverse

Each word gets processed in TWO different ways simultaneously.
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Sink, Transform

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

word_source = ListSource(items=["hello", "world", "python"])


def to_uppercase(text):
    """Convert text to uppercase."""
    return text.upper()


def reverse_text(text):
    """Reverse the text."""
    return text[::-1]


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

# Source node: generates words
source = Source(
    fn=word_source.run,
    name="word_source"
)

# Transform node: convert to uppercase
uppercase = Transform(
    fn=to_uppercase,
    name="uppercase"
)

# Transform node: reverse the text
reverse = Transform(
    fn=reverse_text,
    name="reverse"
)

# Sink nodes: collect results from each path
results_upper = []
collector_upper = Sink(
    fn=results_upper.append,
    name="collector_upper"
)

results_reverse = []
collector_reverse = Sink(
    fn=results_reverse.append,
    name="collector_reverse"
)


# ==============================================================================
# STEP 3: Build and Run the Network
# ==============================================================================
# Fanout: source sends to BOTH uppercase AND reverse
# Each path processes independently

g = network([
    (source, uppercase),          # Path 1: source → uppercase
    (source, reverse),            # Path 2: source → reverse (FANOUT!)
    (uppercase, collector_upper),
    (reverse, collector_reverse)
])

# Run the network
g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print("Uppercase path results:", results_upper)
    print("Reverse path results:", results_reverse)

    assert results_upper == ["HELLO", "WORLD", "PYTHON"]
    assert results_reverse == ["olleh", "dlrow", "nohtyp"]

    print("✓ Fanout completed successfully!")
    print(f"  Source produced: 3 words")
    print(f"  Each word went to 2 destinations")
    print(f"  Total messages processed: 6 (3 words × 2 paths)")
