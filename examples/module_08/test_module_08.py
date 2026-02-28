# examples/module_08/test_module_08.py

"""
Tests for Module 08: Photo Quality Scorer — Process Edition

The network and logic are identical to Module 07. The only difference is
g.process_network() instead of g.run_network(). These tests confirm that:

    Layer 1 — Components work in isolation (no network needed)
    Layer 2 — Transform functions produce correct output
    Layer 3 — The full network runs correctly under process_network()
    Layer 4 — process_network() and run_network() produce equivalent results

Run from the DisSysLab root directory:
    pytest examples/module_08/test_module_08.py -v

Requirements:
    pip install Pillow scipy numpy
    python3 examples/module_07/download_demo_images.py   (run once)
"""

import os
import json
import math
import tempfile
import numpy as np
import pytest
from pathlib import Path

from components.sources.image_folder_source import ImageFolderSource
from components.transformers.sharpness_analyzer import SharpnessAnalyzer
from components.transformers.exposure_analyzer import ExposureAnalyzer
from components.transformers.composition_analyzer import CompositionAnalyzer
from components.sinks.photo_dashboard import PhotoDashboard
from components.sinks import JSONLRecorder
from dsl import network
from dsl.blocks import Source, Transform, Sink, MergeSynch

DEMO_IMAGES = "examples/module_07/demo_images"


# ============================================================================
# Helpers
# ============================================================================

def demo_images_exist() -> bool:
    p = Path(DEMO_IMAGES)
    return p.is_dir() and any(p.glob("*.jpg")) or any(p.glob("*.png"))


skip_no_images = pytest.mark.skipif(
    not demo_images_exist(),
    reason=f"Demo images not found. Run: python3 examples/module_07/download_demo_images.py"
)


def make_synthetic_rgb(width=200, height=150) -> np.ndarray:
    """Create a synthetic RGB image (uint8, H×W×3)."""
    rng = np.random.default_rng(42)
    return (rng.random((height, width, 3)) * 255).astype(np.uint8)


def make_synthetic_msg(filename="test.jpg", width=200, height=150) -> dict:
    """
    Create a synthetic image message in the format ImageFolderSource produces.

    ImageFolderSource converts images to grayscale floats in [0, 1] and
    stores them under the "gray" key alongside the original RGB under "image".
    SharpnessAnalyzer, ExposureAnalyzer, and CompositionAnalyzer all expect
    this dict format.
    """
    rgb = make_synthetic_rgb(width, height)
    # Grayscale: weighted sum matching standard luminance coefficients,
    # normalised to [0, 1] — this is what ImageFolderSource produces.
    gray = (0.2989 * rgb[:, :, 0]
            + 0.5870 * rgb[:, :, 1]
            + 0.1140 * rgb[:, :, 2]) / 255.0
    return {
        "filename": filename,
        "image":    rgb,    # original RGB uint8 array
        "gray":     gray,   # normalised float array in [0, 1]
    }


# ============================================================================
# Layer 1: Component Tests (no network, just functions)
# ============================================================================

class TestSharpnessAnalyzer:
    """SharpnessAnalyzer returns correct keys and sensible values."""

    def test_returns_required_keys(self):
        result = SharpnessAnalyzer().run(make_synthetic_msg())
        assert "filename" in result
        assert "sharpness_score" in result
        assert "laplacian_var" in result
        assert "verdict" in result

    def test_score_in_range(self):
        result = SharpnessAnalyzer().run(make_synthetic_msg())
        assert 0.0 <= result["sharpness_score"] <= 1.0

    def test_laplacian_var_non_negative(self):
        result = SharpnessAnalyzer().run(make_synthetic_msg())
        assert result["laplacian_var"] >= 0.0

    def test_verdict_is_string(self):
        result = SharpnessAnalyzer().run(make_synthetic_msg())
        assert isinstance(result["verdict"], str)
        assert len(result["verdict"]) > 0

    def test_filename_preserved(self):
        result = SharpnessAnalyzer().run(make_synthetic_msg(filename="my_photo.jpg"))
        assert result["filename"] == "my_photo.jpg"


class TestExposureAnalyzer:
    """ExposureAnalyzer returns correct keys and sensible values."""

    def test_returns_required_keys(self):
        result = ExposureAnalyzer().run(make_synthetic_msg())
        assert "filename" in result
        assert "exposure_score" in result
        assert "mean_brightness" in result
        assert "verdict" in result

    def test_score_in_range(self):
        result = ExposureAnalyzer().run(make_synthetic_msg())
        assert 0.0 <= result["exposure_score"] <= 1.0

    def test_mean_brightness_in_range(self):
        result = ExposureAnalyzer().run(make_synthetic_msg())
        # mean_brightness is derived from the normalized gray array, so [0.0, 1.0]
        assert 0.0 <= result["mean_brightness"] <= 1.0

    def test_bright_image_high_brightness(self):
        """An all-white image should have high mean brightness."""
        white_rgb = np.full((100, 100, 3), 255, dtype=np.uint8)
        white_gray = np.ones((100, 100), dtype=np.float64)
        msg = {"filename": "white.jpg", "image": white_rgb, "gray": white_gray}
        result = ExposureAnalyzer().run(msg)
        # mean_brightness is in the same scale as gray (0.0–1.0)
        assert result["mean_brightness"] > 0.75

    def test_dark_image_low_brightness(self):
        """An all-black image should have low mean brightness."""
        black_rgb = np.zeros((100, 100, 3), dtype=np.uint8)
        black_gray = np.zeros((100, 100), dtype=np.float64)
        msg = {"filename": "black.jpg", "image": black_rgb, "gray": black_gray}
        result = ExposureAnalyzer().run(msg)
        # mean_brightness is in the same scale as gray (0.0–1.0)
        assert result["mean_brightness"] < 0.05


class TestCompositionAnalyzer:
    """CompositionAnalyzer returns correct keys and sensible values."""

    def test_returns_required_keys(self):
        result = CompositionAnalyzer().run(make_synthetic_msg())
        assert "filename" in result
        assert "composition_score" in result
        assert "thirds_coverage" in result
        assert "verdict" in result

    def test_score_in_range(self):
        result = CompositionAnalyzer().run(make_synthetic_msg())
        assert 0.0 <= result["composition_score"] <= 1.0


# ============================================================================
# Layer 2: Transform Function Tests (archive_merged from app.py)
# ============================================================================

class TestArchiveMerged:
    """The archive_merged function in app.py produces correct flat dicts."""

    def _make_merged(self, sharpness=0.7, exposure=0.6, composition=0.5):
        sharp_r = {
            "filename": "test.jpg",
            "sharpness_score": sharpness,
            "laplacian_var": 500.0,
            "verdict": "sharp",
        }
        expose_r = {
            "filename": "test.jpg",
            "exposure_score": exposure,
            "mean_brightness": 128.0,
            "verdict": "good",
        }
        comp_r = {
            "filename": "test.jpg",
            "composition_score": composition,
            "thirds_coverage": 0.4,
            "verdict": "ok",
        }
        return [sharp_r, expose_r, comp_r]

    def _archive_merged(self, merged):
        """Inline copy of app.py's archive_merged logic for isolated testing."""
        sharp_r, expose_r, comp_r = merged
        total = float(np.clip(
            0.4 * sharp_r["sharpness_score"]
            + 0.4 * expose_r["exposure_score"]
            + 0.2 * comp_r["composition_score"],
            0.0, 1.0
        ))
        if total > 0.50:
            verdict = "post_it"
        elif total > 0.30:
            verdict = "maybe"
        else:
            verdict = "delete"

        return {
            "filename":            sharp_r["filename"],
            "quality_score":       round(total, 3),
            "verdict":             verdict,
            "laplacian_var":       sharp_r["laplacian_var"],
            "sharpness_score":     sharp_r["sharpness_score"],
            "sharpness_verdict":   sharp_r["verdict"],
            "mean_brightness":     expose_r["mean_brightness"],
            "exposure_score":      expose_r["exposure_score"],
            "exposure_verdict":    expose_r["verdict"],
            "thirds_coverage":     comp_r["thirds_coverage"],
            "composition_score":   comp_r["composition_score"],
            "composition_verdict": comp_r["verdict"],
        }

    def test_returns_required_keys(self):
        result = self._archive_merged(self._make_merged())
        required = [
            "filename", "quality_score", "verdict",
            "laplacian_var", "sharpness_score", "sharpness_verdict",
            "mean_brightness", "exposure_score", "exposure_verdict",
            "thirds_coverage", "composition_score", "composition_verdict",
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_quality_score_clamped(self):
        result = self._archive_merged(self._make_merged(1.0, 1.0, 1.0))
        assert 0.0 <= result["quality_score"] <= 1.0

    def test_verdict_post_it(self):
        result = self._archive_merged(self._make_merged(0.9, 0.9, 0.9))
        assert result["verdict"] == "post_it"

    def test_verdict_maybe(self):
        result = self._archive_merged(self._make_merged(0.4, 0.4, 0.4))
        assert result["verdict"] == "maybe"

    def test_verdict_delete(self):
        result = self._archive_merged(self._make_merged(0.1, 0.1, 0.1))
        assert result["verdict"] == "delete"

    def test_quality_score_weighted_correctly(self):
        """0.4*sharpness + 0.4*exposure + 0.2*composition"""
        sharp, expose, comp = 0.8, 0.6, 0.5
        expected = round(0.4 * sharp + 0.4 * expose + 0.2 * comp, 3)
        result = self._archive_merged(self._make_merged(sharp, expose, comp))
        assert math.isclose(result["quality_score"], expected, abs_tol=0.001)

    def test_filename_preserved(self):
        result = self._archive_merged(self._make_merged())
        assert result["filename"] == "test.jpg"


# ============================================================================
# Layer 3: Full Network — process_network() (requires demo images)
# ============================================================================

class TestProcessNetwork:
    """The full M08 network runs correctly under process_network()."""

    @skip_no_images
    def test_process_network_produces_results(self, tmp_path):
        """process_network() runs without error and produces scored images."""
        results = []

        imgs = ImageFolderSource(folder=DEMO_IMAGES)
        sharpness_an = SharpnessAnalyzer()
        exposure_an = ExposureAnalyzer()
        composition_an = CompositionAnalyzer()
        dashboard = PhotoDashboard()
        recorder = JSONLRecorder(
            path=str(tmp_path / "scores.jsonl"),
            mode="w",
            flush_every=1,
            name="archive"
        )

        def archive_merged(merged):
            sharp_r, expose_r, comp_r = merged
            total = float(np.clip(
                0.4 * sharp_r["sharpness_score"]
                + 0.4 * expose_r["exposure_score"]
                + 0.2 * comp_r["composition_score"],
                0.0, 1.0
            ))
            verdict = "post_it" if total > 0.50 else (
                "maybe" if total > 0.30 else "delete")
            flat = {
                "filename":          sharp_r["filename"],
                "quality_score":     round(total, 3),
                "verdict":           verdict,
                "sharpness_score":   sharp_r["sharpness_score"],
                "exposure_score":    expose_r["exposure_score"],
                "composition_score": comp_r["composition_score"],
            }
            recorder.run(flat)
            results.append(flat)

        image_source = Source(fn=imgs.run,              name="images")
        sharpness_node = Transform(fn=sharpness_an.run,   name="sharpness")
        exposure_node = Transform(fn=exposure_an.run,    name="exposure")
        composition_node = Transform(fn=composition_an.run, name="composition")
        merge = MergeSynch(num_inputs=3,          name="merge_synch")
        dashboard_sink = Sink(fn=dashboard.run,            name="dashboard")
        archive_sink = Sink(fn=archive_merged,           name="archive")

        g = network([
            (image_source,     sharpness_node),
            (image_source,     exposure_node),
            (image_source,     composition_node),
            (sharpness_node,   merge.in_0),
            (exposure_node,    merge.in_1),
            (composition_node, merge.in_2),
            (merge, dashboard_sink),
            (merge, archive_sink),
        ])

        g.process_network(timeout=120)

        assert len(results) > 0, "process_network() produced no results"

    @skip_no_images
    def test_every_result_has_required_keys(self, tmp_path):
        """Every scored image dict contains the expected keys."""
        results = []

        imgs = ImageFolderSource(folder=DEMO_IMAGES)
        sharpness_an = SharpnessAnalyzer()
        exposure_an = ExposureAnalyzer()
        composition_an = CompositionAnalyzer()
        recorder = JSONLRecorder(
            path=str(tmp_path / "scores.jsonl"),
            mode="w", flush_every=1, name="archive"
        )

        def archive_merged(merged):
            sharp_r, expose_r, comp_r = merged
            total = float(np.clip(
                0.4 * sharp_r["sharpness_score"]
                + 0.4 * expose_r["exposure_score"]
                + 0.2 * comp_r["composition_score"],
                0.0, 1.0
            ))
            verdict = "post_it" if total > 0.50 else (
                "maybe" if total > 0.30 else "delete")
            flat = {
                "filename":          sharp_r["filename"],
                "quality_score":     round(total, 3),
                "verdict":           verdict,
                "sharpness_score":   sharp_r["sharpness_score"],
                "exposure_score":    expose_r["exposure_score"],
                "composition_score": comp_r["composition_score"],
            }
            recorder.run(flat)
            results.append(flat)

        image_source = Source(fn=imgs.run,              name="images")
        sharpness_node = Transform(fn=sharpness_an.run,   name="sharpness")
        exposure_node = Transform(fn=exposure_an.run,    name="exposure")
        composition_node = Transform(fn=composition_an.run, name="composition")
        merge = MergeSynch(num_inputs=3,          name="merge_synch")
        archive_sink = Sink(fn=archive_merged,           name="archive")
        dashboard_sink = Sink(fn=lambda _: None,           name="dashboard")

        g = network([
            (image_source,     sharpness_node),
            (image_source,     exposure_node),
            (image_source,     composition_node),
            (sharpness_node,   merge.in_0),
            (exposure_node,    merge.in_1),
            (composition_node, merge.in_2),
            (merge, dashboard_sink),
            (merge, archive_sink),
        ])

        g.process_network(timeout=120)

        required_keys = [
            "filename", "quality_score", "verdict",
            "sharpness_score", "exposure_score", "composition_score",
        ]
        for r in results:
            for key in required_keys:
                assert key in r, f"Missing '{key}' in result: {r}"

    @skip_no_images
    def test_scores_are_in_valid_range(self, tmp_path):
        """All quality scores are between 0.0 and 1.0."""
        results = []

        imgs = ImageFolderSource(folder=DEMO_IMAGES)
        sharpness_an = SharpnessAnalyzer()
        exposure_an = ExposureAnalyzer()
        composition_an = CompositionAnalyzer()

        def archive_merged(merged):
            sharp_r, expose_r, comp_r = merged
            total = float(np.clip(
                0.4 * sharp_r["sharpness_score"]
                + 0.4 * expose_r["exposure_score"]
                + 0.2 * comp_r["composition_score"],
                0.0, 1.0
            ))
            results.append({"quality_score": total})

        image_source = Source(fn=imgs.run,              name="images")
        sharpness_node = Transform(fn=sharpness_an.run,   name="sharpness")
        exposure_node = Transform(fn=exposure_an.run,    name="exposure")
        composition_node = Transform(fn=composition_an.run, name="composition")
        merge = MergeSynch(num_inputs=3,          name="merge_synch")
        archive_sink = Sink(fn=archive_merged,           name="archive")
        dashboard_sink = Sink(fn=lambda _: None,           name="dashboard")

        g = network([
            (image_source,     sharpness_node),
            (image_source,     exposure_node),
            (image_source,     composition_node),
            (sharpness_node,   merge.in_0),
            (exposure_node,    merge.in_1),
            (composition_node, merge.in_2),
            (merge, dashboard_sink),
            (merge, archive_sink),
        ])

        g.process_network(timeout=120)

        for r in results:
            assert 0.0 <= r["quality_score"] <= 1.0, \
                f"Score out of range: {r['quality_score']}"


# ============================================================================
# Layer 4: process_network vs run_network equivalence (requires demo images)
# ============================================================================

class TestProcessVsThreadEquivalence:
    """
    The key lesson of Module 08: process_network() and run_network() produce
    the same results — the DSL hides the difference between threads and processes.
    """

    @skip_no_images
    def test_same_number_of_results(self):
        """Both execution modes score the same number of images."""

        def build_and_run(use_processes):
            results = []

            imgs = ImageFolderSource(folder=DEMO_IMAGES)
            sharpness_an = SharpnessAnalyzer()
            exposure_an = ExposureAnalyzer()
            composition_an = CompositionAnalyzer()

            def archive_merged(merged):
                sharp_r, expose_r, comp_r = merged
                total = float(np.clip(
                    0.4 * sharp_r["sharpness_score"]
                    + 0.4 * expose_r["exposure_score"]
                    + 0.2 * comp_r["composition_score"],
                    0.0, 1.0
                ))
                results.append(round(total, 3))

            image_source = Source(fn=imgs.run,              name="images")
            sharpness_node = Transform(fn=sharpness_an.run,   name="sharpness")
            exposure_node = Transform(fn=exposure_an.run,    name="exposure")
            composition_node = Transform(
                fn=composition_an.run, name="composition")
            merge = MergeSynch(num_inputs=3,          name="merge_synch")
            archive_sink = Sink(fn=archive_merged,           name="archive")
            dashboard_sink = Sink(fn=lambda _: None,
                                  name="dashboard")

            g = network([
                (image_source,     sharpness_node),
                (image_source,     exposure_node),
                (image_source,     composition_node),
                (sharpness_node,   merge.in_0),
                (exposure_node,    merge.in_1),
                (composition_node, merge.in_2),
                (merge, dashboard_sink),
                (merge, archive_sink),
            ])

            if use_processes:
                g.process_network(timeout=120)
            else:
                g.run_network(timeout=120)

            return results

        thread_results = build_and_run(use_processes=False)
        process_results = build_and_run(use_processes=True)

        assert len(thread_results) == len(process_results), (
            f"Thread mode produced {len(thread_results)} results, "
            f"process mode produced {len(process_results)}. "
            "Both should score the same number of images."
        )

    @skip_no_images
    def test_verdicts_match(self):
        """Verdict distribution is the same regardless of execution mode."""

        def collect_verdicts(use_processes):
            verdicts = []

            imgs = ImageFolderSource(folder=DEMO_IMAGES)
            sharpness_an = SharpnessAnalyzer()
            exposure_an = ExposureAnalyzer()
            composition_an = CompositionAnalyzer()

            def archive_merged(merged):
                sharp_r, expose_r, comp_r = merged
                total = float(np.clip(
                    0.4 * sharp_r["sharpness_score"]
                    + 0.4 * expose_r["exposure_score"]
                    + 0.2 * comp_r["composition_score"],
                    0.0, 1.0
                ))
                v = "post_it" if total > 0.50 else (
                    "maybe" if total > 0.30 else "delete")
                verdicts.append(v)

            image_source = Source(fn=imgs.run,              name="images")
            sharpness_node = Transform(fn=sharpness_an.run,   name="sharpness")
            exposure_node = Transform(fn=exposure_an.run,    name="exposure")
            composition_node = Transform(
                fn=composition_an.run, name="composition")
            merge = MergeSynch(num_inputs=3,          name="merge_synch")
            archive_sink = Sink(fn=archive_merged,           name="archive")
            dashboard_sink = Sink(fn=lambda _: None,
                                  name="dashboard")

            g = network([
                (image_source,     sharpness_node),
                (image_source,     exposure_node),
                (image_source,     composition_node),
                (sharpness_node,   merge.in_0),
                (exposure_node,    merge.in_1),
                (composition_node, merge.in_2),
                (merge, dashboard_sink),
                (merge, archive_sink),
            ])

            if use_processes:
                g.process_network(timeout=120)
            else:
                g.run_network(timeout=120)

            return sorted(verdicts)

        thread_verdicts = collect_verdicts(use_processes=False)
        process_verdicts = collect_verdicts(use_processes=True)

        assert thread_verdicts == process_verdicts, (
            "Verdicts differ between thread and process execution.\n"
            f"Threads:   {thread_verdicts}\n"
            f"Processes: {process_verdicts}"
        )
