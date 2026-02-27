# examples/module_07/plot_results.py

"""
Plot photo quality scores from photo_scores.jsonl

Run after app.py has completed:
    python3 examples/module_07/plot_results.py

Requires:
    pip install matplotlib
"""

import json
import sys
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


# ── Load data ─────────────────────────────────────────────────────────────────

LOGFILE = "photo_scores.jsonl"

if not os.path.exists(LOGFILE):
    print(f"Error: {LOGFILE} not found.")
    print("Run app.py first:  python3 -m examples.module_07.app")
    sys.exit(1)

with open(LOGFILE) as f:
    data = [json.loads(line) for line in f if line.strip()]

if not data:
    print(f"Error: {LOGFILE} is empty.")
    sys.exit(1)

print(f"Loaded {len(data)} photos from {LOGFILE}")

# ── Extract series ─────────────────────────────────────────────────────────────

filenames = [d["filename"].replace(".jpg", "") for d in data]
quality = [d["quality_score"] for d in data]
sharpness = [d["sharpness_score"] for d in data]
exposure = [d["exposure_score"] for d in data]
composition = [d["composition_score"] for d in data]
brightness = [d["mean_brightness"] for d in data]
lap_var = [d["laplacian_var"] for d in data]
thirds = [d["thirds_coverage"] for d in data]
verdicts = [d["verdict"] for d in data]

n = len(data)
x = np.arange(n)
width = 0.22

# Verdict colors for the quality score dots
VERDICT_COLORS = {
    "post_it": "green",
    "maybe":   "orange",
    "delete":  "red",
}

# ── Plot ───────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(14, 11))
fig.suptitle("Photo Quality Scorer — Results", fontsize=14, fontweight="bold")

gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.55, wspace=0.35)

# ── Panel 1: Score breakdown (full width) ─────────────────────────────────────
ax1 = fig.add_subplot(gs[0, :])

b1 = ax1.bar(x - width,   sharpness,   width,
             label="Sharpness (40%)",   color="steelblue",  alpha=0.85)
b2 = ax1.bar(x,           exposure,    width,
             label="Exposure (40%)",    color="darkorange", alpha=0.85)
b3 = ax1.bar(x + width,   composition, width,
             label="Composition (20%)", color="seagreen",   alpha=0.85)

# Quality score as a line with verdict-colored dots
for i, (xi, q, v) in enumerate(zip(x, quality, verdicts)):
    color = VERDICT_COLORS.get(v, "gray")
    ax1.plot(xi, q, "o", color=color, markersize=10, zorder=5)

# Dummy plots for legend
ax1.plot([], [], "o", color="green",  markersize=8, label="Post it ✓")
ax1.plot([], [], "o", color="orange", markersize=8, label="Maybe ~")
ax1.plot([], [], "o", color="red",    markersize=8, label="Delete ✗")
ax1.plot(x, quality, "--", color="gray", linewidth=1,
         alpha=0.5, label="Quality score")

ax1.axhline(y=0.50, color="green", linestyle=":", alpha=0.4, linewidth=1.5)
ax1.axhline(y=0.30, color="red",   linestyle=":", alpha=0.4, linewidth=1.5)

ax1.set_xticks(x)
ax1.set_xticklabels(filenames, rotation=25, ha="right", fontsize=9)
ax1.set_ylabel("Score (0–1)")
ax1.set_title("Quality Score Breakdown — Sharpness · Exposure · Composition")
ax1.set_ylim(0, 1.15)
ax1.legend(loc="upper right", fontsize=8, ncol=3)
ax1.grid(True, axis="y", alpha=0.3)

# ── Panel 2: Raw sharpness (Laplacian variance) ───────────────────────────────
ax2 = fig.add_subplot(gs[1, 0])
colors2 = ["steelblue" if s >= 0.3 else "lightsteelblue" for s in sharpness]
ax2.bar(x, lap_var, color=colors2, alpha=0.85)
ax2.axhline(y=2000, color="green", linestyle="--",
            alpha=0.6, label="Sharp threshold")
ax2.axhline(y=300,  color="red",   linestyle="--",
            alpha=0.6, label="Soft threshold")
ax2.set_xticks(x)
ax2.set_xticklabels(filenames, rotation=25, ha="right", fontsize=8)
ax2.set_ylabel("Laplacian Variance")
ax2.set_title("Sharpness — Raw Score\n(higher = sharper)")
ax2.legend(fontsize=8)
ax2.grid(True, axis="y", alpha=0.3)

# ── Panel 3: Mean brightness ───────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, 1])
colors3 = []
for b in brightness:
    if b < 0.35:
        colors3.append("navy")
    elif b > 0.76:
        colors3.append("gold")
    else:
        colors3.append("darkorange")

ax3.bar(x, brightness, color=colors3, alpha=0.85)
ax3.axhline(y=0.35, color="navy", linestyle="--",
            alpha=0.6, label="Dark threshold (0.35)")
ax3.axhline(y=0.76, color="gold", linestyle="--",
            alpha=0.6, label="Bright threshold (0.76)")
ax3.fill_between([-0.5, n - 0.5], 0.35, 0.76,
                 alpha=0.08, color="green", label="Ideal range")
ax3.set_xticks(x)
ax3.set_xticklabels(filenames, rotation=25, ha="right", fontsize=8)
ax3.set_ylabel("Mean Brightness (0–1)")
ax3.set_title("Exposure — Mean Brightness\n(ideal range shaded green)")
ax3.set_xlim(-0.5, n - 0.5)
ax3.set_ylim(0, 1.05)
ax3.legend(fontsize=8)
ax3.grid(True, axis="y", alpha=0.3)

# ── Panel 4: Rule-of-thirds coverage ──────────────────────────────────────────
ax4 = fig.add_subplot(gs[2, 0])
colors4 = ["seagreen" if t >= 0.25 else "lightgreen" for t in thirds]
ax4.bar(x, thirds, color=colors4, alpha=0.85)
ax4.axhline(y=0.25, color="seagreen", linestyle="--",
            alpha=0.6, label="Good threshold (0.25)")
ax4.set_xticks(x)
ax4.set_xticklabels(filenames, rotation=25, ha="right", fontsize=8)
ax4.set_ylabel("Thirds Coverage (0–1)")
ax4.set_title(
    "Composition — Rule of Thirds\n(fraction of edges near power points)")
ax4.legend(fontsize=8)
ax4.grid(True, axis="y", alpha=0.3)

# ── Panel 5: Verdict summary ───────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[2, 1])

post_it = verdicts.count("post_it")
maybe = verdicts.count("maybe")
delete = verdicts.count("delete")

wedge_sizes = [post_it, maybe, delete]
wedge_labels = [f"Post it ✓\n({post_it})",
                f"Maybe ~\n({maybe})", f"Delete ✗\n({delete})"]
wedge_colors = ["green", "orange", "red"]
wedge_explode = [0.05, 0.05, 0.05]

# Only show non-zero slices
nonzero = [(s, l, c, e) for s, l, c, e in
           zip(wedge_sizes, wedge_labels, wedge_colors, wedge_explode) if s > 0]
if nonzero:
    sizes, labels, colors5, explode = zip(*nonzero)
    ax5.pie(sizes, labels=labels, colors=colors5, explode=explode,
            autopct="%1.0f%%", startangle=90,
            textprops={"fontsize": 9})

ax5.set_title(f"Verdict Summary\n({n} photos)")

# ── Save and show ──────────────────────────────────────────────────────────────

outfile = "photo_quality_analysis.png"
plt.savefig(outfile, dpi=150, bbox_inches="tight")
print(f"Saved to {outfile}")
plt.show()

# ── Print text summary ─────────────────────────────────────────────────────────

print()
print("=" * 50)
print("Photo Quality Summary")
print("=" * 50)
print(f"Photos analyzed: {n}")
print()
print(f"  ✅ Post it:  {post_it}")
print(f"  🤔 Maybe:    {maybe}")
print(f"  🗑️  Delete:   {delete}")
print()

best = max(data, key=lambda d: d["quality_score"])
worst = min(data, key=lambda d: d["quality_score"])

print(
    f"Best photo:    {best['filename']}  (score={best['quality_score']:.3f})")
print(
    f"  sharpness={best['sharpness_score']:.3f}  exposure={best['exposure_score']:.3f}  composition={best['composition_score']:.3f}")
print()
print(
    f"Weakest photo: {worst['filename']}  (score={worst['quality_score']:.3f})")
print(
    f"  sharpness={worst['sharpness_score']:.3f}  exposure={worst['exposure_score']:.3f}  composition={worst['composition_score']:.3f}")
print()
print(f"Average quality score: {np.mean(quality):.3f}")
print(f"Average sharpness:     {np.mean(sharpness):.3f}")
print(f"Average exposure:      {np.mean(exposure):.3f}")
print(f"Average composition:   {np.mean(composition):.3f}")
print("=" * 50)
