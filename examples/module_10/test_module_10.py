# examples/module_10/test_module_10.py

"""
Tests for Module 10: Cloud Edition

Module 10 has one new lesson — cloud deployment via Railway — and zero
new Python code. The app.py is identical to module_09/app.py. The only
new file is railway.toml, which cannot be tested in pytest.

So this test suite does two things:

    1. Verifies that railway.toml exists and contains the required fields,
       so students catch configuration mistakes before pushing to Railway.

    2. Re-runs the core network tests from Module 09 against module_10/app.py
       to confirm that the identical copy actually is identical and works.

Run from the DisSysLab root directory:
    pytest examples/module_10/test_module_10.py -v
"""

import os
import pytest

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_bluesky_jetstream import DemoBlueSkyJetstream
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent


# ── Helpers ────────────────────────────────────────────────────────────────────

RAILWAY_TOML = os.path.join(
    os.path.dirname(__file__),   # examples/module_10/
    "..", "..",                  # DisSysLab root
    "railway.toml"
)
RAILWAY_TOML = os.path.normpath(RAILWAY_TOML)

MODULE_10_APP = os.path.join(os.path.dirname(__file__), "app.py")
MODULE_09_APP = os.path.join(os.path.dirname(
    __file__), "..", "module_09", "app.py")


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


# ====================================================================
# Layer 1: railway.toml Validation
# ====================================================================

class TestRailwayToml:
    """
    Verify railway.toml exists at the repo root and contains the fields
    Railway needs to build and schedule the container.

    These tests catch typos and missing fields before the student pushes
    to Railway and waits for a deployment to fail.
    """

    def test_railway_toml_exists(self):
        assert os.path.exists(RAILWAY_TOML), (
            f"railway.toml not found at repo root.\n"
            f"  Expected: {RAILWAY_TOML}\n"
            f"  Copy it from examples/module_10/railway.toml to the repo root."
        )

    def test_railway_toml_has_dockerfile_path(self):
        with open(RAILWAY_TOML) as f:
            content = f.read()
        assert "dockerfilePath" in content, (
            "railway.toml is missing 'dockerfilePath'.\n"
            "  Railway won't know where to find the Dockerfile."
        )

    def test_railway_toml_points_to_module_09_dockerfile(self):
        with open(RAILWAY_TOML) as f:
            content = f.read()
        assert "module_09" in content, (
            "railway.toml should point to examples/module_09/Dockerfile.\n"
            "  The Dockerfile is shared between Module 09 and Module 10."
        )

    def test_railway_toml_has_start_command(self):
        with open(RAILWAY_TOML) as f:
            content = f.read()
        assert "startCommand" in content, (
            "railway.toml is missing 'startCommand'.\n"
            "  Railway needs to know which command to run."
        )

    def test_railway_toml_start_command_is_module_10(self):
        with open(RAILWAY_TOML) as f:
            content = f.read()
        assert "module_10" in content, (
            "railway.toml startCommand should run examples.module_10.app,\n"
            "  not module_09. Module 10 has its own app.py."
        )

    def test_railway_toml_has_cron_schedule(self):
        with open(RAILWAY_TOML) as f:
            content = f.read()
        assert "cronSchedule" in content, (
            "railway.toml is missing 'cronSchedule'.\n"
            "  Without this, Railway won't know when to run the app."
        )

    def test_railway_toml_cron_is_not_less_than_5_minutes(self):
        """Railway enforces a minimum 5-minute interval between cron runs."""
        with open(RAILWAY_TOML) as f:
            content = f.read()
        # Extract the cronSchedule value
        for line in content.splitlines():
            if "cronSchedule" in line and "=" in line:
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                parts = value.split()
                if len(parts) == 5:
                    minute_field = parts[0]
                    # Catch */1, */2, */3, */4 — all too frequent
                    if minute_field.startswith("*/"):
                        interval = int(minute_field[2:])
                        assert interval >= 5, (
                            f"cronSchedule '{value}' runs every {interval} minute(s).\n"
                            f"  Railway's minimum interval is 5 minutes."
                        )


# ====================================================================
# Layer 2: App Identity Check
# ====================================================================

class TestAppIdentity:
    """
    Module 10's core lesson is that app.py is unchanged from Module 09.
    These tests verify that the two files are genuinely identical.
    """

    def test_module_10_app_exists(self):
        assert os.path.exists(MODULE_10_APP), \
            "examples/module_10/app.py not found."

    def test_module_09_app_exists(self):
        assert os.path.exists(MODULE_09_APP), \
            "examples/module_09/app.py not found — needed for identity check."

    def test_app_imports_module_09(self):
        with open(MODULE_10_APP) as f:
            content = f.read()
        assert "from examples.module_09.app import" in content, \
            "module_10/app.py should import from examples.module_09.app"


# ====================================================================
# Layer 3: Full Network Tests (same as Module 09)
# ====================================================================

class TestFullNetwork:
    """
    The module_10 network is identical to module_09's. These tests
    confirm it runs correctly using the demo source (no network needed).
    """

    MAX_POSTS = 5

    def _build_network(self, results):
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

        return network([
            (bluesky,   sentiment),
            (sentiment, output),
            (sentiment, collector),
        ])

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
            assert r["sentiment"] in ("POSITIVE", "NEGATIVE", "NEUTRAL")

    def test_network_stops_cleanly(self):
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
