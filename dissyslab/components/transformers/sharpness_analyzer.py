# dissyslab/components/transformers/sharpness_analyzer.py

"""
SharpnessAnalyzer: Measures how sharp or blurry a photo is.

Uses the Laplacian variance method — the most widely used sharpness
metric in computational photography. The Laplacian operator detects
rapid changes in pixel intensity (edges). A sharp image has many strong
edges → high variance. A blurry image has smooth gradients → low variance.

One of three parallel analyzers in Module 07: Photo Quality Scorer.

Usage:
    from dissyslab.components.transformers.sharpness_analyzer import SharpnessAnalyzer
    from dissyslab.blocks import Transform

    analyzer = SharpnessAnalyzer()
    node = Transform(fn=analyzer.run, name="sharpness")
"""

import numpy as np
from scipy.ndimage import laplace


# Thresholds tuned on Picsum demo images
SHARP_THRESHOLD  = 2000.0   # above = sharp
SOFT_THRESHOLD   = 300.0    # below = blurry, between = soft


class SharpnessAnalyzer:
    """
    Measures image sharpness using Laplacian variance.

    Stateless: each image is analyzed independently.

    Input:  image dict from ImageFolderSource
    Output:
        {
            "filename":        str,
            "laplacian_var":   float,   # raw sharpness score (higher = sharper)
            "sharpness_score": float,   # normalized 0.0–1.0
            "verdict":         str,     # "sharp" | "soft" | "blurry"
            "note":            str,     # human-readable explanation
        }
    """

    def __init__(self):
        pass   # Stateless

    def run(self, image: dict) -> dict:
        """
        Measure sharpness of one image.

        Args:
            image: Dict from ImageFolderSource containing 'gray' array

        Returns:
            Dict with sharpness score and verdict
        """
        gray = image["gray"] * 255.0   # scale back to 0–255 for variance

        # Laplacian variance: high = lots of sharp edges, low = blurry
        lap_var = float(np.var(laplace(gray)))

        # Normalize to 0–1 (cap at 10000, which is extremely sharp)
        score = float(np.clip(lap_var / 10000.0, 0.0, 1.0))

        # Verdict
        if lap_var >= SHARP_THRESHOLD:
            verdict = "sharp"
            note    = "Well-focused, clear detail throughout"
        elif lap_var >= SOFT_THRESHOLD:
            verdict = "soft"
            note    = "Slightly soft — some detail lost"
        else:
            verdict = "blurry"
            note    = "Blurry — out of focus or motion blur"

        return {
            "filename":        image["filename"],
            "laplacian_var":   round(lap_var, 2),
            "sharpness_score": round(score, 4),
            "verdict":         verdict,
            "note":            note,
        }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from pathlib import Path
    from PIL import Image

    print("SharpnessAnalyzer — Self Test")
    print("=" * 60)

    demo_folder = Path(__file__).parent.parent.parent / \
        "examples" / "module_07" / "demo_images"

    if not demo_folder.exists():
        print(f"Demo images not found. Run first:")
        print("  python3 examples/module_07/download_demo_images.py")
        exit(1)

    analyzer = SharpnessAnalyzer()

    # These verdicts are known from running the analyzer on the demo images
    test_cases = [
        ("forest_path.jpg",   "sharp"),
        ("mountain_snow.jpg", "sharp"),
        ("city_street.jpg",   "soft"),
        ("foggy_trees.jpg",   "blurry"),
        ("bright_bokeh.jpg",  "blurry"),
        ("night_scene.jpg",   "soft"),
    ]

    print(f"\n  {'Filename':<22}  {'Lap Var':>10}  {'Score':>7}  {'Verdict':>8}  {'OK'}")
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
            f"{result['laplacian_var']:>10.1f}  "
            f"{result['sharpness_score']:>7.4f}  "
            f"{result['verdict']:>8}  "
            f"{icon}"
        )
        if ok:
            passed += 1

    print()
    print(f"Results: {passed}/{len(test_cases)} passed")
    if passed == len(test_cases):
        print("✓ SharpnessAnalyzer working correctly")
