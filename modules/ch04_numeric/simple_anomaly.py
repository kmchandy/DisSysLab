# modules.ch04_numeric.simple_anomaly

from pathlib import Path
from dsl import network
from dsl.connectors.replay_csv_in import ReplayCSV_In
from .rolling_stats_anom_forecast import rolling_stats_anom_forecast
from .temp_live_sink import temp_live_sink

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
