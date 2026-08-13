# salton_sea_dashboard

Initial demo for Professor Sinclair's Salton Sea H2S / wind monitoring
request. Merges two sources into one snapshot: real, live wind data
from NASA/JPL's Salton Sea buoys, and placeholder H2S readings for the
four CARB sites Professor Sinclair named.

## Run it

```
dsl build .
dsl run .          # prints one merged snapshot to the console
python3 make_dashboard.py   # writes dashboard.html
```

This is an on-demand snapshot, not a continuous poller — run it again
whenever you want a fresh reading.

## What's real and what isn't

- **Wind (NASA/JPL buoys SS1, SS1A): real, live.** Confirmed working
  2026-08-05 against the actual page
  (`https://saltonsea.jpl.nasa.gov/get_met_weather`).
- **H2S (CARB sites): synthetic placeholder, not real data.** CARB's
  own download tool (AQMIS2) works and the `H2S` parameter code is
  confirmed correct, but the site codes Professor Sinclair gave
  (Salton Sea Park 33602, Torres-Martinez 33601, Mecca-Saul Martinez
  33033, Niland English 13997) don't resolve to any data through
  AQMIS2's `site=` query parameter — even for old, settled dates,
  which points at an id-namespace mismatch rather than a real gap.
  Every synthetic H2S message is stamped `"synthetic": True` so it's
  never mistaken for a real reading.

## Next step to make this real

Resolve the CARB site-id mapping — either by clicking through AQMIS2's
own site picker (`arb.ca.gov/aqmis2/aqdselect.php`) with a live
browser, or by asking Professor Sinclair for the site id he's used
when downloading this data before. Once resolved, swap
`synthetic_salton_h2s` for a real CARB-backed source in `office.md` —
both sources nest their payload under one key (`"wind"` / `"h2s"`)
specifically so this swap requires no changes to `JOIN` or
`DASHBOARD`.

## Files

- `office.md` — the office definition.
- `roles/dashboard_formatter.py` — combines the merged wind+H2S
  snapshot into one display-ready dict.
- `make_dashboard.py` — runs the same sources/formatter directly to
  produce `dashboard.html`.
- Sources live in `dissyslab/components/sources/`:
  `jpl_saltonsea_buoy_source.py`, `synthetic_salton_h2s_source.py`.
