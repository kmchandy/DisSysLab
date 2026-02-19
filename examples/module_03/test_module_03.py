# examples/module_03/test_module_03.py

"""
Tests for Module 03: Multiple Sources, Multiple Destinations

Run from the DisSysLab root directory:
    pytest examples/module_03/test_module_03.py -v
"""

import pytest
from components.sources.demo_rss_source import DemoRSSSource, DEMO_FEEDS
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from dsl import network
from dsl.blocks import Source, Transform, Sink


class TestFanin:
    def test_two_sources_merge(self):
        rss1 = DemoRSSSource(feed_name="hacker_news", max_articles=3)
        rss2 = DemoRSSSource(feed_name="tech_news", max_articles=3)
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results = []
        source1 = Source(fn=rss1.run, name="hacker_news")
        source2 = Source(fn=rss2.run, name="tech_news")
        sentiment = Transform(fn=analyze, name="sentiment")
        collector = Sink(fn=results.append, name="out")

        g = network([
            (source1, sentiment),
            (source2, sentiment),
            (sentiment, collector)
        ])
        g.run_network()

        assert len(
            results) == 6, f"Expected 6 results (3+3), got {len(results)}"

    def test_three_sources_merge(self):
        rss1 = DemoRSSSource(feed_name="hacker_news", max_articles=2)
        rss2 = DemoRSSSource(feed_name="tech_news", max_articles=2)
        rss3 = DemoRSSSource(feed_name="reddit_python", max_articles=2)

        results = []
        source1 = Source(fn=rss1.run, name="hn")
        source2 = Source(fn=rss2.run, name="tech")
        source3 = Source(fn=rss3.run, name="reddit")
        passthrough = Transform(fn=lambda x: x, name="pass")
        collector = Sink(fn=results.append, name="out")

        g = network([
            (source1, passthrough),
            (source2, passthrough),
            (source3, passthrough),
            (passthrough, collector)
        ])
        g.run_network()

        assert len(
            results) == 6, f"Expected 6 results (2+2+2), got {len(results)}"


class TestFanout:
    def test_fanout_to_two_sinks(self):
        rss = DemoRSSSource(feed_name="hacker_news", max_articles=5)
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results_file = []
        results_email = []

        source = Source(fn=rss.run, name="source")
        sentiment = Transform(fn=analyze, name="sentiment")
        file_sink = Sink(fn=results_file.append, name="file")
        email_sink = Sink(fn=results_email.append, name="email")

        g = network([
            (source, sentiment),
            (sentiment, file_sink),
            (sentiment, email_sink)
        ])
        g.run_network()

        assert len(results_file) == len(results_email)
        assert len(results_file) == 5

    def test_fanout_to_three_sinks(self):
        rss = DemoRSSSource(feed_name="tech_news", max_articles=4)

        r1, r2, r3 = [], [], []
        source = Source(fn=rss.run, name="source")
        passthrough = Transform(fn=lambda x: x, name="pass")
        s1 = Sink(fn=r1.append, name="s1")
        s2 = Sink(fn=r2.append, name="s2")
        s3 = Sink(fn=r3.append, name="s3")

        g = network([
            (source, passthrough),
            (passthrough, s1),
            (passthrough, s2),
            (passthrough, s3)
        ])
        g.run_network()

        assert len(r1) == len(r2) == len(r3) == 4


class TestDiamond:
    def test_diamond_topology(self):
        rss1 = DemoRSSSource(feed_name="hacker_news", max_articles=3)
        rss2 = DemoRSSSource(feed_name="tech_news", max_articles=3)
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results_file = []
        results_alert = []

        source1 = Source(fn=rss1.run, name="hn")
        source2 = Source(fn=rss2.run, name="tech")
        sentiment = Transform(fn=analyze, name="sentiment")
        file_sink = Sink(fn=results_file.append, name="file")
        alert_sink = Sink(fn=results_alert.append, name="alert")

        g = network([
            (source1, sentiment),
            (source2, sentiment),
            (sentiment, file_sink),
            (sentiment, alert_sink)
        ])
        g.run_network()

        assert len(results_file) == 6
        assert len(results_alert) == 6

    def test_diamond_with_filter(self):
        rss1 = DemoRSSSource(feed_name="hacker_news", max_articles=5)
        rss2 = DemoRSSSource(feed_name="tech_news", max_articles=5)
        spam_det = demo_ai_agent(SPAM_DETECTOR)

        def filter_spam(text):
            result = spam_det(text)
            return None if result["is_spam"] else text

        r1, r2 = [], []
        source1 = Source(fn=rss1.run, name="hn")
        source2 = Source(fn=rss2.run, name="tech")
        spam_gate = Transform(fn=filter_spam, name="spam")
        sink1 = Sink(fn=r1.append, name="s1")
        sink2 = Sink(fn=r2.append, name="s2")

        g = network([
            (source1, spam_gate),
            (source2, spam_gate),
            (spam_gate, sink1),
            (spam_gate, sink2)
        ])
        g.run_network()

        assert len(r1) == len(r2)
        assert len(r1) < 10
