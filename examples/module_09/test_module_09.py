# examples/module_09/test_module_09.py

"""
Tests for Module 09: Container Edition

Module 09 has one new lesson — containers — and one new component:
the BlueSky Jetstream source (live or demo fallback). The network
topology and transform functions are deliberately simple so that
students can focus on the deployment concepts.

Tests are organised in three layers:

    Layer 1 — Source components
        DemoBlueSkyJetstream produces the right dict format and
        respects max_posts. BlueSkyJetstreamSource is tested only
        if a network connection is available (skipped otherwise).

    Layer 2 — Transform functions
        analyze_sentiment enriches a post dict correctly.
        display runs without errors and writes to stdout.

    Layer 3 — Full network
        The complete pipeline runs end-to-end using the demo source,
        collects exactly max_posts results, and every result has the
        required keys.

Run from the DisSysLab root directory:
    pytest examples/module_09/test_module_09.py -v
"""

import io
import sys
import pytest

from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink
from dissyslab.components.sources.demo_bluesky_jetstream import DemoBlueSkyJetstream
from dissyslab.components.transformers.prompts import SENTIMENT_ANALYZER
from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent


# ── Shared fixture ─────────────────────────────────────────────────────────────

def make_post(text="Great news for Python developers!", author="test_user"):
    """Return a minimal post dict matching the BlueSky source format."""
    return {
        "text":           text,
        "author":         author,
        "author_display": author,
        "timestamp":      "2026-01-01T00:00:00Z",
        "likes":          0,
        "reposts":        0,
        "replies":        0,
        "url":            "https://bsky.app/profile/test_user/post/1",
        "hashtags":       [],
        "language":       "en",
    }


def live_bluesky_available():
    """Return True if BlueSkyJetstreamSource connects without error."""
    try:
        from dissyslab.components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
        BlueSkyJetstreamSource(max_posts=1, lifetime=10)
        return True
    except Exception:
        return False


# ====================================================================
# Layer 1: Source Component Tests
# ====================================================================

class TestDemoBlueSkyJetstream:
    """DemoBlueSkyJetstream produces correct output without network access."""

    def test_returns_dict(self):
        src = DemoBlueSkyJetstream(max_posts=1, delay_seconds=0)
        post = src.run()
        assert isinstance(post, dict)

    def test_returns_none_when_exhausted(self):
        src = DemoBlueSkyJetstream(max_posts=2, delay_seconds=0)
        src.run()
        src.run()
        assert src.run() is None

    def test_respects_max_posts(self):
        src = DemoBlueSkyJetstream(max_posts=5, delay_seconds=0)
        posts = []
        while True:
            p = src.run()
            if p is None:
                break
            posts.append(p)
        assert len(posts) == 5

    def test_post_has_required_keys(self):
        src = DemoBlueSkyJetstream(max_posts=1, delay_seconds=0)
        post = src.run()
        for key in ("text", "author", "author_display", "timestamp",
                    "likes", "reposts", "replies", "url", "hashtags", "language"):
            assert key in post, f"Missing key '{key}' in post: {post}"

    def test_text_is_non_empty_string(self):
        src = DemoBlueSkyJetstream(max_posts=1, delay_seconds=0)
        post = src.run()
        assert isinstance(post["text"], str)
        assert len(post["text"]) > 0

    def test_author_is_string(self):
        src = DemoBlueSkyJetstream(max_posts=1, delay_seconds=0)
        post = src.run()
        assert isinstance(post["author"], str)

    def test_hashtags_is_list(self):
        src = DemoBlueSkyJetstream(max_posts=1, delay_seconds=0)
        post = src.run()
        assert isinstance(post["hashtags"], list)

    def test_filter_keywords(self):
        """Keyword filtering reduces the posts returned."""
        src_all = DemoBlueSkyJetstream(max_posts=20, delay_seconds=0)
        src_filtered = DemoBlueSkyJetstream(
            max_posts=20, delay_seconds=0, filter_keywords=["python"]
        )
        all_posts = []
        filtered_posts = []
        while True:
            p = src_all.run()
            if p is None:
                break
            all_posts.append(p)
        while True:
            p = src_filtered.run()
            if p is None:
                break
            filtered_posts.append(p)
        # Every filtered post must mention the keyword
        for post in filtered_posts:
            assert "python" in post["text"].lower() \
                or "python" in [t.lower() for t in post["hashtags"]], \
                f"Keyword filter failed — post does not mention 'python': {post['text']}"


class TestLiveBlueSkyJetstream:
    """
    BlueSkyJetstreamSource tests — skipped if no network connection.
    These tests confirm the live source produces the same dict format
    as the demo source.
    """

    @pytest.mark.skipif(
        not live_bluesky_available(),
        reason="BlueSky Jetstream not reachable — no network or service down"
    )
    def test_live_source_returns_dict(self):
        from dissyslab.components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
        src = BlueSkyJetstreamSource(max_posts=2, lifetime=30)
        post = next(src.run())
        assert isinstance(post, dict)

    @pytest.mark.skipif(
        not live_bluesky_available(),
        reason="BlueSky Jetstream not reachable — no network or service down"
    )
    def test_live_source_has_required_keys(self):
        from dissyslab.components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
        src = BlueSkyJetstreamSource(max_posts=2, lifetime=30)
        post = next(src.run())
        for key in ("text", "author", "hashtags", "language"):
            assert key in post, f"Missing key '{key}' in live post"

    @pytest.mark.skipif(
        not live_bluesky_available(),
        reason="BlueSky Jetstream not reachable — no network or service down"
    )
    def test_live_and_demo_same_schema(self):
        from dissyslab.components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
        live = BlueSkyJetstreamSource(max_posts=1, lifetime=30)
        demo = DemoBlueSkyJetstream(max_posts=1, delay_seconds=0)
        live_post = next(live.run())
        demo_post = demo.run()
        required_keys = {"text", "author", "author_display", "timestamp",
                         "hashtags", "language", "url"}
        assert required_keys.issubset(set(live_post.keys())), \
            f"Live post missing required keys: {required_keys - set(live_post.keys())}"
        assert required_keys.issubset(set(demo_post.keys())), \
            f"Demo post missing required keys: {required_keys - set(demo_post.keys())}"


# ====================================================================
# Layer 2: Transform Function Tests
# ====================================================================

class TestAnalyzeSentiment:
    """analyze_sentiment enriches a post dict with sentiment keys."""

    def setup_method(self):
        _analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze_sentiment(post):
            result = _analyzer(post["text"])
            return {
                **post,
                "sentiment": result["sentiment"],
                "score":     result["score"],
            }

        self.analyze_sentiment = analyze_sentiment

    def test_returns_dict(self):
        result = self.analyze_sentiment(make_post())
        assert isinstance(result, dict)

    def test_original_keys_preserved(self):
        post = make_post(text="Loving this new framework!", author="dev_jane")
        result = self.analyze_sentiment(post)
        assert result["author"] == "dev_jane"
        assert result["text"] == "Loving this new framework!"

    def test_adds_sentiment_key(self):
        result = self.analyze_sentiment(make_post())
        assert "sentiment" in result

    def test_adds_score_key(self):
        result = self.analyze_sentiment(make_post())
        assert "score" in result

    def test_sentiment_is_valid_label(self):
        result = self.analyze_sentiment(make_post())
        assert result["sentiment"] in ("POSITIVE", "NEGATIVE", "NEUTRAL")

    def test_positive_text(self):
        post = make_post(text="This is amazing and wonderful!")
        result = self.analyze_sentiment(post)
        assert result["sentiment"] == "POSITIVE"

    def test_negative_text(self):
        post = make_post(text="This is terrible and awful and I hate it.")
        result = self.analyze_sentiment(post)
        assert result["sentiment"] == "NEGATIVE"


class TestDisplay:
    """display writes a formatted line to stdout without errors."""

    def setup_method(self):
        def display(article):
            icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
            emoji = icon.get(article["sentiment"], "❓")
            label = article["sentiment"]
            author = article["author"]
            text = article["text"][:72]
            print(f"  {emoji} [{label:>8}]  @{author}: {text}")

        self.display = display

    def _enriched_post(self, sentiment="POSITIVE"):
        post = make_post()
        post["sentiment"] = sentiment
        post["score"] = 0.8
        return post

    def test_runs_without_error(self):
        self.display(self._enriched_post("POSITIVE"))

    def test_runs_for_all_sentiments(self):
        for label in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
            self.display(self._enriched_post(label))

    def test_writes_to_stdout(self, capsys):
        self.display(self._enriched_post("POSITIVE"))
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_output_contains_author(self, capsys):
        post = make_post(author="mycoolhandle")
        post["sentiment"] = "NEUTRAL"
        post["score"] = 0.0
        self.display(post)
        captured = capsys.readouterr()
        assert "mycoolhandle" in captured.out

    def test_output_contains_sentiment_label(self, capsys):
        self.display(self._enriched_post("NEGATIVE"))
        captured = capsys.readouterr()
        assert "NEGATIVE" in captured.out


# ====================================================================
# Layer 3: Full Network Tests
# ====================================================================

class TestFullNetwork:
    """
    The complete module_09 pipeline runs end-to-end using the demo source.
    These tests do not require network access or Docker.
    """

    MAX_POSTS = 5   # Small count for fast tests

    def _build_network(self, results):
        """Build the module_09 network and return the compiled graph."""
        src = DemoBlueSkyJetstream(max_posts=self.MAX_POSTS, delay_seconds=0)
        _analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

        def analyze_sentiment(post):
            result = _analyzer(post["text"])
            return {**post, "sentiment": result["sentiment"], "score": result["score"]}

        def display(article):
            icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
            emoji = icon.get(article["sentiment"], "❓")
            print(f"  {emoji} [{article['sentiment']:>8}]  "
                  f"@{article['author']}: {article['text'][:72]}")

        bluesky = Source(fn=src.run,              name="bluesky")
        sentiment = Transform(fn=analyze_sentiment,  name="sentiment")
        output = Sink(fn=display,                 name="display")
        collector = Sink(fn=results.append,          name="collector")

        # Mirror the app topology but add a collector for assertions
        g = network([
            (bluesky,   sentiment),
            (sentiment, output),
            (sentiment, collector),
        ])
        return g

    def test_network_runs_without_error(self):
        results = []
        g = self._build_network(results)
        g.run_network(timeout=30)

    def test_network_produces_results(self):
        results = []
        g = self._build_network(results)
        g.run_network(timeout=30)
        assert len(results) > 0

    def test_network_processes_all_posts(self):
        results = []
        g = self._build_network(results)
        g.run_network(timeout=30)
        assert len(results) == self.MAX_POSTS

    def test_all_results_have_required_keys(self):
        results = []
        g = self._build_network(results)
        g.run_network(timeout=30)
        for r in results:
            for key in ("text", "author", "sentiment", "score"):
                assert key in r, f"Missing key '{key}' in result: {r}"

    def test_sentiment_labels_are_valid(self):
        results = []
        g = self._build_network(results)
        g.run_network(timeout=30)
        for r in results:
            assert r["sentiment"] in ("POSITIVE", "NEGATIVE", "NEUTRAL"), \
                f"Invalid sentiment label: {r['sentiment']}"

    def test_original_post_fields_preserved(self):
        """Source fields (author, hashtags, etc.) survive the transform."""
        results = []
        g = self._build_network(results)
        g.run_network(timeout=30)
        for r in results:
            assert "author" in r
            assert "hashtags" in r
            assert "url" in r

    def test_network_stops_cleanly(self):
        """Network exits on its own without hanging after max_posts."""
        import threading
        results = []
        g = self._build_network(results)
        completed = threading.Event()

        def run():
            g.run_network(timeout=30)
            completed.set()

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=15)
        assert completed.is_set(), \
            "Network did not stop cleanly within 15 seconds"
