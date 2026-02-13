# examples.simple_network.py

"""
Build a distributed system by constructing a graph in which nodes call
ordinary Python functions that are often from existing codebases and libraries. 

These functions are independent of dsl and have no concurrency primitives such 
as threads, processes, locks, or message passing. 

"""

from dsl import network
from dsl.blocks import Source, Transform, Sink

# Import components from the components library
from components.sources.mock_rss_source import MOCK_FEEDS
from components.sources import MockRSSSource
from components.transformers import MockAISpamFilter, MockAISentimentAnalyzer, MockAINonUrgentFilter
from components.sinks import MockEmailAlerter, JSONLRecorder

# ============================================================================
# Create Source Nodes: construction
#        source_agent = Source(fn=source_function, name="source_name")
# ============================================================================

# Objects used for source functions
hacker_articles = MockRSSSource(
    MOCK_FEEDS=MOCK_FEEDS, feed_name="hacker_news", max_articles=100)
tech_articles = MockRSSSource(
    MOCK_FEEDS=MOCK_FEEDS, feed_name="tech_news", max_articles=100)
reddit_articles = MockRSSSource(
    MOCK_FEEDS=MOCK_FEEDS, feed_name="reddit_python", max_articles=100)

# Source agents
hacker_data_source = Source(fn=hacker_articles.run, name="hacker_source")
tech_data_source = Source(fn=tech_articles.run, name="tech_source")
reddit_data_source = Source(fn=reddit_articles.run, name="reddit_source")

# ============================================================================
# Create Transform Nodes:  construction:
#    transform_agent = Transform(fn=transform_function, name="transform_name")
# ============================================================================

discard_spam = Transform(fn=MockAISpamFilter().run, name="spam_filter")
analyze_sentiment = Transform(
    fn=MockAISentimentAnalyzer().run, name="sentiment_analyzer")
discard_non_urgent = Transform(
    fn=MockAINonUrgentFilter().run, name="non_urgent_filter")

# ============================================================================
# Create Sink Nodes. construction:
#        sink_agent = Sink(fn=sink_function, name="sink_name")
# ============================================================================

# Mock email alerter agent for spam (prints to console, no real emails)
email_alerter = MockEmailAlerter(
    to_address="security@example.com",
    subject_prefix="[URGENT]")

issue_alert = Sink(fn=email_alerter.run, name="email_alerter")

# Object used for function in the Sink agent archive_recorder.
recorder = JSONLRecorder(
    path="basic_network_archive.jsonl",
    mode="w",
    flush_every=1,
    name="basic_network_archive")

# The archive recorder agent
archive_recorder = Sink(fn=recorder.run, name="sentiment_archive")

# ============================================================================
# Specify network - a list of edges (x, y) where x → y and x, y are agents.
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

# ============================================================================
# Run network
# ============================================================================
# pretty printing for console output
print(f"{'='*50}")
print(f"Output consists of mock emails")
print(f"{'='*50}")
print()

g.run_network()

print(f"Read 'basic_network_archive.jsonl' to see archived sentiment analysis results.")
