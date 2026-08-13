# dissyslab/gallery/apps/salton_sea_dashboard/make_dashboard_pdf.py

"""
Generates `dashboard.pdf` -- a one-page PDF version of the dashboard,
suitable for emailing to Professor Sinclair.

This sandbox's own outbound network is blocked (same restriction that
affects GitHub/Stooq/PyPI elsewhere in this project), so
JPLSaltonSeaBuoySource.run() can't make its live HTTP call from here.
To avoid sending Professor Sinclair a report with an empty wind table,
this script uses a real reading fetched by hand (via a tool with
broader network access than this sandbox) at the timestamp recorded
below, instead of calling the source's own (blocked-here) run().

On any machine with normal internet access, prefer wiring
JPLSaltonSeaBuoySource.run() into this script directly (the way
make_dashboard.py already does for the HTML version) -- the hand-fetch
below is a one-time workaround for producing this particular PDF from
inside this sandbox, not the intended long-term path.

Usage:
    python3 make_dashboard_pdf.py
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "roles"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem,
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

# Real reading, hand-fetched from https://saltonsea.jpl.nasa.gov/get_met_weather
# on 2026-08-05 (page reported "FRESH", last update 2026-08-05T09:10:47 UTC).
# Same message shape JPLSaltonSeaBuoySource.run() would yield -- see that
# file's docstring.
_REAL_WIND_MSG = {
    "wind": {
        "type": "salton_sea_buoy_wind",
        "source_url": "https://saltonsea.jpl.nasa.gov/get_met_weather",
        "quality_note": (
            "raw data, not quality-checked -- informational only "
            "(NASA/JPL's own caveat on this page)"
        ),
        "buoys": {
            "SS1": {
                "wind_speed_ms": {"min": 2.9, "avg": 5.9, "max": 8.3},
                "wind_direction_deg": {"min": 90.0, "avg": 103.0, "max": 122.0},
                "air_temp_c": {"min": 32.7, "avg": 33.2, "max": 33.7},
                "relative_humidity_pct": {"min": 49.3, "avg": 53.0, "max": 57.1},
                "pressure_mbar": {"min": 1012.0, "avg": 1013.0, "max": 1013.0},
                "last_update_utc": "2026-08-05T09:10:47",
                "download_state": "FRESH",
            },
            "SS1A": {
                "wind_speed_ms": {"min": 3.4, "avg": 5.4, "max": 8.1},
                "wind_direction_deg": {"min": 81.0, "avg": 93.0, "max": 118.0},
                "air_temp_c": {"min": 33.3, "avg": 34.0, "max": 34.5},
                "relative_humidity_pct": {"min": 49.5, "avg": 53.2, "max": 57.5},
                "pressure_mbar": {"min": 1014.0, "avg": 1014.0, "max": 1014.0},
                "last_update_utc": "2026-08-05T09:10:47",
                "download_state": "FRESH",
            },
        },
        "errors": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
}


def run_pipeline():
    h2s_src = SyntheticSaltonH2SSource()
    h2s_msg = next(h2s_src.run())
    merged = {**_REAL_WIND_MSG, **h2s_msg}
    formatter = make_dashboard_formatter()
    [(dash_msg, _)] = formatter(merged)
    return dash_msg


def num(x, digits=1):
    return f"{x:.{digits}f}" if x is not None else "n/a"


def build_pdf(dash_msg, out_path):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleBig", parent=styles["Title"], fontSize=18, spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], fontSize=10, textColor=colors.grey,
        spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6,
    )
    banner_style = ParagraphStyle(
        "Banner", parent=styles["Normal"], fontSize=9.5, backColor=colors.HexColor("#fff6e0"),
        borderColor=colors.HexColor("#e8cf8a"), borderWidth=1, borderPadding=8,
        leading=13,
    )
    caveat_style = ParagraphStyle("Caveat", parent=styles["Normal"], fontSize=9, leading=12)
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story = []
    story.append(Paragraph("Salton Sea Wind &amp; H2S Dashboard", title_style))
    story.append(Paragraph(
        f"NASA/JPL buoy wind &middot; CARB H2S monitoring sites &middot; generated {run_date}",
        subtitle_style,
    ))

    story.append(Paragraph(
        "<b>This is an initial demo, not a finished monitoring tool.</b> "
        "Wind data (below) is real, from NASA/JPL's two Salton Sea buoys "
        "(fetched 2026-08-05). H2S data is <b>synthetic placeholder data</b> "
        "-- the real CARB monitoring-site data isn't wired in yet (site-id "
        "mapping unresolved). Treat every H2S number below as a stand-in "
        "for layout/plumbing purposes only.",
        banner_style,
    ))

    story.append(Paragraph("Wind &mdash; NASA/JPL Buoys (real)", h2_style))
    wind_header = ["Buoy", "Wind Speed (m/s, avg)", "Wind Direction (deg, avg)", "Last Update (UTC)"]
    wind_rows = [wind_header]
    for name in ("SS1", "SS1A"):
        b = dash_msg["buoys"].get(name, {})
        wind_rows.append([
            name,
            num(b.get("wind_speed_ms_avg")),
            num(b.get("wind_direction_deg_avg"), 0),
            str(b.get("last_update_utc") or "n/a"),
        ])
    wind_table = Table(wind_rows, hAlign="LEFT", colWidths=[0.9 * inch, 1.7 * inch, 1.9 * inch, 1.9 * inch])
    wind_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(wind_table)

    story.append(Paragraph("Hydrogen Sulfide &mdash; CARB Sites (SYNTHETIC placeholder)", h2_style))
    h2s_header = ["Site", "H2S (ppb)", "Wind Speed (mph)", "Wind Direction (deg)"]
    h2s_rows = [h2s_header]
    elevated_row_indices = []
    for i, (name, label) in enumerate(SITE_LABELS.items(), start=1):
        s = dash_msg["sites"].get(name, {})
        if s.get("elevated"):
            elevated_row_indices.append(i)
        wind_speed = s.get("wind_speed_mph")
        wind_dir = s.get("wind_direction_deg")
        h2s_rows.append([
            label,
            num(s.get("h2s_ppb")),
            num(wind_speed) if wind_speed is not None else "n/a",
            num(wind_dir, 0) if wind_dir is not None else "n/a",
        ])
    h2s_table = Table(h2s_rows, hAlign="LEFT", colWidths=[2.3 * inch, 1.1 * inch, 1.5 * inch, 1.5 * inch])
    h2s_style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_idx in elevated_row_indices:
        h2s_style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#fdeaea")))
    h2s_table.setStyle(TableStyle(h2s_style_cmds))
    story.append(h2s_table)
    story.append(Paragraph(
        "Rows shaded red exceed this demo's illustrative threshold (25 ppb) "
        "-- not a real regulatory comparison. \"n/a\" wind direction means "
        "that CARB site doesn't report it (Salton Sea Park, Torres-Martinez, "
        "Niland English); the JPL buoy table above is the stand-in for "
        "direction at those sites until a better match is found.",
        caveat_style,
    ))

    story.append(Paragraph("Data quality notes", h2_style))
    notes = dash_msg.get("data_quality_notes", [])
    story.append(ListFlowable(
        [ListItem(Paragraph(n, caveat_style)) for n in notes],
        bulletType="bullet",
    ))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Generated by make_dashboard_pdf.py &middot; DisSysLab salton_sea_dashboard",
        footer_style,
    ))

    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    doc.build(story)


if __name__ == "__main__":
    dash_msg = run_pipeline()
    out_path = os.path.join(os.path.dirname(__file__), "dashboard.pdf")
    build_pdf(dash_msg, out_path)
    print(f"Wrote {out_path}")
