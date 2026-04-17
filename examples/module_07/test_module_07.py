# examples/module_07/test_module_07.py

"""
Tests for Module 07: Photo Quality Scorer

Three layers:
    1. Component tests  — each analyzer class works in isolation
    2. Integration tests — all three analyzers on real images
    3. Network test     — full network produces expected output

Run from the DisSysLab root directory:
    pytest examples/module_07/test_module_07.py -v
"""

import pytest
import numpy as np
from pathlib import Path
from PIL import Image

from dissyslab.components.sources.image_folder_source import ImageFolderSource
from dissyslab.components.transformers.sharpness_analyzer import SharpnessAnalyzer
from dissyslab.components.transformers.exposure_analyzer import ExposureAnalyzer
from dissyslab.components.transformers.composition_analyzer import CompositionAnalyzer
from dissyslab.components.sinks.photo_dashboard import PhotoDashboard, _quality_verdict


# ── Helpers ───────────────────────────────────────────────────────────────────

DEMO_FOLDER = Path("examples/module_07/demo_images")


def _load_image_dict(filename: str) -> dict:
    """Load a demo image into the standard dict format."""
    path = DEMO_FOLDER / filename
    img = Image.open(path).convert("RGB")
    rgb = np.array(img, dtype=float) / 255.0
    gray = rgb @ np.array([0.299, 0.587, 0.114])
    return {
        "filename": filename,
        "filepath": str(path),
        "pixels":   rgb,
        "gray":     gray,
        "width":    img.width,
        "height":   img.height,
        "index":    1,
        "total":    6,
    }


def _make_synthetic_image(brightness: float, blur_sigma: float = 0.5,
                          filename: str = "test.jpg") -> dict:
    """Create a synthetic image dict for unit testing without disk access."""
    from scipy.ndimage import gaussian_filter
    np.random.seed(42)
    h, w = 240, 320
    gray = np.random.random((h, w)) * brightness
    gray = gaussian_filter(gray, sigma=blur_sigma)
    gray = np.clip(gray, 0.0, 1.0)
    rgb = np.stack([gray, gray, gray], axis=-1)
    return {
        "filename": filename,
        "filepath": f"synthetic/{filename}",
        "pixels":   rgb,
        "gray":     gray,
        "width":    w,
        "height":   h,
        "index":    1,
        "total":    1,
    }


def demo_images_available() -> bool:
    return DEMO_FOLDER.exists() and len(list(DEMO_FOLDER.glob("*.jpg"))) >= 6


# ── Layer 1: Component tests (synthetic images, no disk access) ───────────────

class TestSharpnessAnalyzer:
    """SharpnessAnalyzer returns correct keys and verdicts."""

    def setup_method(self):
        self.analyzer = SharpnessAnalyzer()

    def test_returns_required_keys(self):
        img = _make_synthetic_image(0.5)
        result = self.analyzer.run(img)
        assert "filename" in result
        assert "laplacian_var" in result
        assert "sharpness_score" in result
        assert "verdict" in result
        assert "note" in result

    def test_sharp_image_gets_high_score(self):
        from scipy.ndimage import gaussian_filter
        np.random.seed(0)
        gray = np.random.random((240, 320))  # pure noise = maximally sharp
        img = {"filename": "sharp.jpg", "gray": gray,
               "pixels": np.stack([gray]*3, axis=-1),
               "width": 320, "height": 240, "index": 1, "total": 1}
        result = self.analyzer.run(img)
        assert result["sharpness_score"] > 0.5

    def test_blurry_image_gets_low_score(self):
        from scipy.ndimage import gaussian_filter
        np.random.seed(0)
        base = np.random.random((240, 320))
        blurry = gaussian_filter(base, sigma=20)
        img = {"filename": "blurry.jpg", "gray": blurry,
               "pixels": np.stack([blurry]*3, axis=-1),
               "width": 320, "height": 240, "index": 1, "total": 1}
        result = self.analyzer.run(img)
        assert result["sharpness_score"] < 0.1
        assert result["verdict"] == "blurry"

    def test_score_between_0_and_1(self):
        img = _make_synthetic_image(0.5)
        result = self.analyzer.run(img)
        assert 0.0 <= result["sharpness_score"] <= 1.0

    def test_verdict_is_valid_string(self):
        img = _make_synthetic_image(0.5)
        result = self.analyzer.run(img)
        assert result["verdict"] in {"sharp", "soft", "blurry"}

    def test_filename_preserved(self):
        img = _make_synthetic_image(0.5, filename="my_photo.jpg")
        result = self.analyzer.run(img)
        assert result["filename"] == "my_photo.jpg"


class TestExposureAnalyzer:
    """ExposureAnalyzer returns correct keys and verdicts."""

    def setup_method(self):
        self.analyzer = ExposureAnalyzer()

    def test_returns_required_keys(self):
        img = _make_synthetic_image(0.5)
        result = self.analyzer.run(img)
        assert "filename" in result
        assert "mean_brightness" in result
        assert "exposure_score" in result
        assert "verdict" in result
        assert "note" in result
        assert "clipped_shadows" in result
        assert "clipped_highlights" in result

    def test_dark_image_gets_dark_verdict(self):
        img = _make_synthetic_image(brightness=0.1)
        result = self.analyzer.run(img)
        assert result["verdict"] == "dark"

    def test_bright_image_gets_bright_verdict(self):
        np.random.seed(0)
        gray = np.ones((240, 320)) * 0.90
        img = {"filename": "bright.jpg", "gray": gray,
               "pixels": np.stack([gray]*3, axis=-1),
               "width": 320, "height": 240, "index": 1, "total": 1}
        result = self.analyzer.run(img)
        assert result["verdict"] == "bright"

    def test_well_exposed_image_gets_good_verdict(self):
        # Use a uniform gray at 0.55 — _make_synthetic_image scales noise
        # by brightness so mean ends up at brightness/2, not brightness itself
        gray = np.ones((240, 320)) * 0.55
        img = {"filename": "midgray.jpg", "gray": gray,
               "pixels": np.stack([gray]*3, axis=-1),
               "width": 320, "height": 240, "index": 1, "total": 1}
        result = self.analyzer.run(img)
        assert result["verdict"] == "good"

    def test_score_between_0_and_1(self):
        img = _make_synthetic_image(0.5)
        result = self.analyzer.run(img)
        assert 0.0 <= result["exposure_score"] <= 1.0

    def test_mean_brightness_matches_input(self):
        gray = np.ones((240, 320)) * 0.6
        img = {"filename": "test.jpg", "gray": gray,
               "pixels": np.stack([gray]*3, axis=-1),
               "width": 320, "height": 240, "index": 1, "total": 1}
        result = self.analyzer.run(img)
        assert result["mean_brightness"] == pytest.approx(0.6, abs=0.01)


class TestCompositionAnalyzer:
    """CompositionAnalyzer returns correct keys and valid scores."""

    def setup_method(self):
        self.analyzer = CompositionAnalyzer()

    def test_returns_required_keys(self):
        img = _make_synthetic_image(0.5)
        result = self.analyzer.run(img)
        assert "filename" in result
        assert "composition_score" in result
        assert "center_bias" in result
        assert "thirds_coverage" in result
        assert "verdict" in result
        assert "note" in result

    def test_score_between_0_and_1(self):
        img = _make_synthetic_image(0.5)
        result = self.analyzer.run(img)
        assert 0.0 <= result["composition_score"] <= 1.0

    def test_thirds_coverage_between_0_and_1(self):
        img = _make_synthetic_image(0.5)
        result = self.analyzer.run(img)
        assert 0.0 <= result["thirds_coverage"] <= 1.0

    def test_verdict_is_valid_string(self):
        img = _make_synthetic_image(0.5)
        result = self.analyzer.run(img)
        assert result["verdict"] in {"good", "centered", "sparse"}

    def test_blank_image_gets_sparse_verdict(self):
        gray = np.ones((240, 320)) * 0.5   # uniform = no edges
        img = {"filename": "blank.jpg", "gray": gray,
               "pixels": np.stack([gray]*3, axis=-1),
               "width": 320, "height": 240, "index": 1, "total": 1}
        result = self.analyzer.run(img)
        assert result["verdict"] == "sparse"


class TestQualityVerdict:
    """_quality_verdict combines three scores correctly."""

    def test_high_scores_give_post_it(self):
        verdict, score = _quality_verdict(0.9, 0.9, 0.9)
        assert verdict == "Post it ✓"
        assert score > 0.5

    def test_low_scores_give_delete(self):
        verdict, score = _quality_verdict(0.05, 0.1, 0.1)
        assert verdict == "Delete  ✗"
        assert score < 0.3

    def test_mid_scores_give_maybe(self):
        verdict, score = _quality_verdict(0.4, 0.4, 0.4)
        assert verdict == "Maybe   ~"

    def test_score_between_0_and_1(self):
        _, score = _quality_verdict(0.5, 0.5, 0.5)
        assert 0.0 <= score <= 1.0

    def test_sharpness_weight_dominates(self):
        # High sharpness + low everything else should still score reasonably
        _, score_sharp = _quality_verdict(1.0, 0.0, 0.0)
        _, score_comp = _quality_verdict(0.0, 0.0, 1.0)
        assert score_sharp > score_comp   # sharpness weighted 40% vs comp 20%


# ── Layer 2: Integration tests on real demo images ────────────────────────────

@pytest.mark.skipif(not demo_images_available(),
                    reason="Demo images not downloaded — run download_demo_images.py")
class TestAnalyzersOnRealImages:
    """All three analyzers produce correct verdicts on the 6 demo images."""

    def setup_method(self):
        self.sharpness_an = SharpnessAnalyzer()
        self.exposure_an = ExposureAnalyzer()
        self.composition_an = CompositionAnalyzer()

    def _run_all(self, filename):
        img = _load_image_dict(filename)
        return (
            self.sharpness_an.run(img),
            self.exposure_an.run(img),
            self.composition_an.run(img),
        )

    def test_forest_path_is_post_it(self):
        s, e, c = self._run_all("forest_path.jpg")
        verdict, _ = _quality_verdict(s["sharpness_score"],
                                      e["exposure_score"],
                                      c["composition_score"])
        assert verdict == "Post it ✓"

    def test_mountain_snow_is_post_it(self):
        s, e, c = self._run_all("mountain_snow.jpg")
        verdict, _ = _quality_verdict(s["sharpness_score"],
                                      e["exposure_score"],
                                      c["composition_score"])
        assert verdict == "Post it ✓"

    def test_night_scene_is_delete(self):
        s, e, c = self._run_all("night_scene.jpg")
        verdict, _ = _quality_verdict(s["sharpness_score"],
                                      e["exposure_score"],
                                      c["composition_score"])
        assert verdict == "Delete  ✗"

    def test_forest_path_sharpness_is_sharp(self):
        s, _, _ = self._run_all("forest_path.jpg")
        assert s["verdict"] == "sharp"

    def test_foggy_trees_sharpness_is_blurry(self):
        s, _, _ = self._run_all("foggy_trees.jpg")
        assert s["verdict"] == "blurry"

    def test_night_scene_exposure_is_dark(self):
        _, e, _ = self._run_all("night_scene.jpg")
        assert e["verdict"] == "dark"

    def test_bright_bokeh_exposure_is_bright(self):
        _, e, _ = self._run_all("bright_bokeh.jpg")
        assert e["verdict"] == "bright"

    def test_all_analyzers_return_same_filename(self):
        for filename in ["forest_path.jpg", "night_scene.jpg"]:
            s, e, c = self._run_all(filename)
            assert s["filename"] == e["filename"] == c["filename"] == filename

    def test_dashboard_accepts_all_images(self):
        dashboard = PhotoDashboard(show_header=False)
        for filename in ["forest_path.jpg", "mountain_snow.jpg",
                         "city_street.jpg", "foggy_trees.jpg",
                         "bright_bokeh.jpg", "night_scene.jpg"]:
            s, e, c = self._run_all(filename)
            # Should not raise
            dashboard.run([s, e, c])
        assert dashboard._photo_count == 6


# ── Layer 3: Network test ─────────────────────────────────────────────────────

@pytest.mark.skipif(not demo_images_available(),
                    reason="Demo images not downloaded — run download_demo_images.py")
class TestModule07Network:
    """Full network produces one merged result per image and archives them."""

    def test_network_processes_all_images(self, tmp_path):
        import json
        from dissyslab import network
        from dissyslab.blocks import Source, Transform, Sink, MergeSynch
        from dissyslab.components.sinks import JSONLRecorder

        archive_path = str(tmp_path / "test_photo_scores.jsonl")
        imgs = ImageFolderSource(folder=str(DEMO_FOLDER))
        sharpness_an = SharpnessAnalyzer()
        exposure_an = ExposureAnalyzer()
        composition_an = CompositionAnalyzer()
        recorder = JSONLRecorder(path=archive_path, mode="w", flush_every=1)

        results = []

        def collect_and_archive(merged):
            results.append(merged)
            sharp_r, expose_r, comp_r = merged
            recorder.run({
                "filename":       sharp_r["filename"],
                "sharpness":      sharp_r["sharpness_score"],
                "exposure":       expose_r["exposure_score"],
                "composition":    comp_r["composition_score"],
            })

        image_source = Source(fn=imgs.run,               name="images")
        sharpness_node = Transform(fn=sharpness_an.run,    name="sharpness")
        exposure_node = Transform(fn=exposure_an.run,     name="exposure")
        composition_node = Transform(
            fn=composition_an.run,  name="composition")
        merge = MergeSynch(num_inputs=3,           name="merge")
        sink = Sink(fn=collect_and_archive,       name="sink")

        g = network([
            (image_source,     sharpness_node),
            (image_source,     exposure_node),
            (image_source,     composition_node),
            (sharpness_node,   merge.in_0),
            (exposure_node,    merge.in_1),
            (composition_node, merge.in_2),
            (merge, sink),
        ])

        g.run_network(timeout=60)

        # Should have processed all 6 demo images
        assert len(results) == 6

        # Each merged result should be a list of 3 dicts
        for merged in results:
            assert len(merged) == 3
            assert isinstance(merged[0], dict)
            assert isinstance(merged[1], dict)
            assert isinstance(merged[2], dict)

        # Archive file should have 6 lines
        with open(archive_path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 6
        assert "filename" in lines[0]
        assert "sharpness" in lines[0]
        assert "exposure" in lines[0]
        assert "composition" in lines[0]

    def test_merge_synch_emits_list_of_three(self, tmp_path):
        """MergeSynch always emits exactly 3 items per image."""
        from dissyslab import network
        from dissyslab.blocks import Source, Transform, Sink, MergeSynch

        imgs = ImageFolderSource(folder=str(DEMO_FOLDER), max_images=2)
        sharpness_an = SharpnessAnalyzer()
        exposure_an = ExposureAnalyzer()
        composition_an = CompositionAnalyzer()

        merged_outputs = []

        image_source = Source(fn=imgs.run,               name="images")
        sharpness_node = Transform(fn=sharpness_an.run,    name="sharpness")
        exposure_node = Transform(fn=exposure_an.run,     name="exposure")
        composition_node = Transform(
            fn=composition_an.run,  name="composition")
        merge = MergeSynch(num_inputs=3,           name="merge")
        sink = Sink(fn=merged_outputs.append,     name="sink")

        g = network([
            (image_source,     sharpness_node),
            (image_source,     exposure_node),
            (image_source,     composition_node),
            (sharpness_node,   merge.in_0),
            (exposure_node,    merge.in_1),
            (composition_node, merge.in_2),
            (merge, sink),
        ])

        g.run_network(timeout=30)

        assert len(merged_outputs) == 2
        for merged in merged_outputs:
            assert len(merged) == 3


@pytest.mark.skipif(demo_images_available(),
                    reason="Only runs when demo images are missing")
class TestWithoutDemoImages:
    """Graceful error when demo images haven't been downloaded."""

    def test_image_folder_source_raises_helpful_error(self):
        with pytest.raises(FileNotFoundError, match="download_demo_images"):
            ImageFolderSource(folder="examples/module_07/demo_images_missing")
