# examples/module_01_describe_and_build/test_module_01.py

"""
Tests for Module 01: Describe and Build

Tests are organized in three layers:
    1. Component tests — do the individual functions work correctly?
    2. Network tests — do the full pipelines produce the right results?
    3. Filtering tests — does returning None actually drop messages?

Run from the DisSysLab root directory:
    pytest examples/module_01_describe_and_build/test_module_01.py -v
"""

import pytest
from components.sources.mock_rss_source import MockRSSSource, MOCK_FEEDS
from components.transformers.mock_claude_agent import MockClaudeAgent
from dsl import network
from dsl.blocks import Source, Transform, Sink


# ====================================================================
# Layer 1: Component Tests (no network, just functions)
# ====================================================================

class TestMockRSSSource:
    """Test that MockRSSSource produces data correctly."""

    def test_returns_articles(self):
        rss = MockRSSSource(feed_name="hacker_news")
        first = rss.run()
        assert first is not None
        assert isinstance(first, str)

    def test_returns_none_when_exhausted(self):
        rss = MockRSSSource(feed_name="hacker_news", max_articles=2)
        rss.run()  # article 1
        rss.run()  # article 2
        assert rss.run() is None

    def test_respects_max_articles(self):
        rss = MockRSSSource(feed_name="hacker_news", max_articles=3)
        articles = []
        while True:
            article = rss.run()
            if article is None:
                break
            articles.append(article)
        assert len(articles) == 3

    def test_all_feeds_exist(self):
        for feed_name in ["hacker_news", "tech_news", "reddit_python"]:
            rss = MockRSSSource(feed_name=feed_name)
            assert rss.run(
            ) is not None, f"Feed '{feed_name}' returned None on first call"


class TestMockClaudeAgent:
    """Test that MockClaudeAgent analyzes text correctly."""

    def test_spam_detection_catches_spam(self):
        detector = MockClaudeAgent(task="spam_detection")
        result = detector.run("CLICK HERE for FREE MONEY!")
        assert result["is_spam"] is True

    def test_spam_detection_passes_legitimate(self):
        detector = MockClaudeAgent(task="spam_detection")
        result = detector.run(
            "Python 3.13 released with performance improvements")
        assert result["is_spam"] is False

    def test_sentiment_analysis_returns_required_keys(self):
        analyzer = MockClaudeAgent(task="sentiment_analysis")
        result = analyzer.run("This is amazing and wonderful!")
        assert "sentiment" in result
        assert "score" in result
        assert result["sentiment"] in ["POSITIVE", "NEGATIVE", "NEUTRAL"]

    def test_sentiment_positive(self):
        analyzer = MockClaudeAgent(task="sentiment_analysis")
        result = analyzer.run("This is amazing and wonderful!")
        assert result["sentiment"] == "POSITIVE"

    def test_sentiment_negative(self):
        analyzer = MockClaudeAgent(task="sentiment_analysis")
        result = analyzer.run("This is terrible and awful.")
        assert result["sentiment"] == "NEGATIVE"

    def test_urgency_detection_returns_required_keys(self):
        detector = MockClaudeAgent(task="urgency_detection")
        result = detector.run("URGENT! Critical security breach! Act now!")
        assert "urgency" in result
        assert result["urgency"] in ["HIGH", "MEDIUM", "LOW"]

    def test_urgency_high(self):
        detector = MockClaudeAgent(task="urgency_detection")
        result = detector.run(
            "URGENT! Critical emergency! Act immediately now!")
        assert result["urgency"] == "HIGH"


# ====================================================================
# Layer 2: Transform Function Tests (the functions from the examples)
# ====================================================================

class TestTransformFunctions:
    """Test the transform functions used in the example apps."""

    def setup_method(self):
        """Fresh mock agents for each test."""
        self.spam_detector = MockClaudeAgent(task="spam_detection")
        self.sentiment_analyzer = MockClaudeAgent(task="sentiment_analysis")
        self.urgency_detector = MockClaudeAgent(task="urgency_detection")

    def _filter_spam(self, text):
        result = self.spam_detector.run(text)
        if result["is_spam"]:
            return None
        return text

    def _analyze_sentiment(self, text):
        result = self.sentiment_analyzer.run(text)
        return {
            "text": text,
            "sentiment": result["sentiment"],
            "score": result["score"]
        }

    def _only_positive(self, article):
        if article["sentiment"] == "NEGATIVE":
            return None
        return article

    def _analyze_urgency(self, article):
        result = self.urgency_detector.run(article["text"])
        article["urgency"] = result["urgency"]
        return article

    def test_filter_spam_drops_spam(self):
        assert self._filter_spam("CLICK HERE for FREE MONEY!") is None

    def test_filter_spam_passes_legit(self):
        text = "Python 3.13 released with performance improvements"
        assert self._filter_spam(text) == text

    def test_analyze_sentiment_returns_dict_with_text(self):
        result = self._analyze_sentiment("This is great!")
        assert result["text"] == "This is great!"
        assert "sentiment" in result
        assert "score" in result

    def test_only_positive_drops_negative(self):
        article = {"text": "bad day", "sentiment": "NEGATIVE", "score": -0.5}
        assert self._only_positive(article) is None

    def test_only_positive_keeps_positive(self):
        article = {"text": "great day", "sentiment": "POSITIVE", "score": 0.7}
        assert self._only_positive(article) is not None

    def test_only_positive_keeps_neutral(self):
        article = {"text": "normal day", "sentiment": "NEUTRAL", "score": 0.0}
        assert self._only_positive(article) is not None

    def test_analyze_urgency_adds_key(self):
        article = {"text": "URGENT! Critical issue!",
                   "sentiment": "NEGATIVE", "score": -0.5}
        result = self._analyze_urgency(article)
        assert "urgency" in result


# ====================================================================
# Layer 3: Full Network Tests
# ====================================================================

class TestGeneratedNetwork:
    """Test the complete pipeline from example_generated.py."""

    def test_basic_pipeline_runs(self):
        """The basic pipeline runs without errors and collects results."""
        rss = MockRSSSource(feed_name="hacker_news")
        spam_detector = MockClaudeAgent(task="spam_detection")
        sentiment_analyzer = MockClaudeAgent(task="sentiment_analysis")

        def filter_spam(text):
            result = spam_detector.run(text)
            if result["is_spam"]:
                return None
            return text

        def analyze_sentiment(text):
            result = sentiment_analyzer.run(text)
            return {
                "text": text,
                "sentiment": result["sentiment"],
                "score": result["score"]
            }

        results = []

        source = Source(fn=rss.run, name="rss_feed")
        spam_gate = Transform(fn=filter_spam, name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        collector = Sink(fn=results.append, name="collector")

        g = network([
            (source, spam_gate),
            (spam_gate, sentiment),
            (sentiment, collector)
        ])

        g.run_network()

        # Should have results
        assert len(results) > 0, "Pipeline produced no results"

        # Each result should be a dict with required keys
        for r in results:
            assert "text" in r, f"Missing 'text' key in result: {r}"
            assert "sentiment" in r, f"Missing 'sentiment' key in result: {r}"
            assert "score" in r, f"Missing 'score' key in result: {r}"

    def test_spam_is_filtered(self):
        """Spam articles should not appear in the output."""
        rss = MockRSSSource(feed_name="hacker_news")
        spam_detector = MockClaudeAgent(task="spam_detection")
        sentiment_analyzer = MockClaudeAgent(task="sentiment_analysis")

        def filter_spam(text):
            result = spam_detector.run(text)
            if result["is_spam"]:
                return None
            return text

        def analyze_sentiment(text):
            result = sentiment_analyzer.run(text)
            return {
                "text": text,
                "sentiment": result["sentiment"],
                "score": result["score"]
            }

        results = []

        source = Source(fn=rss.run, name="rss_feed")
        spam_gate = Transform(fn=filter_spam, name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        collector = Sink(fn=results.append, name="collector")

        g = network([
            (source, spam_gate),
            (spam_gate, sentiment),
            (sentiment, collector)
        ])

        g.run_network()

        # Count spam in original feed
        spam_keywords = ['click here', 'buy now', 'limited time', 'act now',
                         'free money', 'winner', 'get rich', 'make money fast']
        original_spam_count = sum(
            1 for article in MOCK_FEEDS["hacker_news"]
            if any(kw in article.lower() for kw in spam_keywords)
        )
        assert original_spam_count > 0, "Test data should contain spam"

        # No spam in results
        for r in results:
            text_lower = r["text"].lower()
            for kw in spam_keywords:
                assert kw not in text_lower, f"Spam not filtered: '{r['text']}'"

        # Should have fewer results than original articles
        assert len(results) < len(MOCK_FEEDS["hacker_news"]), \
            "Filtering should reduce the number of articles"

    def test_all_feeds_work(self):
        """Pipeline should work with any mock feed."""
        for feed_name in ["hacker_news", "tech_news", "reddit_python"]:
            rss = MockRSSSource(feed_name=feed_name)
            spam_detector = MockClaudeAgent(task="spam_detection")
            sentiment_analyzer = MockClaudeAgent(task="sentiment_analysis")

            def filter_spam(text, _det=spam_detector):
                result = _det.run(text)
                if result["is_spam"]:
                    return None
                return text

            def analyze_sentiment(text, _ana=sentiment_analyzer):
                result = _ana.run(text)
                return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

            results = []

            source = Source(fn=rss.run, name="rss_feed")
            spam_gate = Transform(fn=filter_spam, name="spam_filter")
            sentiment = Transform(fn=analyze_sentiment, name="sentiment")
            collector = Sink(fn=results.append, name="collector")

            g = network([
                (source, spam_gate),
                (spam_gate, sentiment),
                (sentiment, collector)
            ])

            g.run_network()
            assert len(results) > 0, f"Feed '{feed_name}' produced no results"


class TestModifiedNetwork:
    """Test the extended pipeline from example_modified.py."""

    def test_modified_pipeline_runs(self):
        """The extended pipeline with urgency and positive filter runs."""
        rss = MockRSSSource(feed_name="hacker_news")
        spam_detector = MockClaudeAgent(task="spam_detection")
        sentiment_analyzer = MockClaudeAgent(task="sentiment_analysis")
        urgency_detector = MockClaudeAgent(task="urgency_detection")

        def filter_spam(text):
            result = spam_detector.run(text)
            if result["is_spam"]:
                return None
            return text

        def analyze_sentiment(text):
            result = sentiment_analyzer.run(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def only_positive(article):
            if article["sentiment"] == "NEGATIVE":
                return None
            return article

        def analyze_urgency(article):
            result = urgency_detector.run(article["text"])
            article["urgency"] = result["urgency"]
            return article

        results = []

        source = Source(fn=rss.run, name="rss_feed")
        spam_gate = Transform(fn=filter_spam, name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        positive_filter = Transform(fn=only_positive, name="positive_only")
        urgency = Transform(fn=analyze_urgency, name="urgency")
        collector = Sink(fn=results.append, name="collector")

        g = network([
            (source, spam_gate),
            (spam_gate, sentiment),
            (sentiment, positive_filter),
            (positive_filter, urgency),
            (urgency, collector)
        ])

        g.run_network()

        assert len(results) > 0, "Modified pipeline produced no results"

        # Every result should have all keys
        for r in results:
            assert "text" in r
            assert "sentiment" in r
            assert "urgency" in r

        # No negative sentiment should survive the filter
        for r in results:
            assert r["sentiment"] != "NEGATIVE", \
                f"Negative article not filtered: '{r['text']}'"

    def test_double_filter_reduces_count(self):
        """Two filters (spam + negative) should produce fewer results than one."""
        rss_1 = MockRSSSource(feed_name="hacker_news")
        rss_2 = MockRSSSource(feed_name="hacker_news")
        spam_det_1 = MockClaudeAgent(task="spam_detection")
        spam_det_2 = MockClaudeAgent(task="spam_detection")
        sent_1 = MockClaudeAgent(task="sentiment_analysis")
        sent_2 = MockClaudeAgent(task="sentiment_analysis")
        urg = MockClaudeAgent(task="urgency_detection")

        # Pipeline 1: spam filter only
        def filter_spam_1(text):
            result = spam_det_1.run(text)
            return None if result["is_spam"] else text

        def analyze_1(text):
            result = sent_1.run(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results_1 = []
        g1 = network([
            (Source(fn=rss_1.run, name="src"),
             Transform(fn=filter_spam_1, name="spam")),
            (Transform(fn=filter_spam_1, name="spam"),
             Transform(fn=analyze_1, name="sent")),
            (Transform(fn=analyze_1, name="sent"),
             Sink(fn=results_1.append, name="out"))
        ])
        g1.run_network()

        # Pipeline 2: spam filter + positive filter
        def filter_spam_2(text):
            result = spam_det_2.run(text)
            return None if result["is_spam"] else text

        def analyze_2(text):
            result = sent_2.run(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def only_pos(article):
            return None if article["sentiment"] == "NEGATIVE" else article

        def add_urgency(article):
            result = urg.run(article["text"])
            article["urgency"] = result["urgency"]
            return article

        results_2 = []

        src = Source(fn=rss_2.run, name="src")
        spam = Transform(fn=filter_spam_2, name="spam")
        sent = Transform(fn=analyze_2, name="sent")
        pos = Transform(fn=only_pos, name="pos")
        urgn = Transform(fn=add_urgency, name="urg")
        out = Sink(fn=results_2.append, name="out")

        g2 = network([
            (src, spam), (spam, sent), (sent, pos), (pos, urgn), (urgn, out)
        ])
        g2.run_network()

        assert len(results_2) <= len(results_1), \
            "Adding a filter should not increase result count"
