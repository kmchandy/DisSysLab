from __future__ import annotations
from typing import Dict, Optional, Union

Number = Union[int, float]


class SlidingWindowAnomalyExponential:
    """
    Receives msg: dict containing x_key (float-like).
    Returns the same msg with added keys:
      - ema_key: float
      - std_key: float
      - pred_low_key: float
      - pred_high_key: float
      - anomaly_key: bool
    """

    def __init__(
        self,
        *,
        alpha: float = 0.1,
        k: float = 1.0,
        x_key: str = "x",
        ema_key: str = "ema",
        std_key: str = "std",
        pred_low_key: str = "pred_low",
        pred_high_key: str = "pred_high",
        anomaly_key: str = "anomaly",
        name: Optional[str] = None,
    ) -> None:
        assert 0.0 < alpha <= 1.0
        self.alpha = float(alpha)
        self.k = float(k)
        self.eps = 1e-8  # numerical stability

        self.x_key = x_key
        self.ema_key = ema_key
        self.std_key = std_key
        self.pred_low_key = pred_low_key
        self.pred_high_key = pred_high_key
        self.anomaly_key = anomaly_key

        self._name = name or "ema_std"
        self._initialized = False
        self._ema = 0.0
        self._m = 0.0  # exponentially-weighted variance accumulator

    @property
    def __name__(self) -> str:
        return self._name

    def run(self, msg: Dict[str, Number]) -> Dict[str, object]:
        import math

        x = float(msg[self.x_key])
        a = self.alpha

        if not self._initialized:
            # Initialize state from first observation.
            self._ema = x
            self._m = 0.0
            self._initialized = True

            std = math.sqrt(self.eps)
            anomaly = False
            ema_used = self._ema  # for output on first msg
        else:
            # Use previous ema/std to score current x.
            std = math.sqrt(self._m + self.eps)
            ema_used = self._ema
            anomaly = (x < ema_used - self.k * std) or (x >
                                                        ema_used + self.k * std)

            # Update state after scoring.
            self._m = a * (x - ema_used) ** 2 + (1.0 - a) * self._m
            self._ema = a * x + (1.0 - a) * ema_used

        # Always emit fields so downstream sees consistent keys.
        msg[self.anomaly_key] = bool(anomaly)
        msg[self.ema_key] = float(ema_used)
        msg[self.std_key] = float(std)
        msg[self.pred_low_key] = float(ema_used - self.k * std)
        msg[self.pred_high_key] = float(ema_used + self.k * std)

        return msg
