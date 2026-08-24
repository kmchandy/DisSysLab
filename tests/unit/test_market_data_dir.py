"""Where market data lives — one answer, agreed by both sides.

`mac_speed_suite/office.md` used to name its data directory as
`'../../../../sp100_data'`, and the downloader resolved the same string
relative to itself. The two agreed by arithmetic: four levels above the
office folder is the repository root *in a git clone*, and the
filesystem root after `dsl init`. So the documented way to get your own
copy of a shipped office produced a backtester that could neither read
data nor download any, and the only working path was a clone.

Now both sides ask `dissyslab.market_data`. These tests are mostly
about that agreement.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from dissyslab.market_data import (
    ENV_VAR,
    describe,
    legacy_dirs,
    market_data_dir,
    search_dirs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DOWNLOADER = (
    REPO_ROOT / "dissyslab" / "gallery" / "apps" / "mac_speed_suite"
    / "download_stock_history_from_yf.py"
)
BACKTEST_OFFICE = REPO_ROOT / "dissyslab" / "gallery" / "apps" / "mac_speed_suite"


def _load_downloader():
    spec = importlib.util.spec_from_file_location("_dl", DOWNLOADER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_default_does_not_depend_on_where_you_are(tmp_path, monkeypatch):
    """The whole bug in one assertion. `dsl init` puts an office in an
    arbitrary folder, and the data has to still be findable."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    monkeypatch.chdir(tmp_path)
    here = market_data_dir()
    (tmp_path / "somewhere" / "deep" / "down").mkdir(parents=True)
    monkeypatch.chdir(tmp_path / "somewhere" / "deep" / "down")
    assert market_data_dir() == here


def test_the_env_var_wins(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "elsewhere"))
    assert market_data_dir() == tmp_path / "elsewhere"


def test_an_existing_clone_keeps_working(tmp_path, monkeypatch):
    """An older checkout has ten years of prices in <repo>/sp100_data.
    Moving the default must not make anyone download them again."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    repo = tmp_path / "DisSysLab"
    (repo / "sp100_data").mkdir(parents=True)
    office = repo / "dissyslab" / "gallery" / "apps" / "mac_speed_suite"
    office.mkdir(parents=True)

    assert repo / "sp100_data" in legacy_dirs(office)
    assert repo / "sp100_data" in search_dirs(start=office)


def test_an_explicit_directory_is_honoured_first(tmp_path, monkeypatch):
    """Someone who said where their data is meant it."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    dirs = search_dirs(explicit="/my/prices", start=tmp_path)
    assert dirs[0] == Path("/my/prices")


def test_a_missing_file_names_every_directory_searched(tmp_path, monkeypatch):
    """A user who has the file in a directory we did not search would
    otherwise read that they do not have it."""
    from dissyslab.components.sources.csv_stock_history_source import (
        CSVStockHistorySource,
    )

    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    monkeypatch.chdir(tmp_path)

    source = CSVStockHistorySource(tickers=["NVDA"])
    try:
        source._load_ticker("NVDA")
    except FileNotFoundError as exc:
        message = str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected FileNotFoundError")

    assert "NVDA_1year.csv" in message
    assert str(market_data_dir()) in message
    assert "ships market data" in message  # says why, not just what


def test_the_source_reads_the_default_directory(tmp_path, monkeypatch):
    from dissyslab.components.sources.csv_stock_history_source import (
        CSVStockHistorySource,
    )

    monkeypatch.setenv(ENV_VAR, str(tmp_path / "prices"))
    (tmp_path / "prices").mkdir()
    (tmp_path / "prices" / "NVDA_1year.csv").write_text(
        "Date,Open,High,Low,Close,Volume\n2026-01-02,1,2,0.5,1.5,100\n",
        encoding="utf-8",
    )
    rows = CSVStockHistorySource(tickers=["NVDA"])._load_ticker("NVDA")
    assert rows[0]["close"] == 1.5


# ── the two sides must agree ──────────────────────────────────────────


def test_the_downloader_writes_where_the_office_reads(tmp_path, monkeypatch):
    """The bug was that these two agreed only by arithmetic."""
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "prices"))
    dl = _load_downloader()
    assert Path(dl.data_dir(None)) == market_data_dir()


def test_the_downloaders_standalone_fallback_agrees_too(tmp_path, monkeypatch):
    """The script is run directly, sometimes where `dissyslab` is not
    importable, so it repeats the rule. Two expressions of one rule is
    exactly the shape that drifts, so pin them together."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    monkeypatch.setattr(os.path, "expanduser",
                        lambda p: p.replace("~", str(tmp_path / "home"), 1))

    dl = _load_downloader()
    monkeypatch.setitem(
        __import__("sys").modules, "dissyslab.market_data", None
    )  # force the ImportError branch
    assert Path(dl.data_dir(None)) == market_data_dir()


def test_the_shipped_offices_name_no_data_directory():
    """An office that names a directory is an office that breaks when
    it is copied somewhere else."""
    offending = []
    for office_md in (REPO_ROOT / "dissyslab" / "gallery").glob("*/*/office.md"):
        text = office_md.read_text(encoding="utf-8")
        if "csv_stock_history(" in text and "directory=" in text:
            offending.append(str(office_md.relative_to(REPO_ROOT)))
    assert not offending, (
        f"{offending} pin their market data to a path. Leave `directory=` "
        "out and the office reads the one directory every office shares, "
        "before and after `dsl init`."
    )


def test_describe_lists_directories_for_a_human():
    assert describe([Path("/a"), Path("/b")]) == "/a, /b"


def test_the_explainer_looks_where_the_downloader_writes(tmp_path, monkeypatch):
    """The third copy of the rule, and the one that hid the bug.

    `explain_strategy.py` had its own `_HERE/../../../../sp100_data`
    and a graceful fallback to synthetic prices. After `dsl init` it
    found nothing, invented a price series, produced a workbook that
    looked entirely right, and said so only on the Read me sheet. A
    graceful fallback is very good at concealing the path everyone
    actually takes.
    """
    spec = importlib.util.spec_from_file_location(
        "_explain", BACKTEST_OFFICE / "explain_strategy.py"
    )
    explain = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(explain)

    monkeypatch.setenv(ENV_VAR, str(tmp_path / "prices"))
    (tmp_path / "prices").mkdir()
    assert str(market_data_dir()) in explain._data_dirs(None)

    csv = tmp_path / "prices" / "NVDA_10_year.csv"
    csv.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        + "".join(
            f"2026-01-{d:02d},10,11,9,10.{d},100\n" for d in range(1, 29)
        ),
        encoding="utf-8",
    )
    _bars, provenance = explain.load_bars("NVDA")
    assert "SYNTHETIC" not in provenance, (
        "fell back to invented prices with a real CSV in the standard "
        "directory — the exact failure this test exists for"
    )
    assert str(csv) in provenance


def test_the_explainer_says_where_it_looked_when_it_invents_prices(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "_explain2", BACKTEST_OFFICE / "explain_strategy.py"
    )
    explain = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(explain)

    monkeypatch.setenv(ENV_VAR, str(tmp_path / "empty"))
    # A source checkout has its own sp100_data above the office folder,
    # and the legacy walk-up would find it. That fallback is wanted in
    # real use and only in the way here.
    import dissyslab.market_data as md
    monkeypatch.setattr(md, "legacy_dirs", lambda start=None: [])

    _bars, provenance = explain.load_bars("NVDA")
    assert "SYNTHETIC" in provenance
    assert str(tmp_path / "empty") in provenance
