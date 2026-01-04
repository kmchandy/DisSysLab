from __future__ import annotations
from typing import Dict, Optional


class SlidingWindowAnomalyExponential:
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
