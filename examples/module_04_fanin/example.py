"""
Fanin Example - Merging Multiple Sources into One Destination

This example demonstrates the fanin pattern:
- Multiple sources send messages to one destination
- The destination receives messages from ALL sources
- Messages are processed in the order they arrive (interleaved)

Data flow:
    source_A: ["A1", "A2"] ───┐
                              ├──→ merger → results
    source_B: ["B1", "B2"] ───┘

Result: All messages from both sources, merged together.
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Sink, Transform

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

source_A_data = ListSource(items=["A1", "A2", "A3"])
source_B_data = ListSource(items=["B1", "B2", "B3"])


def add_label(text, label="merged"):
    """Add a label to the text."""
    return f"[{label}] {text}"


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

# Source nodes: two independent sources
source_A = Source(
    fn=source_A_data.run,
    name="source_A"
)

source_B = Source(
    fn=source_B_data.run,
    name="source_B"
)

# Transform node: processes merged messages
merger = Transform(
    fn=add_label,
    name="merger"
)

# Sink node: collect all merged results
results = []
collector = Sink(
    fn=results.append,
    name="collector"
)


# ==============================================================================
# STEP 3: Build and Run the Network
# ==============================================================================
# Fanin: BOTH source_A AND source_B send to merger
# Messages from both sources are merged at the merger node

g = network([
    (source_A, merger),     # Source A → merger (FANIN!)
    (source_B, merger),     # Source B → merger (FANIN!)
    (merger, collector)
])

# Run the network
g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print(f"Results: {results}")

    # All messages from both sources should be present
    assert len(results) == 6, f"Expected 6 messages, got {len(results)}"

    # Check that messages from both sources are present
    a_messages = [r for r in results if 'A' in r]
    b_messages = [r for r in results if 'B' in r]

    assert len(a_messages) == 3, "Should have 3 messages from source A"
    assert len(b_messages) == 3, "Should have 3 messages from source B"

    print("✓ Fanin completed successfully!")
    print(f"  Source A produced: 3 messages")
    print(f"  Source B produced: 3 messages")
    print(f"  Merger received: 6 messages total")
    print(f"  Messages may be interleaved (order depends on timing)")
