# 4.2 • Transform - Numerics detect Anomalies

This page shows how to **replay rows from a CSV file as a live stream** at a chosen pace, optionally applying a transform and a rolling stats/anomaly/forecast function.  
Connectors are described in module 7.

---

## What you’ll do
Run a tiny script that replays a cleaned Open-Meteo CSV, emits each row at ~4×/sec, computes **rolling stats + anomaly flags + prediction bands**, and displays the results in a live console.

---

## Setup (once)
```bash
pip install rich
```
> _Note:_ This example assumes you have `open-meteo_clean.csv`, `ReplayCSV_In`, `rolling_stats_anom_forecast`, and a `temp_live_sink` available in your project paths as shown below.

---

## The CSV → Replay Demo

```python
# modules.ch04_numeric.simple_anomaly

from pathlib import Path
from dsl import network
from dsl.connectors.replay_csv_in import ReplayCSV_In
from lessons.ch02_sources.rolling_stats_anom_forecast import rolling_stats_anom_forecast
from lessons.ch02_sources.temp_live_sink import temp_live_sink

CSV_PATH = str(Path(__file__).resolve().parent / "open-meteo_clean.csv")

def transform_row(row):
    t = row.get("time")
    temp = row.get("temperature_2m_max (°F)")
    if not t or not temp:
        return None
    return {"date": t, "tmax_f": float(temp)}

replay = ReplayCSV_In(path=CSV_PATH, transform=transform_row, period_s=0.25)

xf = rolling_stats_anom_forecast(
    window=20,
    k_anom=2.0,      # anomaly threshold
    k_pred=0.5,      # prediction band width
    key_in="tmax_f",
    date_key="date",
    prefix="w20"
)

def temperature_source():
    for msg in replay.run():
        if msg is None:
            continue
        yield xf(msg)

g = network([(temperature_source, temp_live_sink)])
g.run_network()
```

---

## Run the demo
```bash
python3 -m modules.ch02_sources.feed_replay
```

You’ll see a live stream of key–value output with rolling statistics, anomaly flags, and prediction band fields (names prefixed with `w20_…` by default).

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

## Next steps
- Replace `temp_live_sink` with a **JSONL/CSV recorder** to log outputs (Module 2.5 / Module 5).  
- Chain a **keyword/threshold filter** before the sink to highlight anomalies.  
- Plot the replayed series and prediction bands in a notebook or dashboard.
