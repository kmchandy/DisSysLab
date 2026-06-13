# dissyslab/components/sources/csv_points_source.py

"""
CSVPointsSource — reads ``(x,y)`` pairs from a CSV file.

Designed to be paired with the framework's ``Source`` wrapper:
the wrapped object's ``run()`` returns one ``{"x": float, "y": float}``
dict per call; the wrapper handles ``_poll_os`` between calls.

The class implements the v1.6 checkpoint contract — ``save_state``
and ``load_state`` — so that ``Source``'s framework wrapper can
delegate snapshot persistence to it. The state is just the integer
``cursor`` (number of lines read so far); on recovery the file is
reopened and ``cursor`` lines are skipped.

This source is used by the ``recovery_demo`` gallery office (the
Monte Carlo π estimator) to demonstrate distributed snapshot
checkpoint-recovery. It is a generic CSV reader and is reusable
for any office that needs to stream (x, y) pairs from disk.

Usage in office.md::

    Sources: csv_points_source(path="./samples/points.txt",
                               interval=0.01)

The ``interval`` parameter is wired to the ``Source`` wrapper's
inter-emission sleep; it slows the office down enough that
periodic snapshots have something to capture between firings.

File format: one ``x,y`` per line, comma-separated. Lines starting
with ``#`` are treated as comments and skipped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


class CSVPointsSource:
    """Read ``(x, y)`` pairs from a CSV file one per call.

    Parameters
    ----------
    path : str
        Path to a CSV file with one ``x,y`` per line.
    """

    def __init__(
        self,
        path: str = "./samples/points.txt",
        interval: float = 0.0,
    ):
        self.path = Path(path)
        # Inter-emission sleep in seconds. The framework's Source
        # wrapper also has its own ``interval`` parameter, but that
        # is set at the wrapper construction site (Source(fn=...,
        # interval=...)) and not configurable from office.md. We
        # accept ``interval`` here so the office.md can slow the
        # source down enough for periodic snapshots to fire
        # mid-stream.
        self.interval = float(interval)
        # cursor: number of data lines (non-comment, non-blank) that
        # have been read. This is the only piece of state that needs
        # to survive a snapshot.
        self.cursor: int = 0
        # _file: open file handle. Transient — closed and reopened on
        # the first call after a load_state.
        self._file = None

    # ── Source state contract (v1.6) ─────────────────────────────────
    def save_state(self) -> Dict[str, Any]:
        return {"cursor": self.cursor}

    def load_state(self, state: Dict[str, Any]) -> None:
        self.cursor = int(state.get("cursor", 0))
        # Force reopen on next run() so the file is positioned correctly.
        if self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None

    # ── Per-emission read ────────────────────────────────────────────
    def run(self) -> Optional[Dict[str, float]]:
        """Return one ``{"x": float, "y": float}`` per call; ``None``
        on EOF."""
        if self.interval > 0:
            import time as _t
            _t.sleep(self.interval)
        if self._file is None:
            try:
                self._file = self.path.open("r", encoding="utf-8")
            except FileNotFoundError:
                return None
            # Skip to the saved cursor position. Comment lines do not
            # count toward the cursor (the cursor counts data lines).
            skipped_data = 0
            while skipped_data < self.cursor:
                line = self._file.readline()
                if not line:
                    return None
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                skipped_data += 1

        # Read the next non-comment, non-blank line.
        while True:
            line = self._file.readline()
            if not line:
                return None
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            break

        try:
            x_str, y_str = stripped.split(",")
            x, y = float(x_str), float(y_str)
        except ValueError:
            # Malformed line — skip and try the next.
            return self.run()

        self.cursor += 1
        return {"x": x, "y": y}
