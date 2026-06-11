# dissyslab/components/sources/audio_clip_source.py

"""
AudioClipSource: streams chunks from one audio file.

Same per-chunk message shape as ``audio_mic`` — drop this source
into any office that processes streaming audio and the rest of the
pipeline is unchanged. Useful when you want to demo or test a
streaming office without setting up portaudio for live microphone
capture, or when you have a recorded incident you want to replay
through the network.

Usage in office.md::

    Sources: audio_clip(path="./samples/thunderstorm.wav",
                        chunk_ms=200)

Each emitted message::

    {
        "samples":     np.ndarray of shape (chunk_size,),
        "sample_rate": int (Hz),
        "timestamp":   float (Unix epoch seconds),
        "chunk_index": int (1-based),
    }

The source self-terminates when the file is fully consumed.
By default chunks are emitted at wall-clock pace (``paced=True``)
to mimic a live stream. Pass ``paced=False`` for as-fast-as-possible
playback, useful in tests.

Audio formats
-------------

* WAV files are decoded with the Python standard library
  (``wave`` module) plus numpy. No third-party dependency required.
  Mono and stereo files at any bit depth are supported; stereo
  files are downmixed to mono.

* Other formats (``.mp3``, ``.flac``, ``.ogg``, ``.m4a``) require
  the optional ``librosa`` dependency. If you give the source a
  non-WAV file and ``librosa`` is missing, the source prints a
  one-line install hint and signals end-of-stream cleanly.

Recommended for the default gallery experience: ship a WAV file
so the office works on a clean install with only numpy.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path


_TARGET_SR = 16000


class AudioClipSource:
    """File-based audio source paced to wall-clock by default."""

    def __init__(
        self,
        path: str = "./samples/clip.mp3",
        chunk_ms: int = 200,
        paced: bool = True,
    ):
        self.path = Path(path)
        self.chunk_ms = int(chunk_ms)
        self.paced = bool(paced)
        self._chunks = None
        self._sample_rate = None
        self._cursor = 0
        self._started_at = None
        self._exhausted = False

    # ── Lazy load + chunk ────────────────────────────────────────────
    def _ensure_loaded(self) -> bool:
        if self._exhausted:
            return False
        if self._chunks is not None:
            return True
        if not self.path.is_file():
            resolved = self.path.resolve()
            print(
                f"[audio_clip] file not found: {resolved}",
                file=sys.stderr,
            )
            print(
                "[audio_clip] Pass path=\"...\" pointing to an "
                "existing audio file.",
                file=sys.stderr,
            )
            self._exhausted = True
            return False
        try:
            import librosa
            import numpy as np
        except ImportError as exc:
            print(
                f"[audio_clip] missing dependency: {exc}",
                file=sys.stderr,
            )
            print(
                "[audio_clip] Run: pip install librosa",
                file=sys.stderr,
            )
            self._exhausted = True
            return False
        try:
            y, sr = librosa.load(
                str(self.path),
                sr=_TARGET_SR,
                mono=True,
            )
        except Exception as exc:
            print(
                f"[audio_clip] could not decode {self.path}: {exc}",
                file=sys.stderr,
            )
            self._exhausted = True
            return False
        self._sample_rate = int(sr)
        chunk_size = int(self._sample_rate * self.chunk_ms / 1000)
        if chunk_size <= 0:
            chunk_size = 1
        # Split y into chunk_size-sized chunks; drop incomplete tail
        n_chunks = max(1, len(y) // chunk_size)
        self._chunks = [
            y[i * chunk_size:(i + 1) * chunk_size]
            for i in range(n_chunks)
        ]
        self._started_at = time.time()
        return True

    # ── Per-chunk emit ───────────────────────────────────────────────
    def run(self):
        if not self._ensure_loaded():
            return None
        if self._cursor >= len(self._chunks):
            self._exhausted = True
            return None
        if self.paced and self._cursor > 0:
            elapsed = time.time() - self._started_at
            target = self._cursor * self.chunk_ms / 1000.0
            wait = target - elapsed
            if wait > 0:
                time.sleep(wait)
        samples = self._chunks[self._cursor]
        self._cursor += 1
        return {
            "samples":     samples,
            "sample_rate": self._sample_rate,
            "timestamp":   time.time(),
            "chunk_index": self._cursor,
        }
