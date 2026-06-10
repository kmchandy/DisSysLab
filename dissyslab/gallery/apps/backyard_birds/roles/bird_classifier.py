# dissyslab/gallery/apps/backyard_birds/roles/bird_classifier.py

"""
Alex — the bird_classifier role.

Alex receives one message per audio clip and emits one message per
detected species. The classifier is `BirdNET-Analyzer`_, run via the
`birdnetlib`_ Python wrapper. Both projects are open-source and
maintained by the Cornell Lab of Ornithology / Chemnitz University of
Technology team that publishes the underlying model.

This role demonstrates the *ML-model agent* pattern: an agent in a
DSL office that is not an LLM but a classical classifier. No tokens,
no API key, no temperature — just a model that takes audio in and
emits structured detections out.

Input message (from ``audio_folder``)::

    {"path": "/abs/path/to/clip.mp3", "filename": "clip.mp3", ...}

Output messages — one per detection above the confidence threshold::

    {
        "source":          "backyard_birds",
        "title":           "Carolina Wren",            # common name
        "text":            "Heard 12.0–15.0s into clip.mp3. "
                           "Confidence 0.87.",
        "species":         "Carolina Wren",
        "scientific_name": "Thryothorus ludovicianus",
        "confidence":      0.87,
        "start_time":      12.0,
        "end_time":        15.0,
        "file":            "clip.mp3",
        "path":            "/abs/path/to/clip.mp3",
        "significance":    "HIGH",                     # for display tint
    }

If a clip yields no detections above the confidence threshold, Alex
emits a single "nothing identified" message so the user sees the
clip was processed and not silently dropped.

The BirdNET analyzer is loaded lazily on the first message so that
``dsl build backyard_birds`` succeeds even when ``birdnetlib`` is
not installed.

Setup
-----

::

    pip install birdnetlib librosa resampy

The first call downloads the BirdNET model (~50 MB) to a cache
directory in your home folder. Subsequent calls are offline.

.. _BirdNET-Analyzer: https://github.com/kahst/BirdNET-Analyzer
.. _birdnetlib:       https://github.com/joeweiss/birdnetlib
"""

from __future__ import annotations

import sys

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


# Confidence buckets for the intelligence_display tint. The thresholds
# are conservative — BirdNET detections under 0.5 are noisy.
def _significance(confidence: float) -> str:
    if confidence >= 0.8:
        return "HIGH"
    if confidence >= 0.5:
        return "MEDIUM"
    return "LOW"


_INSTALL_HINT = (
    "[bird_classifier] birdnetlib is not installed. Run:\n"
    "    pip install birdnetlib librosa resampy\n"
    "Then rerun `dsl run backyard_birds`."
)


class _BirdClassifier(Agent):
    """Run BirdNET on each inbound audio file path."""

    def __init__(
        self,
        name: str | None = None,
        min_confidence: float = 0.5,
    ):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=["out_"],
        )
        self.min_confidence = float(min_confidence)
        self._analyzer = None      # lazy
        self._birdnetlib_ok = None  # tri-state: None=unknown, True/False after attempt

    # ── Lazy analyzer construction ───────────────────────────────────
    def _ensure_analyzer(self) -> bool:
        """Return True if the analyzer is ready to use. False if
        birdnetlib is missing (we print a one-time hint and then
        silently drop messages so the office can still demonstrate
        wiring without the dependency)."""
        if self._birdnetlib_ok is False:
            return False
        if self._analyzer is not None:
            return True
        try:
            from birdnetlib.analyzer import Analyzer  # noqa: F401
        except ImportError:
            self._birdnetlib_ok = False
            print(_INSTALL_HINT, file=sys.stderr)
            return False
        try:
            self._analyzer = Analyzer()
            self._birdnetlib_ok = True
            return True
        except Exception as exc:  # pragma: no cover — analyser-init failures
            self._birdnetlib_ok = False
            print(
                f"[bird_classifier] failed to initialise BirdNET: {exc}",
                file=sys.stderr,
            )
            return False

    # ── Per-message classification ───────────────────────────────────
    def _classify(self, path: str, filename: str) -> list[dict]:
        """Return the raw birdnetlib detections list for one file."""
        from birdnetlib import Recording

        recording = Recording(
            self._analyzer,
            path,
            min_conf=self.min_confidence,
        )
        recording.analyze()
        return list(recording.detections or [])

    # ── Agent main loop ──────────────────────────────────────────────
    def run(self) -> None:  # noqa: C901 — straight-line per-message logic
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict):
                continue
            path = msg.get("path") or msg.get("filepath")
            if not path:
                continue
            filename = msg.get("filename") or path.rsplit("/", 1)[-1]

            if not self._ensure_analyzer():
                # birdnetlib missing — emit one diagnostic message and
                # move on so the office still flows end-to-end.
                self.send(
                    {
                        "source":       "backyard_birds",
                        "title":        "BirdNET not installed",
                        "text":         (
                            f"Could not analyze {filename}: "
                            "birdnetlib is missing. "
                            "Run `pip install birdnetlib librosa resampy`."
                        ),
                        "file":         filename,
                        "path":         path,
                        "significance": "LOW",
                    },
                    "out_",
                )
                continue

            try:
                detections = self._classify(path, filename)
            except FileNotFoundError:
                print(
                    f"[bird_classifier] file not found: {path}",
                    file=sys.stderr,
                )
                continue
            except Exception as exc:
                print(
                    f"[bird_classifier] failed on {filename}: {exc}",
                    file=sys.stderr,
                )
                continue

            if not detections:
                self.send(
                    {
                        "source":       "backyard_birds",
                        "title":        f"No birds in {filename}",
                        "text":         (
                            "No species above the confidence "
                            f"threshold ({self.min_confidence:.2f}) "
                            f"in {filename}."
                        ),
                        "file":         filename,
                        "path":         path,
                        "significance": "LOW",
                    },
                    "out_",
                )
                continue

            for det in detections:
                # birdnetlib's keys for a detection record. Falling back
                # gracefully if a key isn't present in a future release.
                common = det.get("common_name", "Unknown")
                scientific = det.get("scientific_name", "")
                conf = float(det.get("confidence", 0.0))
                start = float(det.get("start_time", 0.0))
                end = float(det.get("end_time", 0.0))
                self.send(
                    {
                        "source":          "backyard_birds",
                        "title":           common,
                        "text":            (
                            f"Heard {start:.1f}–{end:.1f}s "
                            f"into {filename}. "
                            f"Confidence {conf:.2f}."
                        ),
                        "species":         common,
                        "scientific_name": scientific,
                        "confidence":      conf,
                        "start_time":      start,
                        "end_time":        end,
                        "file":            filename,
                        "path":            path,
                        "significance":    _significance(conf),
                    },
                    "out_",
                )


role = AgentRoleEntry(
    name="bird_classifier",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_BirdClassifier,
)
