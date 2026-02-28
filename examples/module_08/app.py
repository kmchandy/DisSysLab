# examples/module_08/app.py

"""
Module 08: Photo Quality Scorer — Process Edition

Identical to Module 07, with one change:

    g.process_network()   # was: g.run_network()

In Module 07 each analyzer ran in its own *thread*. Threads share the
same Python interpreter, so the GIL limits true parallelism for pure
Python code.

In Module 08 each analyzer runs in its own *process* — a completely
separate Python interpreter with its own memory. The GIL is not shared,
so all three analyzers genuinely run at the same time on separate CPU
cores.

For the photo scorer this matters: SharpnessAnalyzer, ExposureAnalyzer,
and CompositionAnalyzer all do numpy/scipy work that benefits from
real CPU parallelism.

The network wiring is identical. The DSL hides the difference.

    image_source ──→ sharpness_analyzer  ──┐
                 ├─→ exposure_analyzer   ──┼──→ merge_synch ──→ dashboard
                 └─→ composition_analyzer──┘                └──→ archive

Requirements:
    pip install Pillow scipy numpy

Setup (run once):
    python3 examples/module_07/download_demo_images.py

Run:
    python3 -m examples.module_08.app
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink, MergeSynch
from components.sources.image_folder_source import ImageFolderSource
from components.transformers.sharpness_analyzer import SharpnessAnalyzer
from components.transformers.exposure_analyzer import ExposureAnalyzer
from components.transformers.composition_analyzer import CompositionAnalyzer
from components.sinks.photo_dashboard import PhotoDashboard
from components.sinks import JSONLRecorder


# ── Source ────────────────────────────────────────────────────────────────────
imgs = ImageFolderSource(folder="examples/module_07/demo_images")

# ── Three parallel analyzers ──────────────────────────────────────────────────
sharpness_an = SharpnessAnalyzer()
exposure_an = ExposureAnalyzer()
composition_an = CompositionAnalyzer()

# ── Sinks ─────────────────────────────────────────────────────────────────────
dashboard = PhotoDashboard()
recorder = JSONLRecorder(
    path="photo_scores_m08.jsonl",
    mode="w",
    flush_every=1,
    name="archive"
)


def archive_merged(merged: list) -> None:
    """Flatten merged list into a single dict for JSONL archiving."""
    sharp_r, expose_r, comp_r = merged

    import numpy as np
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

    flat = {
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
    recorder.run(flat)


# ── Build the network ─────────────────────────────────────────────────────────
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


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("Module 08: Photo scorer running with processes (not threads).")
    print("Each analyzer runs in its own OS process — true CPU parallelism.")
    print()
    g.process_network(timeout=120)
    dashboard.print_summary()
    print("Results saved to photo_scores_m08.jsonl")
    print()
    print("Compare with Module 07 (threads):")
    print("  python3 -m examples.module_07.app")
    print()
