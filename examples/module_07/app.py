# examples/module_07/app.py

"""
Module 07: Photo Quality Scorer

Three analyzers examine every photo in parallel — sharpness, exposure,
and composition — then MergeSynch combines the results into a quality
verdict: Post it ✓ / Maybe ~ / Delete ✗

Network topology — identical structure to Module 06:

    image_source ──→ sharpness_analyzer  ──┐
                 ├─→ exposure_analyzer   ──┼──→ merge_synch ──→ dashboard
                 └─→ composition_analyzer──┘                └──→ archive

Compare with Module 06:

    cartpole_source → [reward | policy | curve] → merge_synch → dashboard

Same 9 lines of network wiring. Same pattern. Different domain.
This is the key insight: the gather-scatter pattern works for any data.

Requirements:
    pip install Pillow scipy numpy

Setup (run once):
    python3 examples/module_07/download_demo_images.py

Run:
    python3 -m examples.module_07.app
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, MergeSynch
from components.sources.image_folder_source              import ImageFolderSource
from components.transformers.sharpness_analyzer          import SharpnessAnalyzer
from components.transformers.exposure_analyzer           import ExposureAnalyzer
from components.transformers.composition_analyzer        import CompositionAnalyzer
from components.sinks.photo_dashboard                    import PhotoDashboard
from components.sinks                                    import JSONLRecorder


# ── Source: reads images one at a time ───────────────────────────────────────
# Change this folder to analyze your own photos:
#     imgs = ImageFolderSource(folder="~/Pictures/vacation_2024")

imgs = ImageFolderSource(folder="examples/module_07/demo_images")


# ── Three parallel analyzers ──────────────────────────────────────────────────
# Each receives the same image dict and examines a different aspect.
# They run in parallel threads — MergeSynch waits for all three.

sharpness_an   = SharpnessAnalyzer()
exposure_an    = ExposureAnalyzer()
composition_an = CompositionAnalyzer()


# ── Sinks ─────────────────────────────────────────────────────────────────────
dashboard = PhotoDashboard()
recorder  = JSONLRecorder(
    path="photo_scores.jsonl",
    mode="w",
    flush_every=1,
    name="archive"
)


def archive_merged(merged: list) -> None:
    """
    Flatten merged list into a single dict for JSONL archiving.

    MergeSynch emits [sharpness_result, exposure_result, composition_result].
    This combines them into one flat dict so each line in the JSONL file
    contains the full picture for that photo.
    """
    sharp_r, expose_r, comp_r = merged

    # Compute combined verdict (same logic as PhotoDashboard)
    import numpy as np
    total = float(np.clip(
        0.4 * sharp_r["sharpness_score"]
      + 0.4 * expose_r["exposure_score"]
      + 0.2 * comp_r["composition_score"],
        0.0, 1.0
    ))
    if total > 0.50:    verdict = "post_it"
    elif total > 0.30:  verdict = "maybe"
    else:               verdict = "delete"

    flat = {
        "filename":          sharp_r["filename"],
        "quality_score":     round(total, 3),
        "verdict":           verdict,
        # Sharpness
        "laplacian_var":     sharp_r["laplacian_var"],
        "sharpness_score":   sharp_r["sharpness_score"],
        "sharpness_verdict": sharp_r["verdict"],
        # Exposure
        "mean_brightness":   expose_r["mean_brightness"],
        "exposure_score":    expose_r["exposure_score"],
        "exposure_verdict":  expose_r["verdict"],
        # Composition
        "thirds_coverage":   comp_r["thirds_coverage"],
        "composition_score": comp_r["composition_score"],
        "composition_verdict": comp_r["verdict"],
    }
    recorder.run(flat)


# ── Build the network ─────────────────────────────────────────────────────────

image_source      = Source(fn=imgs.run,              name="images")
sharpness_node    = Transform(fn=sharpness_an.run,   name="sharpness")
exposure_node     = Transform(fn=exposure_an.run,    name="exposure")
composition_node  = Transform(fn=composition_an.run, name="composition")
merge             = MergeSynch(num_inputs=3,          name="merge_synch")
dashboard_sink    = Sink(fn=dashboard.run,            name="dashboard")
archive_sink      = Sink(fn=archive_merged,           name="archive")

g = network([
    # Scatter: one image fans out to three analyzers
    (image_source,     sharpness_node),
    (image_source,     exposure_node),
    (image_source,     composition_node),

    # Gather: three analyzers merge synchronously
    (sharpness_node,   merge.in_0),
    (exposure_node,    merge.in_1),
    (composition_node, merge.in_2),

    # Output: dashboard + archive both receive the merged result
    (merge, dashboard_sink),
    (merge, archive_sink),
])


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("Analyzing photos. Each row = one photo, three parallel analyses.")
    print()
    g.run_network(timeout=120)
    dashboard.print_summary()
    print("Results saved to photo_scores.jsonl")
    print()
    print("To analyze your own photos:")
    print("  Change folder= in app.py to point at your photo directory")
    print()
    print("To plot quality scores:")
    print("  python3 examples/module_07/plot_results.py")
