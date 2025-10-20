# modules.ch04_numeric.generate_waves

from __future__ import annotations
from typing import List, Tuple
import matplotlib.pyplot as plt
import pathlib
import time
from scipy.signal import butter, sosfilt, sosfilt_zi
from typing import Callable, Generator, Iterable, Optional, Sequence, Tuple,  Union
import numpy as np


from dsl import network

Tone = Tuple[float, float]  # (frequency_hz, amplitude)
Theta = Union[float, Sequence[float]]  # radians


# ----------------------------------------------------------------------------
#                        GENERATE SINE WAVES                                |
# ----------------------------------------------------------------------------
class GenerateWaves:
    """
    Incremental synthetic audio source (sum of sines + optional Gaussian noise).

    - Library-first: uses only NumPy.
    - Source contract: zero-arg callable returning a generator that yields 1-D chunks.
    - No precomputation: each yield computes the next chunk using a phase accumulator.

    Parameters
    ----------
    fs : float
        Sample rate (Hz).
    frames_per_chunk : int
        Number of samples per yielded chunk.
    tones : iterable of (f_hz, amplitude)
        Sine components to sum.
    noise_std : float, optional
        Std dev of zero-mean Gaussian noise (default 0.0).
    theta : float or sequence of float, optional
        Initial phase(s) in radians. If scalar, applied to all tones.
        If sequence, length must equal len(tones); applied per tone.
    duration_s : float, optional
        If provided, stop after approximately this many seconds.
    max_chunks : int, optional
        If provided, stop after this many chunks (overrides duration_s if both set).
    name : str, optional
        Human-friendly node label for your graph/logs.
    dtype : np.dtype, optional
        Output dtype (default np.float32).
    """

    def __init__(
        self,
        *,
        fs: float,
        frames_per_chunk: int = 1024,
        tones: Iterable[Tone] = ((440.0, 0.5),),
        noise_std: float = 0.0,
        theta: Theta = 0.0,
        duration_s: Optional[float] = None,
        max_chunks: Optional[int] = None,
        name: str = "src_waves",
        dtype: np.dtype = np.float32,
        sleep_between_chunks: float = 0.0,
    ) -> None:
        self.fs = float(fs)
        self.F = int(frames_per_chunk)
        self.tones = tuple((float(f), float(a)) for f, a in tones)
        self.noise_std = float(noise_std)
        self.duration_s = None if duration_s is None else float(duration_s)
        self.max_chunks = None if max_chunks is None else int(max_chunks)
        self.name = name
        self.dtype = dtype
        self.sleep_between_chunks = float(sleep_between_chunks)

        if self.F <= 0:
            raise ValueError("frames_per_chunk must be > 0")
        if not self.tones:
            raise ValueError(
                "tones must contain at least one (frequency, amplitude) pair")
        if self.fs <= 0:
            raise ValueError("fs must be > 0")

        # Normalize theta → per-tone phases
        if isinstance(theta, (int, float)):
            self.phase = np.array(
                [float(theta)] * len(self.tones), dtype=float)
        else:
            th = np.asarray(list(theta), dtype=float)
            if th.size != len(self.tones):
                raise ValueError(
                    f"theta length {th.size} must match number of tones {len(self.tones)}")
            self.phase = th

        # Precompute constants
        self._two_pi = 2.0 * np.pi
        self._chunk_time = np.arange(self.F, dtype=float) / self.fs
        # How much to advance phase after one chunk for each tone
        self._dphi_per_chunk = np.array(
            [self._two_pi * f * (self.F / self.fs) for (f, _a) in self.tones],
            dtype=float,
        )

    def block(self) -> np.ndarray:
        """Generate the next chunk (1-D array, shape (F,))."""
        x = np.zeros(self.F, dtype=float)
        # Sum sines with current phases
        for i, (f, a) in enumerate(self.tones):
            if a == 0.0:
                continue
            x += a * np.sin(self._two_pi * f *
                            self._chunk_time + self.phase[i])
        if self.noise_std > 0.0:
            x += np.random.normal(0.0, self.noise_std, size=self.F)
        # Advance phases for the next call
        self.phase = (self.phase + self._dphi_per_chunk) % (2.0 * np.pi)
        return x.astype(self.dtype, copy=False)

    def __call__(self) -> Generator[np.ndarray, None, None]:
        """
        Yield successive chunks until max_chunks or duration_s (if provided).
        If neither is set, yields indefinitely (infinite stream).
        """
        chunks_emitted = 0
        max_chunks = self.max_chunks
        if max_chunks is None and self.duration_s is not None:
            max_chunks = int(np.ceil(self.duration_s * self.fs / self.F))

        while True:
            if max_chunks is not None and chunks_emitted >= max_chunks:
                break
            yield self.block()
            chunks_emitted += 1
            time.sleep(self.sleep_between_chunks)

    # Nice label for graph display if your core uses __name__
    @property
    def __name__(self) -> str:
        return self.name


# ----------------------------------------------------------------------------
#                          BANDPASS FILTER                                  |
# ----------------------------------------------------------------------------
class Bandpass:
    """Streaming filter (stateful): preserves continuity across chunks."""

    def __init__(self, *, fs: float, low_hz: float, high_hz: float, order: int = 4, name: str | None = None):
        assert 0 < low_hz < high_hz < 0.5 * fs, "bad band edges"
        nyq = 0.5 * fs
        self.sos = butter(
            order, [low_hz / nyq, high_hz / nyq], btype="bandpass", output="sos")
        self.zi = sosfilt_zi(self.sos) * 0.0
        self.name = name or f"bandpass_{int(low_hz)}_{int(high_hz)}"

    @property
    def __name__(self):  # optional for pretty node labels
        return self.name

    def reset(self):
        self.zi = sosfilt_zi(self.sos) * 0.0

    def __call__(self, x):
        xa = np.asarray(x)
        if xa.ndim == 0:              # treat scalar/0-D as length-1 vector
            xa = xa[None]
        if not np.all(np.isfinite(xa)):  # passthrough non-finite inputs
            return xa
        y, self.zi = sosfilt(self.sos, xa, zi=self.zi)
        return y


# ----------------------------------------------------------------------------
#                               FFT                                         |
# ----------------------------------------------------------------------------
class FFT:
    """
    Block FFT transformer (NumPy rFFT).

    - Callable: takes a 1-D array (or scalar) and returns (freqs, magnitude).
    - Library reuse: uses only numpy.fft.rfft / rfftfreq.
    - Minimal guards for scalar inputs and non-finite values.
    """

    def __init__(
        self,
        *,
        fs: float,
        window: Optional[Callable[[int], np.ndarray]
                         ] = None,  # e.g., np.hanning
        name: Optional[str] = None,
    ):
        assert fs > 0, "fs must be > 0"
        self.fs = float(fs)
        self.window = window
        self.name = name or "fft"

    @property
    def __name__(self) -> str:  # optional pretty node label
        return self.name

    def __call__(self, x) -> Tuple[np.ndarray, np.ndarray]:
        xa = np.asarray(x)
        if xa.ndim == 0:                 # promote scalar to length-1 vector
            xa = xa[None]
        if xa.ndim != 1:
            raise ValueError(f"FFT expects 1-D input; got shape {xa.shape}")
        if not np.all(np.isfinite(xa)):  # passthrough non-finite input unchanged
            return np.array([]), np.array([])

        # Optional window (must be length N)
        if self.window is not None:
            w = self.window(xa.size).astype(xa.dtype, copy=False)
            xa = xa * w

        freqs = np.fft.rfftfreq(xa.size, d=1.0 / self.fs)
        mag = np.abs(np.fft.rfft(xa))
        return freqs, mag


# Simple sink for (freqs, mag) tuples — prints top-K peaks rate-limited.


# modules/ch04_numeric/sinks_fft_capture_min.py


class StoreFFT:
    """
    Transformer-style sink: capture (freqs, mag) into a provided list and
    pass the value through unchanged.
    """

    def __init__(self, store: List[Tuple[np.ndarray, np.ndarray]], name: str = "sink_fft_capture"):
        self.store = store
        self.name = name

    @property
    def __name__(self) -> str:  # nice label for your graph
        return self.name

    def __call__(self, fr_mag):
        try:
            f, m = fr_mag
            f = np.asarray(f)
            m = np.asarray(m)
            if f.ndim == 1 and m.ndim == 1 and f.size == m.size and f.size > 0:
                # copy to decouple from upstream buffers
                self.store.append((f.copy(), m.copy()))
        except Exception:
            # comment-in for debugging:
            print(f"[FFTCapture] failed to capture frame: {type(fr_mag)}")
            pass


def plot_dual_spectra(
        array_0,
        array_1,
        *,
        labels=("source_fft", "bandpass_fft"),
        reduce="last", yscale="linear"):
    """
    Plot spectra captured in `raw_store` and `band_store`.
    reduce: "last" | "mean" | "median"
    """
    def _reduce(store):
        if not store:
            return None, None
        # Keep frames with the same frequency grid as the first one
        f0, _ = store[0]
        mags = [m for f, m in store if f.shape ==
                f0.shape and np.allclose(f, f0)]
        if not mags:
            return None, None
        M = np.stack(mags, axis=0)
        if reduce == "mean":
            mag = M.mean(axis=0)
        elif reduce == "median":
            mag = np.median(M, axis=0)
        else:  # "last"
            mag = M[-1]
        return f0, mag

    fr, mr = _reduce(array_0)
    fb, mb = _reduce(array_1)

    plt.figure(figsize=(9, 4.5))
    if fr is not None:
        plt.plot(fr, mr, label=labels[0])
    if fb is not None:
        plt.plot(fb, mb, "--", label=labels[1])
    plt.title("FFT Comparison")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("|X(f)|")
    plt.yscale(yscale)           # "linear" or "log"
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


waves = GenerateWaves(
    fs=200.0,
    frames_per_chunk=512,
    tones=[(5.0, 1.0), (12.0, 1.0), (30.0, 1.0)],
    theta=[0.0, 0.0, np.pi/4],   # per-tone initial phases (radians)
    noise_std=0.15,
    duration_s=10.0,             # or max_chunks=50
    sleep_between_chunks=0.5,  # simulate real-time source
    name="src_block"
)

bandpass_filter = Bandpass(
    fs=200.0, low_hz=4.0, high_hz=14.0, order=4, name="bandpass_4_14")

fft_source_signal = FFT(fs=200.0, name="fft_source_signal")
fft_after_bandpass = FFT(fs=200.0, name="fft_after_bandpass")

source_fft_array, bandpass_fft_array = [], []
store_source_fft = StoreFFT(store=source_fft_array, name="store_source_fft")
store_bandpass_fft = StoreFFT(
    store=bandpass_fft_array, name="store_bandpass_fft")

g = network([(waves, fft_source_signal),
             (waves, bandpass_filter),
            (bandpass_filter, fft_after_bandpass),
            (fft_source_signal, store_source_fft),
            (fft_after_bandpass, store_bandpass_fft),])

g.run_network()

plot_dual_spectra(
    array_0=source_fft_array,
    array_1=bandpass_fft_array)
