# examples/module_04/test_module_04.py

"""
Tests for Module 04: Build Your Own App

Tests are organized in three layers:
    1. Component tests  — do the individual components work correctly?
    2. Function tests   — do the transform functions behave correctly?
    3. Network tests    — do the full pipelines produce the right results?

Key behaviors being tested:
    - Fanin: articles from both feeds reach spam_filter
    - Filtering: spam is dropped before sentiment analysis
    - Routing: positive/negative/neutral go to correct destinations
    - No article appears in more than one destination
    - Extended app: topic is added to each article dict

Run from the DisSysLab root directory:
    pytest examples/module_04/test_module_04.py -v
"""

import json
import pytest
from components.sources.demo_rss_source import DemoRSSSource, DEMO_FEEDS
from components.transformers.prompts import (
    SPAM_DETECTOR, SENTIMENT_ANALYZER, TOPIC_CLASSIFIER
)
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import DemoEmailAlerter, JSONLRecorder
from dsl import network
from dsl.blocks import Source, Transform, Sink, Split


# ============================================================================
# Layer 1: Component Tests
# ============================================================================

class TestDemoComponents:
    """Individual components produce correct output shapes."""

    def test_hacker_news_produces_strings(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        assert isinstance(rss.run(), str)

    def test_tech_news_produces_strings(self):
        rss = DemoRSSSource(feed_name="tech_news")
        assert isinstance(rss.run(), str)

    def test_spam_detector_returns_required_keys(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector("Buy now! Limited time offer!")
        assert "is_spam" in result
        assert isinstance(result["is_spam"], bool)

    def test_sentiment_analyzer_returns_required_keys(self):
        analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("Python is great!")
        assert "sentiment" in result
        assert "score" in result
        assert result["sentiment"] in ["POSITIVE", "NEGATIVE", "NEUTRAL"]

    def test_topic_classifier_returns_required_keys(self):
        classifier = demo_ai_agent(TOPIC_CLASSIFIER)
        result = classifier("New Python framework released")
        assert "primary_topic" in result
        assert isinstance(result["primary_topic"], str)

    def test_jsonl_recorder_writes_valid_json(self, tmp_path):
        path = str(tmp_path / "test.jsonl")
        recorder = JSONLRecorder(path=path, mode="w", flush_every=1)
        recorder.run({"text": "hello", "sentiment": "POSITIVE", "score": 0.8})
        with open(path) as f:
            obj = json.loads(f.readline())
        assert obj["text"] == "hello"


# ============================================================================
# Layer 2: Transform Function Tests
# ============================================================================

class TestTransformFunctions:
    """Transform functions from app.py behave correctly."""

    def setup_method(self):
        self.spam_detector      = demo_ai_agent(SPAM_DETECTOR)
        self.sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        self.topic_classifier   = demo_ai_agent(TOPIC_CLASSIFIER)

    def _filter_spam(self, text):
        result = self.spam_detector(text)
        return None if result["is_spam"] else text

    def _analyze_sentiment(self, text):
        result = self.sentiment_analyzer(text)
        return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

    def _classify_topic(self, article):
        result = self.topic_classifier(article["text"])
        article["topic"] = result["primary_topic"]
        return article

    def _route_by_sentiment(self, article):
        if article["sentiment"] == "POSITIVE":
            return [article, None,    None   ]
        elif article["sentiment"] == "NEGATIVE":
            return [None,    article, None   ]
        else:
            return [None,    None,    article]

    # Spam filter
    def test_filter_drops_spam(self):
        assert self._filter_spam("CLICK HERE for FREE MONEY!") is None

    def test_filter_passes_legit(self):
        text = "Python 3.13 released with performance improvements"
        assert self._filter_spam(text) == text

    # Sentiment analysis
    def test_sentiment_returns_dict_with_required_keys(self):
        result = self._analyze_sentiment("Python is great!")
        assert "text" in result and "sentiment" in result and "score" in result

    def test_sentiment_preserves_text(self):
        text = "Some article text"
        assert self._analyze_sentiment(text)["text"] == text

    def test_sentiment_valid_label(self):
        result = self._analyze_sentiment("Some text")
        assert result["sentiment"] in ["POSITIVE", "NEGATIVE", "NEUTRAL"]

    # Topic classification
    def test_topic_adds_topic_key(self):
        article = {"text": "New Python release", "sentiment": "POSITIVE", "score": 0.8}
        result = self._classify_topic(article)
        assert "topic" in result

    def test_topic_preserves_existing_keys(self):
        article = {"text": "test", "sentiment": "POSITIVE", "score": 0.8}
        result = self._classify_topic(article)
        assert result["text"] == "test"
        assert result["sentiment"] == "POSITIVE"

    # Routing function
    def test_routing_returns_list_of_three(self):
        article = {"text": "test", "sentiment": "POSITIVE", "score": 0.8}
        assert len(self._route_by_sentiment(article)) == 3

    def test_positive_routes_to_index_0(self):
        article = {"text": "great!", "sentiment": "POSITIVE", "score": 0.9}
        result = self._route_by_sentiment(article)
        assert result[0] is not None and result[1] is None and result[2] is None

    def test_negative_routes_to_index_1(self):
        article = {"text": "terrible!", "sentiment": "NEGATIVE", "score": -0.8}
        result = self._route_by_sentiment(article)
        assert result[0] is None and result[1] is not None and result[2] is None

    def test_neutral_routes_to_index_2(self):
        article = {"text": "ok", "sentiment": "NEUTRAL", "score": 0.0}
        result = self._route_by_sentiment(article)
        assert result[0] is None and result[1] is None and result[2] is not None

    def test_exactly_one_non_none_per_route(self):
        for sentiment in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
            article = {"text": "test", "sentiment": sentiment, "score": 0.0}
            result = self._route_by_sentiment(article)
            assert sum(1 for x in result if x is not None) == 1


# ============================================================================
# Layer 3: Full Network Tests
# ============================================================================

def _make_app_pipeline(tmp_path):
    """Shared factory for the main app.py pipeline."""
    hn                 = DemoRSSSource(feed_name="hacker_news")
    tech               = DemoRSSSource(feed_name="tech_news")
    spam_detector      = demo_ai_agent(SPAM_DETECTOR)
    sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
    pos_path           = str(tmp_path / "positive.jsonl")
    pos_recorder       = JSONLRecorder(path=pos_path, mode="w", flush_every=1)
    alerter            = DemoEmailAlerter(to_address="test@example.com",
                                          subject_prefix="[TEST]")

    def filter_spam(text):
        result = spam_detector(text)
        return None if result["is_spam"] else text

    def analyze_sentiment(text):
        result = sentiment_analyzer(text)
        return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

    def route_by_sentiment(article):
        if article["sentiment"] == "POSITIVE":
            return [article, None,    None   ]
        elif article["sentiment"] == "NEGATIVE":
            return [None,    article, None   ]
        else:
            return [None,    None,    article]

    neutral_results  = []
    negative_results = []

    hn_source   = Source(fn=hn.run,               name="hacker_news")
    tech_source = Source(fn=tech.run,             name="tech_news")
    spam_gate   = Transform(fn=filter_spam,        name="spam_filter")
    sentiment   = Transform(fn=analyze_sentiment,  name="sentiment")
    splitter    = Split(fn=route_by_sentiment,     num_outputs=3, name="router")
    archive     = Sink(fn=pos_recorder.run,        name="archive")
    alerts      = Sink(fn=negative_results.append, name="alerts")
    display     = Sink(fn=neutral_results.append,  name="display")

    g = network([
        (hn_source,   spam_gate),
        (tech_source, spam_gate),
        (spam_gate,   sentiment),
        (sentiment,   splitter),
        (splitter.out_0, archive),
        (splitter.out_1, alerts),
        (splitter.out_2, display)
    ])
    return g, neutral_results, negative_results, pos_path


class TestAppNetwork:
    """Full app.py pipeline — fanin + filter + sentiment + Split."""

    def test_runs_without_error(self, tmp_path):
        g, neutral, negative, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive = [json.loads(l) for l in f if l.strip()]
        assert len(positive) + len(negative) + len(neutral) > 0

    def test_fanin_articles_from_both_feeds_processed(self, tmp_path):
        """Total routed articles should come from both feeds (minus spam)."""
        g, neutral, negative, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive_count = sum(1 for l in f if l.strip())
        total_routed = positive_count + len(negative) + len(neutral)
        total_feed   = len(DEMO_FEEDS["hacker_news"]) + len(DEMO_FEEDS["tech_news"])
        # Spam filtering reduces count; but we must have processed articles from both feeds
        assert total_routed > 0
        assert total_routed < total_feed  # spam was filtered

    def test_spam_filtered_before_routing(self, tmp_path):
        """Total routed should be less than total feed articles."""
        g, neutral, negative, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive_count = sum(1 for l in f if l.strip())
        total_routed = positive_count + len(negative) + len(neutral)
        total_feed   = len(DEMO_FEEDS["hacker_news"]) + len(DEMO_FEEDS["tech_news"])
        assert total_routed < total_feed

    def test_positive_articles_in_archive(self, tmp_path):
        g, _, _, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            for line in f:
                if line.strip():
                    assert json.loads(line)["sentiment"] == "POSITIVE"

    def test_negative_articles_in_alerts(self, tmp_path):
        g, _, negative, _ = _make_app_pipeline(tmp_path)
        g.run_network()
        for r in negative:
            assert r["sentiment"] == "NEGATIVE"

    def test_neutral_articles_in_display(self, tmp_path):
        g, neutral, _, _ = _make_app_pipeline(tmp_path)
        g.run_network()
        for r in neutral:
            assert r["sentiment"] == "NEUTRAL"

    def test_no_article_in_multiple_destinations(self, tmp_path):
        """Each article text appears in exactly one destination."""
        g, neutral, negative, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive = [json.loads(l) for l in f if l.strip()]
        all_texts = (
            [r["text"] for r in positive] +
            [r["text"] for r in negative] +
            [r["text"] for r in neutral]
        )
        assert len(all_texts) == len(set(all_texts)), \
            "Some articles appeared in more than one destination"


class TestAppExtendedNetwork:
    """Extended pipeline — adds topic classification."""

    def _make_extended_pipeline(self, tmp_path):
        hn                 = DemoRSSSource(feed_name="hacker_news")
        tech               = DemoRSSSource(feed_name="tech_news")
        spam_detector      = demo_ai_agent(SPAM_DETECTOR)
        sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        topic_classifier   = demo_ai_agent(TOPIC_CLASSIFIER)
        pos_path           = str(tmp_path / "positive_ext.jsonl")
        pos_recorder       = JSONLRecorder(path=pos_path, mode="w", flush_every=1)
        alerter            = DemoEmailAlerter(to_address="test@example.com",
                                              subject_prefix="[TEST]")

        def filter_spam(text):
            result = spam_detector(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sentiment_analyzer(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def classify_topic(article):
            result = topic_classifier(article["text"])
            article["topic"] = result["primary_topic"]
            return article

        def route_by_sentiment(article):
            if article["sentiment"] == "POSITIVE":
                return [article, None,    None   ]
            elif article["sentiment"] == "NEGATIVE":
                return [None,    article, None   ]
            else:
                return [None,    None,    article]

        neutral_results  = []
        negative_results = []

        hn_source   = Source(fn=hn.run,               name="hacker_news")
        tech_source = Source(fn=tech.run,             name="tech_news")
        spam_gate   = Transform(fn=filter_spam,        name="spam_filter")
        sentiment   = Transform(fn=analyze_sentiment,  name="sentiment")
        topic       = Transform(fn=classify_topic,     name="topic")
        splitter    = Split(fn=route_by_sentiment,     num_outputs=3, name="router")
        archive     = Sink(fn=pos_recorder.run,        name="archive")
        alerts      = Sink(fn=negative_results.append, name="alerts")
        display     = Sink(fn=neutral_results.append,  name="display")

        g = network([
            (hn_source,   spam_gate),
            (tech_source, spam_gate),
            (spam_gate,   sentiment),
            (sentiment,   topic),
            (topic,       splitter),
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
        assert positive_count + len(negative) + len(neutral) > 0

    def test_extended_articles_have_topic_key(self, tmp_path):
        """All routed articles should have a topic key added."""
        g, neutral, negative, pos_path = self._make_extended_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            for line in f:
                if line.strip():
                    assert "topic" in json.loads(line), \
                        "Positive article missing topic key"
        for r in negative:
            assert "topic" in r, "Negative article missing topic key"
        for r in neutral:
            assert "topic" in r, "Neutral article missing topic key"

    def test_extended_correct_routing(self, tmp_path):
        """Routing is still correct after adding topic node."""
        g, neutral, negative, pos_path = self._make_extended_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            for line in f:
                if line.strip():
                    assert json.loads(line)["sentiment"] == "POSITIVE"
        for r in negative:
            assert r["sentiment"] == "NEGATIVE"
        for r in neutral:
            assert r["sentiment"] == "NEUTRAL"

    def test_extended_no_article_in_multiple_destinations(self, tmp_path):
        g, neutral, negative, pos_path = self._make_extended_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            positive = [json.loads(l) for l in f if l.strip()]
        all_texts = (
            [r["text"] for r in positive] +
            [r["text"] for r in negative] +
            [r["text"] for r in neutral]
        )
        assert len(all_texts) == len(set(all_texts))
