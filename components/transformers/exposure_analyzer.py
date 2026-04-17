# components/transformers/exposure_analyzer.py

"""
ExposureAnalyzer: Measures whether a photo is well-exposed, too dark, or too bright.

Exposure is the most common reason hobbyist photos fail. This analyzer
computes mean brightness, checks for clipped highlights/shadows (pixels
stuck at pure white or pure black), and produces a normalized exposure
score and verdict.

One of three parallel analyzers in Module 07: Photo Quality Scorer.

Usage:
    from dissyslab.components.transformers.exposure_analyzer import ExposureAnalyzer
    from dissyslab.blocks import Transform

    analyzer = ExposureAnalyzer()
    node = Transform(fn=analyzer.run, name="exposure")
"""

import numpy as np


# Ideal brightness window (0=black, 1=white)
IDEAL_LOW  = 0.35
IDEAL_HIGH = 0.76

# Clipping thresholds: fraction of pixels that are pure black or pure white
CLIP_THRESHOLD = 0.08   # 5% clipped = problem


class ExposureAnalyzer:
    """
    Measures image exposure quality.

    Checks mean brightness and clipping to determine whether an image
    is well-exposed, underexposed, overexposed, or has blown highlights.

    Stateless: each image is analyzed independently.

    Input:  image dict from ImageFolderSource
    Output:
        {
            "filename":        str,
            "mean_brightness": float,   # 0.0 (black) to 1.0 (white)
            "clipped_shadows": float,   # fraction of near-black pixels
            "clipped_highlights": float, # fraction of near-white pixels
            "exposure_score":  float,   # normalized 0.0–1.0 (higher = better)
            "verdict":         str,     # "good" | "dark" | "bright" | "clipped"
            "note":            str,     # human-readable explanation
        }
    """

    def __init__(self):
        pass   # Stateless

    def run(self, image: dict) -> dict:
        """
        Measure exposure quality of one image.

        Args:
            image: Dict from ImageFolderSource containing 'gray' array

        Returns:
            Dict with exposure score and verdict
        """
        gray = image["gray"]   # values 0.0–1.0

        mean_brightness    = float(gray.mean())
        clipped_shadows    = float((gray < 0.02).mean())    # near pure black
        clipped_highlights = float((gray > 0.98).mean())    # near pure white
        total_clipped      = clipped_shadows + clipped_highlights

        # Exposure score: penalize deviation from ideal window and clipping
        brightness_score = 1.0 - min(
            abs(mean_brightness - IDEAL_LOW),
            abs(mean_brightness - IDEAL_HIGH),
            abs(mean_brightness - (IDEAL_LOW + IDEAL_HIGH) / 2) * 1.5
        ) * 2.0
        brightness_score = float(np.clip(brightness_score, 0.0, 1.0))

        clip_penalty  = float(np.clip(1.0 - total_clipped * 10, 0.0, 1.0))
        exposure_score = brightness_score * clip_penalty

        # Verdict
        if total_clipped > CLIP_THRESHOLD:
            if clipped_highlights > clipped_shadows:
                verdict = "clipped"
                note    = f"Blown highlights — {clipped_highlights*100:.1f}% of pixels are pure white"
            else:
                verdict = "clipped"
                note    = f"Crushed shadows — {clipped_shadows*100:.1f}% of pixels are pure black"
        elif mean_brightness < IDEAL_LOW:
            verdict = "dark"
            note    = f"Underexposed — mean brightness {mean_brightness:.2f} (ideal {IDEAL_LOW}–{IDEAL_HIGH})"
        elif mean_brightness > IDEAL_HIGH:
            verdict = "bright"
            note    = f"Overexposed — mean brightness {mean_brightness:.2f} (ideal {IDEAL_LOW}–{IDEAL_HIGH})"
        else:
            verdict = "good"
            note    = f"Well exposed — mean brightness {mean_brightness:.2f}"

        return {
            "filename":           image["filename"],
            "mean_brightness":    round(mean_brightness,    4),
            "clipped_shadows":    round(clipped_shadows,    4),
            "clipped_highlights": round(clipped_highlights, 4),
            "exposure_score":     round(exposure_score,     4),
            "verdict":            verdict,
            "note":               note,
        }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from pathlib import Path
    from PIL import Image

    print("ExposureAnalyzer — Self Test")
    print("=" * 60)

    demo_folder = Path(__file__).parent.parent.parent / \
        "examples" / "module_07" / "demo_images"

    if not demo_folder.exists():
        print("Demo images not found. Run first:")
        print("  python3 examples/module_07/download_demo_images.py")
        exit(1)

    analyzer = ExposureAnalyzer()

    # Known verdicts for demo images
    test_cases = [
        ("forest_path.jpg",   "good"),
        ("mountain_snow.jpg", "good"),
        ("city_street.jpg",   "good"),
        ("foggy_trees.jpg",   "good"),
        ("bright_bokeh.jpg",  "bright"),
        ("night_scene.jpg",   "dark"),
    ]

    print(f"\n  {'Filename':<22}  {'Brightness':>10}  {'Score':>7}  {'Verdict':>8}  {'OK'}")
    print("  " + "-" * 62)

    passed = 0
    for filename, expected in test_cases:
        path = demo_folder / filename
        img  = Image.open(path).convert("RGB")
        gray = np.array(img, dtype=float) @ np.array([0.299, 0.587, 0.114])
        image_dict = {
            "filename": filename,
            "gray":     gray / 255.0,
            "pixels":   np.array(img, dtype=float) / 255.0,
            "width":    img.width,
            "height":   img.height,
            "index":    1,
            "total":    6,
        }
        result = analyzer.run(image_dict)
        ok     = result["verdict"] == expected
        icon   = "✓" if ok else "✗"
        print(
            f"  {result['filename']:<22}  "
            f"{result['mean_brightness']:>10.4f}  "
            f"{result['exposure_score']:>7.4f}  "
            f"{result['verdict']:>8}  "
            f"{icon}"
        )
        if not ok:
            print(f"    Expected: {expected}  Note: {result['note']}")
        if ok:
            passed += 1

    print()
    print(f"Results: {passed}/{len(test_cases)} passed")
    if passed == len(test_cases):
        print("✓ ExposureAnalyzer working correctly")
