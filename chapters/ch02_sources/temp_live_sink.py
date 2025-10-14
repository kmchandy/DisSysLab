# lessons/ch02_sources/temp_live_sink.py
from typing import Mapping, Any

# ANSI colors
BLUE = "\x1b[94m"   # bright blue
RED = "\x1b[91m"   # bright red
RESET = "\x1b[0m"

CHECK_CHAR = "✓"
CROSS_CHAR = "x"

# Column order & widths:
# date | pred_low | actual | pred_high | fits | anomaly
COLS = [
    ("date",      12),
    ("pred_low",  10),
    ("actual",     7),
    ("pred_high", 10),
    ("fits",       6),
    ("anomaly",    8),
]


def _fmt_num(x, nd=1):
    if x is None:
        return ""
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return ""


def _colored_symbol(ok: bool, invert: bool = False) -> str:
    """
    Returns a colored single-character mark:
      ok=True  -> blue ✓
      ok=False -> red  x
    invert=True flips the meaning (used for anomaly: True=bad)
    """
    val = not ok if invert else ok
    return f"{BLUE}{CHECK_CHAR}{RESET}" if val else f"{RED}{CROSS_CHAR}{RESET}"


def _cell_mark(ok: bool | None, width: int, invert: bool = False) -> str:
    """
    Build a fixed-width cell with a centered colored mark.
    Spaces are added OUTSIDE the color codes so ANSI doesn't break alignment.
    """
    if ok is None:
        return " " * width
    sym = _colored_symbol(ok, invert=invert)  # colored '✓' or 'x'
    left = (width - 1) // 2
    right = width - 1 - left
    return (" " * left) + sym + (" " * right)


def temp_live_sink(msg: Mapping[str, Any]) -> None:
    """
    Prints a table row:
      date | pred_low | actual | pred_high | fits | anomaly
    - Numbers to 1 decimal place
    - fits: blue ✓ if fits, red x if not
    - anomaly: blue ✓ if NO anomaly, red x if anomalous
    Expects in `msg`:
      - date (str)
      - tmax_f / temp_F / temp (numeric actual)
      - pred_low, pred_high (numeric)
      - fits (bool|None)         -> was x_t within band predicted at t-1?
      - anomaly (bool)           -> True means anomalous (|x-μ| > k_anom·σ)
    """
    # Header once
    if not getattr(temp_live_sink, "_header_printed", False):
        header = " ".join(name.ljust(width) for name, width in COLS)
        print(header)
        print("-" * sum(width for _, width in COLS))
        temp_live_sink._header_printed = True

    # Extract values with gentle fallbacks
    date = str(msg.get("date", ""))
    temp = msg.get("tmax_f", msg.get("temp_F", msg.get("temp")))
    pred_lo = msg.get("pred_low")
    pred_hi = msg.get("pred_high")
    fits = msg.get("fits")           # bool or None
    anomaly = msg.get("anomaly")     # bool

    # Build cells with fixed widths
    cells = [
        date.ljust(12),
        _fmt_num(pred_lo, 1).rjust(10),
        _fmt_num(temp, 1).rjust(7),
        _fmt_num(pred_hi, 1).rjust(10),
        _cell_mark(fits,    width=6, invert=False),   # ✓ if fits, x otherwise
        # ✓ if NO anomaly, x if anomalous
        _cell_mark(anomaly, width=8, invert=True),
    ]
    print(" ".join(cells))
