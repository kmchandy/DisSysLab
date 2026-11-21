"""Show one run of the cake room: the board, note by note, and the verdict.

    python show.py                     # the last run in report.jsonl
    python show.py some/report.jsonl   # the last run in another file

Each note shows who wrote it, whom they suspected, and two things the
board alone does not make obvious:

- a **change of mind**: the writer suspects someone other than in their
  last note;
- a **stale read**: other notes landed on the board while the writer was
  thinking, so the note was written without them. The board records, on
  every note, how many notes its writer had read ("read").
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent


def last_run(path: Path) -> dict:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        sys.exit(f"{path} is empty: run the office first (dsl run .)")
    return json.loads(lines[-1])


def show(run: dict) -> str:
    board = run["board"]
    out = [f"The board: {len(board)} notes, in the order they arrived.", ""]
    last: dict[str, str] = {}
    stale = 0
    for note in board:
        by, suspect = note["by"], note["suspect"]
        head = f"{note['n']:>2}. {by:<6} suspects {suspect}"
        marks = []
        if by in last and last[by] != suspect:
            marks.append(f"{by} changes: {last[by]} -> {suspect}")
        if "read" in note and note["read"] < note["n"] - 1:
            missed = list(range(note["read"] + 1, note["n"]))
            stale += 1
            which = f"note {missed[0]}" if len(missed) == 1 else f"notes {missed[0]}-{missed[-1]}"
            marks.append(f"stale read: {which} landed while {by} was thinking")
        last[by] = suspect
        out.append(head)
        out += textwrap.wrap(note["note"], 72, initial_indent="      ", subsequent_indent="      ")
        out += [f"      [{m}]" for m in marks]
        out.append("")
    out.append("Where each detective ended: " +
               ", ".join(f"{by} {s}" for by, s in last.items()))
    if board and "read" in board[0]:
        out.append(f"Stale reads: {stale}")
    else:
        out.append("Stale reads: not recorded in this run")
    out += ["", f"VERDICT: {run.get('culprit')}",
            *textwrap.wrap(run.get("reason", ""), 72, initial_indent="  ", subsequent_indent="  ")]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    path = Path(argv[0]) if argv else HERE / "report.jsonl"
    if not path.exists():
        sys.exit(f"no {path}: run the office first (dsl run .)")
    print(show(last_run(path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
