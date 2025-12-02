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
    window=20,
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
