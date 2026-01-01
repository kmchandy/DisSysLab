# modules.ch04_numeric.synthetic_sines_demo

from __future__ import annotations
import time
from scipy.signal import butter, sosfilt, sosfilt_zi
from typing import Union
import math
from collections import deque
from typing import Iterable, Dict, Any, Tuple

import numpy as np
from scipy.signal import butter, sosfilt, welch, find_peaks
import matplotlib.pyplot as plt

from dsl import network

# ─────────────────────────────────────────────────────────
# 1) Source — sum of noisy sines (yields {"t", "x"})
# ─────────────────────────────────────────────────────────


def src(
    *,
    sample_rate: float = 200.0,
    duration_s: float = 8.0,
    tones: Iterable[Tuple[float, float]] = (
        (5.0, 2.0), (12.0, 2.0), (30.0, 0.5)),  # (freq_hz, amplitude)
    noise_std: float = 0.15,
):
    n_total = int(duration_s * sample_rate)
    dt = 1.0 / sample_rate
    t = 0.0
    tones = list(tones)
    for _ in range(n_total):
        x = 0.0
        for f, a in tones:
            x += a * math.sin(2 * math.pi * f * t)
        x += np.random.normal(scale=noise_std)
        yield {"t": t, "x": float(x)}
        t += dt
        time.sleep(dt)  # real-time pacing

# ─────────────────────────────────────────────────────────
# 2) Transform A — Butterworth band-pass (SciPy)
#    Adds "x_bp" to each message
# ─────────────────────────────────────────────────────────


ArrayLike = Union[float, int, np.ndarray]


class ButterBandpassFilter:
    """
    Streaming Butterworth band-pass that operates on *numeric* inputs only.

    - If called with a scalar (float/int), returns a scalar and advances state by 1 sample.
    - If called with a 1D numpy array, returns an array and advances state by len(array) samples.
    - Maintains persistent IIR state (`zi`) across calls for correct streaming behavior.
    """

    def __init__(
        self,
        *,
        low_hz: float = 4.0,
        high_hz: float = 14.0,
        order: int = 4,
        sample_rate: float = 200.0,
        name: str | None = None,
        strict: bool = False,  # if True, raise on bad inputs; else pass-through for NaN/inf
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be > 0")
        nyq = 0.5 * sample_rate
        if not (0 < low_hz < high_hz < nyq):
            raise ValueError(
                f"cutoffs must satisfy 0 < low < high < Nyquist={nyq:.6g}; got {low_hz}, {high_hz}")

        self.fs = sample_rate
        self.low = low_hz / nyq
        self.high = high_hz / nyq
        self.order = order
        self.strict = strict

        self.sos = butter(order, [self.low, self.high],
                          btype="bandpass", output="sos")
        # start from zero initial conditions
        self.zi = sosfilt_zi(self.sos) * 0.0

        self.name = name or f"butter_bandpass[{low_hz:.3g}-{high_hz:.3g}Hz]_ord{order}@{sample_rate:.3g}Hz"

    def reset(self) -> None:
        """Reset internal filter state."""
        self.zi = sosfilt_zi(self.sos) * 0.0

    def __repr__(self) -> str:
        return f"<ButterBandpassFilter {self.name}>"

    def run(self, msg: Dict) -> ArrayLike:
        """
        Apply the streaming band-pass.
        First extract x = `msg["x"]`, then apply the filter to x.
        - Scalar in  -> scalar out
        - 1D array in -> 1D array out (and state advanced across the whole block)
        """
        # msg is a dict with fields "t", "x".
        x = msg["x"]  # now filter on x.

        # Scalar fast-path
        if np.isscalar(x) or (isinstance(x, np.ndarray) and x.ndim == 0):
            xf = float(x)   # works for Python and NumPy scalars
            if not math.isfinite(xf):
                if self.strict:
                    raise ValueError(f"Non-finite scalar input: {xf}")
                msg["x_bp"] = xf  # pass-through unfiltered
                return msg
            y, self.zi = sosfilt(self.sos, [xf], zi=self.zi)
            msg["x_bp"] = float(y[-1])
            return msg

        # Array path
        x = np.asarray(x)
        if x.ndim != 1:
            raise ValueError(
                f"Only 1D arrays are supported; got shape {x.shape}")
        if not np.all(np.isfinite(x)):
            if self.strict:
                bad = np.where(~np.isfinite(x))[0][:5]
                raise ValueError(
                    f"Array contains non-finite values at indices {bad.tolist()} (showing up to 5).")
            # pass-through non-finite inputs unfiltered
            msg["x_bp"] = x
            return msg

        y, self.zi = sosfilt(self.sos, x, zi=self.zi)
        msg["x_bp"] = y
        return msg


# ─────────────────────────────────────────────────────────
# 3) Transform B — Welch PSD + peak pick (SciPy)
#    Adds: "f0_hz" (top peak), "peaks_hz" (list), and exposes "freqs"/"psd"
# ─────────────────────────────────────────────────────────


class welch_peak_detector:
    def __init__(
        self,
        *,
        window_samples: int = 1024,
        sample_rate: float = 200.0,
        key_in: str = "x_bp",          # detect on band-passed signal
        key_out_freq: str = "f0_hz",
        key_out_peaks: str = "peaks_hz",
        output_freq_key: str = "freqs",
        output_peak_detector_key: str = "psd",
        min_prominence: float = 0.02,
        name: str = "welch_peak_detector"
    ):
        self.buf = deque(maxlen=window_samples)
        self.window_samples = window_samples
        self.sample_rate = sample_rate
        self.key_in = key_in
        self.key_out_freq = key_out_freq
        self.key_out_peaks = key_out_peaks
        self.output_freq_key = output_freq_key
        self.output_peak_detector_key = output_peak_detector_key
        self.min_prominence = min_prominence
        self.name = name

    def run(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        x = float(msg[self.key_in])
        self.buf.append(x)
        if len(self.buf) == self.window_samples:
            arr = np.asarray(self.buf, dtype=np.float32)
            freqs, psd = welch(arr, fs=self.sample_rate,
                               nperseg=min(256, self.window_samples))
            # expose arrays for the snapshot sink
            msg[self.output_freq_key] = freqs.tolist()
            msg[self.output_peak_detector_key] = psd.tolist()
            # Call SciPy peak finder
            peaks, props = find_peaks(psd, prominence=self.min_prominence)
            if peaks.size > 0:
                order = np.argsort(psd[peaks])[::-1]
                main = peaks[order[0]]
                msg[self.key_out_freq] = float(freqs[main])
                msg[self.key_out_peaks] = [float(freqs[p])
                                           for p in peaks[order[:5]]]
            else:
                msg[self.key_out_freq] = None
                msg[self.key_out_peaks] = []
        else:
            msg[self.key_out_freq] = None
            msg[self.key_out_peaks] = []
            msg[self.output_freq_key] = None
            msg[self.output_peak_detector_key] = None
        return msg
# ─────────────────────────────────────────────────────────
# 4) Sink — save a spectrum snapshot (PNG) at the end
#    Call sink.finalize() after g.run_network()
# ─────────────────────────────────────────────────────────


class snapshot_spectrum_sink:
    def __init__(
            self,
            *,
            filename: str = "spectrum.png",
            key_freqs: str = "freqs",
            key_psd="psd",
            name: str = "snapshot_spectrum_sink"):
        self.filename = filename
        self.key_freqs = key_freqs
        self.key_psd = key_psd
        self.name = name
        self.latest = {"freqs": None, "psd": None}

    def run(self, msg: Dict[str, Any]):
        f = msg.get(self.key_freqs)
        Pxx = msg.get(self.key_psd)
        if f is not None and Pxx is not None:
            self.latest[self.key_freqs] = np.asarray(f)
            self.latest[self.key_psd] = np.asarray(Pxx)
        return msg

    def _finalize(self):
        f, Pxx = self.latest[self.key_freqs], self.latest[self.key_psd]
        if f is None or Pxx is None:
            print("[snapshot] No PSD captured; nothing to save.")
            return
        plt.figure()
        plt.semilogy(f, Pxx)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Power spectral density")
        plt.title("Welch PSD snapshot")
        plt.tight_layout()
        plt.savefig(self.filename, dpi=150)
        print(f"[snapshot] Saved {self.filename}")

# ─────────────────────────────────────────────────────────
# 5) (Optional) Console sink for quick feedback
# ─────────────────────────────────────────────────────────


def live_console_sink(msg: Dict[str, Any]):
    t = msg["t"]
    f0 = msg.get("f0_hz")
    if int(t * 10) == t * 10:  # ~10 Hz logging
        print(f"logging")
        print(f"t={t:5.2f}  f0={('None' if f0 is None else f'{f0:6.2f} Hz')}")
    return msg

# ─────────────────────────────────────────────────────────
# 6) Construct and run the network
# ─────────────────────────────────────────────────────────


# Make and name agents.
bp_obj = ButterBandpassFilter(name="bandpass")

before_filter_wpd = welch_peak_detector(key_in="x", name="wpd_before_bp")
after_filter_wpd = welch_peak_detector(key_in="x_bp", name="wpd_after_bp")


before_filter_snap = snapshot_spectrum_sink(
    filename="before_filter_spectrum.png", name="snap_before_bp")
after_filter_snap = snapshot_spectrum_sink(
    filename="after_filter_spectrum.png", name="snap_after_bp")

g = network([
    (src, before_filter_wpd.run),  # Transform 0: Welch + peaks
    (before_filter_wpd.run, before_filter_snap.run),  # optional output

    (src, bp_obj.run),           # Transform 1: band-pass
    (bp_obj.run, after_filter_wpd.run),           # Transform 2: Welch + peaks
    (after_filter_wpd.run, after_filter_snap.run),         # PNG snapshot sink
])

g.run_network()

before_filter_snap._finalize()
after_filter_snap._finalize()
