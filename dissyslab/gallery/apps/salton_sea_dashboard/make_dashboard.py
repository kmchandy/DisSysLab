# dissyslab/gallery/apps/salton_sea_dashboard/make_dashboard.py

"""
Generates `dashboard.html` -- a readable summary of one snapshot from
the salton_sea_dashboard office, for Professor Sinclair.

Runs the same source classes and formatter function the real office
runs (salton_wind + synthetic_salton_h2s -> JOIN -> DASHBOARD), so this
report's numbers are exactly what `dsl run` on this office produces --
not a separate, re-transcribed copy of them.

Usage:
    python3 make_dashboard.py
"""

import html
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "roles"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

from dissyslab.components.sources.jpl_saltonsea_buoy_source import (
    JPLSaltonSeaBuoySource,
)
from dissyslab.components.sources.synthetic_salton_h2s_source import (
    SyntheticSaltonH2SSource,
)
from dashboard_formatter import make_dashboard_formatter

SITE_LABELS = {
    "salton_sea_park": "Salton Sea Park (33602)",
    "torres_martinez": "Torres-Martinez (33601)",
    "mecca_saul_martinez": "Mecca -- Saul Martinez (33033)",
    "niland_english": "Niland English (13997)",
}


def run_pipeline():
    wind_src = JPLSaltonSeaBuoySource()
    h2s_src = SyntheticSaltonH2SSource()

    wind_msg = next(wind_src.run())
    h2s_msg = next(h2s_src.run())

    merged = {**wind_msg, **h2s_msg}  # {"wind": {...}, "h2s": {...}} -- no key collision

    formatter = make_dashboard_formatter()
    [(dash_msg, _)] = formatter(merged)
    return dash_msg


def num(x, digits=1):
    return f"{x:.{digits}f}" if x is not None else "n/a"


def buoy_rows_html(dash_msg):
    rows = []
    for name in ("SS1", "SS1A"):
        b = dash_msg["buoys"].get(name)
        if not b:
            rows.append(f"<tr><td>{name}</td><td colspan='3'>no data</td></tr>")
            continue
        rows.append(f"""
        <tr>
          <td>{name}</td>
          <td>{num(b.get('wind_speed_ms_avg'))}</td>
          <td>{num(b.get('wind_direction_deg_avg'), 0)}</td>
          <td>{html.escape(str(b.get('last_update_utc') or 'n/a'))}</td>
        </tr>""")
    return "".join(rows)


def site_rows_html(dash_msg):
    rows = []
    for name, label in SITE_LABELS.items():
        s = dash_msg["sites"].get(name)
        if not s:
            continue
        css = ' class="elevated-row"' if s.get("elevated") else ""
        wind_speed = s.get("wind_speed_mph")
        wind_dir = s.get("wind_direction_deg")
        rows.append(f"""
        <tr{css}>
          <td>{html.escape(label)}</td>
          <td>{num(s.get('h2s_ppb'))}</td>
          <td>{num(wind_speed) if wind_speed is not None else "n/a"}</td>
          <td>{num(wind_dir, 0) if wind_dir is not None else "n/a"}</td>
        </tr>""")
    return "".join(rows)


def build_html(dash_msg):
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Salton Sea Wind &amp; H2S Dashboard</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; max-width: 900px;
         margin: 40px auto; padding: 0 20px; color: #1a1a1a; line-height: 1.5; }}
  h1 {{ font-size: 26px; margin-bottom: 4px; }}
  .subtitle {{ color: #555; font-size: 15px; margin-top: 0; }}
  .banner {{ background: #fff6e0; border: 1px solid #e8cf8a; border-radius: 8px;
             padding: 14px 18px; margin: 20px 0; font-size: 14px; }}
  .banner strong {{ color: #8a5a00; }}
  h2 {{ border-bottom: 2px solid #eee; padding-bottom: 6px; margin-top: 36px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px 0; font-size: 13.5px; }}
  th, td {{ border: 1px solid #ddd; padding: 7px 9px; text-align: right; }}
  th {{ background: #f5f5f5; text-align: right; }}
  td:first-child, th:first-child {{ text-align: left; }}
  tr.elevated-row {{ background: #fdeaea; font-weight: 600; }}
  .caveats {{ font-size: 13.5px; color: #444; }}
  .caveats li {{ margin-bottom: 8px; }}
  footer {{ margin-top: 40px; font-size: 12px; color: #999; }}
</style>
</head>
<body>

<h1>Salton Sea Wind &amp; H2S Dashboard</h1>
<p class="subtitle">NASA/JPL buoy wind &middot; CARB H2S monitoring sites &middot; generated {run_date}</p>

<div class="banner">
  <strong>This is an initial demo, not a finished monitoring tool.</strong>
  Wind data (below) is real and live, from NASA/JPL's two Salton Sea
  buoys. H2S data is <strong>synthetic placeholder data</strong> -- the
  real CARB monitoring-site data isn't wired in yet (site-id mapping
  unresolved, see the office's README). Treat every H2S number below
  as a stand-in for layout/plumbing purposes only.
</div>

<h2>Wind -- NASA/JPL Buoys (real, live)</h2>
<table>
  <thead>
    <tr><th>Buoy</th><th>Wind Speed (m/s, avg)</th><th>Wind Direction (&deg;, avg)</th><th>Last Update (UTC)</th></tr>
  </thead>
  <tbody>{buoy_rows_html(dash_msg)}</tbody>
</table>

<h2>Hydrogen Sulfide -- CARB Sites (SYNTHETIC placeholder)</h2>
<table>
  <thead>
    <tr><th>Site</th><th>H2S (ppb)</th><th>Wind Speed (mph)</th><th>Wind Direction (&deg;)</th></tr>
  </thead>
  <tbody>{site_rows_html(dash_msg)}</tbody>
</table>
<p class="caveats">Rows shaded red exceed this demo's illustrative
threshold (25 ppb) -- not a real regulatory comparison. "n/a" wind
direction means that CARB site doesn't report it (Salton Sea Park,
Torres-Martinez, Niland English); the JPL buoy table above is the
stand-in for direction at those sites until a better match is found.</p>

<h2>Data quality notes</h2>
<ul class="caveats">
{"".join(f"<li>{html.escape(n)}</li>" for n in dash_msg.get("data_quality_notes", []))}
</ul>

<footer>Generated by make_dashboard.py &middot; DisSysLab salton_sea_dashboard</footer>
</body>
</html>
"""


if __name__ == "__main__":
    dash_msg = run_pipeline()
    out_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build_html(dash_msg))
    print(f"Wrote {out_path}")
    print(f"Wind errors: {dash_msg['errors']['wind']}")
    print(f"H2S errors: {dash_msg['errors']['h2s']}")
