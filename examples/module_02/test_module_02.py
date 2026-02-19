# examples/module_02/test_module_02.py

"""
Tests for Module 02: AI Integration

Run from the DisSysLab root directory:
    pytest examples/module_02/test_module_02.py -v
"""

import pytest
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent
from dsl import network
from dsl.blocks import Source, Transform, Sink


class TestModule02Pipeline:
    def test_pipeline_runs_and_produces_results(self):
        rss = DemoRSSSource(feed_name="hacker_news")
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze_sentiment(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def extract_entities(article):
            article["people"] = []
            article["organizations"] = []
            article["locations"] = []
            return article

        results = []
        source = Source(fn=rss.run, name="rss_feed")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        entities = Transform(fn=extract_entities, name="entities")
        collector = Sink(fn=results.append, name="collector")

        g = network(
            [(source, sentiment), (sentiment, entities), (entities, collector)])
        g.run_network()

        assert len(results) > 0
        for r in results:
            assert "text" in r
            assert "sentiment" in r
            assert "people" in r
            assert "locations" in r

    def test_enrichment_is_progressive(self):
        rss = DemoRSSSource(feed_name="tech_news", max_articles=3)
        sent_ana = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze_sentiment(text):
            result = sent_ana(text)
            return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

        def extract_entities(article):
            article["people"] = []
            article["locations"] = []
            return article

        def add_topic(article):
            article["topic"] = "technology"
            return article

        results = []
        source = Source(fn=rss.run, name="source")
        s1 = Transform(fn=analyze_sentiment, name="sentiment")
        s2 = Transform(fn=extract_entities, name="entities")
        s3 = Transform(fn=add_topic, name="topic")
        collector = Sink(fn=results.append, name="out")

        g = network([(source, s1), (s1, s2), (s2, s3), (s3, collector)])
        g.run_network()

        assert len(results) == 3
        for r in results:
            assert "text" in r
            assert "sentiment" in r
            assert "people" in r
            assert "topic" in r


class TestModule02WithFilter:
    def test_filter_before_ai(self):
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
        source = Source(fn=rss.run, name="source")
        spam_gate = Transform(fn=filter_spam, name="spam")
        sentiment = Transform(fn=analyze_sentiment, name="sentiment")
        collector = Sink(fn=results.append, name="out")

        g = network([(source, spam_gate), (spam_gate, sentiment),
                    (sentiment, collector)])
        g.run_network()

        for r in results:
            text_lower = r["text"].lower()
            assert "click here" not in text_lower
            assert "free money" not in text_lower
