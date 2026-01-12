# modules/drop_None/simple_filter.py

"""
Message Filtering: Dropping Messages by Returning None

This example demonstrates a key DSL concept: when a transform node returns None,
that message is dropped and NOT sent to downstream nodes.

Key Concepts:
- Filtering pattern: return None to drop messages
- All functions are ordinary Python with no concurrency features
- Functions are independent of DSL
"""

from dsl import network
from dsl.decorators import source_map, transform_map, sink_map


# ============================================================================
# Ordinary Python Functions (no concurrency features)
# ============================================================================

list_of_words = ['O', 'hello', 'world', 'python', 'philosophy', 'is', 'fun']


class WordListSource:
    """
    Ordinary Python class that iterates through a list of words.
    Independent of DSL, no concurrency features.
    """

    def __init__(self, items):
        self.items = items
        self.index = 0

    def run(self):
        """Returns next word or None when exhausted."""
        if self.index >= len(self.items):
            return None
        word = self.items[self.index]
        self.index += 1
        return word  # Returns a string, not a dict


def filter_by_length(word, min_length=2, max_length=8):
    """
    Filter: keeps words within length range, drops others.

    This is an ordinary Python function independent of DSL.

    Returns:
        word if length is in range [min_length, max_length]
        None otherwise (which drops the message)
    """
    if min_length <= len(word) <= max_length:
        return word
    return None  # Message is dropped - not sent downstream


results = []


def collect_results(word):
    """
    Sink: collects words that passed the filter.

    This is an ordinary Python function independent of DSL.
    """
    results.append(word)


# ============================================================================
# Wrap Functions to Create Network Nodes
# ============================================================================

# Create source: wrap the word generator
word_source_data = WordListSource(list_of_words)
word_source = source_map(output_keys=["word"])(word_source_data.run)
# Wraps: "hello" → {"word": "hello"}

# Create filter node: extract word, filter it, put it back
filter_node = transform_map(
    input_keys=["word"],
    output_keys=["word"]
)(filter_by_length)
# Input:  {"word": "hello"}
# Output: {"word": "hello"} if passes filter, or None if dropped

# Create sink: extract word and collect it
sink = sink_map(
    input_keys=["word"]
)(collect_results)


# ============================================================================
# Build and Run Network
# ============================================================================

g = network([
    (word_source, filter_node),
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
