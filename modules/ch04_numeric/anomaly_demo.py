# modules.ch04_numeric.anomaly_demo.py
from __future__ import annotations
from dsl import network
from dsl.math_lib.random_walk import RandomWalkOneDimensional
from dsl.math_lib.sliding_window_anomaly_exponential import SlidingWindowAnomalyExponential
from dsl.connectors.sink_jsonl_recorder import JSONLRecorder
from .MakeConsoleSummary import make_console_summary


# Make a source object: one-dimensional random walk
src = RandomWalkOneDimensional(
    n_steps=600, base=100.0, drift_per_step=0.01, sigma=0.6, seed=42, name="src"
)

# Make transform object: exponential moving average anomaly detector
ema = SlidingWindowAnomalyExponential(alpha=0.1, name="ema")

# Make sink object
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

# Finalize writing to JSONL file after network run is complete
if hasattr(rec, "finalize"):
    rec.finalize()
print("Wrote JSONL to anomaly_stream.jsonl")
