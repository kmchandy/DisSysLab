# examples/module_05/test_module_05.py

"""
Tests for Module 05: Job Postings Monitor

Tests are organized in three layers:
    1. Component tests  — do the individual components work correctly?
    2. Function tests   — do the transform functions behave correctly?
    3. Network tests    — do the full pipelines produce the right results?

Key behaviors being tested:
    - DemoJobSource produces postings and exhausts cleanly
    - Spam is dropped before relevance checking
    - Matching postings reach archive and display (fanout from split port)
    - Non-matching postings are discarded
    - No posting appears in both match and discard paths
    - Extended app: salary keys are added to all routed postings

Note: app_live.py is NOT tested here — it requires a real API key and
live network access. Test that manually after setting ANTHROPIC_API_KEY.

Run from the DisSysLab root directory:
    pytest examples/module_05/test_module_05.py -v
"""

import json
import pytest
from components.sources.demo_job_source import DemoJobSource
from components.transformers.prompts import SPAM_DETECTOR, JOB_DETECTOR, SALARY_EXTRACTOR
from components.transformers.demo_ai_agent import demo_ai_agent
from components.sinks import JSONLRecorder
from dsl import network
from dsl.blocks import Source, Transform, Sink, Split
from examples.module_05.demo_job_source import DEMO_JOB_FEEDS


# ============================================================================
# Layer 1: Component Tests
# ============================================================================

class TestDemoJobSource:
    """DemoJobSource produces postings correctly."""

    def test_produces_strings(self):
        src = DemoJobSource(feed_name="python_jobs")
        assert isinstance(src.run(), str)

    def test_exhausts_cleanly(self):
        src = DemoJobSource(feed_name="python_jobs", max_articles=3)
        src.run()
        src.run()
        src.run()
        assert src.run() is None

    def test_respects_max_articles(self):
        src = DemoJobSource(feed_name="python_jobs", max_articles=4)
        count = 0
        while src.run() is not None:
            count += 1
        assert count == 4

    def test_both_feeds_exist(self):
        for feed in ["python_jobs", "ml_jobs"]:
            src = DemoJobSource(feed_name=feed)
            assert src.run() is not None

    def test_demo_feeds_contain_spam(self):
        """Demo data should contain spam for the filter to drop."""
        spam_keywords = ["click here", "free money", "guaranteed", "buy now",
                         "get rich", "make $", "passive income"]
        for feed in ["python_jobs", "ml_jobs"]:
            articles = DEMO_JOB_FEEDS[feed]
            has_spam = any(
                any(kw in a.lower() for kw in spam_keywords)
                for a in articles
            )
            assert has_spam, f"Feed '{feed}' contains no spam — tests won't be meaningful"


class TestDemoAIComponents:
    """Demo AI components return correct shapes for job-related prompts."""

    def test_spam_detector_drops_job_spam(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector(
            "CLICK HERE for FREE MONEY — work from home guaranteed!")
        assert result["is_spam"] is True

    def test_spam_detector_passes_real_job(self):
        detector = demo_ai_agent(SPAM_DETECTOR)
        result = detector(
            "Senior Python Engineer at Stripe — Remote, $180k-$220k")
        assert result["is_spam"] is False

    def test_job_detector_returns_required_keys(self):
        checker = demo_ai_agent(JOB_DETECTOR)
        result = checker("Senior Python Engineer at Stripe — Remote, $180k")
        assert "match" in result
        assert "confidence" in result

    def test_salary_extractor_returns_required_keys(self):
        extractor = demo_ai_agent(SALARY_EXTRACTOR)
        result = extractor(
            "Senior Python Engineer at Stripe — Remote, $180k-$220k")
        assert "salary_mentioned" in result
        assert "salary_text" in result
        assert "min_salary" in result
        assert "max_salary" in result

    def test_salary_extractor_finds_salary(self):
        extractor = demo_ai_agent(SALARY_EXTRACTOR)
        result = extractor(
            "Senior Python Engineer at Stripe — Remote, $180k-$220k")
        assert result["salary_mentioned"] is True
        assert result["min_salary"] == 180000
        assert result["max_salary"] == 220000

    def test_salary_extractor_handles_no_salary(self):
        extractor = demo_ai_agent(SALARY_EXTRACTOR)
        result = extractor("ML Engineer at DeepMind — London or Remote")
        assert result["salary_mentioned"] is False
        assert result["salary_text"] is None


# ============================================================================
# Layer 2: Transform Function Tests
# ============================================================================

class TestTransformFunctions:
    """Transform functions behave correctly."""

    def setup_method(self):
        self.spam_detector = demo_ai_agent(SPAM_DETECTOR)
        self.relevance_checker = demo_ai_agent(JOB_DETECTOR)
        self.salary_extractor = demo_ai_agent(SALARY_EXTRACTOR)

    def _filter_spam(self, text):
        result = self.spam_detector(text)
        return None if result["is_spam"] else text

    def _check_relevance(self, text):
        result = self.relevance_checker(text)
        return {
            "text":       text,
            "match":      result.get("match", "NONE"),
            "confidence": result.get("confidence", 0.0),
            "reason":     result.get("reason", "")
        }

    def _route_by_match(self, posting):
        if posting["match"] in ("STRONG", "PARTIAL"):
            return [posting, None]
        else:
            return [None,    posting]

    def test_filter_drops_spam(self):
        assert self._filter_spam("CLICK HERE for FREE MONEY!") is None

    def test_filter_passes_legit_job(self):
        text = "Senior Python Engineer at Stripe — Remote, $180k"
        assert self._filter_spam(text) == text

    def test_relevance_returns_dict_with_match_key(self):
        result = self._check_relevance("Senior Python Engineer at Stripe")
        assert "match" in result
        assert result["match"] in ("STRONG", "PARTIAL", "NONE")

    def test_relevance_preserves_text(self):
        text = "Senior Python Engineer at Stripe"
        result = self._check_relevance(text)
        assert result["text"] == text

    def test_routing_returns_list_of_two(self):
        posting = {"text": "test", "match": "STRONG",
                   "confidence": 0.9, "reason": ""}
        assert len(self._route_by_match(posting)) == 2

    def test_strong_match_routes_to_index_0(self):
        posting = {"text": "test", "match": "STRONG",
                   "confidence": 0.9, "reason": ""}
        result = self._route_by_match(posting)
        assert result[0] is not None and result[1] is None

    def test_partial_match_routes_to_index_0(self):
        posting = {"text": "test", "match": "PARTIAL",
                   "confidence": 0.6, "reason": ""}
        result = self._route_by_match(posting)
        assert result[0] is not None and result[1] is None

    def test_none_match_routes_to_index_1(self):
        posting = {"text": "test", "match": "NONE",
                   "confidence": 0.1, "reason": ""}
        result = self._route_by_match(posting)
        assert result[0] is None and result[1] is not None


# ============================================================================
# Layer 3: Full Network Tests
# ============================================================================

def _make_app_pipeline(tmp_path):
    """Shared factory for the main app.py pipeline."""
    python_src = DemoJobSource(feed_name="python_jobs")
    ml_src = DemoJobSource(feed_name="ml_jobs")

    spam_detector = demo_ai_agent(SPAM_DETECTOR)
    relevance_checker = demo_ai_agent(JOB_DETECTOR)

    pos_path = str(tmp_path / "matches.jsonl")
    recorder = JSONLRecorder(path=pos_path, mode="w", flush_every=1)

    display_results = []
    discard_results = []

    def filter_spam(text):
        result = spam_detector(text)
        return None if result["is_spam"] else text

    def check_relevance(text):
        result = relevance_checker(text)
        return {"text": text, "match": result.get("match", "NONE"),
                "confidence": result.get("confidence", 0.0),
                "reason": result.get("reason", "")}

    def route_by_match(posting):
        if posting["match"] in ("STRONG", "PARTIAL"):
            return [posting, None]
        else:
            return [None,    posting]

    def discard(msg):
        discard_results.append(msg)

    python_source = Source(fn=python_src.run,      name="python_jobs")
    ml_source = Source(fn=ml_src.run,          name="ml_jobs")
    spam_gate = Transform(fn=filter_spam,       name="spam_filter")
    relevance = Transform(fn=check_relevance,   name="relevance")
    splitter = Split(fn=route_by_match,        num_outputs=2, name="router")
    archive = Sink(fn=recorder.run,           name="archive")
    display = Sink(fn=display_results.append, name="display")
    discard_sink = Sink(fn=discard,                name="discard")

    g = network([
        (python_source,  spam_gate),
        (ml_source,      spam_gate),
        (spam_gate,      relevance),
        (relevance,      splitter),
        (splitter.out_0, archive),
        (splitter.out_0, display),
        (splitter.out_1, discard_sink),
    ])
    return g, display_results, discard_results, pos_path


class TestAppNetwork:
    """Full app.py pipeline — fanin + spam + relevance + Split + fanout."""

    def test_runs_without_error(self, tmp_path):
        g, display, discard, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            archived = [json.loads(l) for l in f if l.strip()]
        assert len(archived) + len(discard) > 0

    def test_spam_filtered_before_routing(self, tmp_path):
        """Total processed should be less than total demo articles."""
        g, display, discard, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            archived_count = sum(1 for l in f if l.strip())
        total_processed = archived_count + len(discard)
        total_feed = len(
            DEMO_JOB_FEEDS["python_jobs"]) + len(DEMO_JOB_FEEDS["ml_jobs"])
        assert total_processed < total_feed, \
            "Spam filter should reduce total count"

    def test_match_articles_in_archive(self, tmp_path):
        """Every archived posting should have match STRONG or PARTIAL."""
        g, _, _, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    assert obj["match"] in ("STRONG", "PARTIAL"), \
                        f"Non-matching posting in archive: {obj['text']}"

    def test_fanout_archive_and_display_receive_same_count(self, tmp_path):
        """Both archive and display should receive every matching posting."""
        g, display, _, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            archived_count = sum(1 for l in f if l.strip())
        assert len(display) == archived_count, \
            "Archive and display should receive the same number of matches"

    def test_no_match_articles_are_discarded(self, tmp_path):
        """Every discarded posting should have match NONE."""
        g, _, discard, _ = _make_app_pipeline(tmp_path)
        g.run_network()
        for posting in discard:
            assert posting["match"] == "NONE", \
                f"Matching posting ended up in discard: {posting['text']}"

    def test_no_posting_in_both_match_and_discard(self, tmp_path):
        """No posting text should appear in both match and discard paths."""
        g, display, discard, pos_path = _make_app_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            archived = [json.loads(l) for l in f if l.strip()]
        match_texts = {r["text"] for r in archived}
        discard_texts = {r["text"] for r in discard}
        overlap = match_texts & discard_texts
        assert len(overlap) == 0, \
            f"Postings in both match and discard: {overlap}"


class TestAppExtendedNetwork:
    """Extended pipeline — adds salary extraction."""

    def _make_extended_pipeline(self, tmp_path):
        python_src = DemoJobSource(feed_name="python_jobs")
        ml_src = DemoJobSource(feed_name="ml_jobs")

        spam_detector = demo_ai_agent(SPAM_DETECTOR)
        relevance_checker = demo_ai_agent(JOB_DETECTOR)
        salary_extractor = demo_ai_agent(SALARY_EXTRACTOR)

        pos_path = str(tmp_path / "matches_ext.jsonl")
        recorder = JSONLRecorder(path=pos_path, mode="w", flush_every=1)
        display_results = []

        def filter_spam(text):
            result = spam_detector(text)
            return None if result["is_spam"] else text

        def check_relevance(text):
            result = relevance_checker(text)
            return {"text": text, "match": result.get("match", "NONE"),
                    "confidence": result.get("confidence", 0.0),
                    "reason": result.get("reason", "")}

        def extract_salary(posting):
            result = salary_extractor(posting["text"])
            posting["salary_mentioned"] = result.get("salary_mentioned", False)
            posting["salary_text"] = result.get("salary_text", None)
            posting["min_salary"] = result.get("min_salary", None)
            posting["max_salary"] = result.get("max_salary", None)
            return posting

        def route_by_match(posting):
            if posting["match"] in ("STRONG", "PARTIAL"):
                return [posting, None]
            else:
                return [None,    posting]

        def discard(msg):
            pass

        python_source = Source(fn=python_src.run,      name="python_jobs")
        ml_source = Source(fn=ml_src.run,          name="ml_jobs")
        spam_gate = Transform(fn=filter_spam,       name="spam_filter")
        relevance = Transform(fn=check_relevance,   name="relevance")
        salary = Transform(fn=extract_salary,    name="salary")
        splitter = Split(fn=route_by_match,
                         num_outputs=2, name="router")
        archive = Sink(fn=recorder.run,           name="archive")
        display = Sink(fn=display_results.append, name="display")
        discard_sink = Sink(fn=discard,                name="discard")

        g = network([
            (python_source,  spam_gate),
            (ml_source,      spam_gate),
            (spam_gate,      relevance),
            (relevance,      salary),
            (salary,         splitter),
            (splitter.out_0, archive),
            (splitter.out_0, display),
            (splitter.out_1, discard_sink),
        ])
        return g, display_results, pos_path

    def test_extended_runs_without_error(self, tmp_path):
        g, display, pos_path = self._make_extended_pipeline(tmp_path)
        g.run_network()
        assert True  # Just verify no exception

    def test_archived_postings_have_salary_keys(self, tmp_path):
        """All archived postings should have salary keys added."""
        g, _, pos_path = self._make_extended_pipeline(tmp_path)
        g.run_network()
        with open(pos_path) as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    assert "salary_mentioned" in obj, \
                        "Archived posting missing salary_mentioned key"
                    assert "salary_text" in obj, \
                        "Archived posting missing salary_text key"

    def test_display_postings_have_salary_keys(self, tmp_path):
        """Display postings should also have salary keys."""
        g, display, _ = self._make_extended_pipeline(tmp_path)
        g.run_network()
        for posting in display:
            assert "salary_mentioned" in posting
            assert "salary_text" in posting
