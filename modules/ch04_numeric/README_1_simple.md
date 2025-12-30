#modules/ch04_numerics/README_1_numeric_transformers.md

# 4.1 • Numeric Transformers
This module gives examples of simple distributed systems in which agents call numeric libraries such as NumPy and Scikit-Learn. 

This page gives you an example of an agent that detects anomalies in streams of data by computing statistics on sliding windows over data streams. The next page gives an example of anomaly detection using exponential smoothing.

---
## What you’ll do


Create a network with three agents: 

1. A source agent that replays temperatures recorded for San Francisco and emits each row at ~4×/sec.
2. An agent that computes statistics over sliding windows; uses these statistics to predict upper and lower ranges of temperature for the next day; and identifies anomalies in the temperature stream if the actual temperature lies outside the predicted range. 
3. An agent that displays results.



---

## Setup (once)
```bash
pip install rich
```
> _Note:_ This example assumes you have `open-meteo_clean.csv`, `ReplayCSV_In`, and `temp_live_sink` available in your project paths as shown below.

---

## Sliding window
``` python
Data Stream →      x0   x1   x2   x3   x4   x5   x6 .....

Window of size 4 at t = 4:
                         ┌──────────────────────────┐
                         |   x1   x2   x3   x4      |
                         └──────────────────────────┘

Window at t+1: x1 drops out and x5 is added
                               ┌──────────────────────────┐
                               |   x2   x3   x4   x5      |
                               └──────────────────────────┘

```

## Predicting range of next value
```markup
                   ┌──────────────────────────┐
Window at t = 4    |   x1   x2   x3   x4      |
                   └──────────────────────────┘

Compute mean and standard deviation of this window
μ = mean(x1, x2, x3, x4)
σ = std(x1, x2, x3, x4)

std_limit: max number of standard deviations from the mean for no anomaly

Predicted range for the next value, x5 =  [ μ - std_limit * σ ,  μ + std_limit * σ ]

Anomaly if x5 is outside this range.
```

## Distributed System Network of Agents
```markup
     +------------------+
     |    replay        |
     | generate stream  |
     | of numbers:      |
     +------------------+
            |
            | messages: x0, x1, x2, x3, ...
            |
            v
     +-------------------------+
     | agent_sliding_window.run|
     | Compute sliding         |
     | windowstatistics        |
     | Predict anomaly band    |
     | for next value          |
     +-------------------------+
            |
            | Output anomaly
            | Enriches message received by adding predicted range
            | and whether anomaly occurred
            v
     +------------------+
     | temp_live_sink   |
     | print anomalies  |
     +------------------+
```
## Simple Anomaly: Network of Three Agents
```python
# modules.ch04_numeric.simple_anomaly
from __future__ import annotations
from collections import deque
import math
from typing import Optional, Dict, Any
from pathlib import Path
from dsl import network
from dsl.connectors.replay_csv_in import ReplayCSV_In
from .temp_live_sink import temp_live_sink

# -------------------------------------------------------------------------
# Receive data and output anomaly using sliding window statistics


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
        '''
        msg: input message containing data value at key self.key_data
        Returns msg enriched with: pred_low, pred_high, fits (if enough data available)
        '''
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


# -------------------------------------------------------------------------
# Source: Replay historical daily max temperature from Open-Meteo
CSV_PATH = str(Path(__file__).resolve().parent / "open-meteo_clean.csv")


def from_CSV_row_to_dict(row):
    t = row.get("time")
    temp = row.get("temperature_2m_max (°F)")
    if not t or not temp:
        return None
    return {"date": t, "tmax_f": float(temp)}


replay = ReplayCSV_In(
    path=CSV_PATH, transform=from_CSV_row_to_dict, period_s=0.25)


# -------------------------------------------------------------------------
# Agent: Sliding window statistics for anomaly detection and forecasting

agent_sliding_window = SlidingWindowAnomaly(
    window_size=20,
    std_limit=2.0,      # anomaly threshold
    key_data="tmax_f",
)

# -------------------------------------------------------------------------
# Create and run network
g = network([(replay.run, agent_sliding_window.run),
            (agent_sliding_window.run, temp_live_sink)])
g.run_network()

```

---

## Run the demo
```bash
python -m modules.ch04_numeric.simple_anomaly
```

You’ll see a live stream of key–value output with rolling statistics, anomaly flags, and prediction band fields.

---
## Troubleshooting

- **No output:** Ensure `CSV_PATH` points to an existing file and your `transform_row` does not return `None` for all rows.  
- **Type errors:** Cast numbers in `transform_row` (e.g., `float(temp)`) and verify column names match the CSV header.  
- **Too fast/slow:** Adjust `period_s` to control replay speed.  
- **Missing fields in sink:** Confirm your sink expects the fields your pipeline emits (e.g., `date`, `tmax_f`, `w20_*`).  

---

## 👉 Next
[Anomaly detection](./README_2_anomaly.md)