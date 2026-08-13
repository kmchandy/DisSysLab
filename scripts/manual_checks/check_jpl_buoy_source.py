# scripts/manual_checks/check_jpl_buoy_source.py

"""
Manual, offline check for JPLSaltonSeaBuoySource's HTML parser.

Not a pytest test -- deliberately lives outside tests/ (see
check_stock_history_source.py's header for why: pytest auto-collecting
and executing manual, no-assertion scripts against real network
endpoints previously broke CI). This script does no network call --
it feeds a canned copy of the real page's table (captured by hand from
https://saltonsea.jpl.nasa.gov/get_met_weather on 2026-08-05) straight
into the parser, so it can be run any time, including from inside a
sandbox with no outbound access to saltonsea.jpl.nasa.gov.

Usage:
    python3 scripts/manual_checks/check_jpl_buoy_source.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dissyslab.components.sources.jpl_saltonsea_buoy_source import (
    JPLSaltonSeaBuoySource,
)

# A trimmed-but-structurally-faithful copy of the real table (same row
# labels, same "min:avg:max" value shape, same two-buoy column order)
# captured from the live page on 2026-08-05.
SAMPLE_HTML = """
<html><body>
<table>
<tr><th>Parameter</th><th>Units</th><th>SS1</th><th>SS1A</th></tr>
<tr><td>Last Update Date (UTC)</td><td>YYYY-MM-DD</td><td>2026-07-29</td><td>2026-07-29</td></tr>
<tr><td>Last Update Time (UTC)</td><td>HH:MM:SS</td><td>05:12:21</td><td>05:12:21</td></tr>
<tr><td>Meterological Download State</td><td>Condition</td><td>STALE</td><td>STALE</td></tr>
<tr><td>Wind Speed</td><td>ms-1</td><td>5.8:6.7:7.4</td><td>5.1:6.0:6.6</td></tr>
<tr><td>Wind Direction</td><td>degrees</td><td>107:111:115</td><td>95:100:105</td></tr>
<tr><td>Air Temperature</td><td>&deg;C</td><td>38.9:39.2:39.4</td><td>39.2:40.0:40.4</td></tr>
<tr><td>Relative Humidity</td><td>%</td><td>38.8:42.2:44.7</td><td>39.5:42.9:46.3</td></tr>
<tr><td>Pressure</td><td>mBar</td><td>1008:1009:1009</td><td>1010:1010:1011</td></tr>
<tr><td>Net Radiation</td><td>Wm-2</td><td>-99.0:-99.0:-99.0</td><td>-99.0:-99.0:-99.0</td></tr>
</table>
</body></html>
"""


def main():
    src = JPLSaltonSeaBuoySource()
    buoys = src._parse(SAMPLE_HTML)

    checks = [
        ("SS1 present", "SS1" in buoys),
        ("SS1A present", "SS1A" in buoys),
        ("SS1 wind_speed_ms avg == 6.7", buoys["SS1"]["wind_speed_ms"]["avg"] == 6.7),
        ("SS1 wind_direction_deg avg == 111.0", buoys["SS1"]["wind_direction_deg"]["avg"] == 111.0),
        ("SS1A wind_speed_ms avg == 6.0", buoys["SS1A"]["wind_speed_ms"]["avg"] == 6.0),
        ("SS1A wind_direction_deg avg == 100.0", buoys["SS1A"]["wind_direction_deg"]["avg"] == 100.0),
        ("SS1 last_update_utc == 2026-07-29T05:12:21", buoys["SS1"]["last_update_utc"] == "2026-07-29T05:12:21"),
        ("SS1 download_state == STALE", buoys["SS1"]["download_state"] == "STALE"),
        ("Net Radiation (-99 sentinel) excluded from SS1", "net_radiation" not in buoys["SS1"] and "Net Radiation" not in buoys["SS1"]),
    ]

    all_passed = True
    for label, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {label}")
        all_passed = all_passed and passed

    print()
    print("Parsed SS1:", buoys["SS1"])
    print("Parsed SS1A:", buoys["SS1A"])
    print()
    print("ALL CHECKS PASSED" if all_passed else "SOME CHECKS FAILED")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
