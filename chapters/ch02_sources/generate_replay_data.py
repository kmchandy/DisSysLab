# lessons/ch02_sources/generate_replay_data.py
#
# Prepares MSFT daily data for 2023 and exposes:
#   TRIM_CSV_PATH (absolute), N_2023_ROWS, msft_transform(row)
#
# Robustness:
# - Try Stooq CSV (no key). Validate header/content.
# - If invalid or empty, fall back to Yahoo Finance CSV (no key) for 2023.
#
# Run standalone for diagnostics:
#   python -m lessons.ch02_sources.generate_replay_data

from __future__ import annotations

import csv
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

# --- Paths (absolute) --------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]  # .../DisSysLab
DATA_DIR = REPO_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RAW_CSV_PATH = DATA_DIR / "_msft_all.csv"
TRIM_CSV_PATH = DATA_DIR / "msft_2023.csv"

START = date(2023, 1, 1)
END = date(2023, 12, 31)

# --- Sources -----------------------------------------------------------------
STOOQ_URL = "https://stooq.com/q/d/l/?s=msft&i=d"


def _yahoo_url_for_2023(symbol: str = "MSFT") -> str:
    # Yahoo expects Unix epochs (seconds). period2 is exclusive; use end of day.
    p1 = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime(2023, 12, 31, 23, 59, 59,
             tzinfo=timezone.utc).timestamp())
    return (
        "https://query1.finance.yahoo.com/v7/finance/download/"
        f"{symbol}?period1={p1}&period2={p2}&interval=1d&events=history&includeAdjustedClose=true"
    )

# --- Utils -------------------------------------------------------------------


def _download_to(path: Path, url: str, timeout: float = 30.0) -> None:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        path.write_bytes(r.read())


def _looks_like_csv_with_header(path: Path) -> bool:
    try:
        head = path.read_text(
            encoding="utf-8", errors="ignore").splitlines()[:3]
    except Exception:
        return False
    if not head:
        return False
    # Must not be HTML, and should start with a CSV header containing "Date"
    joined = "\n".join(head).lower()
    if "<html" in joined or "</html>" in joined:
        return False
    return "date" in head[0].lower() and "," in head[0]


def _trim_csv_year(src_path: Path, dst_path: Path, start: date, end: date) -> int:
    """Copy rows whose Date is within [start, end] inclusive. Return data row count."""
    out_rows = 0
    with src_path.open(newline="", encoding="utf-8") as fin, \
            dst_path.open("w", newline="", encoding="utf-8") as fout:
        reader = csv.DictReader(fin)
        # Common headers (Stooq: capitalized; Yahoo: capitalized too)
        fieldnames = reader.fieldnames or [
            "Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            d = (row.get("Date") or row.get("date") or "").strip()
            if not d:
                continue
            # Accept both YYYY-MM-DD and MM/DD/YYYY if present (Yahoo uses YYYY-MM-DD)
            try:
                if "-" in d:
                    y, m, dd = map(int, d.split("-"))
                    dt = date(y, m, dd)
                else:
                    m, dd, y = map(int, d.split("/"))
                    dt = date(y, m, dd)
            except Exception:
                continue
            if start <= dt <= end:
                writer.writerow(row)
                out_rows += 1
    return out_rows


def _prepare_msft_2023() -> Tuple[Path, int]:
    """Ensure TRIM_CSV_PATH exists with 2023 rows; download+trim as needed."""
    # If already present with data, report and return.
    if TRIM_CSV_PATH.exists():
        try:
            with TRIM_CSV_PATH.open(encoding="utf-8") as f:
                n = max(sum(1 for _ in f) - 1, 0)
            if n > 0:
                print(f"[info] Using existing {TRIM_CSV_PATH} with {n} rows")
                return TRIM_CSV_PATH, n
        except Exception:
            pass  # fall through to re-create

    # 1) Try Stooq (full history), then trim.
    try:
        print("[setup] Downloading MSFT CSV from Stooq…")
        _download_to(RAW_CSV_PATH, STOOQ_URL)
        if not _looks_like_csv_with_header(RAW_CSV_PATH):
            raise RuntimeError("Stooq response not valid CSV")
        n = _trim_csv_year(RAW_CSV_PATH, TRIM_CSV_PATH, START, END)
        print(f"[setup] Stooq trim wrote {n} rows → {TRIM_CSV_PATH}")
        if n > 0:
            return TRIM_CSV_PATH, n
    except Exception as e:
        print(f"[warn] Stooq failed ({e}); will try Yahoo…")

    # 2) Fallback: Yahoo CSV for 2023 only.
    try:
        yahoo_url = _yahoo_url_for_2023("MSFT")
        print("[setup] Downloading MSFT 2023 CSV from Yahoo…")
        _download_to(TRIM_CSV_PATH, yahoo_url)
        if not _looks_like_csv_with_header(TRIM_CSV_PATH):
            raise RuntimeError("Yahoo response not valid CSV")
        # Count rows (exclude header)
        with TRIM_CSV_PATH.open(encoding="utf-8") as f:
            n = max(sum(1 for _ in f) - 1, 0)
        print(f"[setup] Yahoo wrote {n} rows → {TRIM_CSV_PATH}")
        return TRIM_CSV_PATH, n
    except Exception as e:
        print(f"[error] Yahoo fallback failed: {e}")

    # If both failed, create an empty file with header to avoid crashes.
    TRIM_CSV_PATH.write_text("Date,Close\n", encoding="utf-8")
    return TRIM_CSV_PATH, 0

# --- Dataset-specific row transform ------------------------------------------


def msft_transform(row: Dict[str, str]) -> Dict:
    dt = row.get("Date") or row.get("date")
    close = row.get("Close") or row.get("close") or row.get("Adj Close")
    try:
        close_f = float(close) if close is not None and close != "" else None
    except ValueError:
        close_f = None
    return {"date": dt, "close": close_f, "src": "msft_2023"}


# --- Prepare on import & expose metadata -------------------------------------
TRIM_CSV_PATH, N_2023_ROWS = _prepare_msft_2023()

if __name__ == "__main__":
    print(f"[ok] Prepared {TRIM_CSV_PATH} with {N_2023_ROWS} rows")
