#modules/ch04_numerics/README_2_anomaly_detection.md

---

# 4.2 Anomaly Detection with Exponential Smoothing
 This page shows you how to build systems in which agents, running concurrently, execute programs in Python's extensive libraries. 

Many applications require the detection of anomalies in streaming data. There are several ways of detecting anomalies. This example has a network with three agents. The source generates a stream of values that represent locations in a random walk. A second agent receives this stream and computes the exponential moving average and the exponentially-weighted standard deviation after receiving each message. A third agent receives the stream of messages containing the random walk and sliding-window statistics and prints a summary to the console.

This simplistic example illustrates how anomalies can be detected by multiple agents operating concurrently. You can build more complex examples with live streams from multiple sources and more complex detection algorithms and better console displays. For example, look at the [Caltech Community Seismic Network](http://csn.caltech.edu/).



```python
     +------------------+
     |   source: src    |
     |   random walk    |
     +------------------+
            |
            | stream of dict with keys "t_step" and "x" where msg["x"] is 
            | a float that represents the location of a one-dimension random 
            | walk and msg["t_step"] is the number of steps in the walk.
            v
     +----------------------+
     |    ema: exponential  | compute exponential moving average and 
     |     moving average   | exponentially weighted standard deviation.
     |       and std        | 
     +----------------------+
            |
            | dict enriched with "ema" and "std"
            v
     +---------------------------+
     |  rec: print a summary to  |
     |   the console             |
     +---------------------------+
```


The nodes of the graph are:


1) **src** instance of class **RandomWalkDeterministic**. A source that outputs messages which are dicts with two fields **x** and **tstep** where **x** is the state (position) of a linear random walk walk and **t_step** is the step number. 
2) **ema** an instance of the class **EMAStd** which maintains a streaming **exponential moving average** and **exponentially-weighted std** 
3) **Sinks**:
   - **console**: prints a compact summary every N messages (keeps output readable).
   - **jsonl**: appends selected fields to a `*.jsonl` file for later plotting/analysis.

---

```python
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


```
---

## Run it

From DisSysLab:
```
python -m modules.ch04_numeric.anomaly_demo

```

## 👉 Next
[Clustering texts](./README_cluster.md)