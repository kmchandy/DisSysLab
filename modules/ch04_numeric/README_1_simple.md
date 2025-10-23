#modules/ch04_numerics/README_1_numeric_transformers.md

# 4.1 • Numeric Transformers
This module has examples in which nodes of the dsl graph are calls to numeric libraries such as those in NumPy and Scikit-Learn. The previous module showed examples in which the nodes of the dsl graph were calls to LLM functions. Of course, a graph can have nodes that use LLMs as well as numeric libraries.

This page gives you an example of a simple numeric transform using sliding windows. This is a simplistic example of detecting anomalies in streams. The next module gives a more realistic example of anomaly detection. 


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

## A numeric transformer

```python
# modules.ch04_numeric.simple_anomaly

from pathlib import Path
from dsl import network
from dsl.connectors.replay_csv_in import ReplayCSV_In
from .rolling_stats_anom_forecast import rolling_stats_anom_forecast
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
xf = rolling_stats_anom_forecast(
    window=20,
    k_anom=2.0,      # anomaly threshold
    k_pred=0.5,      # prediction band width
    key_in="tmax_f",
    date_key="date",
    prefix="w20"
)

# -------------------------------------------------------------------------
# Sink: Use temp_live_sink to display results

# -------------------------------------------------------------------------
# Network: Connect functions

g = network([(replay.run, xf), (xf, temp_live_sink)])
g.run_network()
```

---

## Run the demo
```bash
python3 -m modules.ch04_numeric.simple_anomaly
```

You’ll see a live stream of key–value output with rolling statistics, anomaly flags, and prediction band fields.

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