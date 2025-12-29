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
    """Format numbers to nd decimals, blank if None or invalid."""
    if x is None:
        return ""
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return ""


def _colored_symbol(ok: bool, *, invert: bool = False) -> str:
    """
    Returns a *colored* single-character symbol:
      - blue ✓
      - red  x
    invert=True flips meaning (used for anomaly):
      anomaly=True  => bad => red x
      anomaly=False => good => blue ✓
    """
    # For anomaly: ok=False means anomaly; ok=True means NO anomaly
    val = (not ok) if invert else ok
    return f"{BLUE}{CHECK_CHAR}{RESET}" if val else f"{RED}{CROSS_CHAR}{RESET}"


def _cell_mark(flag: bool | None, *, width: int, invert: bool = False) -> str:
    """
    Build a fixed-width column centered around a colored ✓ or x.
    If flag is None, return blank cell of correct width.
    All spacing occurs *outside* ANSI codes to preserve table alignment.
    """
    if flag is None:
        return " " * width

    sym = _colored_symbol(flag, invert=invert)
    # center the visible symbol (length considered as 1)
    left = (width - 1) // 2
    right = width - 1 - left
    return (" " * left) + sym + (" " * right)


def temp_live_sink(msg: Mapping[str, Any]) -> None:
    """
    Prints a table row:
      date | pred_low | actual | pred_high | fits | anomaly

    - Numbers to 1 decimal place
    - fits:    ✓ blue if fits,    x red if not
    - anomaly: ✓ blue if NO anomaly, x red if anomaly=True

    Expects:
      - date (string)
      - tmax_f / temp_F / temp (numeric)
      - pred_low, pred_high (numeric)
      - fits (bool or None)
      - anomaly (bool)
    """

    # Print header once
    if not getattr(temp_live_sink, "_header_printed", False):
        header = " ".join(name.ljust(width) for name, width in COLS)
        print(header)
        print("-" * sum(width for _, width in COLS))
        temp_live_sink._header_printed = True

    # Extract values with fallback
    date = str(msg.get("date", ""))
    temp = msg.get("tmax_f", msg.get("temp_F", msg.get("temp")))
    pred_lo = msg.get("pred_low")
    pred_hi = msg.get("pred_high")
    fits = msg.get("fits")         # may be True/False/None
    anomaly = msg.get("anomaly")      # bool or None

    # Construct fixed-width cells
    cells = [
        date.ljust(12),                    # date
        _fmt_num(pred_lo, 1).rjust(10),    # pred_low
        _fmt_num(temp,    1).rjust(7),     # actual
        _fmt_num(pred_hi, 1).rjust(10),    # pred_high
        _cell_mark(fits,    width=6),      # fits: ✓ if fits, x otherwise
        # ✓ if NO anomaly, x if anomalous
        _cell_mark(anomaly, width=8, invert=True),
    ]

    print(" ".join(cells))
