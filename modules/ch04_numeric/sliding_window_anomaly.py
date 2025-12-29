# modules/ch04_numeric/sliding_window_anomaly.py
from __future__ import annotations
from collections import deque
import math
from typing import Optional, Dict, Any


class SlidingWindowAnomaly:
    def __init__(self, window_size: int, std_limit: float, key_data: str) -> None:
        self.window_size = window_size
        # std: standard deviation
        # detect anomaly if actual value is out outside mean ± std_limit·std
        self.std_limit = std_limit
        self.key_data = key_data        # key in the input dict for the data value
        self.window = deque()           # sliding window of data values
        self.sum = 0.0      # sum of values in the window
        self.sum_sq = 0.0   # sum of squares of values in the window
        # boolean which is True if new output is produced for the current input data
        self.new_output = False
        self.pred_low: Optional[float] = None   # predicted low for next value
        self.pred_high: Optional[float] = None  # predicted high for next value

    def run(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        x = msg.get(self.key_data)          # x is data in the message

        # Coerce to float if x is a string
        if isinstance(x, str):
            try:
                x = float(x)
            except Exception:
                x = None

        fits: Optional[bool] = None
        self.new_output = (self.pred_low is not None and x is not None and
                           self.pred_high is not None)
        if self.new_output:
            # output msg is input msg enriched with pred_low, pred_high and fits
            fits = (self.pred_low <= x <= self.pred_high)
            msg["pred_low"] = self.pred_low
            msg["pred_high"] = self.pred_high
            msg["fits"] = fits

        assert x is not None
        # add x to the window and update window stats
        self.window.append(x)
        self.sum += x           # update sum of window
        self.sum_sq += x * x    # update sum of squares of window
        if len(self.window) > self.window_size:
            # remove oldest value from window and update stats
            old = self.window.popleft()
            self.sum -= old
            self.sum_sq -= old * old

        n = len(self.window)
        assert n > 0
        mean = self.sum / n
        var = (self.sum_sq / n) - (mean * mean)
        std = math.sqrt(var)

        # Compute anomaly limits for next data value
        self.pred_low = (mean - self.std_limit * std)
        self.pred_high = (mean + self.std_limit * std)

        return msg
