# dissyslab/components/sources/audio_mic_source.py

"""
AudioMicSource: streams chunks of live microphone audio.

This is the source for the ``loudness_monitor`` gallery office, which
detects loud events in real time. Like ``audio_folder`` (for file-by-
file processing) and ``audio_clip`` (for file-paced testing), it
emits one message per chunk of samples — the downstream agent
decides what to do with them.

Usage in office.md::

    Sources: audio_mic(chunk_ms=200, max_seconds=60)

Each message carries::

    {
        "samples":     np.ndarray of shape (chunk_size,),
        "sample_rate": int (Hz),
        "timestamp":   float (Unix epoch seconds),
        "chunk_index": int (1-based, monotonic per office run),
    }

The source self-terminates after ``max_seconds`` so demo runs stop
on their own. Pass ``max_seconds=None`` for indefinite operation.

Requirements:
    pip install sounddevice
    macOS: brew install portaudio

The ``sounddevice`` import is lazy so ``dsl build`` succeeds even
without portaudio installed. If the dependency is missing at run
time, the source prints a one-line install hint and signals
end-of-stream cleanly.
"""

from __future__ import annotations

import sys
import time


class AudioMicSource:
    """Live-microphone source.

    Parameters
    ----------
    sample_rate:
        Samples per second. 16000 Hz is plenty for loudness metering
        and matches the sample rate downstream audio models (BirdNET,
        Whisper, etc.) expect.
    chunk_ms:
        Chunk size in milliseconds. 200 ms (= 3200 samples at 16 kHz)
        gives ~5 chunks per second — responsive enough to feel
        instant, large enough that arithmetic per chunk is cheap.
    max_seconds:
        Auto-terminate after this many seconds. ``None`` runs
        forever. Defaults to 60 so a demo run ends on its own.
    channels:
        1 = mono (default), 2 = stereo. Multi-channel input is
        averaged to mono before emit so the downstream contract is
        always a 1-D array.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_ms: int = 200,
        max_seconds: float | None = 60,
        channels: int = 1,
    ):
        self.sample_rate = int(sample_rate)
        self.chunk_ms = int(chunk_ms)
        self.max_seconds = max_seconds
        self.channels = int(channels)
        self._chunk_size = int(self.sample_rate * self.chunk_ms / 1000)
        self._sd = None       # lazy sounddevice
        self._stream = None
        self._np = None       # lazy numpy
        self._started_at = None
        self._chunk_index = 0
        self._exhausted = False

    # ── Lazy stream setup ────────────────────────────────────────────
    def _ensure_stream(self) -> bool:
        """Return True if the input stream is open and ready."""
        if self._exhausted:
            return False
        if self._stream is not None:
            return True
        try:
            import sounddevice as sd
            import numpy as np
        except (ImportError, OSError) as exc:
            print(
                "[audio_mic] could not load sounddevice/portaudio: "
                f"{exc}",
                file=sys.stderr,
            )
            print(
                "[audio_mic] Run: pip install sounddevice",
                file=sys.stderr,
            )
            print(
                "[audio_mic] On macOS first: brew install portaudio",
                file=sys.stderr,
            )
            print(
                "[audio_mic] Or use audio_clip(path=\"...\") to test "
                "against a file without a mic.",
                file=sys.stderr,
            )
            self._exhausted = True
            return False
        try:
            self._sd = sd
            self._np = np
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self._chunk_size,
                dtype="float32",
            )
            self._stream.start()
            self._started_at = time.time()
        except Exception as exc:
            print(
                f"[audio_mic] could not open input stream: {exc}",
                file=sys.stderr,
            )
            print(
                "[audio_mic] Check that a microphone is available "
                "and that this app has permission to use it.",
                file=sys.stderr,
            )
            self._exhausted = True
            return False
        return True

    # ── Per-chunk read ───────────────────────────────────────────────
    def run(self):
        """Emit the next audio chunk, or ``None`` to end the stream."""
        if not self._ensure_stream():
            return None
        # Auto-terminate after max_seconds
        if (
            self.max_seconds is not None
            and (time.time() - self._started_at) >= self.max_seconds
        ):
            self._close()
            return None
        try:
            samples, _overflowed = self._stream.read(self._chunk_size)
        except Exception as exc:
            print(
                f"[audio_mic] read error: {exc}",
                file=sys.stderr,
            )
            self._close()
            return None
        # Flatten to mono
        if samples.ndim > 1 and samples.shape[1] > 1:
            samples = samples.mean(axis=1)
        else:
            samples = samples.flatten()
        self._chunk_index += 1
        return {
            "samples":     samples,
            "sample_rate": self.sample_rate,
            "timestamp":   time.time(),
            "chunk_index": self._chunk_index,
        }

    def _close(self) -> None:
        self._exhausted = True
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
