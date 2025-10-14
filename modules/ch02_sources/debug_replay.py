# lessons/ch02_sources/debug_replay.py
from pathlib import Path
import csv
import time

from dsl import network
from dsl.connectors.replay_csv_in import ReplayCSV_In
from dsl.connectors.live_kv_console import kv_live_sink

# --- 0) Point to your CLEAN file robustly ---
CSV_PATH = Path(__file__).resolve().parent / "open-meteo_clean.csv"

# --- 1) Sanity: show first few raw rows (no DictReader quirks) ---


def preview_csv(path: Path, n=3):
    print(f"[preview] reading CSV: {path}")
    if not path.exists():
        print("[error] file not found!")
        return False
    with path.open(newline="", encoding="utf-8", errors="ignore") as f:
        r = csv.reader(f)
        rows = []
        for i, row in enumerate(r):
            rows.append(row)
            if len(rows) >= n:
                break
    print("[preview] first rows:")
    for row in rows:
        print("   ", row)
    return True

# --- 2) Your transform (adjust header names if needed) ---


def transform_row(row):
    # Expect headers exactly as in the CLEAN file (printed by preview).
    t = row.get("time")
    temp = row.get("temperature_2m_max (°F)") or row.get("temperature")
    try:
        temp_f = float(temp) if temp not in (None, "") else None
    except ValueError:
        temp_f = None
    # Return None to skip rows; return dict to emit
    if t is None or temp_f is None:
        return None
    return {"date": t, "tmax_f": temp_f}


# --- 3) Build replay (slow enough to watch) ---
replay = ReplayCSV_In(
    path=str(CSV_PATH),
    transform=transform_row,
    period_s=0.2,
    life_time=None,
    loop=False,
)

# --- 4) Quick smoke tests (no network) ---


def smoke_test_transform_only():
    print("[smoke] transform on first 5 DictReader rows:")
    with CSV_PATH.open(newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            out = transform_row(row)
            print(f"   row {i}: {out}")
            if i >= 4:
                break


def smoke_test_replay_only(m=5):
    print("[smoke] iterating replay.run() directly:")
    it = replay.run()
    count = 0
    for msg in it:
        print("   replay:", msg)
        count += 1
        if count >= m:
            break

# --- 5) If the above looks good, wire a super-simple sink (print) ---


def print_sink(msg):
    print("[sink]", msg)


def source_apply():
    for msg in replay.run():
        if msg is None:
            continue
        yield msg


def run_network_with_print_sink():
    print("[network] wiring source -> print_sink")
    # g = network([(source_apply, print_sink), (source_apply, kv_live_sink)])
    g = network([(source_apply, kv_live_sink)])
    g.run_network()


if __name__ == "__main__":
    ok = preview_csv(CSV_PATH)
    if ok:
        smoke_test_transform_only()
        smoke_test_replay_only(m=5)
        # Uncomment to try the network path with a trivial sink:
        run_network_with_print_sink()
    print("[done]")
