# 2.6 • Source - Replay Archived Data Streams

This page shows how to **replay rows from a CSV file as a live stream** at a specified pace. 
Connectors are described in module 7.

---

## What you’ll do
Run a tiny script that replays temperature data for 2024. This data is in ```open-meteo_clean.csv``` which is obtained by extracting the maximum daily temperature from ```open-meteo-37.79N122.41W18m.csv```.

---

## Setup (once)
```bash
pip install rich
```
> _Note:_ This example assumes you have `open-meteo_clean.csv` and `ReplayCSV_In`. 

---

## The CSV → Replay Demo

```python
# modules.ch02_sources.feed_numeric_replay

from pathlib import Path
from dsl import network
from dsl.connectors.replay_csv_in import ReplayCSV_In

CSV_PATH = str(Path(__file__).resolve().parent / "open-meteo_clean.csv")


def transform_row(row):
    t = row.get("time")
    temp = row.get("temperature_2m_max (°F)")
    if not t or not temp:
        return None
    return {"date": t, "max_temp": float(temp)}


replay = ReplayCSV_In(path=CSV_PATH, transform=transform_row, period_s=0.25)


def print_sink(v):
    print(v)


g = network([(replay.run, print_sink)])
g.run_network()
```

---

## Run the demo
```bash
python3 -m modules.ch02_sources.feed_numeric_replay
```

You’ll see a stream of temperatures.


---

## Troubleshooting

- **No output:** Ensure `CSV_PATH` points to an existing file and your `transform_row` does not return `None` for all rows.  
- **Too fast/slow:** Adjust `period_s` to control replay speed.  
---

## 👉 Next
[**Transformers using AI**  →](../ch03_GPT/README_1_replay.md). See how you can use OpenAI and other AI providers to create transformers.