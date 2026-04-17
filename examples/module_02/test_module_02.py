# examples/module_02/test_module_02.py

"""
Tests for Module 02: Multiple Sources, Multiple Destinations

Tests are organized in three layers:
    1. Component tests  — do the individual components work correctly?
    2. Function tests   — do the transform functions behave correctly?
    3. Network tests    — do the full pipelines produce the right results?

Key behaviors being tested:
    - Fanin: messages from two sources both arrive at the sentiment node
    - Fanout: each analyzed article reaches both sinks
    - Filtering: spam is dropped before reaching downstream nodes (extended app)

Run from the DisSysLab root directory:
    pytest examples/module_02/test_module_02.py -v
"""

import os
import json
import pytest
from dissyslab.components.sources.demo_rss_source import DemoRSSSource, DEMO_FEEDS
from dissyslab.components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent
from dissyslab.components.sinks import JSONLRecorder
from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink


# ============================================================================
# Layer 1: Component Tests
# ============================================================================

class TestDemoRSSSource:
    """Both demo feeds produce articles correctly."""

    def test_hacker_news_produces_articles(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        first = rss.run()
        assert first is not None
        assert isinstance(first, str)

    def test_tech_news_produces_articles(self):
        rss = DemoRSSSource(feed_name="tech_news")
        first = rss.run()
        assert first is not None
        assert isinstance(first, str)

    def test_both_feeds_exhaust_cleanly(self):
        for feed in ["hacker_news", "tech_news"]:
            rss = DemoRSSSource(feed_name=feed, max_articles=3)
            count = 0
            while True:
                article = rss.run()
                if article is None:
                    break
                count += 1
            assert count == 3, f"Feed '{feed}' did not produce exactly 3 articles"


class TestJSONLRecorder:
    """JSONLRecorder writes valid JSON lines."""

    def test_writes_dict_to_file(self, tmp_path):
        path = str(tmp_path / "test.jsonl")
        recorder = JSONLRecorder(path=path, mode="w", flush_every=1)
        recorder.run({"text": "hello", "sentiment": "POSITIVE", "score": 0.8})
        with open(path) as f:
            line = f.readline()
        data = json.loads(line)
        assert data["text"] == "hello"
        assert data["sentiment"] == "POSITIVE"

    def test_writes_multiple_records(self, tmp_path):
        path = str(tmp_path / "test.jsonl")
        recorder = JSONLRecorder(path=path, mode="w", flush_every=1)
        recorder.run(
            {"text": "first",  "sentiment": "POSITIVE", "score":  0.8})
        recorder.run(
            {"text": "second", "sentiment": "NEGATIVE", "score": -0.5})
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["text"] == "first"
        assert json.loads(lines[1])["text"] == "second"


# ============================================================================
# Layer 2: Transform Function Tests
# ============================================================================

class TestTransformFunctions:
    """The transform functions from app.py behave correctly."""

    def setup_method(self):
        self.spam_detector = demo_ai_agent(SPAM_DETECTOR)
        self.sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

    def _analyze_sentiment(self, text):
        result = self.sentiment_analyzer(text)
        return {
            "text":      text,
            "sentiment": result["sentiment"],
            "score":     result["score"]
        }

    def _filter_spam(self, text):
        result = self.spam_detector(text)
        return None if result["is_spam"] else text

    def test_analyze_sentiment_returns_dict(self):
        result = self._analyze_sentiment("Python is great!")
        assert isinstance(result, dict)

    def test_analyze_sentiment_has_required_keys(self):
        result = self._analyze_sentiment("Some text")
        assert "text" in result
        assert "sentiment" in result
        assert "score" in result

    def test_analyze_sentiment_preserves_text(self):
        text = "Python is great!"
        result = self._analyze_sentiment(text)
        assert result["text"] == text

    def test_analyze_sentiment_valid_values(self):
        result = self._analyze_sentiment("Some text")
        assert result["sentiment"] in ["POSITIVE", "NEGATIVE", "NEUTRAL"]
        assert isinstance(result["score"], float)

    def test_filter_spam_drops_spam(self):
        assert self._filter_spam("CLICK HERE for FREE MONEY!") is None

    def test_filter_spam_passes_legitimate(self):
        text = "Python 3.13 released with performance improvements"
        assert self._filter_spam(text) == text


# ============================================================================
# Layer 3: Full Network Tests
# ============================================================================

class TestFaninNetwork:
    """Fanin: messages from both sources reach the sentiment node."""

    def _make_fanin_pipeline(self):
        hn = DemoRSSSource(feed_name="hacker_news")
        tech = DemoRSSSource(feed_name="tech_news")
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results = []
        hn_source = Source(fn=hn.run,              name="hacker_news")
        tech_source = Source(fn=tech.run,            name="tech_news")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        collector = Sink(fn=results.append,         name="collector")

        g = network([
            (hn_source,   sentiment),
            (tech_source, sentiment),
            (sentiment,   collector)
        ])
        return g, results

    def test_fanin_pipeline_runs_without_error(self):
        g, results = self._make_fanin_pipeline()
        g.run_network()
        assert len(results) > 0

    def test_fanin_receives_from_both_sources(self):
        g, results = self._make_fanin_pipeline()
        g.run_network()
        # Should have articles from both feeds combined
        hn_count = len(DEMO_FEEDS["hacker_news"])
        tech_count = len(DEMO_FEEDS["tech_news"])
        assert len(results) == hn_count + tech_count, \
            "Fanin should collect articles from both feeds"

    def test_all_results_have_required_keys(self):
        g, results = self._make_fanin_pipeline()
        g.run_network()
        for r in results:
            assert "text" in r
            assert "sentiment" in r
            assert "score" in r


class TestFanoutNetwork:
    """Fanout: each analyzed article reaches both sinks."""

    def _make_fanout_pipeline(self, tmp_path):
        hn = DemoRSSSource(feed_name="hacker_news")
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        path = str(tmp_path / "fanout_test.jsonl")
        recorder = JSONLRecorder(path=path, mode="w", flush_every=1)

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        display_results = []
        hn_source = Source(fn=hn.run,              name="hacker_news")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        display = Sink(fn=display_results.append, name="display")
        archive = Sink(fn=recorder.run,           name="archive")

        g = network([
            (hn_source, sentiment),
            (sentiment, display),
            (sentiment, archive)
        ])
        return g, display_results, path

    def test_fanout_both_sinks_receive_results(self, tmp_path):
        g, display_results, path = self._make_fanout_pipeline(tmp_path)
        g.run_network()

        # Display sink received results
        assert len(display_results) > 0, "Display sink received no results"

        # File sink received results
        with open(path) as f:
            lines = [l for l in f.readlines() if l.strip()]
        assert len(lines) > 0, "Archive sink wrote nothing to file"

    def test_fanout_both_sinks_receive_same_count(self, tmp_path):
        g, display_results, path = self._make_fanout_pipeline(tmp_path)
        g.run_network()

        with open(path) as f:
            file_count = sum(1 for l in f if l.strip())

        assert len(display_results) == file_count, \
            "Both sinks should receive the same number of messages"

    def test_fanout_file_contains_valid_json(self, tmp_path):
        g, _, path = self._make_fanout_pipeline(tmp_path)
        g.run_network()

        with open(path) as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    assert "text" in obj
                    assert "sentiment" in obj


class TestAppNetwork:
    """The complete app.py pipeline — fanin + fanout together."""

    def _make_app_pipeline(self, tmp_path):
        hn = DemoRSSSource(feed_name="hacker_news")
        tech = DemoRSSSource(feed_name="tech_news")
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        path = str(tmp_path / "app_test.jsonl")
        recorder = JSONLRecorder(path=path, mode="w", flush_every=1)

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        display_results = []
        hn_source = Source(fn=hn.run,              name="hacker_news")
        tech_source = Source(fn=tech.run,            name="tech_news")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        display = Sink(fn=display_results.append, name="display")
        archive = Sink(fn=recorder.run,           name="archive")

        g = network([
            (hn_source,   sentiment),
            (tech_source, sentiment),
            (sentiment,   display),
            (sentiment,   archive)
        ])
        return g, display_results, path

    def test_app_runs_without_error(self, tmp_path):
        g, results, _ = self._make_app_pipeline(tmp_path)
        g.run_network()
        assert len(results) > 0

    def test_app_collects_from_both_feeds(self, tmp_path):
        g, results, _ = self._make_app_pipeline(tmp_path)
        g.run_network()
        expected = len(DEMO_FEEDS["hacker_news"]) + \
            len(DEMO_FEEDS["tech_news"])
        assert len(results) == expected

    def test_app_both_sinks_match(self, tmp_path):
        g, display_results, path = self._make_app_pipeline(tmp_path)
        g.run_network()
        with open(path) as f:
            file_count = sum(1 for l in f if l.strip())
        assert len(display_results) == file_count


class TestAppExtendedNetwork:
    """The app_extended.py pipeline — fanin + spam filter + fanout."""

    def _make_extended_pipeline(self, tmp_path):
        hn = DemoRSSSource(feed_name="hacker_news")
        tech = DemoRSSSource(feed_name="tech_news")
        spam_detector = demo_ai_agent(SPAM_DETECTOR)
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        path = str(tmp_path / "extended_test.jsonl")
        recorder = JSONLRecorder(path=path, mode="w", flush_every=1)

        def filter_spam(text):
            result = spam_detector(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        display_results = []
        hn_source = Source(fn=hn.run,              name="hacker_news")
        tech_source = Source(fn=tech.run,            name="tech_news")
        spam_gate = Transform(fn=filter_spam,       name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        display = Sink(fn=display_results.append, name="display")
        archive = Sink(fn=recorder.run,           name="archive")

        g = network([
            (hn_source,   spam_gate),
            (tech_source, spam_gate),
            (spam_gate,   sentiment),
            (sentiment,   display),
            (sentiment,   archive)
        ])
        return g, display_results, path

    def test_extended_runs_without_error(self, tmp_path):
        g, results, _ = self._make_extended_pipeline(tmp_path)
        g.run_network()
        assert len(results) > 0

    def test_extended_fewer_results_than_basic(self, tmp_path):
        """Spam filtering should reduce the total article count."""
        g, results, _ = self._make_extended_pipeline(tmp_path)
        g.run_network()
        total_articles = (len(DEMO_FEEDS["hacker_news"]) +
                          len(DEMO_FEEDS["tech_news"]))
        assert len(results) < total_articles, \
            "Spam filter should reduce article count below total feed size"

    def test_extended_both_sinks_match(self, tmp_path):
        g, display_results, path = self._make_extended_pipeline(tmp_path)
        g.run_network()
        with open(path) as f:
            file_count = sum(1 for l in f if l.strip())
        assert len(display_results) == file_count
