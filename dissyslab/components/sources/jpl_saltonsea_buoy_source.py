# dissyslab/components/sources/jpl_saltonsea_buoy_source.py

"""
JPLSaltonSeaBuoySource: fetches current wind (and other met) readings
from NASA/JPL's two moored buoys on the Salton Sea, CA.

Why this exists
================

Professor Sinclair (an environmental-monitoring collaborator, see
``salton_sea_dashboard`` gallery app) tracks hydrogen-sulfide (H2S)
odor near the Salton Sea via CARB monitoring sites, two of which
(Salton Sea Park, Torres-Martinez) report H2S and wind *speed* but not
wind *direction* -- which matters a lot for "is the smell blowing
toward people" questions. NASA/JPL runs two buoys moored directly on
the sea (SS1, SS1A) that report wind direction hourly, at
``https://saltonsea.jpl.nasa.gov/get_met_weather`` -- a plain,
publicly-readable HTML page, no key or login. This class scrapes that
page.

Confirmed live and working (fetched by hand, 2026-08-05): a small HTML
table, one row per parameter, one column per buoy (SS1, SS1A). Most
values are given as ``"min:avg:max"`` over the previous 30 minutes
(e.g. ``"5.8:6.7:7.4"``); a few rows are plain status strings (e.g.
``"STALE"``) or dates/times. This class parses the numeric
``min:avg:max`` rows into ``{"min":..., "avg":..., "max":...}`` and
leaves everything else as the raw string.

**Data caveat, in JPL's own words on that page:** "The data are raw
data and have not been quality checked. They are provided for
informational purposes only and should not be used for scientific
studies." This class passes that caveat straight through as
``"quality_note"`` on every message, deliberately, so it survives
however far downstream this data travels.

Message shape. Note everything is nested under one top-level key,
``"wind"`` -- deliberately, so this source can be merged with another
(e.g. ``SyntheticSaltonH2SSource``, nested under ``"h2s"``) by
DisSysLab's generic ``synchronizer`` role without any key collision;
see ``_backtester_core.py`` in ``mac_speed_suite`` for the same
nest-under-your-own-key convention and why it matters:
    {
        "wind": {
            "type":        "salton_sea_buoy_wind",
            "source_url":  "https://saltonsea.jpl.nasa.gov/get_met_weather",
            "quality_note": "raw data, not quality-checked -- informational only (JPL)",
            "buoys": {
                "SS1": {
                    "wind_speed_ms":      {"min": 5.8, "avg": 6.7, "max": 7.4},
                    "wind_direction_deg": {"min": 107.0, "avg": 111.0, "max": 115.0},
                    "air_temp_c":         {"min": 38.9, "avg": 39.2, "max": 39.4},
                    "relative_humidity_pct": {"min": 38.8, "avg": 42.2, "max": 44.7},
                    "pressure_mbar":      {"min": 1008.0, "avg": 1009.0, "max": 1009.0},
                    "last_update_utc":    "2026-07-29T05:12:21",
                    "download_state":     "STALE",
                },
                "SS1A": {...},
            },
            "errors":    {},
            "timestamp": "2026-08-05T09:31:00+00:00",
        }
    }

If the fetch or parse fails outright, this yields
``{"wind": {"type": "salton_sea_buoy_wind", "buoys": {}, "errors":
{"fetch": "..."}, "timestamp": ...}}`` instead of crashing -- same
per-source error isolation convention as
``WeatherSource``/``CSVStockHistorySource``.

Usage:
    from dissyslab.components.sources.jpl_saltonsea_buoy_source import (
        JPLSaltonSeaBuoySource,
    )
    from dissyslab.blocks import Source

    buoy = JPLSaltonSeaBuoySource()
    source = Source(fn=buoy.run, name="salton_wind")

Design notes:
    - One-shot generator (yields once, then stops), matching the
      on-demand "regenerate the dashboard when you run it" design for
      ``salton_sea_dashboard`` -- not a continuous poller. Pass
      ``poll_interval`` if a future version of this app wants live
      polling; not wired up yet.
    - Parsing is done with BeautifulSoup against the page's own
      "Parameter" row labels (e.g. "Wind Speed", "Wind Direction"),
      not against column position or CSS classes -- more robust to
      the page's own styling changes than position-based scraping.
    - This class has not yet been exercised against a live network
      call from inside this sandbox (outbound access to
      saltonsea.jpl.nasa.gov is blocked here); it was written against
      the exact table captured via a hand fetch of the real page on
      2026-08-05, and there is an offline parser test using a saved
      copy of that table's HTML in
      ``scripts/manual_checks/check_jpl_buoy_source.py``. Confirm with
      a real run (``dsl run``) once this office is exercised somewhere
      with real network access.
"""

from datetime import datetime, timezone
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = "https://saltonsea.jpl.nasa.gov/get_met_weather"

# Page's own "Parameter" column labels -> our output keys.
# Rows not listed here are ignored (there are several housekeeping /
# diagnostic rows on the page -- extraction window bookkeeping, RTD
# temp, power supply voltage -- not relevant to a wind/odor dashboard).
_NUMERIC_PARAM_MAP = {
    "Wind Speed": "wind_speed_ms",
    "Wind Direction": "wind_direction_deg",
    "Air Temperature": "air_temp_c",
    "Relative Humidity": "relative_humidity_pct",
    "Pressure": "pressure_mbar",
}
_STRING_PARAM_MAP = {
    "Last Update Date (UTC)": "_last_update_date",
    "Last Update Time (UTC)": "_last_update_time",
    "Meterological Download State": "download_state",
}

_BUOY_NAMES = ["SS1", "SS1A"]


class JPLSaltonSeaBuoySource:
    """
    Fetches https://saltonsea.jpl.nasa.gov/get_met_weather and yields
    the two buoys' (SS1, SS1A) current wind/met readings as a single
    dict, then stops.

    Args:
        url:     Page to fetch. Default is JPL's live Salton Sea page;
                 override in tests with a local file:// URL or by
                 monkeypatching ``_fetch_html``.
        timeout: Request timeout in seconds.

    Example:
        >>> buoy = JPLSaltonSeaBuoySource()
        >>> source = Source(fn=buoy.run, name="salton_wind")
    """

    def __init__(self, url: str = DEFAULT_URL, timeout: float = 15.0):
        self.url = url
        self.timeout = timeout

    def _fetch_html(self) -> str:
        resp = requests.get(
            self.url,
            timeout=self.timeout,
            headers={"User-Agent": "Mozilla/5.0 (DisSysLab salton_sea_dashboard)"},
        )
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _parse_min_avg_max(text: str) -> Optional[Dict[str, float]]:
        text = text.strip()
        parts = text.split(":")
        if len(parts) != 3:
            return None
        try:
            lo, avg, hi = (float(p) for p in parts)
        except ValueError:
            return None
        if lo == -99.0 and avg == -99.0 and hi == -99.0:
            return None  # JPL's own "no data" sentinel
        return {"min": lo, "avg": avg, "max": hi}

    def _parse(self, html: str) -> Dict[str, Dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = None
        for candidate in soup.find_all("table"):
            header_text = candidate.get_text()
            if "SS1" in header_text and "Parameter" in header_text:
                table = candidate
                break
        if table is None:
            raise ValueError("could not find the SS1/SS1A parameter table on the page")

        buoys: Dict[str, Dict] = {name: {} for name in _BUOY_NAMES}

        for row in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            cells = [c for c in cells if c != ""]
            if len(cells) < 3:
                continue
            label = cells[0]
            values = cells[1:]  # one per buoy, in _BUOY_NAMES order (+ maybe a units cell)
            # The page's header/units rows repeat "Parameter"/"Units"; skip those.
            if label in ("Parameter", "Units"):
                continue

            # Values list may have a leading "Units" cell in some rows;
            # take the last len(_BUOY_NAMES) entries, which are always
            # the per-buoy values regardless of whether a units cell
            # preceded them.
            if len(values) < len(_BUOY_NAMES):
                continue
            per_buoy_values = values[-len(_BUOY_NAMES):]

            if label in _NUMERIC_PARAM_MAP:
                key = _NUMERIC_PARAM_MAP[label]
                for name, raw in zip(_BUOY_NAMES, per_buoy_values):
                    parsed = self._parse_min_avg_max(raw)
                    if parsed is not None:
                        buoys[name][key] = parsed
            elif label in _STRING_PARAM_MAP:
                key = _STRING_PARAM_MAP[label]
                for name, raw in zip(_BUOY_NAMES, per_buoy_values):
                    buoys[name][key] = raw

        for name in _BUOY_NAMES:
            date_part = buoys[name].pop("_last_update_date", None)
            time_part = buoys[name].pop("_last_update_time", None)
            if date_part and time_part:
                buoys[name]["last_update_utc"] = f"{date_part}T{time_part}"

        return buoys

    def run(self):
        """
        One-shot generator: fetch the page, parse both buoys' current
        readings, yield a single dict, then stop. Never raises -- a
        fetch/parse failure lands in ``errors`` instead.
        """
        errors: Dict[str, str] = {}
        buoys: Dict[str, Dict] = {}
        try:
            html = self._fetch_html()
            buoys = self._parse(html)
        except Exception as exc:  # noqa: BLE001 -- isolate fetch/parse failures
            errors["fetch"] = str(exc)

        yield {
            "wind": {
                "type":         "salton_sea_buoy_wind",
                "source_url":   self.url,
                "quality_note": (
                    "raw data, not quality-checked -- informational only "
                    "(NASA/JPL's own caveat on this page)"
                ),
                "buoys":        buoys,
                "errors":       errors,
                "timestamp":    datetime.now(timezone.utc).isoformat(),
            }
        }
