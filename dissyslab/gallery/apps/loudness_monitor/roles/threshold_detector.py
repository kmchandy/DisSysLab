# dissyslab/gallery/apps/loudness_monitor/roles/threshold_detector.py

"""
Bryn — the threshold_detector role.

Watches an inbound dB stream and emits **only** at the rising edge
above ``db_threshold``. After a fire, the detector re-arms once the
level has been continuously below threshold for ``debounce_ms`` —
the debounce prevents a single loud event from re-triggering on
each chunk.

This is the "respond" half of sense-respond. Most chunks produce
zero downstream messages; only the events do.

Input message (from rms_meter)::

    {"db": float, "rms": float, "timestamp": float, "chunk_index": int}

Output message (only on rising-edge events)::

    {
        "event":         "loud",
        "peak_db":       float,
        "started_at":    "2026-06-10T14:32:11",
        "title":         "Loud event",
        "text":          "Detected at -22.1 dBFS.",
        "significance":  "HIGH" | "MEDIUM" | "LOW",
        "source":        "loudness_monitor",
    }
"""

from __future__ import annotations

import time
from datetime import datetime

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


def _significance(peak_db: float) -> str:
    """Bucket peak dB into a display tint."""
    if peak_db >= -15:
        return "HIGH"
    if peak_db >= -22:
        return "MEDIUM"
    return "LOW"


def _description(peak_db: float) -> str:
    """Plain-language label for the loud event.

    These describe the level of the *signal in the recording*
    (dBFS), not the perceived loudness in your room (dB SPL).
    The two are related only by your playback gain, so we avoid
    claims like 'dangerous' that depend on physical loudness.
    """
    if peak_db >= -10:
        return "Very loud peak"
    if peak_db >= -15:
        return "Loud peak"
    if peak_db >= -22:
        return "Notable burst"
    return "Above ambient"


def _format_position(seconds: float | None) -> str:
    """Render seconds as ``MM:SS.s`` (e.g. ``"00:33.2"``)."""
    if seconds is None:
        return "??:??.?"
    minutes = int(seconds // 60)
    rem = seconds - minutes * 60
    return f"{minutes:02d}:{rem:04.1f}"


def _level_bar(peak_db: float, threshold_db: float, width: int = 10) -> str:
    """A small visual indicator of how far the peak exceeded threshold.

    Empty when peak is at threshold, full when peak is 0 dBFS.
    Uses Unicode block characters with an ASCII fallback path is
    handled by the terminal — most modern terminals render these
    fine.
    """
    span = -threshold_db
    if span <= 0:
        return ""
    fraction = max(0.0, min(1.0, (peak_db - threshold_db) / span))
    filled = int(round(fraction * width))
    return "█" * filled + "░" * (width - filled)


class _ThresholdDetector(Agent):
    """Edge-triggered threshold detector with debounce.

    State machine
    -------------
    armed = True  : ready to fire on the next chunk above threshold
    armed = False : suppressing — must observe ``debounce_ms`` of
                    below-threshold readings before re-arming

    Below-threshold readings are tracked via ``_below_since_ts``,
    a wall-clock timestamp of the first below-threshold reading
    since the last above-threshold reading. Any above-threshold
    reading resets ``_below_since_ts`` to ``None``.
    """

    def __init__(
        self,
        name: str | None = None,
        db_threshold: float = -30.0,
        debounce_ms: float = 400.0,
    ):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=["out_"],
        )
        self.db_threshold = float(db_threshold)
        self.debounce_ms = float(debounce_ms)
        self._armed = True
        self._below_since_ts = None
        self._event_counter = 0

    def run(self) -> None:
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict):
                continue
            db = msg.get("db")
            ts = msg.get("timestamp") or time.time()
            stream_position = msg.get("stream_position_seconds")
            if db is None:
                continue

            above = db >= self.db_threshold

            if above:
                # Any above-threshold reading resets debounce
                self._below_since_ts = None
                if self._armed:
                    self._fire(db, ts, stream_position)
                    self._armed = False
            else:
                if not self._armed:
                    if self._below_since_ts is None:
                        self._below_since_ts = ts
                    else:
                        elapsed_ms = (ts - self._below_since_ts) * 1000.0
                        if elapsed_ms >= self.debounce_ms:
                            self._armed = True
                            self._below_since_ts = None

    # ── Emit one event message ───────────────────────────────────────
    def _fire(
        self,
        peak_db: float,
        ts: float,
        stream_position: float | None,
    ) -> None:
        self._event_counter += 1
        started_at = datetime.fromtimestamp(ts).isoformat(
            timespec="seconds",
        )
        sig = _significance(peak_db)
        desc = _description(peak_db)
        position_str = _format_position(stream_position)
        bar = _level_bar(peak_db, self.db_threshold)
        self.send(
            {
                "event":         "loud",
                "event_index":   self._event_counter,
                "peak_db":       peak_db,
                "started_at":    started_at,
                "stream_position_seconds": stream_position,
                "title":         f"{desc} at {position_str}",
                "text": (
                    f"Event #{self._event_counter} — "
                    f"peak {peak_db:+.1f} dBFS  {bar}  ({sig})"
                ),
                "significance":  sig,
                "source":        "loudness_monitor",
            },
            "out_",
        )


role = AgentRoleEntry(
    name="threshold_detector",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_ThresholdDetector,
)
