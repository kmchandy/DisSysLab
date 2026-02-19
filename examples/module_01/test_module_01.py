# examples/module_01/test_module_01.py

"""
Tests for Module 01: Describe and Build

Run from the DisSysLab root directory:
    pytest examples/module_01/test_module_01.py -v
"""

import pytest
from components.sources.demo_rss_source import DemoRSSSource, DEMO_FEEDS
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER, URGENCY_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_agent
from dsl import network
from dsl.blocks import Source, Transform, Sink


# ====================================================================
# Layer 1: Component Tests
# ====================================================================

class TestDemoRSSSource:
    def test_returns_articles(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        first = rss.run()
        assert first is not None
        assert isinstance(first, str)

    def test_returns_none_when_exhausted(self):
        rss = DemoRSSSource(feed_name="hacker_news", max_articles=2)
        rss.run()
        rss.run()
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
            assert rss.run(
            ) is not None, f"Feed '{feed_name}' returned None on first call"


class TestDemoAIAgent:
    def test_spam_detection_catches_spam(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector("CLICK HERE for FREE MONEY!")
        assert result["is_spam"] is True

    def test_spam_detection_passes_legitimate(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector("Python 3.13 released with performance improvements")
        assert result["is_spam"] is False

    def test_sentiment_analysis_returns_required_keys(self):
        analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("This is amazing and wonderful!")
        assert "sentiment" in result
        assert "score" in result
        assert result["sentiment"] in ["POSITIVE", "NEGATIVE", "NEUTRAL"]

    def test_sentiment_positive(self):
        analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("This is amazing and wonderful!")
        assert result["sentiment"] == "POSITIVE"

    def test_sentiment_negative(self):
        analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("This is terrible and awful.")
        assert result["sentiment"] == "NEGATIVE"

    def test_urgency_detection_returns_required_keys(self):
        detector = demo_ai_agent(URGENCY_DETECTOR)
        result = detector("URGENT! Critical security breach! Act now!")
        assert "urgency" in result
        assert result["urgency"] in ["HIGH", "MEDIUM", "LOW"]

    def test_urgency_high(self):
        detector = demo_ai_agent(URGENCY_DETECTOR)
        result = detector("URGENT! Critical emergency! Act immediately now!")
        assert result["urgency"] == "HIGH"


# ====================================================================
# Layer 2: Transform Function Tests
# ====================================================================

class TestTransformFunctions:
    def setup_method(self):
        self.spam_detector = demo_ai_agent(SPAM_DETECTOR)
        self.sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        self.urgency_detector = demo_ai_agent(URGENCY_DETECTOR)

    def _filter_spam(self, text):
        result = self.spam_detector(text)
        return None if result["is_spam"] else text

    def _analyze_sentiment(self, text):
        result = self.sentiment_analyzer(text)
        return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

    def _only_positive(self, article):
        return None if article["sentiment"] == "NEGATIVE" else article

    def _analyze_urgency(self, article):
        result = self.urgency_detector(article["text"])
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
    def test_basic_pipeline_runs(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        spam_det = demo_ai_agent(SPAM_DETECTOR)
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def filter_spam(text):
            result = spam_det(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results = []
        source = Source(fn=rss.run, name="rss_feed")
        spam_gate = Transform(fn=filter_spam, name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        collector = Sink(fn=results.append, name="collector")

        g = network([(source, spam_gate), (spam_gate, sentiment),
                    (sentiment, collector)])
        g.run_network()

        assert len(results) > 0, "Pipeline produced no results"
        for r in results:
            assert "text" in r
            assert "sentiment" in r
            assert "score" in r

    def test_spam_is_filtered(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        spam_det = demo_ai_agent(SPAM_DETECTOR)
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def filter_spam(text):
            result = spam_det(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results = []
        source = Source(fn=rss.run, name="rss_feed")
        spam_gate = Transform(fn=filter_spam, name="spam_filter")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        collector = Sink(fn=results.append, name="collector")

        g = network([(source, spam_gate), (spam_gate, sentiment),
                    (sentiment, collector)])
        g.run_network()

        spam_keywords = ['click here', 'buy now', 'limited time', 'act now',
                         'free money', 'winner', 'get rich', 'make money fast']
        original_spam_count = sum(
            1 for article in DEMO_FEEDS["hacker_news"]
            if any(kw in article.lower() for kw in spam_keywords)
        )
        assert original_spam_count > 0
        for r in results:
            text_lower = r["text"].lower()
            for kw in spam_keywords:
                assert kw not in text_lower
        assert len(results) < len(DEMO_FEEDS["hacker_news"])

    def test_all_feeds_work(self):
        for feed_name in ["hacker_news", "tech_news", "reddit_python"]:
            rss = DemoRSSSource(feed_name=feed_name)
            spam_det = demo_ai_agent(SPAM_DETECTOR)
            sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

            def filter_spam(text, _det=spam_det):
                result = _det(text)
                return None if result["is_spam"] else text

            def analyze_sentiment(text, _ana=sent_ana):
                result = _ana(text)
                return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

            results = []
            source = Source(fn=rss.run, name="rss_feed")
            spam_gate = Transform(fn=filter_spam, name="spam_filter")
            sentiment = Transform(fn=analyze_sentiment, name="sentiment")
            collector = Sink(fn=results.append, name="collector")

            g = network(
                [(source, spam_gate), (spam_gate, sentiment), (sentiment, collector)])
            g.run_network()
            assert len(results) > 0, f"Feed '{feed_name}' produced no results"


class TestModifiedNetwork:
    def test_modified_pipeline_runs(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        spam_det = demo_ai_agent(SPAM_DETECTOR)
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)
        urg_det = demo_ai_agent(URGENCY_DETECTOR)

        def filter_spam(text):
            result = spam_det(text)
            return None if result["is_spam"] else text

        def analyze_sentiment(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def only_positive(article):
            return None if article["sentiment"] == "NEGATIVE" else article

        def analyze_urgency(article):
            result = urg_det(article["text"])
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
            (source, spam_gate), (spam_gate, sentiment),
            (sentiment, positive_filter), (positive_filter, urgency),
            (urgency, collector)
        ])
        g.run_network()

        assert len(results) > 0
        for r in results:
            assert "text" in r
            assert "sentiment" in r
            assert "urgency" in r
        for r in results:
            assert r["sentiment"] != "NEGATIVE"

    def test_double_filter_reduces_count(self):
        rss_1 = DemoRSSSource(feed_name="hacker_news")
        rss_2 = DemoRSSSource(feed_name="hacker_news")
        spam_det_1 = demo_ai_agent(SPAM_DETECTOR)
        spam_det_2 = demo_ai_agent(SPAM_DETECTOR)
        sent_1 = demo_ai_agent(SENTIMENT_ANALYZER)
        sent_2 = demo_ai_agent(SENTIMENT_ANALYZER)
        urg = demo_ai_agent(URGENCY_DETECTOR)

        def filter_spam_1(text):
            result = spam_det_1(text)
            return None if result["is_spam"] else text

        def analyze_1(text):
            result = sent_1(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        results_1 = []
        src1 = Source(fn=rss_1.run, name="src")
        spam1 = Transform(fn=filter_spam_1, name="spam")
        sent1_node = Transform(fn=analyze_1, name="sent")
        out1 = Sink(fn=results_1.append, name="out")
        g1 = network([(src1, spam1), (spam1, sent1_node), (sent1_node, out1)])
        g1.run_network()

        def filter_spam_2(text):
            result = spam_det_2(text)
            return None if result["is_spam"] else text

        def analyze_2(text):
            result = sent_2(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def only_pos(article):
            return None if article["sentiment"] == "NEGATIVE" else article

        def add_urgency(article):
            result = urg(article["text"])
            article["urgency"] = result["urgency"]
            return article

        results_2 = []
        src = Source(fn=rss_2.run, name="src")
        spam = Transform(fn=filter_spam_2, name="spam")
        sent = Transform(fn=analyze_2, name="sent")
        pos = Transform(fn=only_pos, name="pos")
        urgn = Transform(fn=add_urgency, name="urg")
        out = Sink(fn=results_2.append, name="out")
        g2 = network([(src, spam), (spam, sent),
                     (sent, pos), (pos, urgn), (urgn, out)])
        g2.run_network()

        assert len(results_2) <= len(results_1)
