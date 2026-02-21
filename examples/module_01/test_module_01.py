# examples/module_01_describe_and_build/test_module_01.py

"""
Tests for Module 01: Describe and Build

Tests are organized in three layers:
    1. Component tests  — do the individual components work correctly?
    2. Function tests   — do the transform functions behave correctly?
    3. Network tests    — do the full pipelines produce the right results?

Run from the DisSysLab root directory:
    pytest examples/module_01_describe_and_build/test_module_01.py -v
"""

import pytest
from components.sources.demo_rss_source import DemoRSSSource, DEMO_FEEDS
from components.transformers.prompts import (
    SPAM_DETECTOR, SENTIMENT_ANALYZER, URGENCY_DETECTOR
)
from components.transformers.demo_ai_agent import demo_ai_agent
from dsl import network
from dsl.blocks import Source, Transform, Sink


# ============================================================================
# Layer 1: Component Tests (no network, just the components themselves)
# ============================================================================

class TestDemoRSSSource:
    """DemoRSSSource produces the right data in the right shape."""

    def test_returns_articles(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        first = rss.run()
        assert first is not None
        assert isinstance(first, str)

    def test_returns_none_when_exhausted(self):
        rss = DemoRSSSource(feed_name="hacker_news", max_articles=2)
        rss.run()   # article 1
        rss.run()   # article 2
        assert rss.run() is None

    def test_respects_max_articles(self):
        rss = DemoRSSSource(feed_name="hacker_news", max_articles=3)
        articles = []
        while True:
            article = rss.run()
            if article is None:
                break
            articles.append(article)
        assert len(articles) == 3

    def test_all_feeds_exist(self):
        for feed_name in ["hacker_news", "tech_news", "reddit_python"]:
            rss = DemoRSSSource(feed_name=feed_name)
            first = rss.run()
            assert first is not None, f"Feed '{feed_name}' returned None on first call"
            assert isinstance(
                first, str), f"Feed '{feed_name}' returned non-string"


class TestDemoAiAgent:
    """demo_ai_agent returns the right structure for each prompt type."""

    def test_spam_detector_catches_spam(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector("CLICK HERE for FREE MONEY! Limited time offer!")
        assert "is_spam" in result
        assert result["is_spam"] is True

    def test_spam_detector_passes_legitimate(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector("Python 3.13 released with performance improvements")
        assert "is_spam" in result
        assert result["is_spam"] is False

    def test_spam_detector_returns_required_keys(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector("Any text here")
        assert "is_spam" in result
        assert "confidence" in result
        assert "reason" in result

    def test_sentiment_analyzer_returns_required_keys(self):
        analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("This is amazing and wonderful!")
        assert "sentiment" in result
        assert "score" in result
        assert "reasoning" in result

    def test_sentiment_positive(self):
        analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("This is amazing and wonderful!")
        assert result["sentiment"] == "POSITIVE"

    def test_sentiment_negative(self):
        analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("This is terrible and awful.")
        assert result["sentiment"] == "NEGATIVE"

    def test_sentiment_valid_values(self):
        analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("Some text")
        assert result["sentiment"] in ["POSITIVE", "NEGATIVE", "NEUTRAL"]
        assert isinstance(result["score"], float)

    def test_urgency_detector_returns_required_keys(self):
        detector = demo_ai_agent(URGENCY_DETECTOR)
        result = detector("URGENT! Critical security breach! Act now!")
        assert "urgency" in result
        assert "metrics" in result
        assert "reasoning" in result

    def test_urgency_high(self):
        detector = demo_ai_agent(URGENCY_DETECTOR)
        result = detector("URGENT! Critical emergency! Act immediately!")
        assert result["urgency"] == "HIGH"

    def test_urgency_valid_values(self):
        detector = demo_ai_agent(URGENCY_DETECTOR)
        result = detector("Some text")
        assert result["urgency"] in ["HIGH", "MEDIUM", "LOW"]


# ============================================================================
# Layer 2: Transform Function Tests
# Tests the functions defined in app.py in isolation — no network needed.
# ============================================================================

class TestTransformFunctions:
    """The transform functions from app.py behave correctly."""

    def setup_method(self):
        """Fresh agents for each test."""
        self.spam_detector = demo_ai_agent(SPAM_DETECTOR)
        self.sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        self.urgency_detector = demo_ai_agent(URGENCY_DETECTOR)

    # Mirror the functions from app.py exactly
    def _filter_spam(self, text):
        result = self.spam_detector(text)
        if result["is_spam"]:
            return None
        return text

    def _analyze_sentiment(self, text):
        result = self.sentiment_analyzer(text)
        return {
            "text":      text,
            "sentiment": result["sentiment"],
            "score":     result["score"]
        }

    def _only_positive(self, article):
        if article["sentiment"] == "NEGATIVE":
            return None
        return article

    def _analyze_urgency(self, article):
        result = self.urgency_detector(article["text"])
        article["urgency"] = result["urgency"]
        return article

    # filter_spam tests
    def test_filter_spam_returns_none_for_spam(self):
        assert self._filter_spam("CLICK HERE for FREE MONEY!") is None

    def test_filter_spam_returns_text_for_legit(self):
        text = "Python 3.13 released with performance improvements"
        assert self._filter_spam(text) == text

    # analyze_sentiment tests
    def test_analyze_sentiment_returns_dict(self):
        result = self._analyze_sentiment("This is great!")
        assert isinstance(result, dict)

    def test_analyze_sentiment_preserves_text(self):
        text = "This is great!"
        result = self._analyze_sentiment(text)
        assert result["text"] == text

    def test_analyze_sentiment_has_required_keys(self):
        result = self._analyze_sentiment("Some text")
        assert "text" in result
        assert "sentiment" in result
        assert "score" in result

    # only_positive tests
    def test_only_positive_drops_negative(self):
        article = {"text": "bad day", "sentiment": "NEGATIVE", "score": -0.5}
        assert self._only_positive(article) is None

    def test_only_positive_keeps_positive(self):
        article = {"text": "great day", "sentiment": "POSITIVE", "score": 0.7}
        assert self._only_positive(article) is not None

    def test_only_positive_keeps_neutral(self):
        article = {"text": "normal day", "sentiment": "NEUTRAL", "score": 0.0}
        assert self._only_positive(article) is not None

    # analyze_urgency tests
    def test_analyze_urgency_adds_urgency_key(self):
        article = {"text": "URGENT! Critical issue!",
                   "sentiment": "NEGATIVE", "score": -0.5}
        result = self._analyze_urgency(article)
        assert "urgency" in result

    def test_analyze_urgency_preserves_existing_keys(self):
        article = {"text": "some text", "sentiment": "POSITIVE", "score": 0.7}
        result = self._analyze_urgency(article)
        assert result["text"] == "some text"
        assert result["sentiment"] == "POSITIVE"


# ============================================================================
# Layer 3: Full Network Tests
# Tests the complete pipelines from app.py and app_extended.py.
# ============================================================================

class TestAppNetwork:
    """The complete pipeline from app.py produces correct results."""

    def _make_pipeline(self, feed="hacker_news"):
        """Build the app.py pipeline and return (network, results_list)."""
        rss = DemoRSSSource(feed_name=feed)
        spam_detector = demo_ai_agent(SPAM_DETECTOR)
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

        def filter_spam(text):
            result = spam_detector(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results = []
        source = Source(fn=rss.run,              name="rss_feed")
        spam_gate = Transform(fn=filter_spam,       name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        collector = Sink(fn=results.append,         name="collector")

        g = network([
            (source,    spam_gate),
            (spam_gate, sentiment),
            (sentiment, collector)
        ])
        return g, results

    def test_pipeline_runs_without_error(self):
        g, results = self._make_pipeline()
        g.run_network()
        assert len(results) > 0, "Pipeline produced no results"

    def test_all_results_have_required_keys(self):
        g, results = self._make_pipeline()
        g.run_network()
        for r in results:
            assert "text" in r,      f"Missing 'text' in: {r}"
            assert "sentiment" in r, f"Missing 'sentiment' in: {r}"
            assert "score" in r,     f"Missing 'score' in: {r}"

    def test_spam_is_filtered_out(self):
        g, results = self._make_pipeline()
        g.run_network()

        spam_keywords = [
            "click here", "buy now", "limited time", "act now",
            "free money", "winner", "get rich", "make money fast"
        ]

        # Verify the original feed contains spam
        original_spam_count = sum(
            1 for article in DEMO_FEEDS["hacker_news"]
            if any(kw in article.lower() for kw in spam_keywords)
        )
        assert original_spam_count > 0, "Test data should contain spam articles"

        # Verify no spam in results
        for r in results:
            text_lower = r["text"].lower()
            for kw in spam_keywords:
                assert kw not in text_lower, f"Spam not filtered: '{r['text']}'"

    def test_results_fewer_than_original(self):
        g, results = self._make_pipeline()
        g.run_network()
        original_count = len(DEMO_FEEDS["hacker_news"])
        assert len(results) < original_count, \
            "Spam filter should reduce article count"

    def test_all_feeds_work(self):
        for feed in ["hacker_news", "tech_news", "reddit_python"]:
            g, results = self._make_pipeline(feed=feed)
            g.run_network()
            assert len(results) > 0, f"Feed '{feed}' produced no results"


class TestAppExtendedNetwork:
    """The complete pipeline from app_extended.py produces correct results."""

    def _make_extended_pipeline(self):
        """Build the app_extended.py pipeline and return (network, results_list)."""
        rss = DemoRSSSource(feed_name="hacker_news")
        spam_detector = demo_ai_agent(SPAM_DETECTOR)
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        urgency_detector = demo_ai_agent(URGENCY_DETECTOR)

        def filter_spam(text):
            result = spam_detector(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def only_positive(article):
            return None if article["sentiment"] == "NEGATIVE" else article

        def analyze_urgency(article):
            result = urgency_detector(article["text"])
            article["urgency"] = result["urgency"]
            return article

        results = []
        source = Source(fn=rss.run,              name="rss_feed")
        spam_gate = Transform(fn=filter_spam,       name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        positive_filter = Transform(fn=only_positive,     name="positive_only")
        urgency = Transform(fn=analyze_urgency,   name="urgency")
        collector = Sink(fn=results.append,         name="collector")

        g = network([
            (source,          spam_gate),
            (spam_gate,       sentiment),
            (sentiment,       positive_filter),
            (positive_filter, urgency),
            (urgency,         collector)
        ])
        return g, results

    def test_extended_pipeline_runs_without_error(self):
        g, results = self._make_extended_pipeline()
        g.run_network()
        assert len(results) > 0, "Extended pipeline produced no results"

    def test_all_results_have_required_keys(self):
        g, results = self._make_extended_pipeline()
        g.run_network()
        for r in results:
            assert "text" in r
            assert "sentiment" in r
            assert "urgency" in r

    def test_no_negative_articles_in_results(self):
        g, results = self._make_extended_pipeline()
        g.run_network()
        for r in results:
            assert r["sentiment"] != "NEGATIVE", \
                f"Negative article not filtered: '{r['text']}'"

    def test_extended_produces_fewer_results_than_basic(self):
        """Two filters should produce fewer results than one."""
        g_basic, results_basic = self._make_pipeline_basic()
        g_basic.run_network()

        g_extended, results_extended = self._make_extended_pipeline()
        g_extended.run_network()

        assert len(results_extended) <= len(results_basic), \
            "Adding a second filter should not increase result count"

    def _make_pipeline_basic(self):
        """Build the basic (non-extended) pipeline for comparison."""
        rss = DemoRSSSource(feed_name="hacker_news")
        spam_detector = demo_ai_agent(SPAM_DETECTOR)
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

        def filter_spam(text):
            result = spam_detector(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results = []
        source = Source(fn=rss.run,              name="rss_feed")
        spam_gate = Transform(fn=filter_spam,       name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        collector = Sink(fn=results.append,         name="collector")

        g = network([
            (source,    spam_gate),
            (spam_gate, sentiment),
            (sentiment, collector)
        ])
        return g, results
