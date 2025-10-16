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
