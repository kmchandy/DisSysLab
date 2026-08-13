# dissyslab/components/sources/synthetic_salton_h2s_source.py

"""
SyntheticSaltonH2SSource: generates fake-but-plausible hydrogen-sulfide
(H2S) and wind readings for the four CARB monitoring sites Professor
Sinclair named near the Salton Sea, with no network call at all.

Why this exists
================

The real H2S data lives in CARB's AQMIS2 system
(``arb.ca.gov/aqmis2/``), which does have a working, confirmed download
tool (``display.php`` / ``pickdownload.php``, parameterized by
``site=``, ``param=H2S``, date -- the ``H2S`` parameter code itself is
confirmed correct, see this class's sibling comment in
``docs/SOURCES_AND_SINKS.md``). What's *not* yet confirmed is the
mapping from the site codes Professor Sinclair gave (Salton Sea Park
33602, Torres-Martinez 33601, Mecca-Saul Martinez 33033, Niland
English 13997 -- these read like CARB's public "ARB site codes" from
the interactive map) to whatever internal ``site=`` id AQMIS2's
download tool actually expects: querying with these codes directly
returns "No Data Available" even for well-established past dates,
which points at an id-namespace mismatch rather than a genuine data
gap. Resolving that needs either a live browser walkthrough of
AQMIS2's own site picker, or the site id Professor Sinclair may
already have from downloading this data before.

Rather than block the whole ``salton_sea_dashboard`` demo on that
unknown, this class produces synthetic readings for the same four
named sites, in a message shape a real CARB-backed source can drop in
to replace with zero downstream changes. Swap this out the moment the
real site ids are confirmed.

**This is not real monitoring data.** Every message is stamped
``"synthetic": True`` for exactly that reason -- so it is never
mistaken for a real odor reading downstream or in a report. Values are
a plausible background H2S level per site with a low-probability
occasional spike (mimicking a real odor event), not any actual
measurement or model of Salton Sea emissions.

Message shape. Note everything is nested under one top-level key,
``"h2s"`` -- deliberately, matching ``JPLSaltonSeaBuoySource``'s
``"wind"`` nesting, so the two sources merge cleanly through
DisSysLab's generic ``synchronizer`` role with no key collision:
    {
        "h2s": {
            "type":      "salton_h2s",
            "synthetic": True,
            "sites": {
                "salton_sea_park": {
                    "arb_code":           "33602",
                    "h2s_ppb":            8.4,
                    "wind_speed_mph":     6.1,
                    "wind_direction_deg": None,
                },
                "torres_martinez":  {...},   # also no wind_direction_deg
                "mecca_saul_martinez": {...},   # has wind_direction_deg
                "niland_english":  {
                    "arb_code": "13997", "h2s_ppb": ..., "wind_speed_mph": None,
                    "wind_direction_deg": None,
                },
            },
            "timestamp": "2026-08-05T09:31:00+00:00",
        }
    }

Sensor coverage per site (matches what Professor Sinclair described --
Niland English's wind instrumentation is simply unconfirmed, not
assumed absent, hence ``None`` rather than a fabricated number):
    - salton_sea_park:      H2S, wind speed            (no direction)
    - torres_martinez:      H2S, wind speed            (no direction)
    - mecca_saul_martinez:  H2S, wind speed, direction
    - niland_english:       H2S only

Usage:
    from dissyslab.components.sources.synthetic_salton_h2s_source import (
        SyntheticSaltonH2SSource,
    )
    from dissyslab.blocks import Source

    fake_h2s = SyntheticSaltonH2SSource(seed=42)
    source = Source(fn=fake_h2s.run, name="salton_h2s")

Design notes:
    - One-shot generator (yields once, then stops) -- matches
      ``JPLSaltonSeaBuoySource``'s "regenerate on each run" shape for
      this on-demand dashboard, and the ``SyntheticStockHistorySource``
      convention this class is deliberately modeled on.
    - ``seed`` makes a run reproducible (same seed -> identical
      output); leave ``seed=None`` for a fresh random reading each run.
    - Background H2S level and spike probability/magnitude are rough,
      order-of-magnitude-plausible guesses (ambient background
      generally low single-digit to teens ppb, occasional odor-event
      spikes into the tens-to-100+ ppb range near the Sea) -- not
      calibrated to any real distribution. Good enough to exercise
      dashboard plumbing and layout; not for any actual air-quality
      conclusion.
"""

import random
from datetime import datetime, timezone
from typing import Dict, Optional

# name -> (arb_code, has_wind_speed, has_wind_direction, background_h2s_ppb)
_SITES = {
    "salton_sea_park":     ("33602", True,  False, 10.0),
    "torres_martinez":     ("33601", True,  False, 6.0),
    "mecca_saul_martinez": ("33033", True,  True,  4.0),
    "niland_english":      ("13997", False, False, 3.0),
}


class SyntheticSaltonH2SSource:
    """
    Generates one synthetic H2S(+wind) reading per named Salton Sea
    CARB site and yields them as a single dict, then stops.

    Args:
        spike_probability: Chance any one site shows an odor-event
                            spike this run. Default 0.15.
        seed:               Optional int for reproducible output.
    """

    def __init__(self, spike_probability: float = 0.15, seed: Optional[int] = None):
        self.spike_probability = spike_probability
        self._rng = random.Random(seed)

    def run(self):
        """
        One-shot generator: produce one synthetic reading per site,
        yield a single dict, then stop.
        """
        sites: Dict[str, Dict] = {}
        for name, (arb_code, has_speed, has_dir, background) in _SITES.items():
            is_spike = self._rng.random() < self.spike_probability
            h2s_ppb = (
                round(background + self._rng.uniform(30, 120), 1)
                if is_spike
                else round(max(0.0, background + self._rng.uniform(-2, 3)), 1)
            )
            sites[name] = {
                "arb_code": arb_code,
                "h2s_ppb": h2s_ppb,
                "wind_speed_mph": (
                    round(self._rng.uniform(1, 15), 1) if has_speed else None
                ),
                "wind_direction_deg": (
                    round(self._rng.uniform(0, 360), 0) if has_dir else None
                ),
            }

        yield {
            "h2s": {
                "type":      "salton_h2s",
                "synthetic": True,
                "sites":     sites,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
