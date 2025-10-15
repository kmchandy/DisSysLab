# lessons/ch02_sources/rolling_stats_anom_forecast.py
from collections import deque
import math
from typing import Callable, Optional, Dict, Any


def rolling_stats_anom_forecast(
    *,
    window: int = 20,
    k_anom: float = 2.0,           # anomaly threshold (|x-μ| > k_anom·σ)
    # prediction band width for NEXT value (μ ± k_pred·σ)
    k_pred: float = 0.5,
    key_in: str = "tmax_f",
    date_key: str = "date",
    time_key: str = "time",
    prefix: str = "w",
    printer: Callable[[str], None] = print,
    debug: bool = False,
):
    """
    Adds rolling stats, anomaly flag, and one-step-ahead prediction band.
    Also reports whether the *current* value fit in the band predicted at t-1.

    Emits on each message:
      {prefix}_n, {prefix}_mean, {prefix}_std,
      anomaly (bool),
      pred_low, pred_high           # band for the NEXT value (t+1), built at t
      fits (bool|None)              # did current x fall in the band predicted at t-1?
      cover_total, cover_hits, cover_rate
    """
    q = deque()
    s = 0.0
    ss = 0.0

    prev_pred_low: Optional[float] = None   # band predicted at t-1 for x_t
    prev_pred_high: Optional[float] = None
    prev_pred_made_for: Optional[str] = None

    cover_total = 0
    cover_hits = 0

    def transform(msg: Dict[str, Any]) -> Dict[str, Any]:
        nonlocal s, ss, prev_pred_low, prev_pred_high, prev_pred_made_for
        nonlocal cover_total, cover_hits

        x = msg.get(key_in)
        d = msg.get(date_key, "-")
        t = msg.get(time_key, "-")

        # Coerce to float if string
        if isinstance(x, str):
            try:
                x = float(x)
            except Exception:
                x = None

        # 1) Verify previous prediction against current x (fit/miss)
        fits: Optional[bool] = None
        if prev_pred_low is not None and x is not None:
            fits = (prev_pred_low <= x <= prev_pred_high)
            cover_total += 1
            if fits:
                cover_hits += 1
            elif debug:
                printer(
                    f"[miss] {d}: x={x:.3f} ∉ [{prev_pred_low:.3f}, {prev_pred_high:.3f}] (pred @ {prev_pred_made_for})")

        # 2) Update rolling stats with current x
        if x is not None:
            q.append(x)
            s += x
            ss += x*x
            if len(q) > window:
                old = q.popleft()
                s -= old
                ss -= old*old

        n = len(q)
        mean = (s / n) if n > 0 else None
        var = max(ss / n - (mean*mean if mean is not None else 0.0),
                  0.0) if n > 0 else None
        std = math.sqrt(var) if var is not None else None

        out = dict(msg)
        out[f"{prefix}_n"] = n
        out[f"{prefix}_mean"] = mean
        out[f"{prefix}_std"] = std

        # 3) Anomaly test on current x using k_anom
        anomalous = (std is not None and std > 0 and x is not None and n >= 2
                     and abs(x - mean) > k_anom * std)
        out["anomaly"] = anomalous
        if anomalous:
            printer(
                f"Anomaly. {d}, {t}, mean={mean:.3f}, std={std:.3f}, x={x:.3f}")

        # 4) Build prediction band for NEXT value using k_pred
        if std is not None and mean is not None and n >= 2:
            pred_low = mean - k_pred * std
            pred_high = mean + k_pred * std
            out["pred_low"] = pred_low
            out["pred_high"] = pred_high
            prev_pred_low = pred_low
            prev_pred_high = pred_high
            prev_pred_made_for = d
        else:
            out["pred_low"] = None
            out["pred_high"] = None
            prev_pred_low = None
            prev_pred_high = None
            prev_pred_made_for = None

        out["fits"] = fits
        out["cover_total"] = cover_total
        out["cover_hits"] = cover_hits
        out["cover_rate"] = (cover_hits / cover_total) if cover_total else None

        if debug:
            printer(f"[dbg] {d}: n={n} μ={mean} σ={std} "
                    f"next=[{out['pred_low']},{out['pred_high']}] fits={fits} "
                    f"cov={cover_hits}/{cover_total}")
        return out

    return transform
