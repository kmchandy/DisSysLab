# examples/module_04/test_module_04.py

"""
Tests for Module 04: Smart Routing (Split)

Run from the DisSysLab root directory:
    pytest examples/module_04/test_module_04.py -v
"""

import pytest
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from dsl import network
from dsl.blocks import Source, Transform, Sink, Split


class TestSplitBasic:
    def test_split_routes_to_correct_outputs(self):
        from components.sources.list_source import ListSource

        data = ListSource(items=[1, 2, 3, 4, 5, 6])

        def route_even_odd(n):
            if n % 2 == 0:
                return [n, None]
            else:
                return [None, n]

        evens = []
        odds = []

        source = Source(fn=data.run, name="numbers")
        splitter = Split(fn=route_even_odd, num_outputs=2, name="router")
        even_sink = Sink(fn=evens.append, name="evens")
        odd_sink = Sink(fn=odds.append, name="odds")

        g = network([
            (source, splitter),
            (splitter.out_0, even_sink),
            (splitter.out_1, odd_sink)
        ])
        g.run_network()

        assert sorted(evens) == [2, 4, 6]
        assert sorted(odds) == [1, 3, 5]

    def test_split_can_send_to_multiple_outputs(self):
        from components.sources.list_source import ListSource

        data = ListSource(items=[10, 20, 30])

        def route_to_all(n):
            return [n, n, n]

        r0, r1, r2 = [], [], []

        source = Source(fn=data.run, name="source")
        splitter = Split(fn=route_to_all, num_outputs=3, name="router")
        s0 = Sink(fn=r0.append, name="s0")
        s1 = Sink(fn=r1.append, name="s1")
        s2 = Sink(fn=r2.append, name="s2")

        g = network([
            (source, splitter),
            (splitter.out_0, s0),
            (splitter.out_1, s1),
            (splitter.out_2, s2)
        ])
        g.run_network()

        assert sorted(r0) == [10, 20, 30]
        assert sorted(r1) == [10, 20, 30]
        assert sorted(r2) == [10, 20, 30]

    def test_split_can_drop_messages(self):
        from components.sources.list_source import ListSource

        data = ListSource(items=[1, 2, 3, 4, 5])

        def route_or_drop(n):
            if n > 3:
                return [n, None]
            else:
                return [None, None]

        kept = []
        other = []

        source = Source(fn=data.run, name="source")
        splitter = Split(fn=route_or_drop, num_outputs=2, name="router")
        s0 = Sink(fn=kept.append, name="kept")
        s1 = Sink(fn=other.append, name="other")

        g = network([
            (source, splitter),
            (splitter.out_0, s0),
            (splitter.out_1, s1)
        ])
        g.run_network()

        assert sorted(kept) == [4, 5]
        assert other == []


class TestSplitWithSentiment:
    def test_sentiment_routing(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze_sentiment(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def route_by_sentiment(article):
            score = article["score"]
            if score > 0.2:
                return [article, article, None]
            elif score < -0.2:
                return [None, article, article]
            else:
                return [None, article, None]

        archive = []
        console = []
        alerts = []

        source = Source(fn=rss.run, name="bluesky")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        splitter = Split(fn=route_by_sentiment, num_outputs=3, name="router")
        archive_sink = Sink(fn=archive.append, name="archive")
        console_sink = Sink(fn=console.append, name="console")
        alert_sink = Sink(fn=alerts.append, name="alerts")

        g = network([
            (source, sentiment),
            (sentiment, splitter),
            (splitter.out_0, archive_sink),
            (splitter.out_1, console_sink),
            (splitter.out_2, alert_sink)
        ])
        g.run_network()

        for r in archive:
            assert r["score"] > 0.2
        for r in alerts:
            assert r["score"] < -0.2

    def test_split_with_spam_filter_before(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        spam_det = demo_ai_agent(SPAM_DETECTOR)
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def filter_spam(text):
            result = spam_det(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def route_by_sentiment(article):
            score = article["score"]
            if score > 0.2:
                return [article, None]
            else:
                return [None, article]

        positive = []
        other = []

        source = Source(fn=rss.run, name="source")
        spam_gate = Transform(fn=filter_spam, name="spam")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        splitter = Split(fn=route_by_sentiment, num_outputs=2, name="router")
        pos_sink = Sink(fn=positive.append, name="positive")
        other_sink = Sink(fn=other.append, name="other")

        g = network([
            (source, spam_gate),
            (spam_gate, sentiment),
            (sentiment, splitter),
            (splitter.out_0, pos_sink),
            (splitter.out_1, other_sink)
        ])
        g.run_network()

        spam_keywords = ['click here', 'free money',
                         'act now', 'make money fast']
        for r in positive + other:
            text_lower = r["text"].lower()
            for kw in spam_keywords:
                assert kw not in text_lower

        for r in positive:
            assert r["score"] > 0.2


class TestSplitWithFanin:
    def test_fanin_then_split(self):
        rss1 = DemoRSSSource(feed_name="hacker_news", max_articles=5)
        rss2 = DemoRSSSource(feed_name="tech_news", max_articles=5)
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def route(article):
            if article["score"] > 0.2:
                return [article, None]
            else:
                return [None, article]

        positive = []
        other = []

        src1 = Source(fn=rss1.run, name="hn")
        src2 = Source(fn=rss2.run, name="tech")
        sentiment = Transform(fn=analyze, name="sentiment")
        splitter = Split(fn=route, num_outputs=2, name="router")
        pos_sink = Sink(fn=positive.append, name="pos")
        other_sink = Sink(fn=other.append, name="other")

        g = network([
            (src1, sentiment),
            (src2, sentiment),
            (sentiment, splitter),
            (splitter.out_0, pos_sink),
            (splitter.out_1, other_sink)
        ])
        g.run_network()

        assert len(positive) + len(other) == 10
