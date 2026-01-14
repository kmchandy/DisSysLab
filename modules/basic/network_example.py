# modules/basic/network_example.py

"""
Build a Distributed System from Ordinary Python Functions

This example demonstrates a key feature of DSL: you can build a distributed
system where nodes are ordinary Python functions that are often from 
existing codebases and libraries. These functions are independent of dsl and
have no concurrency primitives such as threads, processes, locks, or message
passing. 

Key Concepts Demonstrated:
- Fanin: Multiple sources merge into one processing node
- Fanout: One node broadcasts to multiple downstream nodes
- Content-based routing: Spam goes to alerter, clean messages to pipeline
- Message passing: Data flows automatically between nodes as dicts

This is Module 2 - it uses MOCK components for teaching.
In Module 9, students replace mocks with real components (same interface!).
"""

from dsl import network
from dsl.decorators import source_map, transform_map, sink_map
from dsl.blocks.sink import Sink

# Import MOCK components from the components library
from components.sources import MockRSSSource
from components.transformers.mock_AI_spam_filter import MockAISpamFilter
from components.transformers.mock_AI_sentiment_analyzer import MockAISentimentAnalyzer
from components.transformers.mock_AI_non_urgent_filter import MockAINonUrgentFilter
from components.sinks import ConsoleSink, MockEmailAlerter

# Import connectors (these will eventually move to components/sinks too)
from examples.connectors.sink_jsonl_recorder import JSONLRecorder


# ============================================================================
# STEP 1: Create Source Nodes (Mock RSS Feeds)
# ============================================================================

# Mock Hacker News feed (uses test data, no API needed)
hn_data = MockRSSSource(feed_name="hacker_news", max_articles=100)
hn_source = source_map(output_keys=["text"])(hn_data.run)

# Mock Tech News feed (uses test data, no API needed)
tech_data = MockRSSSource(feed_name="tech_news", max_articles=100)
tech_source = source_map(output_keys=["text"])(tech_data.run)

# Mock Reddit News feed (uses test data, no API needed)
reddit_data = MockRSSSource(feed_name="reddit_python", max_articles=100)
reddit_source = source_map(output_keys=["text"])(reddit_data.run)

# ============================================================================
# STEP 2: Create Transform Nodes (Mock AI Agents)
# ============================================================================

# Mock spam detector (keyword matching, no API needed)
spam_filter_object = MockAISpamFilter()
spam_filter_function = transform_map(
    input_keys=["text"],
    output_keys=["text"]
)(spam_filter_object.run)

# Mock sentiment analyzer (keyword matching, no API needed)
sentiment_analyzer_object = MockAISentimentAnalyzer()
sentiment_analyzer_function = transform_map(
    input_keys=["text"],
    output_keys=["sentiment", "score", "reasoning"]
)(sentiment_analyzer_object.run)

# Mock urgency detector (keyword matching, no API needed)
urgent_filter_object = MockAINonUrgentFilter()
urgency_filter_function = transform_map(
    input_keys=["text"],
    output_keys=[]
)(urgent_filter_object.run)


# ============================================================================
# STEP 4: Create Sink Nodes (Output Destinations)
# ============================================================================


# Mock email alerter for spam (prints to console, no real emails)
urgency_alerter_handler = MockEmailAlerter(
    to_address="security@example.com",
    subject_prefix="[URGENT]"
)
urgency_alerter = sink_map(input_keys=["text"])(urgency_alerter_handler.run)

# Console display for urgency results
display_handler = ConsoleSink()
display = sink_map(input_keys=[])(display_handler.run)

# File archive for sentiment results
archive_handler = JSONLRecorder(
    path="basic_network_archive.jsonl",
    mode="w",
    flush_every=1,
    name="basic_network_archive"
)
archive_recorder = sink_map(input_keys=[])(archive_handler.run)


# ============================================================================
# STEP 5: Build Network Topology
# ============================================================================


g = network([
    # Fanin: Multiple RSS sources merge into spam detector
    (hn_source, spam_filter_function),
    (tech_source, spam_filter_function),
    (reddit_source, spam_filter_function),

    # Spam messages are dropped by spam detector
    # Non-spam messages broadcast to sentiment and urgency analyzers
    (spam_filter_function, sentiment_analyzer_function),
    (spam_filter_function, urgency_filter_function),

    # Urgency results go to console display and email alerter
    (urgency_filter_function, urgency_alerter),

    # Sentiment results go to archive
    (sentiment_analyzer_function, archive_recorder),
])


g.run_network()

# ============================================================================
# STEP 6: Execute the Network
# ============================================================================

# if __name__ == "__main__":
#     print("=" * 70)
#     print("Running Mock Distributed Network (Module 2)")
#     print("=" * 70)
#     print()
#     print("Network Components:")
#     print("  Sources:     Mock RSS feeds (test data)")
#     print("  Transforms:  Mock AI agents (keyword matching)")
#     print("  Sinks:       Mock email, File archive, Console")
#     print()
#     print("Network Flow:")
#     print("  RSS → Spam Detection → Route →")
#     print("    ├─ Spam → Mock Email Alert")
#     print("    └─ Clean → Sentiment → Archive + Urgency → Console")
#     print()
#     print("=" * 70)
#     print()

#     try:
#         # Run the network
#         print("Starting network execution...")
#         print()
#         g.run_network()

#         # Print statistics
#         print()
#         print("=" * 70)
#         print("Network Execution Complete!")
#         print("=" * 70)
#         print()

#         # Print usage stats for mock agents
#         print("Mock AI Agent Usage:")
#         print("-" * 70)
#         spam_detector_agent.print_usage_stats()
#         sentiment_agent.print_usage_stats()
#         urgency_agent.print_usage_stats()

#         # Print RSS stats
#         print("Mock RSS Feed Statistics:")
#         print("-" * 70)
#         hn_data.print_stats()
#         tech_data.print_stats()

#         # Clean up
#         archive_handler.finalize()
#         display_handler.finalize()

#         print()
#         print("=" * 70)
#         print("Pipeline Complete!")
#         print("=" * 70)
#         print()
#         print("What you just saw:")
#         print("  ✓ Mock RSS feeds provided test data")
#         print("  ✓ Mock AI agents used keyword matching")
#         print("  ✓ Mock email alerter printed to console")
#         print("  ✓ Real file archiving (check basic_network_archive.jsonl)")
#         print()
#         print("To view archived sentiment data:")
#         print("  cat basic_network_archive.jsonl | jq '.'")
#         print()
#         print("=" * 70)
#         print("Module 2 → Module 9 Upgrade Path:")
#         print("=" * 70)
#         print("To upgrade to REAL components (Module 9):")
#         print("  1. Replace: MockRSSSource → RSSSource")
#         print("  2. Replace: MockClaudeAgent → ClaudeAgent")
#         print("  3. Replace: MockEmailAlerter → GmailAlerter")
#         print("  4. Add API keys (Anthropic, Gmail)")
#         print("  5. Same network topology, real data!")
#         print("=" * 70)

#     except KeyboardInterrupt:
#         print("\n\nNetwork interrupted by user")
#         print("Cleaning up...")
#         archive_handler.finalize()
#         display_handler.finalize()
#         spam_alerter_handler.print_stats()

#     except Exception as e:
#         print()
#         print("=" * 70)
#         print("❌ Network Execution Failed")
#         print("=" * 70)
#         print(f"Error: {e}")
#         print()
#         import traceback
#         traceback.print_exc()

#         # Try to clean up
#         try:
#             archive_handler.finalize()
#             display_handler.finalize()
#         except:
#             pass
