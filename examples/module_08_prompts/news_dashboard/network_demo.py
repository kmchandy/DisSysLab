"""
News Dashboard - Demo Version

Uses prepackaged data. No API keys needed. No cost.
Everyone should run this first.
"""

from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.AI_summarizer import Summarizer
from components.transformers.AI_sentiment_analyzer import SentimentAnalyzer
from components.transformers.AI_topic_clusterer import TopicClusterer
from components.sinks.demo_console_dashboard import ConsoleDashboard
from core.network import Network


def build_news_dashboard():
    """Build and run the news intelligence dashboard with demo data."""

    # Create network
    net = Network("News Intelligence Dashboard - Demo")

    # Source: Read from prepackaged RSS data
    rss_source = DemoRSSSource(
        data_file="module_8/news_dashboard/demo_data/rss_feeds.json"
    )

    # Transformers: All built from prompts
    summarizer = Summarizer()
    sentiment = SentimentAnalyzer()
    topic_cluster = TopicClusterer()

    # Sink: Pretty console display
    dashboard = ConsoleDashboard()

    # Wire the network
    net.add_edge(rss_source, summarizer)
    net.add_edge(summarizer, sentiment)
    net.add_edge(sentiment, topic_cluster)
    net.add_edge(topic_cluster, dashboard)

    # Run
    print("\n" + "="*60)
    print("PERSONAL NEWS INTELLIGENCE DASHBOARD - DEMO")
    print("="*60)
    print("\nProcessing 20 prepackaged news articles...")
    print("All transformers built from AI prompts\n")

    net.run()

    print("\n" + "="*60)
    print("Demo complete!")
    print("\nNext steps:")
    print("1. Check components/transformers/prompts.py to see the prompts")
    print("2. Read the transformer code in components/transformers/")
    print("3. Try network_real.py when you have API access")
    print("="*60 + "\n")


if __name__ == "__main__":
    build_news_dashboard()
