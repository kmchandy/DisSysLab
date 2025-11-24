# dsl/connectors/replay_csv_in.py
from __future__ import annotations
import csv
import time
from typing import Dict, Iterable, Optional, Callable


class ReplayCSV_In:
    """
    Replays numeric (or mixed) rows from a CSV file at a steady pace.

    Params:
      path: CSV file path.
      transform: optional fn(row_dict) -> Dict to pick/rename/convert fields.
      period_s: seconds to wait between emitted rows (pace students can watch).
      life_time: total seconds to run (None = until file end).
      loop: if True, loop back to start when end-of-file is reached (until life_time).
      start_row: 0-based row index to start from (after header).
      max_rows: optional cap on number of rows to emit (per loop).

    Yields:
      Dict messages (already transformed if transform is provided).
    """

    def __init__(
        self,
        *,
        path: str,
        transform: Optional[Callable[[Dict[str, str]], Dict]] = None,
        period_s: float = 0.5,
        life_time: Optional[float] = None,
        loop: bool = False,
        start_row: int = 0,
        max_rows: Optional[int] = None,
    ):
        self.path = path
        self.transform = transform
        self.period_s = period_s
        self.life_time = life_time
        self.loop = loop
        self.start_row = start_row
        self.max_rows = max_rows

    def __call__(self) -> Iterable[Dict]:
        start_t = time.time()
        emitted = 0
        while True:
            with open(self.path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                # fast-skip to start_row
                for _ in range(self.start_row):
                    try:
                        next(reader)
                    except StopIteration:
                        break

                for row in reader:
                    if self.life_time is not None and (time.time() - start_t) >= self.life_time:
                        return
                    if self.max_rows is not None and emitted >= self.max_rows:
                        return

                    msg = self.transform(row) if self.transform else row
                    yield msg
                    emitted += 1
                    time.sleep(self.period_s)

            if not self.loop:
                return
    run = __call__
