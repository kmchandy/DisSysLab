# modules.ch04_numeric.filters

import time
import math
from collections import deque, Counter
from typing import Iterable, Tuple, Dict, Any

import numpy as np
from scipy.signal import butter, sosfilt, welch, find_peaks
import matplotlib.pyplot as plt

from dsl import network

# ─────────────────────────────────────────────────────────
# 1) Source — noisy sum of sines, yields {"t": seconds, "x": value}
# ─────────────────────────────────────────────────────────


def sine_mixture_source(
    *,
    sample_rate: float = 200.0,
    duration_s: float = 8.0,
    tones: Iterable[Tuple[float, float]] = (
        (5.0, 1.0), (12.0, 0.6), (30.0, 0.3)),
    noise_std: float = 0.15,
):
    n_total = int(duration_s * sample_rate)
    dt = 1.0 / sample_rate
    t = 0.0
    tones = list(tones)
    for _ in range(n_total):
        x = sum(a * math.sin(2 * math.pi * f * t) for f, a in tones)
        x += np.random.normal(scale=noise_std)
        yield {"t": t, "x": float(x)}
        t += dt
        time.sleep(dt)  # real-time pacing

# ─────────────────────────────────────────────────────────
# 2) Transform — Butterworth band-pass (SciPy), adds "x_bp"
# ─────────────────────────────────────────────────────────


class butter_bandpass_transform():
    def __init__(self,
                 *,
                 name="butter_bandpass",
                 low_hz: float = 4.0,
                 high_hz: float = 14.0,
                 order: int = 4,
                 sample_rate: float = 200.0,
                 key_in: str = "x",
                 key_out: str = "x_bp",
                 ):
        self.name = name
        self.key_in = key_in
        self.key_out = key_out
        self.nyq = 0.5 * sample_rate
        self.low = low_hz / self.nyq
        self.high = high_hz / self.nyq
        self.sos = butter(order, [self.low, self.high],
                          btype="bandpass", output="sos")

    def run(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        x = float(msg[self.key_in])
        y = float(sosfilt(self.sos, [x])[-1])   # streaming one-sample step
        msg[self.key_out] = y
        return msg


# ─────────────────────────────────────────────────────────────────────
# 3) Transform — Welch PSD + Top-K peaks (on any input key), exposes arrays
#     Adds:
#       - "peaks_hz": list of top-K peak freqs (desc power)
#       - "f0_hz": top peak
#       - "freqs": PSD frequency grid
#       - "psd": PSD values
# ─────────────────────────────────────────────────────────────────────


def welch_peak_detector(
    *,
    window_samples: int = 1024,
    sample_rate: float = 200.0,
    key_in: str = "x",
    top_k: int = 3,
    min_prominence: float = 0.02,
    key_out_peaks: str = "peaks_hz",
    key_out_f0: str = "f0_hz",
):
    buf = deque(maxlen=window_samples)

    def welch_peak(msg: Dict[str, Any]) -> Dict[str, Any]:
        x = float(msg[key_in])
        buf.append(x)

        # Default outputs
        msg[key_out_peaks] = []
        msg[key_out_f0] = None
        msg["freqs"] = None
        msg["psd"] = None

        if len(buf) == window_samples:
            arr = np.asarray(buf, dtype=np.float32)
            # Welch: nperseg kept small for responsiveness; adjust as needed
            freqs, psd = welch(arr, fs=sample_rate,
                               nperseg=min(256, window_samples))

            # Expose arrays (for optional snapshot)
            msg["freqs"] = freqs.tolist()
            msg["psd"] = psd.tolist()

            peaks, props = find_peaks(psd, prominence=min_prominence)
            if peaks.size > 0:
                order = np.argsort(psd[peaks])[::-1]
                top = peaks[order[:top_k]]
                peaks_hz = [float(freqs[p]) for p in top]
                msg[key_out_peaks] = peaks_hz
                msg[key_out_f0] = peaks_hz[0]

        return msg

    return welch_peak

# ─────────────────────────────────────────────────────────
# 4) Optional sink — Save a spectrum snapshot (PNG) at the end
# ─────────────────────────────────────────────────────────


def snapshot_spectrum_sink(filename="spectrum.png", key_freqs="freqs", key_psd="psd"):
    latest = {"freqs": None, "psd": None}

    def spectrum_sink(msg: Dict[str, Any]):
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
        plt.title("Welch PSD snapshot (RAW)")
        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        print(f"[snapshot] Saved {filename}")

    spectrum_sink.finalize = _finalize
    return spectrum_sink

# ─────────────────────────────────────────────────────────
# 5) Two labeled console sinks (one per branch) — Option A
# ─────────────────────────────────────────────────────────


def make_live_console_sink(label: str, every_n: int = 20):
    i = 0

    def live_console(msg: Dict[str, Any]):
        nonlocal i
        i += 1
        if i % every_n == 0:
            t = msg["t"]
            peaks = msg.get("peaks_hz", [])
            f0 = msg.get("f0_hz")
            peaks_str = "[" + ", ".join(f"{p:.2f}" for p in peaks) + "]"
            f0_str = "None" if f0 is None else f"{f0:.2f} Hz"
            print(f"[{label:<4}] t={t:5.2f}  f0={f0_str:>8}  peaks={peaks_str}")
        return msg
    return live_console


def make_summary_sink(label: str, interval_s: float = 2.0, round_to: float = 0.25, show_top: int = 3):
    """
    Aggregates peaks over time and prints periodic summaries.
      - interval_s: print cadence (seconds)
      - round_to:   round peak Hz to nearest bin (e.g., 0.25 Hz) for counting
      - show_top:   how many most-common peaks to display per print
    """
    last_print = time.monotonic()
    counts = Counter()
    last_f0 = None
    msgs = 0

    def _round_freqs(peaks):
        if round_to <= 0:
            return [float(p) for p in peaks]
        q = round_to
        return [round(float(p) / q) * q for p in peaks]

    def summary(msg: dict):
        nonlocal last_print, last_f0, msgs
        msgs += 1
        peaks = msg.get("peaks_hz") or []
        f0 = msg.get("f0_hz")
        t = msg.get("t", 0.0)

        # Update aggregates
        if peaks:
            counts.update(_round_freqs(peaks))
        last_f0 = f0 if f0 is not None else last_f0

        # Periodic summary
        now = time.monotonic()
        if now - last_print >= interval_s:
            last_print = now
            # Build top list
            top = counts.most_common(show_top)
            top_str = ", ".join(f"{f:.2f}Hz×{c}" for f,
                                c in top) if top else "—"
            f0_str = "None" if last_f0 is None else f"{last_f0:.2f} Hz"
            print(
                f"[{label:<4}] t={t:5.2f}  f0(latest)={f0_str:>8}  top{show_top}={top_str}  msgs={msgs}")
        return msg

    def _finalize():
        top = counts.most_common(show_top)
        top_str = ", ".join(f"{f:.2f}Hz×{c}" for f, c in top) if top else "—"
        f0_str = "None" if last_f0 is None else f"{last_f0:.2f} Hz"
        total = sum(counts.values())
        print(f"[{label:<4}] FINAL  f0(last)={f0_str:>8}  unique_peaks={len(counts)}  total_peaks={total}  top{show_top}={top_str}")

    summary.finalize = _finalize
    return summary


# ─────────────────────────────────────────────────────────
# 6) Wire the graph — Option B fan-out (RAW vs BAND) + labeled sinks
# ─────────────────────────────────────────────────────────

# Wrap source so Graph receives a callable (not a generator object)


def src():
    yield from sine_mixture_source(
        sample_rate=200.0, duration_s=8.0,
        tones=((5.0, 1.0), (12.0, 0.6), (30.0, 0.3)),
        noise_std=0.15,
    )


butter_bandpass = butter_bandpass_transform(
    low_hz=4.0, high_hz=14.0, order=4, sample_rate=200.0, key_in="x", key_out="x_bp")
det_all = welch_peak_detector(
    window_samples=1024, sample_rate=200.0, key_in="x",    top_k=3, min_prominence=0.02)
det_band = welch_peak_detector(
    window_samples=1024, sample_rate=200.0, key_in="x_bp", top_k=3, min_prominence=0.02)

# console_raw = make_live_console_sink(label="RAW",  every_n=20)
# console_band = make_live_console_sink(label="BAND", every_n=20)

console_raw = make_summary_sink(
    label="RAW",  interval_s=2.0, round_to=0.25, show_top=3)
console_band = make_summary_sink(
    label="BAND", interval_s=2.0, round_to=0.25, show_top=3)

snap = snapshot_spectrum_sink("spectrum.png")  # optional, from RAW detector

g = network([
    # Fan-out
    (src, butter_bandpass),            # path 1: band-pass
    (src, det_all),       # path 2: raw → peaks

    # Continue band path
    (butter_bandpass,  det_band),

    # Labeled sinks (Option A: one per branch)
    (det_all,  console_raw),
    (det_band, console_band),

    # Optional snapshot from RAW path
    (det_all,  snap),
])

g.run_network()


# Print final summaries
for sink in (console_raw, console_band):
    if hasattr(sink, "finalize"):
        sink.finalize()

# Save spectrum.png
if hasattr(snap, "finalize"):
    snap.finalize()
