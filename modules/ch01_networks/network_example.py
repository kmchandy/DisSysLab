# modules/ch01_networks/network_example.py

"""
Building a Distributed System from Ordinary Python Functions

This example demonstrates the core value of the DSL: you can build a distributed
system where nodes are simply ordinary Python functions—no threads, processes,
locks, or explicit message passing required.

Key Concepts Demonstrated:
- Fanin: Multiple sources merge into one processing node
- Fanout: One node broadcasts to multiple downstream nodes
- Message passing: Data flows automatically between nodes as dicts
"""

from dsl import network
from dsl.decorators import msg_map
from dsl.connectors.sink_jsonl_recorder import JSONLRecorder
from dsl.connectors.sink_console_recorder import ConsoleRecorder

from .simple_text_analysis import (
    SourceOfSocialMediaPosts,
    example_posts_from_X,
    example_posts_from_Reddit,
    example_posts_from_Facebook,
    clean_text,
    analyze_sentiment,
    analyze_urgency
)


# ============================================================================
# STEP 1: Create Source Nodes
# ============================================================================

from_X = SourceOfSocialMediaPosts(posts=example_posts_from_X, name="from_X")
from_Reddit = SourceOfSocialMediaPosts(
    posts=example_posts_from_Reddit, name="from_Reddit")
from_Facebook = SourceOfSocialMediaPosts(
    posts=example_posts_from_Facebook, name="from_Facebook")


# ============================================================================
# STEP 2: Create Processing Nodes by Wrapping Vanilla Python Functions
# ============================================================================

clean = msg_map(
    input_keys=["text"],
    output_keys=["clean_text"]
)(clean_text)

sentiment_analyzer = msg_map(
    input_keys=["clean_text"],
    output_keys=["sentiment", "score"]
)(analyze_sentiment)

urgency_analyzer = msg_map(
    input_keys=["clean_text"],
    output_keys=["urgency", "metrics"]
)(analyze_urgency)


# ============================================================================
# STEP 3: Create Sink Nodes (Output Destinations)
# ============================================================================

display = ConsoleRecorder()

archive_recorder = JSONLRecorder(
    path="sentiment_archive.jsonl",
    mode="w",
    flush_every=1,
    name="sentiment_archive"
)


# ============================================================================
# STEP 4: Define Network Topology
# ============================================================================

g = network([
    # Fanin: Three sources merge into clean
    (from_X, clean),
    (from_Reddit, clean),
    (from_Facebook, clean),

    # Fanout: clean broadcasts to two analyzers
    (clean, sentiment_analyzer),
    (clean, urgency_analyzer),

    # Route to different outputs
    (sentiment_analyzer, archive_recorder),
    (urgency_analyzer, display)
])


# ============================================================================
# STEP 5: Execute the Network
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Running Distributed Social Media Analysis Network")
    print("=" * 70)
    print()

    g.run_network()

    # Clean up
    archive_recorder.finalize()
    display.finalize()

    print()
    print("=" * 70)
    print("Pipeline Complete!")
    print("=" * 70)
    print()
    print("To view archived sentiment data:")
    print("  cat sentiment_archive.jsonl | jq '.'")
    print("=" * 70)
