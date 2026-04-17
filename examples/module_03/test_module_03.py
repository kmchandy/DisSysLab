# examples/module_03/test_module_03.py

"""
Tests for Module 03: Smart Routing

Tests are organized in three layers:
    1. Component tests  — do the individual components work correctly?
    2. Function tests   — do the transform and routing functions behave correctly?
    3. Network tests    — do the full pipelines produce the right results?

Key behaviors being tested:
    - Split routing function returns correct list structure
    - Each article goes to exactly one output port
    - Positive → out_0, Negative → out_1, Neutral → out_2
    - Spam is dropped before routing (extended app)

Run from the DisSysLab root directory:
    pytest examples/module_03/test_module_03.py -v
"""

import json
import pytest
from dissyslab.components.sources.demo_rss_source import DemoRSSSource, DEMO_FEEDS
from dissyslab.components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent
from dissyslab.components.sinks import DemoEmailAlerter, JSONLRecorder
from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink, Split


# ============================================================================
# Layer 1: Component Tests
# ============================================================================

class TestDemoComponents:
    """Demo components produce correct output shapes."""

    def test_rss_source_produces_strings(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        article = rss.run()
        assert article is not None
        assert isinstance(article, str)

    def test_sentiment_analyzer_returns_required_keys(self):
        analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("Python is great!")
        assert "sentiment" in result
        assert "score" in result
        assert result["sentiment"] in ["POSITIVE", "NEGATIVE", "NEUTRAL"]

    def test_demo_email_alerter_accepts_dict(self):
        alerter = DemoEmailAlerter(to_address="test@example.com",
                                   subject_prefix="[TEST]")
        # Should not raise
        alerter.run({"text": "Test article",
                    "sentiment": "NEGATIVE", "score": -0.5})


# ============================================================================
# Layer 2: Transform and Routing Function Tests
# ============================================================================

class TestRoutingFunction:
    """The routing function returns the correct list structure."""

    def setup_method(self):
        self.sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        self.spam_detector = demo_ai_agent(SPAM_DETECTOR)

    def _analyze_sentiment(self, text):
        result = self.sentiment_analyzer(text)
        return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

    def _route_by_sentiment(self, article):
        if article["sentiment"] == "POSITIVE":
            return [article, None,    None]
        elif article["sentiment"] == "NEGATIVE":
            return [None,    article, None]
        else:
            return [None,    None,    article]

    def test_routing_returns_list(self):
        article = {"text": "test", "sentiment": "POSITIVE", "score": 0.8}
        result = self._route_by_sentiment(article)
        assert isinstance(result, list)

    def test_routing_returns_correct_length(self):
        article = {"text": "test", "sentiment": "POSITIVE", "score": 0.8}
        result = self._route_by_sentiment(article)
        assert len(result) == 3

    def test_positive_routes_to_index_0(self):
        article = {"text": "amazing!", "sentiment": "POSITIVE", "score": 0.9}
        result = self._route_by_sentiment(article)
        assert result[0] is not None    # out_0 gets the article
        assert result[1] is None        # out_1 skipped
        assert result[2] is None        # out_2 skipped

    def test_negative_routes_to_index_1(self):
        article = {"text": "terrible!", "sentiment": "NEGATIVE", "score": -0.8}
        result = self._route_by_sentiment(article)
        assert result[0] is None        # out_0 skipped
        assert result[1] is not None    # out_1 gets the article
        assert result[2] is None        # out_2 skipped

    def test_neutral_routes_to_index_2(self):
        article = {"text": "normal day", "sentiment": "NEUTRAL", "score": 0.0}
        result = self._route_by_sentiment(article)
        assert result[0] is None        # out_0 skipped
        assert result[1] is None        # out_1 skipped
        assert result[2] is not None    # out_2 gets the article

    def test_exactly_one_non_none_per_route(self):
        """Every article goes to exactly one destination."""
        for sentiment in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
            article = {"text": "test", "sentiment": sentiment, "score": 0.0}
            result = self._route_by_sentiment(article)
            non_none = [x for x in result if x is not None]
            assert len(non_none) == 1, \
                f"Expected 1 non-None for {sentiment}, got {len(non_none)}"

    def test_filter_spam_drops_spam(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector("CLICK HERE for FREE MONEY!")
        assert result["is_spam"] is True

    def test_filter_spam_passes_legit(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector("Python 3.13 released with performance improvements")
        assert result["is_spam"] is False


# ============================================================================
# Layer 3: Full Network Tests
# ============================================================================

class TestAppNetwork:
    """The complete app.py pipeline routes articles correctly."""

    def _make_pipeline(self, tmp_path):
        rss = DemoRSSSource(feed_name="hacker_news")
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        pos_path = str(tmp_path / "positive.jsonl")
        pos_recorder = JSONLRecorder(path=pos_path, mode="w", flush_every=1)
        alerter = DemoEmailAlerter(to_address="test@example.com",
                                              subject_prefix="[TEST]")

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def route_by_sentiment(article):
            if article["sentiment"] == "POSITIVE":
                return [article, None,    None]
            elif article["sentiment"] == "NEGATIVE":
                return [None,    article, None]
            else:
                return [None,    None,    article]

        neutral_results = []
        negative_results = []

        source = Source(fn=rss.run,              name="rss_feed")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        splitter = Split(fn=route_by_sentiment,
                         num_outputs=3, name="router")
        archive = Sink(fn=pos_recorder.run,       name="archive")
        alerts = Sink(fn=negative_results.append, name="alerts")
        display = Sink(fn=neutral_results.append,  name="display")

        g = network([
            (source,         sentiment),
            (sentiment,      splitter),
            (splitter.out_0, archive),
            (splitter.out_1, alerts),
            (splitter.out_2, display)
        ])
        return g, neutral_results, negative_results, pos_path

    def test_pipeline_runs_without_error(self, tmp_path):
        g, neutral, negative, pos_path = self._make_pipeline(tmp_path)
        g.run_network()
        total = (neutral + negative +
                 [1] * sum(1 for _ in open(pos_path) if _.strip()))
        assert len(total) > 0

    def test_all_articles_routed_somewhere(self, tmp_path):
        g, neutral, negative, pos_path = self._make_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive_count = sum(1 for l in f if l.strip())
        total_routed = positive_count + len(negative) + len(neutral)
        # All non-spam articles should be routed somewhere
        assert total_routed > 0

    def test_no_article_routed_to_multiple_destinations(self, tmp_path):
        """Each article text should appear in exactly one destination."""
        g, neutral, negative, pos_path = self._make_pipeline(tmp_path)
        g.run_network()

        with open(pos_path) as f:
            positive = [json.loads(l) for l in f if l.strip()]

        all_texts = (
            [r["text"] for r in positive] +
            [r["text"] for r in negative] +
            [r["text"] for r in neutral]
        )
        # No duplicates — each article in exactly one place
        assert len(all_texts) == len(set(all_texts)), \
            "Some articles appeared in more than one destination"

    def test_positive_articles_in_archive(self, tmp_path):
        g, neutral, negative, pos_path = self._make_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive = [json.loads(l) for l in f if l.strip()]
        for r in positive:
            assert r["sentiment"] == "POSITIVE", \
                f"Non-positive article in archive: {r['text']}"

    def test_negative_articles_in_alerts(self, tmp_path):
        g, neutral, negative, pos_path = self._make_pipeline(tmp_path)
        g.run_network()
        for r in negative:
            assert r["sentiment"] == "NEGATIVE", \
                f"Non-negative article in alerts: {r['text']}"

    def test_neutral_articles_in_display(self, tmp_path):
        g, neutral, negative, pos_path = self._make_pipeline(tmp_path)
        g.run_network()
        for r in neutral:
            assert r["sentiment"] == "NEUTRAL", \
                f"Non-neutral article in display: {r['text']}"


class TestAppExtendedNetwork:
    """The app_extended.py pipeline — spam filter + Split routing."""

    def _make_extended_pipeline(self, tmp_path):
        rss = DemoRSSSource(feed_name="hacker_news")
        spam_detector = demo_ai_agent(SPAM_DETECTOR)
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        pos_path = str(tmp_path / "positive_ext.jsonl")
        pos_recorder = JSONLRecorder(path=pos_path, mode="w", flush_every=1)
        alerter = DemoEmailAlerter(to_address="test@example.com",
                                              subject_prefix="[TEST]")

        def filter_spam(text):
            result = spam_detector(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def route_by_sentiment(article):
            if article["sentiment"] == "POSITIVE":
                return [article, None,    None]
            elif article["sentiment"] == "NEGATIVE":
                return [None,    article, None]
            else:
                return [None,    None,    article]

        neutral_results = []
        negative_results = []

        source = Source(fn=rss.run,               name="rss_feed")
        spam_gate = Transform(fn=filter_spam,        name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment,  name="sentiment")
        splitter = Split(fn=route_by_sentiment,
                         num_outputs=3, name="router")
        archive = Sink(fn=pos_recorder.run,        name="archive")
        alerts = Sink(fn=negative_results.append, name="alerts")
        display = Sink(fn=neutral_results.append,  name="display")

        g = network([
            (source,         spam_gate),
            (spam_gate,      sentiment),
            (sentiment,      splitter),
            (splitter.out_0, archive),
            (splitter.out_1, alerts),
            (splitter.out_2, display)
        ])
        return g, neutral_results, negative_results, pos_path

    def test_extended_runs_without_error(self, tmp_path):
        g, neutral, negative, pos_path = self._make_extended_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive_count = sum(1 for l in f if l.strip())
        total = positive_count + len(negative) + len(neutral)
        assert total > 0

    def test_extended_fewer_total_than_feed(self, tmp_path):
        """Spam filtering should reduce the total article count."""
        g, neutral, negative, pos_path = self._make_extended_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive_count = sum(1 for l in f if l.strip())
        total_routed = positive_count + len(negative) + len(neutral)
        feed_total = len(DEMO_FEEDS["hacker_news"])
        assert total_routed < feed_total, \
            "Spam filter should reduce total article count"

    def test_extended_correct_routing(self, tmp_path):
        """Articles still route to correct destinations after spam filtering."""
        g, neutral, negative, pos_path = self._make_extended_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive = [json.loads(l) for l in f if l.strip()]
        for r in positive:
            assert r["sentiment"] == "POSITIVE"
        for r in negative:
            assert r["sentiment"] == "NEGATIVE"
        for r in neutral:
            assert r["sentiment"] == "NEUTRAL"
