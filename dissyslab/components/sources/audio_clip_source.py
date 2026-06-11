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
import wave
from pathlib import Path


# WAV extensions decoded by the stdlib path.
_WAV_EXTS = {".wav", ".wave"}


class AudioClipSource:
    """File-based audio source paced to wall-clock by default."""

    def __init__(
        self,
        path: str = "./samples/clip.wav",
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

        # numpy is the only hard dependency. rms_meter needs it
        # anyway so the rest of the office wouldn't run without it.
        try:
            import numpy as np
        except ImportError:
            print(
                "[audio_clip] numpy is required.\n"
                "[audio_clip] Run: pip install numpy",
                file=sys.stderr,
            )
            self._exhausted = True
            return False

        # WAV → stdlib path. Everything else → optional librosa.
        if self.path.suffix.lower() in _WAV_EXTS:
            y, sr = self._load_wav(np)
        else:
            y, sr = self._load_non_wav(np)
        if y is None:
            self._exhausted = True
            return False

        self._sample_rate = int(sr)
        chunk_size = int(self._sample_rate * self.chunk_ms / 1000)
        if chunk_size <= 0:
            chunk_size = 1
        n_chunks = max(1, len(y) // chunk_size)
        self._chunks = [
            y[i * chunk_size:(i + 1) * chunk_size]
            for i in range(n_chunks)
        ]
        self._started_at = time.time()
        return True

    # ── WAV decoder (stdlib only) ────────────────────────────────────
    def _load_wav(self, np):
        """Decode a WAV file with the stdlib ``wave`` module + numpy.

        Returns ``(samples_mono_float32, sample_rate)`` or
        ``(None, None)`` on failure.
        """
        try:
            with wave.open(str(self.path), "rb") as wf:
                nchannels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                sample_rate = wf.getframerate()
                nframes = wf.getnframes()
                raw = wf.readframes(nframes)
        except Exception as exc:
            print(
                f"[audio_clip] could not read WAV {self.path}: {exc}",
                file=sys.stderr,
            )
            return None, None

        # Convert raw bytes to float32 in [-1, 1] based on bit depth.
        if sampwidth == 1:           # 8-bit unsigned
            y = (
                np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
                / 128.0
                - 1.0
            )
        elif sampwidth == 2:         # 16-bit signed
            y = (
                np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                / 32768.0
            )
        elif sampwidth == 3:         # 24-bit signed (rare; expand to int32)
            arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
            i32 = (
                (arr[:, 0].astype(np.int32))
                | (arr[:, 1].astype(np.int32) << 8)
                | (arr[:, 2].astype(np.int32) << 16)
            )
            # Sign-extend
            i32 = np.where(i32 & 0x800000, i32 - 0x1000000, i32)
            y = i32.astype(np.float32) / float(2 ** 23)
        elif sampwidth == 4:         # 32-bit signed
            y = (
                np.frombuffer(raw, dtype=np.int32).astype(np.float32)
                / float(2 ** 31)
            )
        else:
            print(
                f"[audio_clip] unsupported WAV sample width: "
                f"{sampwidth} bytes",
                file=sys.stderr,
            )
            return None, None

        # Downmix to mono if needed.
        if nchannels > 1:
            y = y.reshape(-1, nchannels).mean(axis=1)
        return y.astype(np.float32), int(sample_rate)

    # ── Non-WAV decoder (optional librosa) ───────────────────────────
    def _load_non_wav(self, np):
        """Decode mp3/flac/ogg/m4a via librosa if it is installed.

        librosa pulls in numba / llvmlite, which are heavy and
        sometimes fail to install. We do not require it for the
        default gallery experience; we ship a WAV instead. But if
        a user points us at a non-WAV file, we try.
        """
        try:
            import librosa
        except ImportError:
            print(
                f"[audio_clip] {self.path.suffix} files require the "
                "optional 'librosa' dependency.\n"
                "[audio_clip] Either pip install librosa (and accept "
                "the numba/llvmlite build), or convert your file to "
                "WAV first, e.g.:\n"
                "[audio_clip]     ffmpeg -i input.mp3 output.wav",
                file=sys.stderr,
            )
            return None, None
        try:
            y, sr = librosa.load(str(self.path), sr=None, mono=True)
            return y.astype(np.float32), int(sr)
        except Exception as exc:
            print(
                f"[audio_clip] could not decode {self.path}: {exc}",
                file=sys.stderr,
            )
            return None, None

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
        # stream_position_seconds is start-of-chunk in the audio
        # stream. For audio_clip this is position in the source
        # file; for audio_mic it is wall-clock seconds since the
        # office started capturing. The field's name is the same so
        # downstream agents do not need to know which kind of source
        # they are reading from.
        stream_position_seconds = (self._cursor - 1) * (self.chunk_ms / 1000.0)
        return {
            "samples":     samples,
            "sample_rate": self._sample_rate,
            "timestamp":   time.time(),
            "chunk_index": self._cursor,
            "stream_position_seconds": stream_position_seconds,
        }
