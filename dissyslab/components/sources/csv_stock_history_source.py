# dissyslab/components/sources/csv_stock_history_source.py

"""
CSVStockHistorySource: reads real daily OHLCV price history for one or
more tickers from local CSV files.

Why this exists
================

Since 2026-08-18 this is the *only* history source, and reading from
disk is the design rather than a fallback.

Two sources preceded it. ``StockHistorySource`` wrapped Stooq's
historical endpoint, which stopped serving data (404, then a JavaScript
browser challenge); ``SyntheticStockHistorySource`` generated fake bars
to unblock development while that was broken. Both were removed.

Fetching is now a separate, explicit step the user runs once --
``gallery/apps/mac_speed_suite/download_stock_history_from_yf.py``
builds the CSVs this class reads. That separation is deliberate on two
counts. Yahoo's terms do not permit us to redistribute their prices, so
each user must fetch their own; and a backtest that re-downloads on
every run is slow, non-reproducible, and hostage to a vendor's uptime,
while one that reads a file gives the same answer next month.

Expected CSV format
====================

One file per ticker, with a header row and at least the columns
``Date, Open, High, Low, Close, Volume`` (case-insensitive; an
``Adj Close`` column, if present, is ignored -- ``Close`` is used
throughout this office, and the download script already writes
split/dividend-adjusted prices into ``Close``). Dates may be in any
format ``datetime`` can parse (``YYYY-MM-DD`` is typical); rows are
sorted by date before being returned, so file row order doesn't matter.

By default, a ticker's filename is ``{TICKER}_1year.csv`` in
``directory`` (matching the files Mani placed in
``DisSysLab/sp100_data/``); pass ``filename_pattern`` to match a
different naming convention (must contain ``{ticker}``).

Message shape (unchanged from the two removed sources, so nothing
downstream -- SIGNAL_COMPUTER,
BACKTESTER, EVALUATOR -- needs to know or care which source produced it):
    {
        "type":      "stock_history",
        "tickers":   ["AMD", "NFLX", ...],
        "start":     "20250801",
        "end":       "20260731",
        "history": {
            "AMD": [{"date": "2025-08-01", "open": ..., "high": ...,
                     "low": ..., "close": ..., "volume": ...}, ...],
            ...
        },
        "errors":    {"XYZ": "file not found: ..."},
        "timestamp": "2026-08-02T15:00:00+00:00",
    }

A ticker whose file is missing or unparseable lands in ``errors``
instead of crashing the whole batch -- same per-ticker error isolation
convention the removed history sources used.

Design notes:
    - One-shot generator (yields once, then stops) -- same "send once"
      shape as the other two stock-history sources.
    - ``directory`` may be relative (resolved against the current
      working directory the office is run from) or absolute.
    - ``start``/``end``, if given, filter rows to that inclusive date
      range after loading -- useful for testing on a subset of a
      longer file without re-exporting it.
"""

import csv
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence


class CSVStockHistorySource:
    """
    Reads per-ticker daily-bar CSV files from a local directory and
    yields them as a single bulk dict.

    Get the files with
    ``gallery/apps/mac_speed_suite/download_stock_history_from_yf.py``
    (needs ``pip install "dissyslab[market]"``). Nothing in this
    repository ships market data -- Yahoo's terms do not permit
    redistributing it, so every user fetches their own.

    Args:
        tickers:           Ticker symbols whose files should be loaded,
                            e.g. ["AMD", "NFLX", "NVDA", "PLTR", "TSLA"].
                            Must be non-empty.
        directory:          Directory containing the per-ticker CSV
                            files. Relative paths are resolved against
                            the current working directory.
        filename_pattern:   Filename template, must contain
                            ``{ticker}``. Default "{ticker}_1year.csv".
        start:              Optional first date to include ("YYYY-MM-DD"
                            or "YYYYMMDD"). Default: no lower bound.
        end:                Optional last date to include (same
                            formats). Default: no upper bound.

    Example:
        >>> real = CSVStockHistorySource(
        ...     tickers=["AMD", "NFLX", "NVDA", "PLTR", "TSLA"],
        ...     directory="sp100_data",
        ... )
        >>> source = Source(fn=real.run, name="price_history")
    """

    def __init__(
        self,
        tickers: Sequence[str],
        directory: str,
        filename_pattern: str = "{ticker}_1year.csv",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ):
        if not tickers:
            raise ValueError(
                "CSVStockHistorySource requires at least one ticker, "
                f"got {tickers!r}"
            )
        if "{ticker}" not in filename_pattern:
            raise ValueError(
                "filename_pattern must contain '{ticker}', got "
                f"{filename_pattern!r}"
            )
        self.tickers = [t.strip().upper() for t in tickers]
        self.directory = directory
        self.filename_pattern = filename_pattern
        self._start_date = self._parse_date(start) if start else None
        self._end_date = self._parse_date(end) if end else None

    @staticmethod
    def _parse_date(d: str):
        s = d.strip()
        if len(s) == 8 and s.isdigit():
            return datetime.strptime(s, "%Y%m%d").date()
        return datetime.strptime(s, "%Y-%m-%d").date()

    @staticmethod
    def _find_column(fieldnames: List[str], *candidates: str) -> Optional[str]:
        lower_map = {f.strip().lower(): f for f in fieldnames}
        for c in candidates:
            if c in lower_map:
                return lower_map[c]
        return None

    def _load_ticker(self, ticker: str) -> List[Dict]:
        path = os.path.join(
            self.directory, self.filename_pattern.format(ticker=ticker)
        )
        if not os.path.isfile(path):
            raise FileNotFoundError(f"file not found: {path}")

        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            date_col = self._find_column(fieldnames, "date")
            open_col = self._find_column(fieldnames, "open")
            high_col = self._find_column(fieldnames, "high")
            low_col = self._find_column(fieldnames, "low")
            close_col = self._find_column(fieldnames, "close")
            volume_col = self._find_column(fieldnames, "volume")
            missing = [
                name for name, col in [
                    ("date", date_col), ("open", open_col),
                    ("high", high_col), ("low", low_col),
                    ("close", close_col),
                ] if col is None
            ]
            if missing:
                raise ValueError(
                    f"{path}: missing required column(s) {missing} "
                    f"(found columns: {fieldnames})"
                )

            rows = []
            for row in reader:
                raw_date = row[date_col].strip()
                d = self._parse_date(raw_date)
                if self._start_date and d < self._start_date:
                    continue
                if self._end_date and d > self._end_date:
                    continue
                rows.append({
                    "date":   d.isoformat(),
                    "open":   float(row[open_col]),
                    "high":   float(row[high_col]),
                    "low":    float(row[low_col]),
                    "close":  float(row[close_col]),
                    "volume": int(float(row[volume_col])) if volume_col and row.get(volume_col) else None,
                })

        rows.sort(key=lambda r: r["date"])
        return rows

    def run(self):
        """
        One-shot generator: load every ticker's CSV file, then yield a
        single bulk dict and stop -- same "fire once" shape as the
        other stock-history sources.
        """
        history: Dict[str, List[Dict]] = {}
        errors: Dict[str, str] = {}

        for ticker in self.tickers:
            try:
                history[ticker] = self._load_ticker(ticker)
            except Exception as exc:  # noqa: BLE001 -- isolate one bad ticker
                errors[ticker] = str(exc)

        all_dates = [
            bar["date"] for bars in history.values() for bar in bars
        ]

        yield {
            "type":      "stock_history",
            "tickers":   list(history.keys()),
            "start":     min(all_dates) if all_dates else None,
            "end":       max(all_dates) if all_dates else None,
            "history":   history,
            "errors":    errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
