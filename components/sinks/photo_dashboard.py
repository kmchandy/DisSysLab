# components/sinks/photo_dashboard.py

"""
PhotoDashboard: Displays merged photo quality analysis to the terminal.

Receives the merged output from MergeSynch — a list of three dicts,
one from each analyzer — and prints a clean per-photo summary with
a quality verdict.

Usage:
    from components.sinks.photo_dashboard import PhotoDashboard
    from dsl.blocks import Sink

    dashboard = PhotoDashboard()
    sink = Sink(fn=dashboard.run, name="dashboard")

The merged message format (list from MergeSynch):
    [sharpness_result, exposure_result, composition_result]
"""

import numpy as np


VERDICT_ICONS = {
    "Post it ✓": "✅",
    "Maybe   ~": "🤔",
    "Delete  ✗": "🗑️ ",
}

SHARPNESS_ICONS = {
    "sharp":  "🔍",
    "soft":   "🌫️ ",
    "blurry": "💧",
}

EXPOSURE_ICONS = {
    "good":    "☀️ ",
    "dark":    "🌑",
    "bright":  "💡",
    "clipped": "⚠️ ",
}

COMPOSITION_ICONS = {
    "good":     "🎨",
    "centered": "⊞ ",
    "sparse":   "📐",
}


def _quality_verdict(sharpness_score: float,
                     exposure_score:  float,
                     composition_score: float) -> tuple:
    """
    Combine three scores into one quality verdict.

    Weights: sharpness 40%, exposure 40%, composition 20%.
    Returns (verdict_str, total_score).
    """
    total = (0.4 * sharpness_score
           + 0.4 * exposure_score
           + 0.2 * composition_score)
    total = float(np.clip(total, 0.0, 1.0))

    if total > 0.50:
        verdict = "Post it ✓"
    elif total > 0.30:
        verdict = "Maybe   ~"
    else:
        verdict = "Delete  ✗"

    return verdict, round(total, 3)


class PhotoDashboard:
    """
    Terminal dashboard for photo quality scoring.

    Receives merged output from MergeSynch and prints a structured
    summary showing sharpness, exposure, and composition for each photo,
    combined into a single quality verdict.
    """

    def __init__(self, show_header: bool = True):
        self._photo_count = 0
        self._show_header = show_header
        self._verdicts    = []   # track summary for end

    def run(self, merged: list) -> None:
        """
        Display one photo's merged analysis.

        Args:
            merged: List of [sharpness_result, exposure_result, composition_result]
                    from MergeSynch
        """
        sharpness_r, exposure_r, composition_r = merged

        self._photo_count += 1
        filename = sharpness_r["filename"]

        if self._show_header and self._photo_count == 1:
            self._print_header()

        # Combined verdict
        verdict, score = _quality_verdict(
            sharpness_r["sharpness_score"],
            exposure_r["exposure_score"],
            composition_r["composition_score"],
        )
        self._verdicts.append((filename, verdict, score))

        # Icons
        verdict_icon = VERDICT_ICONS.get(verdict, "  ")
        sharp_icon   = SHARPNESS_ICONS.get(sharpness_r["verdict"], "  ")
        expose_icon  = EXPOSURE_ICONS.get(exposure_r["verdict"],   "  ")
        comp_icon    = COMPOSITION_ICONS.get(composition_r["verdict"], "  ")

        total = self._photo_count
        index = sharpness_r.get("index", self._photo_count)

        print(f"┌─ {filename}  ({index}/{total})  {verdict_icon} {verdict}  score={score:.2f}")
        print(f"│  Sharpness   {sharp_icon} {sharpness_r['verdict']:<8}"
              f"  lap_var={sharpness_r['laplacian_var']:>8.1f}"
              f"  score={sharpness_r['sharpness_score']:.3f}")
        print(f"│  Exposure    {expose_icon} {exposure_r['verdict']:<8}"
              f"  brightness={exposure_r['mean_brightness']:.3f}   "
              f"  score={exposure_r['exposure_score']:.3f}")
        print(f"│  Composition {comp_icon} {composition_r['verdict']:<10}"
              f"  thirds={composition_r['thirds_coverage']:.3f}      "
              f"  score={composition_r['composition_score']:.3f}")
        print(f"│  Note: {sharpness_r['note']}")
        print(f"└{'─' * 65}")
        print()

    def print_summary(self) -> None:
        """Print a final summary after all photos are processed."""
        if not self._verdicts:
            return
        post   = [v for v in self._verdicts if v[1] == "Post it ✓"]
        maybe  = [v for v in self._verdicts if v[1] == "Maybe   ~"]
        delete = [v for v in self._verdicts if v[1] == "Delete  ✗"]

        print("=" * 67)
        print(f"  Summary: {len(self._verdicts)} photos analyzed")
        print(f"  ✅ Post it: {len(post)}   🤔 Maybe: {len(maybe)}   🗑️  Delete: {len(delete)}")
        print()
        if post:
            print("  Best shots:")
            for fname, _, score in sorted(post, key=lambda x: -x[2]):
                print(f"    ✅ {fname}  (score={score:.2f})")
        print("=" * 67)
        print()

    def _print_header(self):
        """Print dashboard header on first photo."""
        print()
        print("╔" + "═" * 65 + "╗")
        print("║   📸  Photo Quality Scorer" + " " * 38 + "║")
        print("║   3 analyzers running in parallel via MergeSynch" + " " * 14 + "║")
        print("╚" + "═" * 65 + "╝")
        print()
        print("  Each photo is analyzed for: sharpness · exposure · composition")
        print("  ✅ Post it  🤔 Maybe  🗑️  Delete")
        print()


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("PhotoDashboard — Self Test")
    print("=" * 60)
    print("Simulating merged output from MergeSynch...")
    print()

    dashboard = PhotoDashboard()

    test_merges = [
        [
            {"filename": "mountain_snow.jpg", "index": 1, "total": 3,
             "laplacian_var": 7411.3, "sharpness_score": 0.741,
             "verdict": "sharp", "note": "Well-focused, clear detail throughout"},
            {"filename": "mountain_snow.jpg",
             "mean_brightness": 0.436, "clipped_shadows": 0.003,
             "clipped_highlights": 0.001, "exposure_score": 0.790,
             "verdict": "good", "note": "Well exposed — mean brightness 0.44"},
            {"filename": "mountain_snow.jpg",
             "composition_score": 0.499, "center_bias": 0.612,
             "thirds_coverage": 0.250, "verdict": "sparse",
             "note": "Few strong compositional elements"},
        ],
        [
            {"filename": "foggy_trees.jpg", "index": 2, "total": 3,
             "laplacian_var": 87.7, "sharpness_score": 0.009,
             "verdict": "blurry", "note": "Blurry — out of focus or motion blur"},
            {"filename": "foggy_trees.jpg",
             "mean_brightness": 0.458, "clipped_shadows": 0.000,
             "clipped_highlights": 0.000, "exposure_score": 0.799,
             "verdict": "good", "note": "Well exposed — mean brightness 0.46"},
            {"filename": "foggy_trees.jpg",
             "composition_score": 0.870, "center_bias": 0.498,
             "thirds_coverage": 0.464, "verdict": "good",
             "note": "Subject near rule-of-thirds points"},
        ],
        [
            {"filename": "night_scene.jpg", "index": 3, "total": 3,
             "laplacian_var": 403.4, "sharpness_score": 0.040,
             "verdict": "soft", "note": "Slightly soft — some detail lost"},
            {"filename": "night_scene.jpg",
             "mean_brightness": 0.128, "clipped_shadows": 0.039,
             "clipped_highlights": 0.000, "exposure_score": 0.338,
             "verdict": "dark", "note": "Underexposed — mean brightness 0.13"},
            {"filename": "night_scene.jpg",
             "composition_score": 0.422, "center_bias": 0.521,
             "thirds_coverage": 0.211, "verdict": "sparse",
             "note": "Few strong compositional elements"},
        ],
    ]

    for merged in test_merges:
        dashboard.run(merged)

    dashboard.print_summary()
    print("✓ PhotoDashboard working correctly")
