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


def sine_mixture_source(
    *,
    sample_rate: float = 200.0,
    duration_s: float = 8.0,
    tones: Iterable[Tuple[float, float]] = (
        (5.0, 1.0), (12.0, 0.6), (30.0, 0.3)),  # (freq_hz, amplitude)
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

    def run(self, x: ArrayLike) -> ArrayLike:
        """
        Apply the streaming band-pass.
        - Scalar in  -> scalar out
        - 1D array in -> 1D array out (and state advanced across the whole block)
        """
        # Scalar fast-path
        if isinstance(x, (float, int)):
            xf = float(x)
            if not math.isfinite(xf):
                if self.strict:
                    raise ValueError(f"Non-finite scalar input: {xf}")
                return x  # pass-through
            y, self.zi = sosfilt(self.sos, [xf], zi=self.zi)
            return float(y[-1])

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
            return x

        y, self.zi = sosfilt(self.sos, x, zi=self.zi)
        return y


# ─────────────────────────────────────────────────────────
# 3) Transform B — Welch PSD + peak pick (SciPy)
#    Adds: "f0_hz" (top peak), "peaks_hz" (list), and exposes "freqs"/"psd"
# ─────────────────────────────────────────────────────────


def welch_peak_detector(
    *,
    window_samples: int = 1024,
    sample_rate: float = 200.0,
    key_in: str = "x_bp",          # detect on band-passed signal
    key_out_freq: str = "f0_hz",
    key_out_peaks: str = "peaks_hz",
    min_prominence: float = 0.02
):
    buf = deque(maxlen=window_samples)

    def _transform(msg: Dict[str, Any]) -> Dict[str, Any]:
        x = float(msg[key_in])
        buf.append(x)
        if len(buf) == window_samples:
            arr = np.asarray(buf, dtype=np.float32)
            freqs, psd = welch(arr, fs=sample_rate,
                               nperseg=min(256, window_samples))
            # expose arrays for the snapshot sink
            msg["freqs"] = freqs.tolist()
            msg["psd"] = psd.tolist()
            peaks, props = find_peaks(psd, prominence=min_prominence)
            if peaks.size > 0:
                order = np.argsort(psd[peaks])[::-1]
                main = peaks[order[0]]
                msg[key_out_freq] = float(freqs[main])
                msg[key_out_peaks] = [float(freqs[p])
                                      for p in peaks[order[:5]]]
            else:
                msg[key_out_freq] = None
                msg[key_out_peaks] = []
        else:
            msg[key_out_freq] = None
            msg[key_out_peaks] = []
            msg["freqs"] = None
            msg["psd"] = None
        return msg
    return _transform

# ─────────────────────────────────────────────────────────
# 4) Sink — save a spectrum snapshot (PNG) at the end
#    Call sink.finalize() after g.run_network()
# ─────────────────────────────────────────────────────────


def snapshot_spectrum_sink(filename="spectrum.png", key_freqs="freqs", key_psd="psd"):
    latest = {"freqs": None, "psd": None}

    def _sink(msg: Dict[str, Any]):
        f = msg.get(key_freqs)
        Pxx = msg.get(key_psd)
        if f is not None and Pxx is not None:
            latest["freqs"] = np.asarray(f)
            latest["psd"] = np.asarray(Pxx)
        return msg

    def _finalize():
        f, Pxx = latest["freqs"], latest["psd"]
        if f is None or Pxx is None:
            print("[snapshot] No PSD captured; nothing to save.")
            return
        plt.figure()
        plt.semilogy(f, Pxx)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Power spectral density")
        plt.title("Welch PSD snapshot")
        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        print(f"[snapshot] Saved {filename}")
    _sink.finalize = _finalize
    return _sink

# ─────────────────────────────────────────────────────────
# 5) (Optional) Console sink for quick feedback
# ─────────────────────────────────────────────────────────


def live_console_sink(msg: Dict[str, Any]):
    t = msg["t"]
    f0 = msg.get("f0_hz")
    if int(t * 10) == t * 10:  # ~10 Hz logging
        print(f"t={t:5.2f}  f0={('None' if f0 is None else f'{f0:6.2f} Hz')}")
    return msg

# ─────────────────────────────────────────────────────────
# 6) Wire the graph — library functions as nodes
# ─────────────────────────────────────────────────────────


def src():
    # yield for generator function (callable)
    yield from sine_mixture_source(
        sample_rate=200.0, duration_s=8.0,
        tones=((5.0, 1.0), (12.0, 0.6), (30.0, 0.3)),
        noise_std=0.15,
    )


bp_obj = ButterBandpassFilter()


def bp(v):
    bp_obj.run(v)


det = welch_peak_detector(
    window_samples=1024, sample_rate=200.0, key_in="x_bp", min_prominence=0.02)

snap = snapshot_spectrum_sink("spectrum.png")

# g = network([
#     (src, bp),           # Transform 1: band-pass
#     (bp, det),           # Transform 2: Welch + peaks
#     (det, live_console_sink),  # optional console
#     (det, snap),         # PNG snapshot sink
# ])
g = network([
    (src, bp), (bp, live_console_sink),         # PNG snapshot sink
])
print(g.nodes)
g.run_network()
if hasattr(snap, "finalize"):
    snap.finalize()
