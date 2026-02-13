# examples/simple_network_2.py

"""
Build a distributed system by constructing a graph in which nodes call
ordinary Python functions that are often from existing codebases and libraries. 

These functions are independent of dsl and have no concurrency primitives such 
as threads, processes, locks, or message passing. 

"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, MergeSynch

# Import components from the components library
from components.sources.mock_rss_source import MOCK_FEEDS_2
from components.sources import MockRSSSource
from components.transformers import MockAISpamFilter, MockAISentimentAnalyzer, MockAINonUrgentFilter
from components.sinks import MockEmailAlerter, JSONLRecorder

# ============================================================================
# Create Source Nodes: construction
#        source_agent = Source(fn=source_function, name="source_name")
# ============================================================================

# Objects used for source functions
X_posts = MockRSSSource(
    MOCK_FEEDS=MOCK_FEEDS_2, feed_name="example_posts_from_X", max_articles=100)
Reddit_posts = MockRSSSource(
    MOCK_FEEDS=MOCK_FEEDS_2, feed_name="example_posts_from_Reddit", max_articles=100)
Facebook_posts = MockRSSSource(
    MOCK_FEEDS=MOCK_FEEDS_2, feed_name="example_posts_from_Facebook", max_articles=100)

# Source agents
X_data_source = Source(fn=X_posts.run, name="hacker_source")
Reddit_data_source = Source(fn=Reddit_posts.run, name="tech_source")
Facebook_data_source = Source(fn=Facebook_posts.run, name="reddit_source")

# ============================================================================
# Create Transform Nodes:  construction:
#    transform_agent = Transform(fn=transform_function, name="transform_name")
# ============================================================================


def clean_text(text):
    """
    Removes emojis and cleans whitespace.

    This is a pure Python function - it knows nothing about distributed systems.

    Args:
        text: String to clean

    Returns:
        Cleaned string
    """
    import re
    cleaned = re.sub(r'[^\w\s.,!?-]', '', text)
    cleaned = ' '.join(cleaned.split())
    return cleaned


def print_msg(msg):
    print(f"text")
    print(f"{msg[0]}")
    print(f"sentiment: {msg[1]['sentiment']}")
    print(f"reasoning")
    print(f"{msg[1]['reasoning']}")
    print(f"{'-'*40}")
    print()


discard_spam = Transform(fn=MockAISpamFilter().run, name="spam_filter")
analyze_sentiment = Transform(
    fn=MockAISentimentAnalyzer().run, name="sentiment_analyzer")
clean = Transform(
    fn=clean_text, name="clean_text_transformer")
merge_synch_text_and_sentiment = MergeSynch(
    num_inputs=2, name="merge_text_and_sentiment")

# ============================================================================
# Create Sink Nodes. construction:
#        sink_agent = Sink(fn=sink_function, name="sink_name")
# ============================================================================

# Mock email alerter agent for spam (prints to console, no real emails)
print_output = Sink(fn=print_msg, name="print_output")

# ============================================================================
# Specify network - a list of edges (x, y) where x → y and x, y are agents.
# ============================================================================

g = network([
    (X_data_source, clean),
    (Reddit_data_source, clean),
    (Facebook_data_source, clean),
    (clean, discard_spam),
    (discard_spam, analyze_sentiment),
    (discard_spam.out_, merge_synch_text_and_sentiment.in_0),
    (analyze_sentiment.out_, merge_synch_text_and_sentiment.in_1),
    (merge_synch_text_and_sentiment, print_output),
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
