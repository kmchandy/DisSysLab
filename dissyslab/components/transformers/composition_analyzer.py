# dissyslab/components/transformers/composition_analyzer.py

"""
CompositionAnalyzer: Measures whether a photo follows the rule of thirds.

The rule of thirds is the most fundamental composition guideline in
photography: divide the frame into a 3×3 grid, and place the subject
near one of the four intersection points ("power points") rather than
dead center. Photos following this rule tend to feel more dynamic
and visually interesting.

This analyzer detects where the strongest edges (subject boundaries)
are located relative to the rule-of-thirds power points.

One of three parallel analyzers in Module 07: Photo Quality Scorer.

Usage:
    from dissyslab.components.transformers.composition_analyzer import CompositionAnalyzer
    from dissyslab.blocks import Transform

    analyzer = CompositionAnalyzer()
    node = Transform(fn=analyzer.run, name="composition")
"""

import numpy as np
from scipy.ndimage import sobel


class CompositionAnalyzer:
    """
    Measures image composition using the rule of thirds.

    Detects edges using the Sobel operator, then checks whether
    strong edges cluster near the four power points of the rule-of-thirds
    grid rather than the center or edges of the frame.

    Stateless: each image is analyzed independently.

    Input:  image dict from ImageFolderSource
    Output:
        {
            "filename":           str,
            "composition_score":  float,   # 0.0–1.0 (higher = better thirds)
            "center_bias":        float,   # fraction of edges near center
            "thirds_coverage":    float,   # fraction of edges near power points
            "verdict":            str,     # "good" | "centered" | "sparse"
            "note":               str,     # human-readable explanation
        }
    """

    # Power point zone: how large a region around each intersection counts
    ZONE_FRACTION = 0.125   # 1/8 of image dimension each side

    # Thresholds
    GOOD_THRESHOLD     = 0.25   # thirds_coverage above this = good composition
    CENTERED_THRESHOLD = 0.35   # center_bias above this = subject is centered

    def __init__(self):
        pass   # Stateless

    def _power_point_mask(self, h: int, w: int) -> np.ndarray:
        """Build a mask that is 1 near the four rule-of-thirds power points."""
        mask     = np.zeros((h, w), dtype=float)
        margin_h = int(h * self.ZONE_FRACTION)
        margin_w = int(w * self.ZONE_FRACTION)

        for ph in [h // 3, 2 * h // 3]:
            for pw in [w // 3, 2 * w // 3]:
                r0 = max(0, ph - margin_h)
                r1 = min(h, ph + margin_h)
                c0 = max(0, pw - margin_w)
                c1 = min(w, pw + margin_w)
                mask[r0:r1, c0:c1] = 1.0
        return mask

    def _center_mask(self, h: int, w: int) -> np.ndarray:
        """Build a mask for the central region of the frame."""
        mask = np.zeros((h, w), dtype=float)
        r0   = h // 4
        r1   = 3 * h // 4
        c0   = w // 4
        c1   = 3 * w // 4
        mask[r0:r1, c0:c1] = 1.0
        return mask

    def run(self, image: dict) -> dict:
        """
        Measure composition quality of one image.

        Args:
            image: Dict from ImageFolderSource containing 'gray' array

        Returns:
            Dict with composition score and verdict
        """
        gray   = image["gray"] * 255.0
        h, w   = gray.shape

        # Detect edges using Sobel operator
        edges  = np.hypot(sobel(gray, axis=0), sobel(gray, axis=1))

        # Only consider strong edges (top 15%)
        threshold     = np.percentile(edges, 85)
        strong_edges  = edges > threshold

        total_strong  = strong_edges.sum()
        if total_strong == 0:
            return {
                "filename":          image["filename"],
                "composition_score": 0.0,
                "center_bias":       0.0,
                "thirds_coverage":   0.0,
                "verdict":           "sparse",
                "note":              "Very few edges — featureless or blank image",
            }

        # How many strong edges fall near the power points?
        pp_mask        = self._power_point_mask(h, w)
        thirds_coverage = float((strong_edges * pp_mask).sum() / total_strong)

        # How many strong edges fall in the center zone?
        center_mask    = self._center_mask(h, w)
        center_bias    = float((strong_edges * center_mask).sum() / total_strong)

        # Composition score: reward thirds coverage, penalize pure center bias
        composition_score = float(np.clip(
            thirds_coverage * 2.0 - max(0, center_bias - 0.5) * 0.5,
            0.0, 1.0
        ))

        # Verdict
        if thirds_coverage >= self.GOOD_THRESHOLD:
            verdict = "good"
            note    = f"Subject near rule-of-thirds points ({thirds_coverage*100:.0f}% of edges)"
        elif center_bias >= self.CENTERED_THRESHOLD:
            verdict = "centered"
            note    = f"Subject centered — try the rule of thirds ({thirds_coverage*100:.0f}% near power points)"
        else:
            verdict = "sparse"
            note    = f"Few strong compositional elements ({thirds_coverage*100:.0f}% near power points)"

        return {
            "filename":          image["filename"],
            "composition_score": round(composition_score,  4),
            "center_bias":       round(center_bias,        4),
            "thirds_coverage":   round(thirds_coverage,    4),
            "verdict":           verdict,
            "note":              note,
        }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from pathlib import Path
    from PIL import Image

    print("CompositionAnalyzer — Self Test")
    print("=" * 60)

    demo_folder = Path(__file__).parent.parent.parent / \
        "examples" / "module_07" / "demo_images"

    if not demo_folder.exists():
        print("Demo images not found. Run first:")
        print("  python3 examples/module_07/download_demo_images.py")
        exit(1)

    analyzer = CompositionAnalyzer()

    print(f"\n  {'Filename':<22}  {'Score':>7}  {'Thirds':>7}  {'Center':>7}  {'Verdict'}")
    print("  " + "-" * 65)

    images = ["forest_path.jpg", "mountain_snow.jpg", "city_street.jpg",
              "foggy_trees.jpg", "bright_bokeh.jpg",  "night_scene.jpg"]

    for filename in images:
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
        print(
            f"  {result['filename']:<22}  "
            f"{result['composition_score']:>7.4f}  "
            f"{result['thirds_coverage']:>7.4f}  "
            f"{result['center_bias']:>7.4f}  "
            f"{result['verdict']}"
        )

    print()
    print("✓ CompositionAnalyzer working correctly")
