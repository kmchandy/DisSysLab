# examples/simple_network_claude.py

"""
AI-Powered Distributed System with Claude API

This example demonstrates using real AI services (Claude) in a distributed network:
1. Multiple RSS sources feed articles into the system
2. Claude AI performs spam detection
3. Claude AI analyzes sentiment
4. Claude AI detects urgency
5. Urgent messages trigger email alerts
6. Sentiment analysis is archived

Data flow: RSS feeds → spam filter → sentiment + urgency → email/archive
"""
from components.sinks import MockEmailAlerter, JSONLRecorder
from components.transformers.claude_agent import (
    create_spam_detector,
    create_sentiment_analyzer,
    create_urgency_detector
)
from components.sources import MockRSSSource
from components.sources.mock_rss_source import MOCK_FEEDS
from dsl.blocks import Source, Transform, Sink
from dsl import network
from dotenv import load_dotenv
load_dotenv()


# Import components from the components library

# ============================================================================
# STEP 1: Create AI Agents (Claude-powered)
# ============================================================================

# These use the real Claude API - make sure ANTHROPIC_API_KEY is set
spam_detector = create_spam_detector()
sentiment_analyzer = create_sentiment_analyzer()
urgency_detector = create_urgency_detector()


# ============================================================================
# STEP 2: Create Source Nodes
# ============================================================================

hacker_articles = MockRSSSource(
    MOCK_FEEDS=MOCK_FEEDS, feed_name="hacker_news", max_articles=10)  # Limited for API costs
tech_articles = MockRSSSource(
    MOCK_FEEDS=MOCK_FEEDS, feed_name="tech_news", max_articles=10)
reddit_articles = MockRSSSource(
    MOCK_FEEDS=MOCK_FEEDS, feed_name="reddit_python", max_articles=10)

# Source nodes
hacker_source = Source(fn=hacker_articles.run, name="hacker_source")
tech_source = Source(fn=tech_articles.run, name="tech_source")
reddit_source = Source(fn=reddit_articles.run, name="reddit_source")


# ============================================================================
# STEP 3: Create Transform Nodes (AI-powered)
# ============================================================================

# Transform: AI spam detection
discard_spam = Transform(
    fn=spam_detector.run,
    name="claude_spam_filter"
)

# Transform: AI sentiment analysis
analyze_sentiment = Transform(
    fn=sentiment_analyzer.run,
    name="claude_sentiment_analyzer"
)

# Transform: AI urgency detection
detect_urgency = Transform(
    fn=urgency_detector.run,
    name="claude_urgency_detector"
)


# ============================================================================
# STEP 4: Filter non-spam and extract urgent messages
# ============================================================================

def filter_non_spam(spam_result):
    """
    Filter out spam messages.

    Args:
        spam_result: Dict from spam_detector with {is_spam, confidence, reason}

    Returns:
        Original message if not spam, None if spam (filtered out)
    """
    if spam_result.get("is_spam", False):
        return None  # Filter out spam
    return spam_result.get("original_text", "")


def filter_high_urgency(urgency_result):
    """
    Filter to keep only high urgency messages.

    Args:
        urgency_result: Dict from urgency_detector with {urgency, metrics, reasoning}

    Returns:
        Message if urgency is HIGH, None otherwise
    """
    if urgency_result.get("urgency") == "HIGH":
        return urgency_result
    return None  # Filter out non-urgent


filter_spam = Transform(fn=filter_non_spam, name="filter_spam")
filter_urgent = Transform(fn=filter_high_urgency, name="filter_urgent")


# ============================================================================
# STEP 5: Create Sink Nodes
# ============================================================================

# Email alerter for urgent messages
email_alerter = MockEmailAlerter(
    to_address="security@example.com",
    subject_prefix="[URGENT - AI Detected]"
)
alert_sink = Sink(fn=email_alerter.run, name="email_alerter")

# Archive recorder for sentiment analysis
recorder = JSONLRecorder(
    path="claude_sentiment_archive.jsonl",
    mode="w",
    flush_every=1,
    name="claude_archive"
)
archive_sink = Sink(fn=recorder.run, name="sentiment_archive")


# ============================================================================
# STEP 6: Build and Run Network
# ============================================================================

# Network topology:
#   3 sources → spam filter → sentiment analyzer → archive
#                          └→ urgency detector → filter → email alerts

g = network([
    # Fan-in: Three sources merge
    (hacker_source, discard_spam),
    (tech_source, discard_spam),
    (reddit_source, discard_spam),

    # Fan-out: Spam filter broadcasts to two analyzers
    (discard_spam, analyze_sentiment),
    (discard_spam, detect_urgency),

    # Sentiment analysis → archive
    (analyze_sentiment, archive_sink),

    # Urgency detection → filter → alerts
    (detect_urgency, filter_urgent),
    (filter_urgent, alert_sink),
])

# ============================================================================
# Run the network
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AI-Powered News Analysis Network (using Claude API)")
    print("=" * 70)
    print()
    print("⚠️  Note: This uses the real Claude API and will incur costs")
    print("    Limited to 30 articles total to minimize costs")
    print()

    g.run_network()

    print()
    print("=" * 70)
    print("Network Complete!")
    print("=" * 70)
    print()

    # Print usage statistics
    print("API Usage Statistics:")
    print("-" * 70)
    spam_detector.print_usage_stats()
    sentiment_analyzer.print_usage_stats()
    urgency_detector.print_usage_stats()

    print(f"\nResults saved to: claude_sentiment_archive.jsonl")
    print("View with: cat claude_sentiment_archive.jsonl | jq '.'")
