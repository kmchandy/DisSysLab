"""Tests for office runtime context helpers (pure / offline)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

if importlib.util.find_spec("anthropic") is None:
    pytest.skip(
        "anthropic not installed — office submodule imports chain through it",
        allow_module_level=True,
    )


@pytest.fixture()
def wardrobe_office_dir(tmp_path: Path) -> Path:
    root = tmp_path / "wardrobe_demo"
    root.mkdir()
    (root / "office.md").write_text(
        "# Office: wardrobe_demo\n"
        'Sources: web_scraper(url="https://forecast.weather.gov/MapClick.php?lat=1&lon=2"),\n'
        "weatherapi(key=stub)\n"
    )
    return root


def test_forecast_digest_skips_when_weatherapi_marker_present(
    wardrobe_office_dir: Path,
):
    """When office declares ``weatherapi(``, NOAA scrape must not prefetch."""
    from dissyslab.office.office_run_context import forecast_digest_for_office_md

    txt = wardrobe_office_dir.joinpath("office.md").read_text()
    assert forecast_digest_for_office_md(txt) == ""


def test_wardrobe_inventory_digest_roundtrip(tmp_path: Path) -> None:
    from dissyslab.office.office_run_context import (
        build_office_run_context_env,
    )

    d = tmp_path / "wf"
    d.mkdir()
    (d / "office.md").write_text("# Office: x\nweatherapi()\n")
    inv = {"items": [{"id": "item_test", "category": "top", "description": "unit"}]}
    (d / "wardrobe_inventory.json").write_text(json.dumps(inv))
    ctx = build_office_run_context_env(d)
    blob = ctx.get("OFFICE_WARDROBE_INVENTORY_DIGEST", "")
    assert "`item_test`" in blob
    assert "**Canonical wardrobe" in blob
