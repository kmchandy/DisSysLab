# dissyslab/gallery/apps/salton_sea_dashboard/roles/dashboard_formatter.py

"""
DASHBOARD -- combines JOIN's merged wind + H2S snapshot into one
display-ready dict for console_printer (and for make_dashboard.py's
HTML report, which calls this same function directly on the same
inputs).

Input message shape (JOIN's merged output -- see
``jpl_saltonsea_buoy_source.py`` and
``synthetic_salton_h2s_source.py``'s docstrings for why each source
nests its payload under its own key, which is what makes this merge
collision-free):
    {
        "wind": {"type": "salton_sea_buoy_wind", "buoys": {...}, ...},
        "h2s":  {"type": "salton_h2s", "synthetic": True, "sites": {...}, ...},
    }

Output message shape:
    {
        "type":         "salton_sea_dashboard",
        "generated_at": "2026-08-05T09:31:00+00:00",
        "buoys": {
            "SS1":  {"wind_speed_ms_avg": 6.7, "wind_direction_deg_avg": 111.0,
                      "last_update_utc": "2026-07-29T05:12:21"},
            "SS1A": {...},
        },
        "sites": {
            "salton_sea_park": {
                "arb_code": "33602", "h2s_ppb": 8.4, "wind_speed_mph": 6.1,
                "wind_direction_deg": None, "elevated": False, "synthetic": True,
            },
            ...
        },
        "data_quality_notes": [
            "wind: raw data, not quality-checked -- informational only (NASA/JPL)",
            "h2s: SYNTHETIC placeholder data -- CARB site-id mapping unresolved, see synthetic_salton_h2s_source.py",
        ],
        "errors": {"wind": {}, "h2s": {}},
    }

``elevated`` is a purely illustrative threshold (``h2s_ppb > 25``) for
this demo, not a real regulatory comparison -- meaningless anyway
while the H2S values themselves are synthetic. Swap in a real
regulatory threshold once the real CARB source is wired in.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from dissyslab.blocks.role import Role
from dissyslab.office.library import AgentRoleEntry

_ELEVATED_H2S_PPB = 25.0  # illustrative only -- not a real regulatory limit


def make_dashboard_formatter():
    def dashboard_formatter(msg: Dict[str, Any]):
        """Worker body: (message) -> [(message, outport_name), ...]."""
        wind = msg.get("wind", {}) or {}
        h2s = msg.get("h2s", {}) or {}

        buoys_out: Dict[str, Dict] = {}
        for name, reading in (wind.get("buoys") or {}).items():
            speed = reading.get("wind_speed_ms", {})
            direction = reading.get("wind_direction_deg", {})
            buoys_out[name] = {
                "wind_speed_ms_avg": speed.get("avg"),
                "wind_direction_deg_avg": direction.get("avg"),
                "last_update_utc": reading.get("last_update_utc"),
            }

        sites_out: Dict[str, Dict] = {}
        for name, reading in (h2s.get("sites") or {}).items():
            h2s_ppb = reading.get("h2s_ppb")
            sites_out[name] = {
                **reading,
                "elevated": bool(h2s_ppb is not None and h2s_ppb > _ELEVATED_H2S_PPB),
                "synthetic": bool(h2s.get("synthetic")),
            }

        out_msg = {
            "type": "salton_sea_dashboard",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "buoys": buoys_out,
            "sites": sites_out,
            "data_quality_notes": [
                f"wind: {wind.get('quality_note', 'no quality note provided')}",
                (
                    "h2s: SYNTHETIC placeholder data -- CARB site-id mapping "
                    "unresolved, see synthetic_salton_h2s_source.py"
                    if h2s.get("synthetic")
                    else "h2s: real CARB data"
                ),
            ],
            "errors": {
                "wind": wind.get("errors", {}),
                "h2s": h2s.get("errors", {}),
            },
        }
        return [(out_msg, "out")]

    return dashboard_formatter


# ── Role registration (this office's roles/ dir; see library.py) ───────

role = AgentRoleEntry(
    name="dashboard_formatter",
    in_ports=("in_",),
    out_ports=("out",),
    factory=lambda: Role(fn=make_dashboard_formatter(), statuses=["out"]),
)
