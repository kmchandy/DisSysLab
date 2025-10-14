# lessons/ch02_sources/clean_openmeteo.py
import csv
import sys
from pathlib import Path


def find_data_header_index(rows):
    """
    Find the index of the row that starts the real data header.
    Accepts 'time' with any spaces/case and ignores blank lines.
    """
    for i, r in enumerate(rows):
        if not r:
            continue
        first = (r[0] or "").strip().lower()
        if first == "time":
            return i
    return None


def main():
    # Resolve script folder and default input/output
    here = Path(__file__).resolve().parent
    default_in = here / "open-meteo-37.79N122.41W18m.csv"
    out_path = here / "open-meteo_clean.csv"

    # Allow optional CLI arg for the input file
    raw_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_in

    if not raw_path.exists():
        print(f"[error] Input CSV not found: {raw_path}")
        print(f"        (Tip: put the file next to this script or pass a path: "
              f"python -m lessons.ch02_sources.clean_openmeteo /full/path/to.csv)")
        sys.exit(1)

    print(f"[info] Reading: {raw_path}")
    rows = []
    with raw_path.open(newline="", encoding="utf-8", errors="ignore") as fin:
        reader = csv.reader(fin)
        for r in reader:
            # Normalize: strip whitespace from cells
            rows.append([c.strip() for c in r])

    idx = find_data_header_index(rows)
    if idx is None:
        print("[error] Could not find a 'time' header row in the file.")
        # Print a few first non-empty rows to help debug
        shown = 0
        for r in rows:
            if r and any(cell for cell in r):
                print("  row:", r)
                shown += 1
                if shown >= 5:
                    break
        sys.exit(2)

    # Write a clean CSV with just the data table
    header = rows[idx]
    data_rows = [r for r in rows[idx + 1:] if r and len(r) >= 2]

    # Optional: unify the temperature header text
    # Keep original header if you prefer.
    if header[0].strip().lower() == "time":
        # e.g., ['time', 'temperature_2m_max (°F)']
        header = ["time", header[1]]

    with out_path.open("w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout)
        writer.writerow(header)
        for r in data_rows:
            writer.writerow([r[0], r[1]])

    print(f"[ok] Wrote clean CSV: {out_path}  (rows: {len(data_rows)})")


if __name__ == "__main__":
    main()
