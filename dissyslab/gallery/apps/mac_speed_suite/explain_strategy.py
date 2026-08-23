#!/usr/bin/env python3
"""Show a strategy's working, bar by bar, in Excel.

Why this exists
---------------
`report.html` answers "how did it do". This answers a different
question: **is this the strategy I meant?** A tester who thinks about
markets, not about Python, cannot check that from a signal column. They
need the intermediate quantities -- the channel bounds, the two moving
averages -- and the rule that turned them into a position.

Each derived quantity appears twice: the value the Python produced, and
the same quantity as a live Excel formula over the price cells. The
formula is there to be *read*, and edited. `=MAX(D7:D9)` in row 10 says
"the three rows above this one, not this one" without anyone explaining
the boundary convention, and if that is not your rule you can change it
and watch the signal column move.

The two columns do not verify each other. Both express one author's
understanding of the rule, so a misreading appears in both. What they
catch is an inconsistency between the two expressions -- and what the
formula gives you is a specification you can read.

Usage
-----
    python3 explain_strategy.py --strategy donchian --variant 20
    python3 explain_strategy.py --strategy mac --variant med --ticker NVDA
    python3 explain_strategy.py --strategy donchian --strategy mac --rows 25
    python3 explain_strategy.py --strategy donchian --bars 300:340

With no --bars, a window is chosen that contains a signal change:
twenty rows in which nothing happens demonstrate nothing.

With no price data on disk, a small synthetic series is used and the
sheet says so.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "roles"))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", ".."))

from donchian_signal import (                                    # noqa: E402
    DONCHIAN_VARIANTS, _donchian_compute_variant_signal,
)
from mac_signal import (                                         # noqa: E402
    MAC_VARIANTS, _ewma, _mac_compute_variant_signal,
)


# ── loading bars ───────────────────────────────────────────────────────


DEFAULT_DATA_DIR = os.path.join(_HERE, "..", "..", "..", "..", "sp100_data")


def load_bars(ticker: str, directory: str) -> Tuple[List[dict], str]:
    """Real bars if the CSV is there, otherwise a synthetic series.

    Returns ``(bars, provenance)``; the provenance string goes on the
    Read me sheet so nobody mistakes made-up prices for real ones.
    """
    path = os.path.join(directory, f"{ticker}_10_year.csv")
    if os.path.isfile(path):
        from dissyslab.components.sources.csv_stock_history_source import (
            CsvStockHistorySource,
        )
        src = CsvStockHistorySource(
            tickers=[ticker], directory=directory,
            filename_pattern="{ticker}_10_year.csv",
        )
        return src._load_ticker(ticker), f"{ticker}, from {os.path.relpath(path, _HERE)}"

    return _synthetic_bars(), (
        "SYNTHETIC PRICES -- no CSV found. These are made up, so the "
        "numbers mean nothing; the formulas and the rule are still real. "
        "Run download_stock_history_from_yf.py for real prices."
    )


def _synthetic_bars(n: int = 120) -> List[dict]:
    """A deterministic sawtooth: rises for 15 bars, falls for 10.

    Chosen so every strategy produces several signal changes in a short
    window, which is what makes a trace worth reading.
    """
    bars, price = [], 100.0
    up, run = True, 0
    for i in range(n):
        step = 1.4 if up else -2.0
        price += step
        run += 1
        if (up and run == 15) or (not up and run == 10):
            up, run = not up, 0
        bars.append({
            "date": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}",
            "open": round(price - step, 2),
            "high": round(price + 0.8, 2),
            "low": round(price - 0.8, 2),
            "close": round(price, 2),
        })
    return bars


# ── traces ─────────────────────────────────────────────────────────────
#
# A trace recomputes the intermediates and then **asserts that they
# imply the signal the real strategy module produced**. In both
# strategies the signal is a function of the intermediates alone, so
# agreement on the signal is agreement on the intermediates. If this
# file ever drifts from the strategy it explains, the export fails
# rather than quietly showing the wrong working.


class Trace:
    def __init__(self, name: str, warmup: int, columns: List[str],
                 rows: List[dict], rule: str, notes: List[str]):
        # Filled in by _trace_sheet once the table length is known.
        self.alpha_cells: Dict[str, str] = {}
        self.name = name          # e.g. "donchian_20"
        self.warmup = warmup      # rows of context the formulas need
        self.columns = columns
        self.rows = rows
        self.rule = rule
        self.notes = notes


def donchian_trace(bars: List[dict], variant: str) -> Trace:
    n = DONCHIAN_VARIANTS[variant]
    truth = _donchian_compute_variant_signal(bars, n)

    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    rows, pos = [], 0.0
    for t, b in enumerate(bars):
        upper = max(highs[t - n:t]) if t >= n else None
        lower = min(lows[t - n:t]) if t >= n else None
        why = "window not full -- flat"
        if t >= n:
            if b["close"] > upper:
                pos, why = 1.0, f"close {b['close']} > upper {upper} -- go long"
            elif b["close"] < lower:
                pos, why = -1.0, f"close {b['close']} < lower {lower} -- go short"
            else:
                why = "no breakout -- hold"
        rows.append({
            "t": t, "date": b["date"], "high": b["high"], "low": b["low"],
            "close": b["close"], "upper": upper, "lower": lower,
            "signal": pos, "why": why,
        })

    _agree(rows, truth, f"donchian_{variant}")
    return Trace(
        name=f"donchian_{variant}", warmup=n,
        columns=["t", "date", "high", "low", "close", "upper", "lower",
                 "signal", "why"],
        rows=rows,
        rule=(f"Donchian({n}). The upper channel is the highest high of "
              f"the {n} bars BEFORE today; the lower channel is the "
              f"lowest low of those same bars. Today's close above the "
              f"upper channel goes long; below the lower channel goes "
              f"short; otherwise hold whatever you held. Flat until the "
              f"first breakout."),
        notes=[f"The first {n} rows are context. The formulas in the "
               f"first visible row read them, so they are shown."],
    )


def mac_trace(bars: List[dict], variant: str) -> Trace:
    fast_span, slow_span = MAC_VARIANTS[variant]
    truth = _mac_compute_variant_signal(bars, (fast_span, slow_span))

    closes = [b["close"] for b in bars]
    fast, slow = _ewma(closes, fast_span), _ewma(closes, slow_span)
    rows = []
    for t, b in enumerate(bars):
        sig = 1.0 if fast[t] > slow[t] else -1.0
        if t == 0:
            why = "seeded: both averages equal the first close, so not above -- short"
        elif fast[t] > slow[t]:
            why = f"fast {fast[t]:.4f} > slow {slow[t]:.4f} -- long"
        else:
            why = f"fast {fast[t]:.4f} <= slow {slow[t]:.4f} -- short"
        rows.append({
            "t": t, "date": b["date"], "close": b["close"],
            "fast": fast[t], "slow": slow[t], "signal": sig, "why": why,
        })

    _agree(rows, truth, f"mac_{variant}")
    af, asl = 2.0 / (fast_span + 1), 2.0 / (slow_span + 1)
    return Trace(
        name=f"mac_{variant}", warmup=0,
        columns=["t", "date", "close", "fast", "slow", "signal", "why"],
        rows=rows,
        rule=(f"Exponential moving averages of the close at spans "
              f"{fast_span} and {slow_span} (alpha = 2/(span+1), so "
              f"{af:.4f} and {asl:.4f}). Both are seeded with the first "
              f"close. Long while the faster is above the slower, short "
              f"otherwise -- a tie counts as short."),
        notes=["The averages depend on every earlier bar, so the first "
               "visible row is seeded from the full run rather than "
               "recomputed. Rows below it are the recurrence, each "
               "reading the row above.",
               "A tie goes short. On a flat price series both averages "
               "are equal for ever, so the signal is short for ever. "
               "That follows from the rule as written; it may not be "
               "what was intended."],
    )


def _agree(rows: List[dict], truth: List[float], label: str) -> None:
    mine = [r["signal"] for r in rows]
    if mine != list(truth):
        bad = next(i for i, (a, b) in enumerate(zip(mine, truth)) if a != b)
        raise SystemExit(
            f"{label}: this explainer disagrees with the strategy at bar "
            f"{bad} (explainer {mine[bad]}, strategy {truth[bad]}). The "
            f"working shown here would be wrong, so nothing was written. "
            f"Fix explain_strategy.py to match the role."
        )


TRACERS: Dict[str, Tuple[Callable, Dict[str, Any]]] = {
    "donchian": (donchian_trace, DONCHIAN_VARIANTS),
    "mac": (mac_trace, MAC_VARIANTS),
}


# ── choosing the window ────────────────────────────────────────────────


def pick_window(trace: Trace, rows: int) -> Tuple[int, int]:
    """A window containing a signal change, or the last `rows` bars.

    Twenty bars in which nothing happens prove nothing, so the default
    centres on the first change after warmup.
    """
    sig = [r["signal"] for r in trace.rows]
    change = next(
        (i for i in range(trace.warmup + 1, len(sig)) if sig[i] != sig[i - 1]),
        None,
    )
    if change is None:
        return max(0, len(sig) - rows), len(sig)
    start = max(0, change - rows // 3)
    return start, min(len(sig), start + rows)


# ── writing the workbook ───────────────────────────────────────────────


HEADER_FILL = "DDEBF7"
FORMULA_FILL = "FFF2CC"
CONTEXT_FILL = "F2F2F2"


def write_workbook(traces: List[Trace], windows: List[Tuple[int, int]],
                   provenance: str, out_path: str) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = openpyxl.Workbook()
    _read_me(wb.active, traces, provenance)
    for tr, (lo, hi) in zip(traces, windows):
        _trace_sheet(wb.create_sheet(tr.name[:31]), tr, lo, hi)
    wb.save(out_path)


def _read_me(ws, traces: List[Trace], provenance: str) -> None:
    from openpyxl.styles import Alignment, Font

    ws.title = "Read me"
    lines: List[Tuple[str, bool]] = [
        ("What this is", True),
        ("One row per trading day, showing every quantity the strategy "
         "computed and the rule that turned them into a position.", False),
        ("", False),
        ("Shaded columns are live Excel formulas, not numbers. Click one "
         "and read the formula bar: it is the rule, in a form you can "
         "check and change. Change a price and the shaded columns "
         "recompute.", False),
        ("", False),
        ("The unshaded value columns are what the Python produced. They "
         "do not verify the formulas -- both say the same author's "
         "understanding of the rule. If they disagree, one of the two "
         "has a slip and the match column says so.", False),
        ("", False),
        ("Prices", True),
        (provenance, False),
        ("", False),
    ]
    for tr in traces:
        lines.append((f"Sheet: {tr.name}", True))
        lines.append((tr.rule, False))
        for note in tr.notes:
            lines.append((f"  - {note}", False))
        lines.append(("", False))

    for i, (text, bold) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=text)
        c.font = Font(name="Arial", bold=bold, size=12 if bold else 11)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 100


def _trace_sheet(ws, tr: Trace, lo: int, hi: int) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill

    first = max(0, lo - tr.warmup)          # context the formulas need
    shown = tr.rows[first:hi]

    headers = _headers(tr)
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(name="Arial", bold=True)
        c.fill = PatternFill("solid", fgColor=HEADER_FILL)
        c.alignment = Alignment(wrap_text=True, vertical="top")

    col = {name: chr(ord("A") + i) for i, name in enumerate(headers)}
    anchor = len(shown) + 3
    tr.alpha_cells = {"fast": f"$B${anchor}", "slow": f"$B${anchor + 1}"}
    for i, r in enumerate(shown):
        excel_row = i + 2
        ws.append(_row_values(tr, r, shown, i, excel_row, col))

    _style(ws, tr, shown, lo, first, col, headers)
    ws.freeze_panes = "A2"


def _headers(tr: Trace) -> List[str]:
    out: List[str] = []
    for name in tr.columns:
        out.append(name)
        if name in _DERIVED[tr.name.split("_")[0]]:
            out.append(f"{name} (excel)")
            out.append("match")
    return out


_DERIVED = {"donchian": ("upper", "lower"), "mac": ("fast", "slow")}


def _row_values(tr: Trace, r: dict, shown: List[dict], i: int,
                excel_row: int, col: Dict[str, str]) -> List[Any]:
    kind = tr.name.split("_")[0]
    out: List[Any] = []
    for name in tr.columns:
        out.append(r.get(name))
        if name not in _DERIVED[kind]:
            continue
        formula = _formula(tr, kind, name, r, i, excel_row, col)
        out.append(formula)
        vcol, fcol = col[name], col[f"{name} (excel)"]
        out.append(
            f'=IF({vcol}{excel_row}="","",'
            f'IF(ROUND({vcol}{excel_row},6)=ROUND({fcol}{excel_row},6),'
            f'"ok","DIFFERS"))'
        )
    return out


def _formula(tr: Trace, kind: str, name: str, r: dict, i: int,
             excel_row: int, col: Dict[str, str]) -> Optional[str]:
    if kind == "donchian":
        if r[name] is None or i < tr.warmup:
            return None
        src = col["high"] if name == "upper" else col["low"]
        fn = "MAX" if name == "upper" else "MIN"
        return (f"={fn}({src}{excel_row - tr.warmup}:{src}{excel_row - 1})")

    # mac: the recurrence, seeded on the first visible row because the
    # average depends on every earlier bar.
    if i == 0:
        return r[name]
    alpha_cell = tr.alpha_cells[name]
    return (f"={alpha_cell}*{col['close']}{excel_row}"
            f"+(1-{alpha_cell})*{col[name + ' (excel)']}{excel_row - 1}")


def _style(ws, tr: Trace, shown: List[dict], lo: int, first: int,
           col: Dict[str, str], headers: List[str]) -> None:
    from openpyxl.styles import Font, PatternFill

    formula_cols = [c for h, c in col.items() if h.endswith("(excel)")]
    for i in range(len(shown)):
        row = i + 2
        for c in ws[row]:
            c.font = Font(name="Arial")
        for letter in formula_cols:
            ws[f"{letter}{row}"].fill = PatternFill("solid", fgColor=FORMULA_FILL)
        if first + i < lo:                      # context rows
            for c in ws[row]:
                if c.column_letter not in formula_cols:
                    c.fill = PatternFill("solid", fgColor=CONTEXT_FILL)

    if tr.name.startswith("mac"):
        # Below the table, not beside it -- the header row is occupied,
        # and writing into it silently replaced the 'why' heading.
        fast_span, slow_span = MAC_VARIANTS[tr.name.split("_", 1)[1]]
        anchor = len(shown) + 3
        ws[f"A{anchor}"] = "alpha fast = 2/(span+1)"
        ws[f"A{anchor + 1}"] = "alpha slow = 2/(span+1)"
        ws[f"B{anchor}"] = 2.0 / (fast_span + 1)
        ws[f"B{anchor + 1}"] = 2.0 / (slow_span + 1)
        for r in (anchor, anchor + 1):
            ws[f"A{r}"].font = Font(name="Arial", bold=True)
            ws[f"B{r}"].font = Font(name="Arial")
            ws[f"B{r}"].number_format = "0.000000"

    widths = {"t": 5, "date": 11, "why": 46}
    for h, letter in col.items():
        ws.column_dimensions[letter].width = widths.get(h, 13)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if isinstance(c.value, float):
                c.number_format = "0.0000"


# ── entry point ────────────────────────────────────────────────────────


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--strategy", action="append", default=None,
                   choices=sorted(TRACERS), help="repeatable")
    p.add_argument("--variant", action="append", default=None,
                   help="repeatable; defaults to the first of each strategy")
    p.add_argument("--ticker", default="AMD")
    p.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    p.add_argument("--bars", default=None, metavar="LO:HI",
                   help="bar range; default is a window containing a change")
    p.add_argument("--rows", type=int, default=30)
    p.add_argument("--out", default="strategy_working.xlsx")
    a = p.parse_args(argv)

    strategies = a.strategy or ["donchian"]
    bars, provenance = load_bars(a.ticker, a.data_dir)

    traces, windows = [], []
    for i, s in enumerate(strategies):
        tracer, variants = TRACERS[s]
        variant = (a.variant[i] if a.variant and i < len(a.variant)
                   else sorted(variants)[0])
        if variant not in variants:
            p.error(f"{s}: unknown variant {variant!r}; "
                    f"choose from {sorted(variants)}")
        tr = tracer(bars, variant)
        traces.append(tr)
        if a.bars:
            lo, hi = (int(x) for x in a.bars.split(":"))
        else:
            lo, hi = pick_window(tr, a.rows)
        windows.append((lo, hi))

    write_workbook(traces, windows, provenance, a.out)
    print(f"wrote {a.out}")
    for tr, (lo, hi) in zip(traces, windows):
        print(f"  {tr.name}: bars {lo}-{hi - 1}"
              f"{f' (+{tr.warmup} rows of context)' if tr.warmup else ''}")
    print("Formula cells have no cached value until a spreadsheet "
          "application opens the file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
