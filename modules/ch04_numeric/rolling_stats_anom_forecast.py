# lessons/ch02_sources/rolling_stats_anom_forecast.py
from __future__ import annotations
from collections import deque
import math
from typing import Callable, Optional, Dict, Any


class RollingStatsAnomForecast:
    """
    Adds rolling stats, anomaly flag, and one-step-ahead prediction band.
    Also reports whether the *current* value fit in the band predicted at t-1.

    On each message (a dict), this transform appends:
      {prefix}_n, {prefix}_mean, {prefix}_std,
      anomaly (bool),
      pred_low, pred_high           # band for the NEXT value (t+1), built at t
      fits (bool|None)              # did current x fall in the band predicted at t-1?
      cover_total, cover_hits, cover_rate
    """

    def __init__(
        self,
        *,
        window: int = 20,
        k_anom: float = 2.0,           # anomaly threshold (|x-μ| > k_anom·σ)
        # prediction band width for NEXT value (μ ± k_pred·σ)
        k_pred: float = 0.5,
        key_in: str = "tmax_f",
        date_key: str = "date",
        time_key: str = "time",
        prefix: str = "w",
        printer: Callable[[str], None] = print,
        debug: bool = False,
        name: Optional[str] = None,
    ) -> None:
        self.window = int(window)
        self.k_anom = float(k_anom)
        self.k_pred = float(k_pred)
        self.key_in = key_in
        self.date_key = date_key
        self.time_key = time_key
        self.prefix = prefix
        self.printer = printer
        self.debug = debug
        self._name = name or f"rolling_stats_{prefix}"

        # rolling window state
        self.q = deque()
        self.s = 0.0     # sum(x)
        self.ss = 0.0    # sum(x^2)

        # last-step prediction band (for fit/miss on current x)
        self.prev_pred_low: Optional[float] = None
        self.prev_pred_high: Optional[float] = None
        self.prev_pred_made_for: Optional[str] = None

        # coverage stats
        self.cover_total = 0
        self.cover_hits = 0

    @property
    def __name__(self) -> str:
        return self._name

    def reset(self) -> None:
        self.q.clear()
        self.s = 0.0
        self.ss = 0.0
        self.prev_pred_low = None
        self.prev_pred_high = None
        self.prev_pred_made_for = None
        self.cover_total = 0
        self.cover_hits = 0

    def __call__(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        x = msg.get(self.key_in)
        d = msg.get(self.date_key, "-")
        t = msg.get(self.time_key, "-")

        # Coerce to float if string
        if isinstance(x, str):
            try:
                x = float(x)
            except Exception:
                x = None

        # 1) Verify previous prediction against current x (fit/miss)
        fits: Optional[bool] = None
        if self.prev_pred_low is not None and x is not None:
            # type: ignore[operator]
            fits = (self.prev_pred_low <= x <= self.prev_pred_high)
            self.cover_total += 1
            if fits:
                self.cover_hits += 1
            elif self.debug:
                self.printer(
                    f"[miss] {d}: x={x:.3f} ∉ "
                    f"[{self.prev_pred_low:.3f}, {self.prev_pred_high:.3f}] "
                    f"(pred @ {self.prev_pred_made_for})"
                )

        # 2) Update rolling stats with current x
        if x is not None:
            self.q.append(x)
            self.s += x
            self.ss += x * x
            if len(self.q) > self.window:
                old = self.q.popleft()
                self.s -= old
                self.ss -= old * old

        n = len(self.q)
        mean = (self.s / n) if n > 0 else None
        var = max(self.ss / n - (mean *
                  mean if mean is not None else 0.0), 0.0) if n > 0 else None
        std = math.sqrt(var) if var is not None else None

        out = dict(msg)
        out[f"{self.prefix}_n"] = n
        out[f"{self.prefix}_mean"] = mean
        out[f"{self.prefix}_std"] = std

        # 3) Anomaly test on current x using k_anom
        anomalous = (std is not None and std > 0 and x is not None and n >= 2
                     # type: ignore[operator]
                     and abs(x - mean) > self.k_anom * std)
        out["anomaly"] = anomalous
        if anomalous:
            self.printer(
                f"Anomaly. {d}, {t}, mean={mean:.3f}, std={std:.3f}, x={x:.3f}"
            )

        # 4) Build prediction band for NEXT value using k_pred
        if std is not None and mean is not None and n >= 2:
            pred_low = mean - self.k_pred * std
            pred_high = mean + self.k_pred * std
            out["pred_low"] = pred_low
            out["pred_high"] = pred_high
            self.prev_pred_low = pred_low
            self.prev_pred_high = pred_high
            self.prev_pred_made_for = d
        else:
            out["pred_low"] = None
            out["pred_high"] = None
            self.prev_pred_low = None
            self.prev_pred_high = None
            self.prev_pred_made_for = None

        out["fits"] = fits
        out["cover_total"] = self.cover_total
        out["cover_hits"] = self.cover_hits
        out["cover_rate"] = (
            self.cover_hits / self.cover_total) if self.cover_total else None

        if self.debug:
            self.printer(
                f"[dbg] {d}: n={n} μ={mean} σ={std} "
                f"next=[{out['pred_low']},{out['pred_high']}] fits={fits} "
                f"cov={self.cover_hits}/{self.cover_total}"
            )
        return out
