# modules/basic/network.py

"""
Build a distributed system by constructing a graph in which nodes call
ordinary Python functions that are often from existing codebases and libraries. 

These functions are independent of dsl and have no concurrency primitives such 
as threads, processes, locks, or message passing. 

"""

from dsl import network
from dsl.blocks import Source, Transform, Sink

# Import components from the components library
from components.sources import MockRSSSource
from components.transformers import MockAISpamFilter, MockAISentimentAnalyzer, MockAINonUrgentFilter
from components.sinks import MockEmailAlerter, JSONLRecorder

# ============================================================================
# STEP 1: Create Source Nodes (Mock RSS Feeds)
# ============================================================================

hacker_data_source = Source(MockRSSSource(
    feed_name="hacker_news", max_articles=100).run)
tech_data_source = Source(MockRSSSource(
    feed_name="tech_news", max_articles=100).run)
reddit_data_source = Source(MockRSSSource(
    feed_name="reddit_python", max_articles=100).run)

# ============================================================================
# STEP 2: Create Transform Nodes
# ============================================================================

discard_spam = Transform(MockAISpamFilter().run)
analyze_sentiment = Transform(MockAISentimentAnalyzer().run)
discard_non_urgent = Transform(MockAINonUrgentFilter().run)

# ============================================================================
# STEP 4: Create Sink Nodes
# ============================================================================

# Mock email alerter for spam (prints to console, no real emails)
issue_alert = Sink(MockEmailAlerter(
    to_address="security@example.com",
    subject_prefix="[URGENT]").run
)

# File archive for sentiment results
archive_recorder = Sink(JSONLRecorder(
    path="basic_network_archive.jsonl",
    mode="w",
    flush_every=1,
    name="basic_network_archive").run
)

# ============================================================================
# STEP 5: Build Network Topology
# ============================================================================

g = network([
    (hacker_data_source, discard_spam),
    (tech_data_source, discard_spam),
    (reddit_data_source, discard_spam),
    (discard_spam, analyze_sentiment),
    (discard_spam, discard_non_urgent),
    (discard_non_urgent, issue_alert),
    (analyze_sentiment, archive_recorder),
])

g.run_network()
