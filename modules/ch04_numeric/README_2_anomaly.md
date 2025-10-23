#modules/ch04_numerics/README_2_anomaly_detection.md

---

# 4.2 An Example of Anomaly Detection

Many applications require the detection of anomalies in streaming data. There are several ways of detecting anomalies. This example shows an algorithm that uses exponential moving statistics, and bands around predicted values.

The nodes of the graph are:


1) **RandomWalkDeterministic** emits a reproducible sequence `{t_step, x}` (no wall-clock timing, no sleeps).
2) **EMAStd** maintains a streaming **exponential moving average** (level) and **exp-weighted std** (volatility). No buffers; O(1) per message.
3) **ZScoreBands** computes a **z-score** `z = (x − ema)/std` and **dynamic bands** `ema ± k·std`.
4) **FlagAnomaly** marks `anomaly=True` if `|z| ≥ z_thresh` or `x` falls outside the bands (after a short warm-up).
5) **Sinks**:
   - **console**: prints a compact summary every N messages (keeps output readable).
   - **jsonl**: appends selected fields to a `*.jsonl` file for later plotting/analysis.

---

## Parameters

### RandomWalkDeterministic
- `steps` (int): number of messages to emit (finite run → easy postprocessing).
- `base` (float): starting value of the series.
- `drift_per_step` (float): deterministic change per step (e.g., 0.01).
- `sigma` (float): Gaussian noise std per step (higher → noisier).
- `seed` (int): makes the sequence reproducible.
- `name` (str, optional): label used in graph diagrams/logs.

### EMAStd  -- exponential moving statistics
- `alpha` (float in (0,1]): responsiveness; larger = faster, noisier.  
  Tip: small `alpha` (e.g., 0.03) makes **std** adapt slowly → clearer anomalies.
- `eps` (float): tiny constant under the square root for numerical safety.
- `std_min` (float): floor to prevent division by (near) zero early on.
- `name` (str, optional): display label.

### ZScoreBands -- bands around predictions. 
- `k` (float): band width multiplier; typical values: 1.5–2.5.
- `std_floor` (float): guard against tiny std when computing z-scores.
- `z_clip` (float|None): if set, also add a clipped `z_clipped` for stable printing.
- `name` (str, optional).

### FlagAnomaly when actual value is outside bands.
- `z_thresh` (float): anomaly if `|z| ≥ z_thresh` (and/or outside bands).
- `warmup_steps` (int): suppress alerts for early steps while stats settle.
- `name` (str, optional).

### Sinks
- **console**: `every_n` controls how often to print (e.g., 20).
- **JSONLRecorder**: `path` for the output file; stores key fields per line.


---

## Run it

From DisSysLab:
```
python -m modules.ch05_ds.anomaly_demo
```

## 👉 Next
[Better techniques: TFIDF and PCA](./README_3_TFIDF.md)