# modules/ch01_networks/simple_filter.py

"""
Message Filtering: Dropping Messages by Returning None

This example demonstrates a key DSL concept: when a node returns None,
that message is dropped and NOT sent to downstream nodes.
"""

from dsl import network
from dsl.decorators import msg_map


# ============================================================================
# Ordinary Python Functions (no concurrency features)
# ============================================================================

list_of_words = ['O', 'hello', 'world', 'python', 'philosophy', 'is', 'fun']


def from_list(items=list_of_words):
    """Source: yields a dict for each word in the list"""
    for item in items:
        yield {"word": item}


def filter_by_length(word, min_length=2, max_length=8):
    """
    Filter: keeps words within length range, drops others.

    Returns:
        word if length is in range [min_length, max_length]
        None otherwise (which drops the message)
    """
    if min_length <= len(word) <= max_length:
        return word
    return None  # Message is dropped - not sent downstream


results = []


def collect_results(word):
    """Sink: collects words that passed the filter"""
    results.append(word)


# ============================================================================
# Wrap Functions to Create Network Nodes
# ============================================================================

# Note: from_list is a generator that yields dicts, so it's already a source
filter_node = msg_map(
    input_keys=["word"],
    output_keys=["word"]
)(filter_by_length)

sink = msg_map(
    input_keys=["word"],
    output_keys=None  # Sink has no outputs
)(collect_results)


# ============================================================================
# Build and Run Network
# ============================================================================

g = network([
    (from_list, filter_node),
    (filter_node, sink)
])

g.run_network()


# ============================================================================
# Verify Results: Print Output
# ============================================================================
print()
print("Input words:", list_of_words)
print()
print("Filtered words (2-8 chars):", results)
print()

dropped_words = [word for word in list_of_words if word not in results]
if dropped_words:
    print("Dropped words:")
    for word in dropped_words:
        print(f"  '{word}' (length {len(word)})")

assert results == ['hello', 'world', 'python', 'is', 'fun'], \
    "Filter didn't work correctly!"

print("\n✓ Filter test passed!")
