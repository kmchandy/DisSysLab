#modules/ch04_numerics/README_1_numeric_transformers.md

# 4.1 • Numeric Transformers
This module gives examples of simple distributed systems in which agents are calls to numeric libraries such as those in NumPy and Scikit-Learn. Distributed systems allow you to create networks of agents of different types that communicate with each other and run forever.

This page gives you an example of an agent that detects anomalies in streams of data. This example computes statistics on sliding windows over data streams. The next module gives other algorithms for anomaly detection.

---
## What you’ll do


Run a tiny script that replays temperatures recorded for San Francisco, emits each row at ~4×/sec, computes statistics over sliding windows, and uses these statistics to predict future temperatures and identify anomalies in the temperature stream. The results are displayed on the console.



---

## Setup (once)
```bash
pip install rich
```
> _Note:_ This example assumes you have `open-meteo_clean.csv`, `ReplayCSV_In`, `rolling_stats_anom_forecast`, and a `temp_live_sink` available in your project paths as shown below.

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

Anomaly range factor is k_anom
Predicted range for the next value, x5 =  [ μ - k_anom * σ ,  μ + k_anom * σ ]

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
     +----------------------+
     |      xf              |
     | Compute sliding      |
     | windowstatistics     |
     | Predict anomaly band |
     | for next value       |
     +----------------------+
            |
            | Output anomaly
            |  
            |
            v
     +------------------+
     | temp_live_sink   |
     | print anomalies  |
     +------------------+
```

```python
# modules.ch04_numeric.simple_anomaly

from pathlib import Path
from dsl import network
from dsl.connectors.replay_csv_in import ReplayCSV_In
from .rolling_stats_anom_forecast import RollingStatsAnomForecast
from .temp_live_sink import temp_live_sink

# -------------------------------------------------------------------------
# Source: Generate historical daily max temperature from Open-Meteo
CSV_PATH = str(Path(__file__).resolve().parent / "open-meteo_clean.csv")


def transform_row(row):
    t = row.get("time")
    temp = row.get("temperature_2m_max (°F)")
    if not t or not temp:
        return None
    return {"date": t, "tmax_f": float(temp)}


replay = ReplayCSV_In(path=CSV_PATH, transform=transform_row, period_s=0.25)


# -------------------------------------------------------------------------
# Transform: Rolling statistics for anomaly detection and forecasting
xf = RollingStatsAnomForecast(
    window=20,       # window size
    k_anom=2.0,      # anomaly threshold 
    key_in="tmax_f",
    date_key="date",
    prefix="w20"
)

# -------------------------------------------------------------------------
# Sink: Use temp_live_sink to display results

# -------------------------------------------------------------------------
# Network: Connect functions

g = network([(replay, xf), (xf, temp_live_sink)])
g.run_network()

```

---

## Run the demo
```bash
python3 -m modules.ch04_numeric.simple_anomaly
```

You’ll see a live stream of key–value output with rolling statistics, anomaly flags, and prediction band fields.

## Explanation
```replay``` is an object with a method ```__call__```. The object gets weather data from the specified file and outputs a message stream where each message is a dict containing the date and maximum temperature. You can define the edge of the graph from ```replay``` to ```xf``` as ```(replay, xf)``` or ```(replay.__call__, xf)``` or ```(replay.run, xf)```. 

The message stream generated by ```replay``` is received by object ```xf``` which computes anomalies using a simple algorithm that uses basic statistics on sliding windows to predict the next value in the stream. The stream output by ```xf``` is displayed on the console by ```temp_live_sink```.

---

## Parameters you can modify

| Parameter | Type | Description |
|-----------|------|-------------|
| **path** | str | Path to the CSV file to replay. |
| **transform** | callable \| None | Maps a CSV row (dict) → cleaned dict (return `None` to skip a row). |
| **period_s** | float | Seconds between emitted rows (e.g., `0.25` ≈ 4 msgs/sec). |
| **window** | int | Rolling window length for stats (e.g., `20`). |
| **k_anom** | float | Anomaly threshold multiplier (e.g., `2.0`). |
| **k_pred** | float | Prediction band half-width multiplier (e.g., `0.5`). |
| **key_in** | str | Input numeric field name (e.g., `"tmax_f"`). |
| **date_key** | str | Timestamp/date field name (e.g., `"date"`). |
| **prefix** | str | Prefix for derived fields (e.g., `"w20"` → `w20_mean`, `w20_lo`, `w20_hi`, etc.). |

> _Tip:_ Customize `transform_row` to rename columns and cast types up front so downstream transformers can operate on a predictable schema.

---

## Troubleshooting

- **No output:** Ensure `CSV_PATH` points to an existing file and your `transform_row` does not return `None` for all rows.  
- **Type errors:** Cast numbers in `transform_row` (e.g., `float(temp)`) and verify column names match the CSV header.  
- **Too fast/slow:** Adjust `period_s` to control replay speed.  
- **Missing fields in sink:** Confirm your sink expects the fields your pipeline emits (e.g., `date`, `tmax_f`, `w20_*`).  

---

## Try
- Replace `temp_live_sink` with a **JSONL/CSV recorder** to log outputs (Module 2.5 / Module 5).  
- Chain a **keyword/threshold filter** before the sink to highlight anomalies.  
- Plot the replayed series and prediction bands in a notebook or dashboard.

## 👉 Next
[Anomaly detection](./README_2_anomaly.md)