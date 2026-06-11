# dissyslab/gallery/apps/wildlife_watcher/roles/animal_classifier.py

"""
Alex — the animal_classifier role.

Wraps `MobileNetV3-Small`_ from torchvision, pretrained on ImageNet,
and emits one prediction per inbound image. This is a per-office
role because its contract is on *content* (specific image input
shape, specific ImageNet output classes); the generic *gating*
that comes after it lives in the framework library as
``confidence_filter``.

The classifier emits the top prediction plus a category flag
(``"animal"`` if the top class index is in the ImageNet
organisms/animals range, otherwise ``"object"``). It deliberately
does **not** filter — the downstream ``confidence_filter`` decides
which messages reach the sink. Each agent has one well-defined job.

.. _MobileNetV3-Small: https://pytorch.org/vision/stable/models/generated/torchvision.models.mobilenet_v3_small.html

Input message (from ``image_folder``)::

    {
        "filename": "deer.jpg",
        "filepath": "/abs/path/to/deer.jpg",
        "pixels":   H×W×3 float ndarray in [0, 1],
        "width":    int,
        "height":   int,
        "index":    int,
        "total":    int,
    }

Output message (one per image, no filtering)::

    {
        "source":       "wildlife_watcher",
        "filename":     "deer.jpg",
        "label":        "hartebeest",
        "label_index":  351,
        "confidence":   0.74,
        "category":     "animal",     # or "object"
        "top_5":        [(label, confidence), ...],
        "title":        "Saw a hartebeest",
        "text":         "in deer.jpg — 0.74 confidence",
        "significance": "HIGH",       # by confidence bucket
    }

Setup
-----

::

    pip install torch torchvision pillow

First inference downloads the ~5 MB MobileNetV3-Small weights from
the PyTorch hub. Subsequent inferences are offline.
"""

from __future__ import annotations

import sys

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


# In the ImageNet 1000-class index, indices below this threshold
# are organisms (fish, birds, reptiles, mammals). Higher indices
# are mostly objects, food, scenes. This is the standard heuristic
# used in many camera-trap pipelines; if you have a model with a
# different label ordering, override with your own list.
_ANIMAL_INDEX_CUTOFF = 398


_INSTALL_HINT = (
    "[animal_classifier] torch / torchvision / Pillow not installed.\n"
    "[animal_classifier] Run: pip install torch torchvision pillow\n"
    "[animal_classifier] Then rerun `dsl run wildlife_watcher`."
)


def _significance(confidence: float) -> str:
    if confidence >= 0.7:
        return "HIGH"
    if confidence >= 0.4:
        return "MEDIUM"
    return "LOW"


def _category(label_index: int) -> str:
    return "animal" if label_index < _ANIMAL_INDEX_CUTOFF else "object"


class _AnimalClassifier(Agent):
    """One MobileNetV3-Small forward pass per inbound image."""

    def __init__(self, name: str | None = None):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=["out_"],
        )
        self._model = None
        self._preprocess = None
        self._categories = None
        self._torch = None
        self._install_ok = None  # None=untried, True/False after attempt

    # ── Lazy model load ──────────────────────────────────────────────
    def _ensure_model(self) -> bool:
        if self._install_ok is False:
            return False
        if self._model is not None:
            return True
        try:
            import torch
            from torchvision.models import (
                mobilenet_v3_small,
                MobileNet_V3_Small_Weights,
            )
        except ImportError:
            self._install_ok = False
            print(_INSTALL_HINT, file=sys.stderr)
            return False
        try:
            weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1
            self._model = mobilenet_v3_small(weights=weights).eval()
            self._preprocess = weights.transforms()
            self._categories = weights.meta["categories"]
            self._torch = torch
            self._install_ok = True
            return True
        except Exception as exc:  # pragma: no cover — model-load failures
            self._install_ok = False
            print(
                f"[animal_classifier] failed to load MobileNetV3: {exc}",
                file=sys.stderr,
            )
            return False

    # ── Per-image classification ─────────────────────────────────────
    def _classify(self, pixels, filename: str) -> dict | None:
        """Run one forward pass and pack the message dict."""
        import numpy as np
        from PIL import Image

        try:
            # pixels is H×W×3 float in [0,1]. PIL expects uint8.
            arr = (np.asarray(pixels) * 255.0).clip(0, 255).astype("uint8")
            pil = Image.fromarray(arr)
            tensor = self._preprocess(pil).unsqueeze(0)
            with self._torch.inference_mode():
                logits = self._model(tensor)
                probs = self._torch.softmax(logits[0], dim=0)
                top5_probs, top5_idx = probs.topk(5)
            top5 = [
                (self._categories[int(i)], float(p))
                for i, p in zip(top5_idx, top5_probs)
            ]
            top_label, top_conf = top5[0]
            top_index = int(top5_idx[0])
        except Exception as exc:
            print(
                f"[animal_classifier] inference failed on {filename}: {exc}",
                file=sys.stderr,
            )
            return None

        cat = _category(top_index)
        sig = _significance(top_conf)
        article = "an" if top_label[:1].lower() in "aeiou" else "a"
        return {
            "source":       "wildlife_watcher",
            "filename":     filename,
            "label":        top_label,
            "label_index":  top_index,
            "confidence":   top_conf,
            "category":     cat,
            "top_5":        top5,
            "title":        f"Saw {article} {top_label}",
            "text":         (
                f"in {filename} — confidence {top_conf:.2f}  "
                f"({cat})"
            ),
            "significance": sig,
        }

    # ── Agent main loop ──────────────────────────────────────────────
    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict):
                continue
            pixels = msg.get("pixels")
            if pixels is None:
                continue
            filename = msg.get("filename") or "?"

            if not self._ensure_model():
                # torch/torchvision missing — emit one diagnostic
                # message so the office still flows end-to-end.
                self.send(
                    {
                        "source":       "wildlife_watcher",
                        "filename":     filename,
                        "label":        "(classifier unavailable)",
                        "confidence":   0.0,
                        "category":     "error",
                        "title":        "Classifier unavailable",
                        "text": (
                            f"Could not classify {filename}: torch / "
                            "torchvision / Pillow not installed."
                        ),
                        "significance": "LOW",
                    },
                    "out_",
                )
                continue

            out = self._classify(pixels, filename)
            if out is not None:
                self.send(out, "out_")


role = AgentRoleEntry(
    name="animal_classifier",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_AnimalClassifier,
)
