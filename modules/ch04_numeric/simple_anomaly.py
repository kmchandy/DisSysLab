# modules.ch04_numeric.simple_anomaly
from __future__ import annotations
from typing import Any
from pathlib import Path
from dsl import network
from dsl.connectors.replay_csv_in import ReplayCSV_In
from dsl.math_lib.sliding_window_anomaly import SlidingWindowAnomaly
from .temp_live_sink import temp_live_sink

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
    path=CSV_PATH,
    transform=from_CSV_row_to_dict,
    period_s=0.25,
    name="source_replay")


# -------------------------------------------------------------------------
# Agent: Sliding window statistics for anomaly detection

agent_sliding_window = SlidingWindowAnomaly(
    window_size=20,
    std_limit=2.0,      # anomaly threshold
    key_data="tmax_f",
    name="sliding_window_anomaly_agent"
)

# -------------------------------------------------------------------------
# Create and run network
g = network([(replay.run, agent_sliding_window.run),
            (agent_sliding_window.run, temp_live_sink)])
g.run_network()
