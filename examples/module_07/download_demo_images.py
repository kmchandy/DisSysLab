# examples/module_07/download_demo_images.py

"""
Download demo images for Module 07: Photo Quality Scorer.

Downloads 6 free-to-use photos from Lorem Picsum (https://picsum.photos),
which hosts CC0-licensed photographs. Each image covers a different
point on the quality spectrum so the three analyzers produce varied,
interesting results.

Run once before using app.py:
    python3 examples/module_07/download_demo_images.py

Images are saved to:
    examples/module_07/demo_images/

─────────────────────────────────────────────────────────────────
CUSTOMIZE THIS SCRIPT

To analyze photos that interest YOU, edit the IMAGES list below.

Option A: Use different Picsum IDs
    Browse https://picsum.photos to find IDs you like, then replace
    the entries in IMAGES. Each ID is a stable, permanent URL.

Option B: Use your own local photos
    Skip this script entirely. Point ImageFolderSource at any folder:

        source = ImageFolderSource(folder="~/Pictures/vacation_2024")

Option C: Use any CC0 image URL
    Replace the url field with any direct-link image URL.
    Good sources:
        https://picsum.photos          (CC0 photography)
        https://www.nasa.gov/images    (US government = public domain)
        https://commons.wikimedia.org  (filter by CC0 license)
─────────────────────────────────────────────────────────────────
"""

import os
import urllib.request
from pathlib import Path

# ── Image list ────────────────────────────────────────────────────────────────
# Edit this list to download photos that interest you.
# Each entry: (filename, picsum_id, description, expected_verdict)

IMAGES = [
    # Sharp, well-exposed forest path — strong subject, good light
    ("forest_path.jpg",   25,  "Forest path",      "Post it ✓"),
    # Very sharp mountain/snow scene — high contrast, clear detail
    ("mountain_snow.jpg", 29,  "Mountain scene",   "Post it ✓"),
    # City street — decent exposure but busy composition
    ("city_street.jpg",   14,  "City street",      "Maybe   ~"),
    # Foggy trees — atmospheric but soft/low sharpness
    ("foggy_trees.jpg",   80,  "Foggy trees",      "Maybe   ~"),
    # Bright bokeh — overexposed and very blurry background
    ("bright_bokeh.jpg",  130, "Bright bokeh",     "Delete  ✗"),
    # Night scene — underexposed/very dark
    ("night_scene.jpg",   120, "Night scene",      "Delete  ✗"),
]

SAVE_DIR = Path(__file__).parent / "demo_images"
WIDTH, HEIGHT = 640, 480
BASE_URL = "https://picsum.photos/id/{id}/{w}/{h}"
HEADERS  = {"User-Agent": "DisSysLab-Education/1.0 Python/3"}


def download_image(picsum_id: int, save_path: Path) -> bool:
    """Download one image from Picsum. Returns True on success."""
    url = BASE_URL.format(id=picsum_id, w=WIDTH, h=HEIGHT)
    try:
        req  = urllib.request.Request(url, headers=HEADERS)
        data = urllib.request.urlopen(req, timeout=15).read()
        save_path.write_bytes(data)
        size_kb = len(data) // 1024
        print(f"  ✓  {save_path.name:<22}  {size_kb:>4} KB  (picsum id={picsum_id})")
        return True
    except Exception as e:
        print(f"  ✗  {save_path.name:<22}  FAILED: {e}")
        return False


def main():
    print()
    print("Module 07 — Downloading demo images")
    print("=" * 50)
    print(f"Saving to: {SAVE_DIR}")
    print()

    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    for filename, picsum_id, description, verdict in IMAGES:
        save_path = SAVE_DIR / filename
        if save_path.exists():
            print(f"  –  {filename:<22}  already exists, skipping")
            ok += 1
            continue
        if download_image(picsum_id, save_path):
            ok += 1

    print()
    print(f"Downloaded {ok}/{len(IMAGES)} images")
    print()

    if ok == len(IMAGES):
        print("Expected quality scores:")
        print()
        print(f"  {'Filename':<22}  {'Description':<18}  {'Expected verdict'}")
        print("  " + "-" * 58)
        for filename, _, description, verdict in IMAGES:
            print(f"  {filename:<22}  {description:<18}  {verdict}")
        print()
        print("Run the analyzer:")
        print("  python3 -m examples.module_07.app")
    else:
        print("Some downloads failed. Check your internet connection and retry.")

    print()


if __name__ == "__main__":
    main()
