# dsl/examples/ch05_ds/anomaly_demo.py
from __future__ import annotations
import json
from typing import Dict, Optional
import time

from dsl import network
'''
You’ll see a brief summary every N messages and a `anomaly_stream.jsonl` file with the run.

---

## Tuning tips
- Want **more anomalies** without code changes? Try:
  - `EMAStd(alpha=0.03)` (slower volatility adapts → bigger z early in jumps)
  - `ZScoreBands(k=1.5)`
  - `FlagAnomaly(z_thresh=2.0)`
- Want **obvious, teachable spikes**? Add a few deterministic shocks in the source (e.g., +20 at `t_step=120`). Keeps the run reproducible and the screenshots compelling.

---

## What to look for in the console
Lines like:
t= 60 x=+101.234 ema=+101.120 z= +1.72 [+100.500,+101.740] anomaly=True (|z|>=1.5)

Interpretation:
- `z` measures how far away the current value is from the adaptive mean.
- Bands move with `ema`; a jump beyond `band_hi/lo` flags an anomaly.
- Early steps are “warmup” until the history is large enough for stats stabilize.

'''

# --- Source (deterministic random walk) --------------------------------------


class RandomWalkDeterministic:
    """
    Minimal, deterministic random-walk source.
    Yields exactly `steps` messages: {"t_step": int, "x": float}
    """

    def __init__(
        self,
        *,
        steps: int = 500,             # number of steps of random walk generated
        base: float = 100.0,          # starting value of random walk
        drift_per_step: float = 0.1,  # deterministic drift added to each step
        sigma: float = 5.0,           # stddev of Gaussian noise added to each step
        seed: int = 0,                # random number generator seed for reproducibility
        sleep_time_per_step: float = 0.01,
        name: Optional[str] = None,
    ) -> None:
        import random
        self.steps = int(steps)
        self.x = float(base)
        self.drift = float(drift_per_step)
        self.sigma = float(sigma)
        self.rng = random.Random(seed)  # uniform random number generator
        self.sleep_time_per_step = float(sleep_time_per_step)
        self._name = name or "src_random_walk"

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self):
        for i in range(self.steps):
            # add drift and Gaussian noise to walk position
            self.x += self.drift
            self.x += self.rng.gauss(0.0, self.sigma)
            yield {"t_step": i, "x": float(self.x)}
            time.sleep(self.sleep_time_per_step)  # simulate real-time stream

# --- Transform 1: EMA + exponentially-weighted std --------------------------


class EMAStd:
    """
    Receives a message which is a dict with key "x" (float) which is a random walk value.
    Outputs the same message with added keys: "ema" (float) and "std" (float) where
    ema is the exponential moving average of x, and std is the exponentially-weighted 
    standard deviation.

    """

    def __init__(
            self, *,
            # exponential smoothing factor (0 < alpha <= 1)
            alpha: float = 0.1,
            eps: float = 1e-8,          # small constant to avoid zero stddev
            std_min: float = 1e-6,      # minimum stddev to avoid zero division
            name: Optional[str] = None):
        assert 0.0 < alpha <= 1.0
        self.alpha = float(alpha)
        self.eps = float(eps)       # square of min stddev
        self._name = name or "ema_std"
        self._initialized = False
        self._ema = 0.0             # exponential moving average
        self._m = 0.0               # exponentially-weighted variance accumulator

    @property
    def __name__(self) -> str:
        return self._name

    def reset(self):  # optional
        self._initialized = False
        self._ema = 0.0
        self._m = 0.0

    def __call__(self, msg: Dict[str, float]) -> Dict[str, float]:
        import math
        x = float(msg["x"])
        a = self.alpha  # shorthand for exponential smoothing factor

        if not self._initialized:
            self._ema = x
            self._m = 0.0
            self._initialized = True
            std = math.sqrt(self.eps)  # initial stddev is a small constant.
        else:
            ema_prev = self._ema
            self._m = a * (x - ema_prev) ** 2 + (1.0 - a) * self._m
            self._ema = a * x + (1.0 - a) * ema_prev
            # add eps (small constant) for numerical stability
            std = math.sqrt(self._m + self.eps)

        msg["ema"] = float(self._ema)
        msg["std"] = float(std)
        return msg

# --- Transform 2: Z-score + bands -------------------------------------------


class ZScoreBands:
    def __init__(
            self, *,
            k: float = 2.0,
            std_floor: float = 1e-6,
            z_clip: Optional[float] = None,
            name: Optional[str] = None):
        assert k >= 0.0
        assert std_floor > 0.0
        # number of stddevs for bands. E.g., k=2 → bands at ±2 stddevs from ema.
        self.k = float(k)
        self.std_floor = float(std_floor)  # to avoid division by zero
        # z_clip: if set, clip the maximum number of stddevs from ema to z_clip
        self.z_clip = float(z_clip) if z_clip is not None else None
        self._name = name or f"zscore_bands_k{int(self.k)}"

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Dict[str, float]) -> Dict[str, float]:
        # msg is a dict with fields "x", "ema", "std" where "x" is the current value,
        # of a stream, "ema" is the exponential moving average, and "std" is the
        # exponentially-weighted standard deviation.
        # Compute z which is the number of standard deviations x is from ema.
        x = float(msg["x"])
        ema = float(msg["ema"])
        std = float(msg["std"])
        denom = max(self.std_floor, std)
        z = (x - ema) / denom
        msg["z"] = float(z)
        msg["band_hi"] = float(ema + self.k * std)
        msg["band_lo"] = float(ema - self.k * std)
        if self.z_clip is not None:
            msg["z_clipped"] = float(max(-self.z_clip, min(self.z_clip, z)))
        return msg

# --- Transform 3: Anomaly flagger -------------------------------------------


class FlagAnomaly:
    """
    Simple rule: anomaly if |z| >= z_thresh or x outside [band_lo, band_hi].
    Optional warm-up to avoid early false flags.
    """

    def __init__(
            self, *,
            z_thresh: float = 2.5,
            warmup_steps: int = 20,
            name: Optional[str] = None):
        self.z_thresh = float(z_thresh)
        self.warmup = int(warmup_steps)
        self._name = name or f"flag_anomaly_z{self.z_thresh:g}"

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Dict[str, float]) -> Dict[str, float]:
        # msg is a dict with fields "x", "ema", "std", "z", "band_lo", "band_hi"
        # msg is generated by ZScoreBands transform.
        i = int(msg.get("t_step", 0))
        if i < self.warmup:
            # Not enough history yet to make a reliable decision.
            msg["anomaly"] = False
            msg["reason"] = "warmup"
            return msg
        x = float(msg["x"])
        z = float(msg["z"])
        lo = float(msg["band_lo"])
        hi = float(msg["band_hi"])
        hit = abs(z) >= self.z_thresh or (x < lo) or (x > hi)
        msg["anomaly"] = bool(hit)
        if hit:
            msg["reason"] = f"|z|>={self.z_thresh:g}" if abs(
                z) >= self.z_thresh else "outside_bands"
        else:
            msg["reason"] = "in_band"
        return msg

# --- Sinks: console summary + JSONL recorder --------------------------------


def make_console_summary(every_n: int = 20):
    """
    Prints a compact summary every N messages (keeps output readable).
    """
    i = {"n": 0}

    def _sink(msg: Dict[str, float]):
        i["n"] += 1
        if i["n"] % every_n == 0:
            print(f"t={msg['t_step']:4d}  x={msg['x']:+8.3f}  ema={msg['ema']:+8.3f}  "
                  f"z={msg['z']:+6.2f}  [{msg['band_lo']:+8.3f},{msg['band_hi']:+8.3f}]  "
                  f"anomaly={msg['anomaly']} ({msg.get('reason', '')})")
        return msg
    _sink.__name__ = f"console_every_{every_n}"
    return _sink


class JSONLRecorder:
    """
    Append selected fields to a JSONL file (one record per message).
    """

    def __init__(self, path: str = "anomaly_stream.jsonl", *, name: Optional[str] = None):
        self.path = path
        self._fh = open(self.path, "w", encoding="utf-8")
        self._name = name or "jsonl_recorder"

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Dict[str, float]):
        rec = {k: msg[k] for k in (
            "t_step", "x", "ema", "std", "z", "band_lo", "band_hi", "anomaly", "reason") if k in msg}
        self._fh.write(json.dumps(rec) + "\n")
        return msg

    def finalize(self):
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass


# --- Make the graph (anomaly branch: fan-out to sinks) ----------------------
if __name__ == "__main__":
    # Source: deterministic, finite stream
    src = RandomWalkDeterministic(
        steps=600, base=100.0, drift_per_step=0.01, sigma=0.6, seed=42, name="src_random_walk"
    )

    # Transforms
    ema = EMAStd(alpha=0.1, name="ema_std")
    zb = ZScoreBands(k=2.0, std_floor=1e-6, z_clip=5.0, name="zscore_bands")
    flag = FlagAnomaly(z_thresh=1.5, warmup_steps=20, name="flag_anom")

    # Sinks
    console = make_console_summary(every_n=20)
    rec = JSONLRecorder(path="anomaly_stream.jsonl", name="jsonl_out")

    g = network([
        (src,  ema),
        (ema,  zb),
        (zb,   flag),
        # fan-out to two sinks
        (flag, console),
        (flag, rec),
    ])
    g.run_network()
    if hasattr(rec, "finalize"):
        rec.finalize()
    print("Wrote JSONL to anomaly_stream.jsonl")
