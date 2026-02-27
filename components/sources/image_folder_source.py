# components/sources/image_folder_source.py

"""
ImageFolderSource: Reads images from a folder and emits them one at a time.

Each message is a dict containing the filename, pixel array, and dimensions.
The three downstream analyzers each receive this same dict and examine a
different aspect of the image simultaneously.

This is the source for Module 07: Photo Quality Scorer.

Usage:
    from components.sources.image_folder_source import ImageFolderSource
    from dsl.blocks import Source

    imgs = ImageFolderSource(folder="examples/module_07/demo_images")
    source = Source(fn=imgs.run, name="images")

Requirements:
    pip install Pillow numpy
"""

import os
import numpy as np
from pathlib import Path
from PIL import Image


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


class ImageFolderSource:
    """
    Reads image files from a folder and emits one per call.

    Emits a dict for each image:
        {
            "filename":  str,         # just the filename, e.g. "sunset.jpg"
            "filepath":  str,         # full path
            "pixels":    np.ndarray,  # H×W×3 float array, values 0.0–1.0
            "gray":      np.ndarray,  # H×W float array (grayscale)
            "width":     int,
            "height":    int,
            "index":     int,         # 1-based position in folder
            "total":     int,         # total images in folder
        }

    Returns None when all images have been emitted (signals network to stop).
    """

    def __init__(self, folder: str = "examples/module_07/demo_images",
                 max_images: int = None):
        """
        Args:
            folder:     Path to folder containing images
            max_images: Maximum images to emit (None = all)
        """
        self.folder     = Path(folder)
        self.max_images = max_images
        self._files     = self._find_images()
        self._index     = 0

    def _find_images(self) -> list:
        """Find all supported image files in folder, sorted by name."""
        if not self.folder.exists():
            raise FileNotFoundError(
                f"Image folder not found: {self.folder}\n"
                f"Run first: python3 examples/module_07/download_demo_images.py"
            )
        files = sorted([
            f for f in self.folder.iterdir()
            if f.suffix.lower() in SUPPORTED_EXTENSIONS
        ])
        if not files:
            raise ValueError(f"No images found in {self.folder}")
        return files

    def run(self):
        """
        Emit the next image as a dict, or None when exhausted.

        Called repeatedly by Source() until None is returned.
        """
        limit = self.max_images or len(self._files)
        if self._index >= min(len(self._files), limit):
            return None

        filepath = self._files[self._index]
        self._index += 1

        img   = Image.open(filepath).convert("RGB")
        w, h  = img.size
        rgb   = np.array(img, dtype=float) / 255.0      # H×W×3, values 0-1
        gray  = rgb @ np.array([0.299, 0.587, 0.114])   # H×W, luminance

        return {
            "filename": filepath.name,
            "filepath": str(filepath),
            "pixels":   rgb,
            "gray":     gray,
            "width":    w,
            "height":   h,
            "index":    self._index,
            "total":    min(len(self._files), limit),
        }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("ImageFolderSource — Self Test")
    print("=" * 60)

    demo_folder = Path(__file__).parent.parent.parent / \
        "examples" / "module_07" / "demo_images"

    if not demo_folder.exists():
        print(f"Demo images not found at: {demo_folder}")
        print("Run: python3 examples/module_07/download_demo_images.py")
        exit(1)

    src = ImageFolderSource(folder=str(demo_folder))
    print(f"Found images in: {demo_folder}")
    print()

    print(f"  {'#':>3}  {'Filename':<22}  {'Size':>12}  {'Pixels':>14}  {'Bright':>7}")
    print("  " + "-" * 65)

    count = 0
    while True:
        msg = src.run()
        if msg is None:
            break
        brightness = msg["gray"].mean()
        h, w = msg["gray"].shape
        print(
            f"  {msg['index']:>3}  "
            f"{msg['filename']:<22}  "
            f"{msg['width']:>5}×{msg['height']:<5}  "
            f"{h*w:>14,}  "
            f"{brightness:>7.3f}"
        )
        count += 1

    print()
    print(f"Emitted {count} images, then returned None (network stops)")
    print()
    print("✓ ImageFolderSource working correctly")
