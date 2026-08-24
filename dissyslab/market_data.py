"""Where a user's own market data lives.

The problem this fixes
----------------------
`mac_speed_suite/office.md` used to name its data directory as
``'../../../../sp100_data'`` -- four levels above the office folder,
which is the repository root in a source checkout and the *filesystem
root* after ``dsl init``. So the documented way to get your own copy of
a shipped office produced a backtester that could neither find data nor
download any, and the only working path was a git clone. That was an
accident of a relative path, not a decision.

The rule now
------------
One directory, the same for every office and every install:

* ``$DSL_MARKET_DATA`` if it is set, else
* ``~/.dissyslab/market_data``

An office does not say where its data is. It says which tickers it
wants, and the tickers are the part the user actually chooses.

Why one shared directory rather than one per office
---------------------------------------------------
Ten years of daily bars for a basket is a slow download and the same
file serves every office that mentions the ticker. Per-office copies
would mean re-downloading on every ``dsl init``, and would multiply the
one thing here that is *not* ours to redistribute.

Nothing in this repository ships market data. Yahoo's terms do not
permit it, so every user fetches their own -- which is also why the
fetching tool is in an extra you install deliberately rather than
something that arrives by accident.

Older layouts
-------------
Before this, data lived in ``<repo>/sp100_data`` in a clone. Those
directories are still searched, so an existing checkout keeps working
and nobody has to re-download to pick up this change. They are a
fallback, not the default: new downloads go to the standard place.
"""
from __future__ import annotations

import os
from pathlib import Path

#: Set this to keep market data somewhere else -- a shared drive, an
#: external disk, a directory your backup skips.
ENV_VAR = "DSL_MARKET_DATA"

_LEGACY_DIR_NAME = "sp100_data"


def market_data_dir() -> Path:
    """The directory downloads are written to and offices read from."""
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".dissyslab" / "market_data"


def legacy_dirs(start: Path | None = None) -> list[Path]:
    """Pre-existing ``sp100_data`` directories, nearest first.

    Walks up from ``start`` (the office folder, in a run) looking for
    the old layout. A clone that already has ten years of prices in it
    should not have to fetch them again because we moved the default.
    """
    start = Path(start or Path.cwd()).resolve()
    out: list[Path] = []
    for parent in [start, *start.parents]:
        candidate = parent / _LEGACY_DIR_NAME
        if candidate.is_dir():
            out.append(candidate)
    return out


def search_dirs(explicit: str | None = None, start: Path | None = None) -> list[Path]:
    """Every directory to look in, in order, for a ticker's CSV.

    An explicit ``directory=`` in ``office.md`` wins -- someone who
    said where their data is meant it. Otherwise the standard
    directory, then any older layout found by walking up.
    """
    dirs: list[Path] = []
    if explicit:
        dirs.append(Path(explicit).expanduser())
    dirs.append(market_data_dir())
    for legacy in legacy_dirs(start):
        if legacy not in dirs:
            dirs.append(legacy)
    return dirs


def describe(dirs: list[Path]) -> str:
    """A one-line 'looked in …' for an error message.

    Every "not found" here should say where it looked. The alternative
    is a user who has the file, in a directory we never searched,
    reading that they do not have it.
    """
    return ", ".join(str(d) for d in dirs)
