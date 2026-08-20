# Office: salton_sea_dashboard

# Initial demo for Professor Sinclair's Salton Sea H2S / wind
# monitoring request (see the project notes and the
# conversation this app came out of). Two sources feed one merged
# snapshot:
#
#   - `salton_wind`: NASA/JPL's two moored buoys (SS1, SS1A) --
#     REAL, live wind speed/direction (confirmed working 2026-08-05).
#   - `synthetic_salton_h2s`: the four CARB sites Sinclair named
#     (Salton Sea Park 33602, Torres-Martinez 33601, Mecca-Saul
#     Martinez 33033, Niland English 13997) -- SYNTHETIC for now.
#     The real CARB AQMIS2 download tool works and the H2S parameter
#     code is confirmed, but the site-id mapping for these four codes
#     isn't resolved yet (queries return "No Data Available" even for
#     old, settled dates -- looks like an id-namespace mismatch, not a
#     real data gap). See synthetic_salton_h2s_source.py's docstring.
#
# Swap `synthetic_salton_h2s` for a real CARB-backed source once the
# site ids are confirmed -- both sources nest their payload under one
# key ("wind" / "h2s") specifically so JOIN's merge and DASHBOARD's
# formatting don't need to change either.
#
# This is an on-demand snapshot office, not a continuous poller:
# run it again (`dsl run`) whenever you want a fresh reading.

Sources: salton_wind, synthetic_salton_h2s
Sinks: console_printer

Agents:
JOIN is a synchronizer(inports=['wind', 'h2s']).
DASHBOARD is a dashboard_formatter.

Connections:
salton_wind's out is JOIN's wind.
synthetic_salton_h2s's out is JOIN's h2s.
JOIN's out is DASHBOARD.
DASHBOARD's out is console_printer.
