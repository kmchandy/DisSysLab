# components/sources/clock_source.py

"""
ClockSource: Emits periodic tick messages into a DisSysLab pipeline.

ClockSource is a source node — it produces messages that flow into the
network just like RSSSource or BlueSkyJetstreamSource. It is wired
alongside article sources into the StatefulAgent using fanin:

    RSSNormalizer  ──┐
                     ├──→ StatefulAgent → ReportWriter → Sink
    ClockSource    ──┘

Each tick message:
    {"type": "tick", "timestamp": "<ISO string>"}

Usage:
    from dissyslab.components.sources.clock_source import ClockSource
    from dissyslab.blocks import Source

    clock  = ClockSource(interval_seconds=86400)   # fire once a day
    source = Source(fn=clock.run, name="clock")

For testing (fire immediately, stop after N ticks):
    clock = ClockSource(interval_seconds=0, max_ticks=1)

Presets:
    ClockSource.hourly()   — every hour
    ClockSource.daily()    — every 24 hours (default)
    ClockSource.weekly()   — every 7 days
"""

import time
from datetime import datetime, timezone
from typing import Optional


class ClockSource:
    """
    Emits periodic tick dicts into the pipeline.

    No authentication required. No external dependencies.

    Args:
        interval_seconds: Seconds between ticks. Default: 86400 (1 day).
        max_ticks:        Stop after this many ticks. None = run forever.
                          Set to a small number for testing.

    Example:
        >>> clock = ClockSource(interval_seconds=86400)
        >>> source = Source(fn=clock.run, name="clock")
    """

    def __init__(
        self,
        interval_seconds: int = 86400,
        max_ticks: Optional[int] = None,
    ):
        self.interval_seconds = interval_seconds
        self.max_ticks = max_ticks

    def run(self):
        """
        Generator that yields one tick dict per interval.

        Compatible with Source(fn=clock.run, name="clock") directly —
        Source() in dsl/blocks/source.py auto-wraps generators.
        """
        ticks = 0

        while True:
            if self.interval_seconds > 0:
                time.sleep(self.interval_seconds)

            ticks += 1
            yield {
                "type":      "tick",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if self.max_ticks is not None and ticks >= self.max_ticks:
                return

    # ── Convenience presets ───────────────────────────────────────────────

    @classmethod
    def hourly(cls, max_ticks: Optional[int] = None) -> "ClockSource":
        return cls(interval_seconds=3_600, max_ticks=max_ticks)

    @classmethod
    def daily(cls, max_ticks: Optional[int] = None) -> "ClockSource":
        return cls(interval_seconds=86_400, max_ticks=max_ticks)

    @classmethod
    def weekly(cls, max_ticks: Optional[int] = None) -> "ClockSource":
        return cls(interval_seconds=604_800, max_ticks=max_ticks)
