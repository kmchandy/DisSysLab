# modules.ch04_numeric.anomaly_demo.py
from __future__ import annotations
import json
from typing import Dict, Optional
from dsl import network
from dsl.math_lib.random_walk import RandomWalkOneDimensional
from dsl.math_lib.sliding_window_anomaly_exponential import SlidingWindowAnomalyExponential

# -----------------------------------------------------------------
# Sink agents:
# (1) Agent that writes summary to console
# (2) Agent that writes selected fields to JSONL file


def make_console_summary(every_n: int = 1):
    """
    Prints a compact summary every N messages (keeps output readable).
    """
    i = {"n": 0}

    def _sink(msg: Dict[str, float]):
        i["n"] += 1
        if i["n"] % every_n == 0:
            print(f"t={msg['t_step']:3d}  x={msg['x']:+8.2f}  ema={msg['ema']:+8.2f} std={msg['std']:+6.2f}"
                  f"band = [{msg['pred_low']:3f}, {msg['pred_high']:3f}] anomaly={msg['anomaly']}"
                  )
        return msg
    _sink.__name__ = f"console_every_{every_n}"
    return _sink


class JSONLRecorder:
    """
    Append selected fields to a JSONL file (one record per message).
    """

    def __init__(self, path: str = "anomaly_stream.jsonl", *, name: Optional[str] = None):
        self.path = path
        self._fh = open(self.path, "w", encoding="utf-8")  # file handle
        self._name = name or "jsonl_recorder"

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self, msg: Dict[str, float]):
        self._fh.write(json.dumps(msg, default=str) + "\n")
        return msg

    def finalize(self):
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass

    run = __call__


if __name__ == "__main__":
    # Source: deterministic, finite stream
    src = RandomWalkOneDimensional(
        n_steps=600, base=100.0, drift_per_step=0.01, sigma=0.6, seed=42, name="src"
    )

    # Transforms
    ema = SlidingWindowAnomalyExponential(alpha=0.1, name="ema")

    # Sinks
    console = make_console_summary(every_n=20)
    rec = JSONLRecorder(path="anomaly_stream.jsonl", name="rec")

    # Build and run network
    g = network([
        (src.run,  ema.run),
        # fan-out to two sinks
        (ema.run, console),
        (ema.run, rec),
    ])
    g.run_network()

    # Finalize writing to JSONL file
    if hasattr(rec, "finalize"):
        rec.finalize()
    print("Wrote JSONL to anomaly_stream.jsonl")
