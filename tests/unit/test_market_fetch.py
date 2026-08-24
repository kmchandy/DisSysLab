"""Downloading price history as something an assistant can run.

It used to be a script inside one gallery app, run from a terminal
after a `cd` into that folder — so a tester's path to a backtest went
through a git clone and two shell commands. A capability an assistant
cannot reach is a capability the user has to reach themselves.

The download stays a deliberate act: nothing here ships market data,
the vendor's terms do not permit it, and every user fetches their own.
What changed is that it is now something you *ask for*.

No network in these tests. `fetch` takes its downloader as an argument
precisely so the plumbing — filenames, destinations, skipping, the
agreement between fetch and read — can be tested without depending on
a vendor being up.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.market_fetch import (
    DEFAULT_PATTERN,
    FetchError,
    confirm_office_reads,
    fetch,
    office_basket,
)

HEADER = "Date,Open,High,Low,Close,Volume"


class _Frame:
    """The little of a DataFrame this code uses."""

    def __init__(self, rows):
        self.rows = rows
        self.columns = ["Open", "High", "Low", "Close", "Volume"]

    def __len__(self):
        return len(self.rows)

    def to_csv(self, path):
        Path(path).write_text(
            HEADER + "\n" + "".join(self.rows), encoding="utf-8"
        )


def _fake_download(calls=None):
    def download(ticker, years):
        if calls is not None:
            calls.append((ticker, years))
        return _Frame([
            f"2026-01-{d:02d},10,11,9,10.{d},100\n" for d in range(1, 29)
        ])
    return download


def test_it_writes_where_offices_read(tmp_path, monkeypatch):
    monkeypatch.setenv("DSL_MARKET_DATA", str(tmp_path / "prices"))
    results = fetch(["nvda"], years=10, download=_fake_download())
    assert results[0].ticker == "NVDA"
    assert results[0].path == tmp_path / "prices" / "NVDA_10_year.csv"
    assert results[0].path.is_file()


def test_the_default_filename_is_what_the_offices_ask_for(tmp_path):
    """`--years 10` has to produce `NVDA_10_year.csv`, because that is
    the name the shipped trading offices look for. Fetch and read agree
    by construction rather than by the user getting a filename right."""
    fetch(["NVDA"], years=10, dest=tmp_path, download=_fake_download())
    assert (tmp_path / "NVDA_10_year.csv").is_file()
    assert DEFAULT_PATTERN.format(ticker="NVDA", years=10) == "NVDA_10_year.csv"


def test_it_does_not_re_download_what_is_already_there(tmp_path):
    """Ten years of daily bars is slow, and a backtest that silently
    re-downloads is not reproducible."""
    calls = []
    fetch(["NVDA"], years=10, dest=tmp_path, download=_fake_download(calls))
    assert calls == [("NVDA", 10)]

    again = fetch(["NVDA"], years=10, dest=tmp_path,
                  download=_fake_download(calls))
    assert calls == [("NVDA", 10)]          # not called a second time
    assert again[0].skipped
    assert again[0].rows == 28              # reports what is on disk


def test_force_re_downloads(tmp_path):
    calls = []
    fetch(["NVDA"], years=10, dest=tmp_path, download=_fake_download(calls))
    fetch(["NVDA"], years=10, dest=tmp_path, force=True,
          download=_fake_download(calls))
    assert len(calls) == 2


def test_a_thing_that_is_not_a_ticker_is_refused(tmp_path):
    """The argument reaches a network call and a filename. Neither is a
    good place to find out it was a sentence."""
    with pytest.raises(FetchError) as exc:
        fetch(["../../etc/passwd"], dest=tmp_path, download=_fake_download())
    assert "not ticker symbols" in str(exc.value)


# ── reading the basket out of an office ───────────────────────────────


BACKTEST_OFFICE = """# Office: t

Sources: csv_stock_history(tickers=['AMD', 'NVDA'], filename_pattern='{ticker}_10_year.csv')
Sinks: console_printer

Agents:
Jay is a summarizer.

Connections:
csv_stock_history's destination is Jay.
Jay's out is console_printer.
"""


def test_the_basket_comes_from_the_office_itself(tmp_path):
    (tmp_path / "office.md").write_text(BACKTEST_OFFICE, encoding="utf-8")
    tickers, pattern, years = office_basket(tmp_path)
    assert tickers == ["AMD", "NVDA"]
    assert pattern == "{ticker}_10_year.csv"
    assert years == 10


def test_no_office_says_what_to_do_instead(tmp_path):
    with pytest.raises(FetchError) as exc:
        office_basket(tmp_path)
    assert "dsl fetch-prices NVDA AMD" in str(exc.value)


def test_an_office_that_reads_no_prices_says_so(tmp_path):
    (tmp_path / "office.md").write_text(
        "# Office: t\n\nSources: bbc_world\n", encoding="utf-8"
    )
    with pytest.raises(FetchError) as exc:
        office_basket(tmp_path)
    assert "no csv_stock_history" in str(exc.value)


# ── the fetch and the read must agree ─────────────────────────────────


def test_the_office_can_read_what_was_just_fetched(tmp_path, monkeypatch):
    """Fetching and reading are two pieces of code agreeing on a
    directory and a filename. Proving it here means the user finds out
    now, rather than from an office that runs and produces nothing."""
    office = tmp_path / "office"
    office.mkdir()
    (office / "office.md").write_text(BACKTEST_OFFICE, encoding="utf-8")
    dest = tmp_path / "prices"

    tickers, pattern, years = office_basket(office)
    fetch(tickers, years=years, pattern=pattern, dest=dest,
          download=_fake_download())

    assert confirm_office_reads(office, tickers, pattern, dest=dest) == []


def test_the_confirmation_looks_where_the_files_went(tmp_path, monkeypatch):
    """A --dest fetch confirmed against the default directory would
    report a failure that is only the check looking in the wrong
    place."""
    monkeypatch.setenv("DSL_MARKET_DATA", str(tmp_path / "somewhere-else"))
    (tmp_path / "somewhere-else").mkdir()
    office = tmp_path / "office"
    office.mkdir()
    (office / "office.md").write_text(BACKTEST_OFFICE, encoding="utf-8")
    dest = tmp_path / "prices"

    fetch(["AMD", "NVDA"], years=10, pattern="{ticker}_10_year.csv",
          dest=dest, download=_fake_download())

    assert confirm_office_reads(office, ["AMD", "NVDA"],
                                "{ticker}_10_year.csv", dest=dest) == []
    # and without dest it looks in the shared directory instead, which
    # is empty here
    import dissyslab.market_data as md
    monkeypatch.setattr(md, "legacy_dirs", lambda start=None: [])
    assert confirm_office_reads(office, ["AMD", "NVDA"],
                                "{ticker}_10_year.csv") != []


def test_a_missing_ticker_is_named_not_hidden(tmp_path, monkeypatch):
    # Isolate: the search deliberately also looks in the shared and
    # legacy directories, and on a real machine one of them may hold
    # the ticker this test wants to be missing.
    monkeypatch.setenv("DSL_MARKET_DATA", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    import dissyslab.market_data as md
    monkeypatch.setattr(md, "legacy_dirs", lambda start=None: [])

    office = tmp_path / "office"
    office.mkdir()
    (office / "office.md").write_text(BACKTEST_OFFICE, encoding="utf-8")
    dest = tmp_path / "prices"
    fetch(["AMD"], years=10, pattern="{ticker}_10_year.csv", dest=dest,
          download=_fake_download())

    problems = confirm_office_reads(office, ["AMD", "NVDA"],
                                    "{ticker}_10_year.csv", dest=dest)
    assert len(problems) == 1
    assert problems[0].startswith("NVDA")


# ── the subcommand exists and is documented ───────────────────────────


def test_fetch_prices_is_a_real_subcommand():
    """An assistant reads `dsl --help` to learn what this install can
    do; the skill's own instructions say to treat that list as the
    authority."""
    import subprocess
    import sys

    out = subprocess.run(
        [sys.executable, "-m", "dissyslab.cli", "--help"],
        capture_output=True, text=True,
    ).stdout
    assert "fetch-prices" in out
