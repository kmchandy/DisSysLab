# 4.1 • Numeric Transformers — Synthetic Sine Mixture (Library Functions as Nodes)

This demo shows how **plain Python functions that call existing libraries** (NumPy/SciPy) can act as **nodes** in a DisSysLab network.  
We synthesize a **sum of noisy sine waves**, then run **two transforms**:
1) a **Butterworth band-pass filter** (SciPy), and  
2) a **spectrum/peak detector** (Welch PSD + peak pick, SciPy),  
and finally **save a spectrum snapshot (PNG)** for your README/slides.

---

## What you’ll do
- Generate a live stream: `x(t) = Σ A_k sin(2π f_k t) + noise`.  
- **Transform 1**: Isolate a target band with `scipy.signal.butter` + `sosfilt`.  
- **Transform 2**: Estimate the spectrum via `scipy.signal.welch` and find dominant **frequency peaks** via `scipy.signal.find_peaks`.  
- **Sink**: Save `spectrum.png` once enough data has accumulated (no live plotting required).

---

## Setup (once)
```bash
pip install numpy scipy matplotlib rich
```

---

## The Synthetic Sine Mixture Demo

```python
# modules.ch04_numeric.synthetic_sines_demo

import time
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
    tones: Iterable[Tuple[float, float]] = ((5.0, 1.0), (12.0, 0.6), (30.0, 0.3)),  # (freq_hz, amplitude)
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

def butter_bandpass_transform(
    *,
    low_hz: float = 4.0,
    high_hz: float = 14.0,
    order: int = 4,
    sample_rate: float = 200.0,
    key_in: str = "x",
    key_out: str = "x_bp",
):
    nyq = 0.5 * sample_rate
    low = low_hz / nyq
    high = high_hz / nyq
    sos = butter(order, [low, high], btype="bandpass", output="sos")
    def _transform(msg: Dict[str, Any]) -> Dict[str, Any]:
        x = float(msg[key_in])
        y = float(sosfilt(sos, [x])[-1])  # one-sample step
        msg[key_out] = y
        return msg
    return _transform

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
            freqs, psd = welch(arr, fs=sample_rate, nperseg=min(256, window_samples))
            # expose arrays for the snapshot sink
            msg["freqs"] = freqs.tolist()
            msg["psd"] = psd.tolist()
            peaks, props = find_peaks(psd, prominence=min_prominence)
            if peaks.size > 0:
                order = np.argsort(psd[peaks])[::-1]
                main = peaks[order[0]]
                msg[key_out_freq] = float(freqs[main])
                msg[key_out_peaks] = [float(freqs[p]) for p in peaks[order[:5]]]
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
        f = msg.get(key_freqs); Pxx = msg.get(key_psd)
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
        plt.xlabel("Frequency (Hz)"); plt.ylabel("Power spectral density")
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

src = sine_mixture_source(sample_rate=200.0, duration_s=8.0,
                          tones=((5.0, 1.0), (12.0, 0.6), (30.0, 0.3)),
                          noise_std=0.15)

bp  = butter_bandpass_transform(low_hz=4.0, high_hz=14.0, order=4, sample_rate=200.0, key_in="x", key_out="x_bp")
det = welch_peak_detector(window_samples=1024, sample_rate=200.0, key_in="x_bp", min_prominence=0.02)

snap = snapshot_spectrum_sink("spectrum.png")

g = network([
    (src, bp),           # Transform 1: band-pass
    (bp, det),           # Transform 2: Welch + peaks
    (det, live_console_sink),  # optional console
    (det, snap),         # PNG snapshot sink
])

g.run_network()
if hasattr(snap, "finalize"): snap.finalize()
```

---

## Run the demo
```bash
python3 -m modules.ch04_numeric.synthetic_sines_demo
```

You’ll see console lines (after the buffer fills) and a saved `spectrum.png`.

---

## Parameters you can modify

| Parameter | Where | Description |
|-----------|------|-------------|
| **sample_rate** | source/transforms | Keep consistent (e.g., `200.0`). |
| **tones** | source | List of `(freq_hz, amplitude)` pairs. |
| **noise_std** | source | Gaussian noise level. |
| **low_hz / high_hz / order** | band-pass | Butterworth passband and order. |
| **window_samples** | detector | Rolling buffer for Welch PSD. |
| **min_prominence** | detector | Peak detection sensitivity. |

---

## Troubleshooting
- **No PNG saved:** Ensure the detector emitted `freqs`/`psd` (wait until the buffer fills or lower `window_samples`).  
- **No peaks detected:** Lower `min_prominence`, increase tone amplitudes, or reduce noise.  
- **Peaks off by ~Δf:** Increase `window_samples` for finer spectral resolution.

---

## Next steps
- Swap the source for real audio (file or mic) and reuse the same two transforms.  
- Add a third node (e.g., `sklearn` anomaly detector) and log results to JSONL.
