# modules.ch04_numeric.anomaly_demo.py
from __future__ import annotations
import json
from typing import Dict, Optional
import time
import random

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
- Bands move with `ema`; a jump beyond `pred_high/lo` flags an anomaly.
- Early steps are “warmup” until the history is large enough for stats stabilize.

'''

# --- Source (deterministic random walk) --------------------------------------


class RandomWalkDeterministic:
    """
    Yields exactly `n_steps` messages: {"t_step": int, "x": float}
    where x is a random walk with drift (drift_per_step), Gaussian noise (standard deviation 
    of sigma), and occasional big jumps with probability prob_jump and std of jump_stdev.
    """

    def __init__(
        self,
        *,
        n_steps: int = 500,           # number of steps of random walk generated
        base: float = 100.0,          # starting value of random walk
        drift_per_step: float = 0.1,  # deterministic drift added to each step
        sigma: float = 5.0,           # stddev of Gaussian noise added to each step
        seed: int = 0,                # random number generator seed for reproducibility
        prob_jump: float = 0.1,       # prob of big jump at a step
        jump_stdev: float = 100.0,    # standard deviation of a big jump
        sleep_time_per_step: float = 0.01,
        name: Optional[str] = None,
    ) -> None:
        import random
        self.n_steps = int(n_steps)
        self.x = float(base)
        self.drift = float(drift_per_step)
        self.sigma = float(sigma)
        self.prob_jump = float(prob_jump)
        self.jump_stdev = float(jump_stdev)
        self.rng = random.Random(seed)  # uniform random number generator
        self.sleep_time_per_step = float(sleep_time_per_step)
        self._name = name or "src_random_walk"

    @property
    def __name__(self) -> str:
        return self._name

    def run(self):
        for i in range(self.n_steps):
            # add drift and Gaussian noise to walk position
            self.x += self.drift
            self.x += self.rng.gauss(0.0, self.sigma)
            # add a big jump with probability prob_jump
            if random.random() < self.prob_jump:
                self.x += self.rng.gauss(0.0, self.jump_stdev)
            yield {"t_step": i, "x": float(self.x)}
            time.sleep(self.sleep_time_per_step)  # simulate real-time stream


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
            k: float = 1.0,
            name: Optional[str] = None):
        assert 0.0 < alpha <= 1.0
        self.alpha = float(alpha)
        # square of min stddev. A small constant for numerical stability.
        self.eps = 1e-8
        # threshold multiplier for volatility spike detection
        self.k = float(k)
        self._name = name or "ema_std"
        self._initialized = False
        self._ema = 0.0             # exponential moving average
        self._m = 0.0               # exponentially-weighted variance accumulator

    @property
    def __name__(self) -> str:
        return self._name

    def run(self, msg: Dict[str, float]) -> Dict[str, float]:
        import math
        x = float(msg["x"])
        a = self.alpha  # shorthand for exponential smoothing factor

        if not self._initialized:
            self._ema = x
            self._m = 0.0
            self._initialized = True
            std = math.sqrt(self.eps)  # initial stddev is a small constant.
        else:
            # add eps (small constant) for numerical stability
            std = math.sqrt(self._m + self.eps)
            if (x < self._ema - self.k * std) or (x > self._ema + self.k * std):
                # Volatility spike detected; reset variance accumulator.
                msg["anomaly"] = True
            else:
                msg["anomaly"] = False
            msg["ema"] = float(self._ema)
            msg["std"] = float(std)
            msg["pred_low"] = float(self._ema - self.k * std)
            msg["pred_high"] = float(self._ema + self.k * std)
            ema_prev = self._ema
            # self._m is the updated exponentially-weighted variance accumulator.
            self._m = a * (x - ema_prev) ** 2 + (1.0 - a) * self._m
            # self._ema is the updated exponential moving average.
            self._ema = a * x + (1.0 - a) * ema_prev
        return msg

# --- Sinks: console summary + JSONL recorder --------------------------------


def make_console_summary(every_n: int = 1):
    """
    Prints a compact summary every N messages (keeps output readable).
    """
    i = {"n": 0}

    def _sink(msg: Dict[str, float]):
        i["n"] += 1
        if i["n"] % every_n == 0:
            print(f"t={msg['t_step']:4d}  x={msg['x']:+8.3f}  ema={msg['ema']:+8.3f} std={msg['std']:+6.3f}"
                  f"band = [{msg['pred_low']}, {msg['pred_high']}] anomaly={msg['anomaly']}"
                  )
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
            "t_step", "x", "ema", "std", "z", "pred_low", "pred_high", "anomaly") if k in msg}
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
        n_steps=600, base=100.0, drift_per_step=0.01, sigma=0.6, seed=42, name="src_random_walk"
    )
    f = src.run

    # Transforms
    ema = EMAStd(alpha=0.1, name="ema_std")
    # Sinks
    console = make_console_summary(every_n=20)
    rec = JSONLRecorder(path="anomaly_stream.jsonl", name="jsonl_out")

    g = network([
        (src.run,  ema.run),
        # fan-out to two sinks
        (ema.run, console),
        (ema.run, rec),
    ])
    g.run_network()
    if hasattr(rec, "finalize"):
        rec.finalize()
    print("Wrote JSONL to anomaly_stream.jsonl")
