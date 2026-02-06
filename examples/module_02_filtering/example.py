"""
Message Filtering Example - Conditional Data Processing

This example demonstrates how to filter messages in a pipeline:
- Return a value to pass the message downstream
- Return None to drop the message (it won't continue)

Data flow: [1,2,3,4,5,6,7,8,9,10] → FILTER (keep even) → results

Expected output: [2, 4, 6, 8, 10]  (only even numbers)
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Sink, Transform

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

number_source = ListSource(items=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


def keep_only_even(number):
    """
    Filter function: keeps even numbers, drops odd numbers.

    Key insight: Returning None tells DisSysLab to DROP this message.
    """
    if number % 2 == 0:
        return number  # Pass even numbers through
    else:
        return None    # Drop odd numbers


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

# Source node: generates numbers 1-10
source = Source(
    fn=number_source.run,
    name="number_source"
)

# Transform node: filter - only even numbers pass through
filter_even = Transform(
    fn=keep_only_even,
    name="filter_even"
)

# Sink node: collect results
results = []
collector = Sink(
    fn=results.append,
    name="collector"
)


# ==============================================================================
# STEP 3: Build and Run the Network
# ==============================================================================
# Network: source → filter_even → collector
# Messages that return None from filter_even are DROPPED

g = network([
    (source, filter_even),      # 1,2,3,... → filter (2,4,6,8,10 pass through)
    (filter_even, collector)    # 2,4,6,8,10 → results
])

# Run the network
g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print(f"Results: {results}")
    expected = [2, 4, 6, 8, 10]  # Only even numbers
    assert results == expected, f"Expected {expected}, got {results}"
    print("✓ Filtering completed successfully!")
    print(f"  Started with: 10 numbers")
    print(f"  Filtered to: 5 even numbers")
    print(f"  Dropped: 5 odd numbers")
