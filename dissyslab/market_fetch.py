"""Fetch a user's own price history, as something an assistant can run.

Why this is a subcommand and not a script
-----------------------------------------
It was a script inside one gallery app, run from a terminal after a
``cd`` into that app's folder -- which meant a tester's path to a
backtest went through a git clone and two shell commands. A capability
an assistant cannot reach is a capability the user has to reach
themselves.

``dsl fetch-prices NVDA AMD --years 10`` works from anywhere, after a
plain ``pip install``, and an assistant can run it, read what it says
and act on the result. That is the whole point: the download stays a
deliberate act -- your own copy, your own agreement with the vendor --
but it becomes something you *ask for* rather than something you run.

What it does not do
-------------------
It never ships data. Yahoo's terms do not permit redistributing their
prices, so nothing here caches, mirrors or bundles them; every user
fetches their own, which is also why ``yfinance`` lives in an extra you
install deliberately rather than something that arrives by accident.

It does not re-fetch what you already have unless asked. Ten years of
daily bars for a basket is slow, and a backtest that silently
re-downloads is neither reproducible nor kind to the vendor.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from dissyslab.market_data import market_data_dir

#: What ``--years 10`` writes. Matches what the shipped trading offices
#: ask for, so a fetch and the office that reads it agree by
#: construction rather than by the user getting a filename right.
DEFAULT_PATTERN = "{ticker}_{years}_year.csv"

_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,12}$")


class FetchError(RuntimeError):
    """Something the user can act on. Never a traceback."""


@dataclass(frozen=True)
class FetchResult:
    ticker: str
    path: Path
    rows: int
    skipped: bool = False


def office_basket(office_dir: Path) -> tuple[list[str], str, int]:
    """(tickers, filename_pattern, years) from an office's own line.

    Read from ``office.md`` so a fetch matches what the office will
    later look for. The two used to agree by arithmetic and that is the
    bug this whole area is repairing.
    """
    office_md = Path(office_dir) / "office.md"
    if not office_md.is_file():
        raise FetchError(
            f"no office.md in {office_dir}. Name the tickers instead: "
            "dsl fetch-prices NVDA AMD --years 10"
        )
    text = office_md.read_text(encoding="utf-8", errors="replace")
    call = re.search(r"csv_stock_history\((.*?)\)", text, re.DOTALL)
    if not call:
        raise FetchError(
            f"{office_md} has no csv_stock_history(...) source, so it "
            "reads no price data. Name the tickers instead."
        )
    args = call.group(1)
    tick_m = re.search(r"tickers\s*=\s*\[([^\]]*)\]", args)
    tickers = (
        re.findall(r"['\"]([A-Za-z0-9.\-]+)['\"]", tick_m.group(1))
        if tick_m else []
    )
    if not tickers:
        raise FetchError(f"{office_md} names no tickers.")
    pat_m = re.search(r"filename_pattern\s*=\s*['\"]([^'\"]+)['\"]", args)
    pattern = pat_m.group(1) if pat_m else "{ticker}_1year.csv"
    yr_m = re.search(r"(\d+)_?year", pattern)
    years = int(yr_m.group(1)) if yr_m else 1
    return tickers, pattern, years


def _filename(pattern: str, ticker: str, years: int) -> str:
    return pattern.format(ticker=ticker, years=years)


def _download(ticker: str, years: int):
    """One ticker, as a DataFrame. The seam tests replace."""
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - environment
        raise FetchError(
            "downloading price history needs yfinance, which is in the "
            'market extra:  pip install "dissyslab[market]"'
        ) from exc

    data = yf.download(ticker, period=f"{years}y", interval="1d",
                       auto_adjust=True)
    if data is None or len(data) == 0:
        # yfinance swallows transport errors and returns an empty
        # frame, so at this point the cause is genuinely unknown. Say
        # the three real possibilities rather than picking one and
        # sending the reader down the wrong path.
        raise FetchError(
            f"{ticker}: the vendor returned no rows. Any of three "
            "things:\n"
            "  - the symbol is not one they carry (check the spelling)\n"
            "  - no network route to the vendor from here\n"
            "  - you are being rate-limited; wait and try again\n"
            "Any message printed above this line came from yfinance and "
            "usually says which."
        )
    # yfinance returns MultiIndex columns like ("Close", "AAPL"); keep
    # the metric name so the CSV has one clean header row.
    if hasattr(data.columns, "get_level_values"):
        data.columns = data.columns.get_level_values(0)
    data.index.name = "Date"
    return data[["Open", "High", "Low", "Close", "Volume"]]


def fetch(
    tickers,
    years: int = 10,
    pattern: str = DEFAULT_PATTERN,
    dest: Path | None = None,
    force: bool = False,
    download=_download,
) -> list[FetchResult]:
    """Fetch each ticker into the shared market-data directory."""
    dest = Path(dest) if dest else market_data_dir()
    bad = [t for t in tickers if not _TICKER_RE.match(t)]
    if bad:
        raise FetchError(f"not ticker symbols: {bad}")

    dest.mkdir(parents=True, exist_ok=True)
    results: list[FetchResult] = []
    for raw in tickers:
        ticker = raw.strip().upper()
        path = dest / _filename(pattern, ticker, years)
        if path.is_file() and not force:
            # Slow, and a backtest that silently re-downloads is not
            # reproducible. Say it was skipped rather than doing it.
            results.append(FetchResult(ticker, path, _count_rows(path), True))
            continue
        frame = download(ticker, years)
        frame.to_csv(path)
        results.append(FetchResult(ticker, path, len(frame)))
    return results


def _count_rows(path: Path) -> int:
    try:
        with path.open(encoding="utf-8") as f:
            return max(sum(1 for _ in f) - 1, 0)
    except OSError:
        return 0


def confirm_office_reads(office_dir: Path, tickers, pattern: str,
                         dest: Path | None = None) -> list[str]:
    """Check the office can now load what was just fetched.

    Fetching and reading are two different pieces of code agreeing on a
    directory and a filename. Proving the agreement here means the user
    finds out now, rather than from an office that runs and produces
    nothing.
    """
    from dissyslab.components.sources.csv_stock_history_source import (
        CSVStockHistorySource,
    )

    # Look where the files were actually written. Confirming against
    # the default directory after a --dest fetch would report a failure
    # that is only this function looking in the wrong place.
    source = CSVStockHistorySource(
        tickers=list(tickers),
        directory=str(dest) if dest else None,
        filename_pattern=pattern,
    )
    unreadable = []
    for ticker in tickers:
        try:
            source._load_ticker(ticker.upper())
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            unreadable.append(f"{ticker}: {exc}")
    return unreadable
